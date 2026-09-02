"""
vlm/vlm_utils.py
────────────────────────────────────────────────────────────────
封装所有与 Qwen VLM 的通信逻辑，对外只暴露两个函数：

  call_qwen_with_json(sys_prompt, image_path, context) -> dict
  call_qwen_text_only(sys_prompt, context)             -> dict

核心防御体系（两层 JSON 防御）：
  Layer 1 — 正则提取：从任意格式响应里抢救出 JSON 片段
  Layer 2 — 重试兜底：若 Layer 1 失败，重新发请求最多 MAX_RETRIES 次
  （格式约束由各阶段提示词末尾的"输出格式强制规定"负责）

图像处理（双向 Resize 保护）：
  - 上行：图片超过 MAX_PIXELS 时等比压缩，防止 OOM 崩溃
  - 下行：图片太小（低于 MIN_SIDE）时等比放大，防止 VLM 看不清
────────────────────────────────────────────────────────────────
"""

import re
import json
import base64
import logging
from io import BytesIO
from typing import Optional

import requests
from PIL import Image

# ──────────────────────────────────────────────
# 配置区：按需修改
# ──────────────────────────────────────────────
OLLAMA_BASE_URL  = "http://localhost:11434"
OLLAMA_API_URL   = f"{OLLAMA_BASE_URL}/api/chat"
MODEL_NAME       = "qwen3.5:9b"        # ollama pull qwen3.5:9b

MAX_RETRIES      = 3                      # JSON 解析失败时最多重试几次
REQUEST_TIMEOUT  = 240                    # 单次请求超时（秒）

# 双向 Resize 保护阈值
MAX_PIXELS       = 1344 * 1344           # 超过此像素数则压缩（~1.8MP）
MIN_SIDE         = 224                   # 短边低于此值则放大
MAX_SIDE         = 1344                  # 长边上限

# 阶段一循环保护：最多允许调用几次复原工具才强制结束
MAX_RESTORATION_CALLS = 5

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# 图像预处理：双向 Resize 保护
# ══════════════════════════════════════════════

def _resize_image_safe(image_path: str) -> str:
    """
    双向 Resize 保护：
      - 图片过大 → 等比缩小至 MAX_SIDE
      - 图片过小 → 等比放大至 MIN_SIDE
    返回 Base64 编码字符串（直接用于 API 调用）。
    不修改磁盘上的原始文件。
    """
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        raise IOError(f"无法打开图片 {image_path}: {e}")

    w, h = img.size
    short_side = min(w, h)
    long_side  = max(w, h)
    total_px   = w * h

    needs_resize = False

    # 向下保护：图片太大
    if total_px > MAX_PIXELS or long_side > MAX_SIDE:
        scale = min(MAX_SIDE / long_side, (MAX_PIXELS / total_px) ** 0.5)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.info(f"[Resize↓] {w}×{h} → {new_w}×{new_h} (原图 {total_px/1e6:.1f}MP)")
        needs_resize = True

    # 向上保护：图片太小
    elif short_side < MIN_SIDE:
        scale = MIN_SIDE / short_side
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.BICUBIC)
        logger.info(f"[Resize↑] {w}×{h} → {new_w}×{new_h}")
        needs_resize = True

    if not needs_resize:
        logger.debug(f"[Resize] 无需调整，原始尺寸 {w}×{h}")

    # 编码为 Base64
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64


# ══════════════════════════════════════════════
# 三层 JSON 防御体系
# ══════════════════════════════════════════════

def _extract_json_from_text(text: str) -> Optional[dict]:
    """
    Layer 2：正则抢救 JSON。
    按优先级依次尝试：
      1. 去掉 ```json ... ``` 代码块包裹后解析
      2. 直接找第一个 { ... } 最外层括号对解析
    """
    if not text:
        return None

    # 尝试 1：去掉 Markdown 代码块
    md_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    match = md_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试 2：贪婪匹配最外层 {}
    brace_pattern = re.compile(r"\{[\s\S]*\}", re.DOTALL)
    match = brace_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            # 尝试修复尾部截断（末尾缺 }）
            raw = match.group(0)
            for suffix in ["}", "}}"]:
                try:
                    return json.loads(raw + suffix)
                except json.JSONDecodeError:
                    continue

    return None


def _call_ollama_raw(messages: list) -> str:
    """
    最底层 HTTP 调用，返回原始文本字符串。
    统一处理网络错误，向上只抛 RuntimeError。
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,   # 低温度，输出更稳定，利于 JSON 格式
            "top_p": 0.9,
            "num_predict": 2000,  # 限制最大输出 token，防止模型失控胡乱生成
        }
    }
    try:
        resp = requests.post(OLLAMA_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"无法连接 Ollama 服务 ({OLLAMA_BASE_URL})。"
            "请确认 ollama serve 已运行，且端口 11434 未被占用。"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama 请求超时（>{REQUEST_TIMEOUT}s），图片可能过大或模型负载过高。")
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"Ollama 响应格式异常: {e} | 原始响应: {resp.text[:200]}")


def _parse_with_retry(messages: list, stage_name: str = "") -> dict:
    """
    两层防御 + 重试的完整流程：
      Layer 1 正则抢救：从任意格式响应里提取 JSON
      Layer 2 最多重试 MAX_RETRIES 次，失败后返回兜底结构
    """
    for attempt in range(1, MAX_RETRIES + 1):
        raw_text = _call_ollama_raw(messages)
        logger.debug(f"[{stage_name}] 第{attempt}次原始响应: {raw_text[:200]}")

        # 先尝试直接解析
        try:
            result = json.loads(raw_text.strip())
            logger.info(f"[{stage_name}] JSON 直接解析成功（第{attempt}次）")
            return result
        except json.JSONDecodeError:
            pass

        # Layer 2：正则抢救
        result = _extract_json_from_text(raw_text)
        if result is not None:
            logger.info(f"[{stage_name}] JSON 正则抢救成功（第{attempt}次）")
            return result

        # 本次失败，准备重试
        logger.warning(
            f"[{stage_name}] 第{attempt}/{MAX_RETRIES}次 JSON 解析失败，"
            f"原始响应片段: {raw_text[:100]!r}"
        )

        if attempt < MAX_RETRIES:
            # 把失败的回复加入对话，要求模型纠正格式
            messages = messages + [
                {"role": "assistant", "content": raw_text},
                {
                    "role": "user",
                    "content": (
                        "你的回复不是合法 JSON。请严格只输出 JSON 对象，"
                        "以 { 开头，以 } 结尾，不要任何额外文字或代码块标记。"
                    )
                }
            ]

    # Layer 3 彻底失败：返回保底结构，让状态机可以识别并处理
    logger.error(f"[{stage_name}] {MAX_RETRIES} 次重试全部失败，返回兜底结构。")
    return {
        "reasoning": "JSON 解析彻底失败，返回兜底结构",
        "tool_name": "error",
        "tool_arguments": {},
        "_raw_response": raw_text[:500]
    }


# ══════════════════════════════════════════════
# 对外公开接口
# ══════════════════════════════════════════════

def call_qwen_with_json(
    sys_prompt: str,
    image_path: Optional[str] = None,
    context: Optional[str] = None,
    stage_name: str = ""
) -> dict:
    """
    带图像（或纯文本）调用 Qwen VLM，返回解析好的 dict。

    参数：
      sys_prompt  — 角色人设提示词（来自 memory/*.txt）
      image_path  — 图片路径（None 则纯文本模式）
      context     — 额外文本上下文（如 BBox 列表、历史记录等）
      stage_name  — 日志标识，方便调试定位（如 "阶段一"）

    返回：
      dict，保证包含 "tool_name" 字段。
      若两层防御全部失败，tool_name == "error"。
    """
    # 构建文字部分
    text_parts = ["请分析并决定下一步操作。"]
    if context:
        text_parts.append(f"\n【上下文信息】\n{context}")
    text_content = "\n".join(text_parts)

    # Ollama 原生格式：content 为纯字符串，图片放顶层 images 列表
    user_message: dict = {"role": "user", "content": text_content}
    if image_path:
        b64_image = _resize_image_safe(image_path)
        user_message["images"] = [b64_image]

    messages = [
        {"role": "system", "content": sys_prompt.strip()},
        user_message,
    ]

    return _parse_with_retry(messages, stage_name=stage_name)


def call_qwen_text_only(
    sys_prompt: str,
    context: str,
    stage_name: str = ""
) -> dict:
    """
    纯文本模式（阶段二、四专用）。
    无图像，速度更快，token 消耗更少。
    """
    return call_qwen_with_json(
        sys_prompt=sys_prompt,
        image_path=None,
        context=context,
        stage_name=stage_name
    )


def call_raw_text(sys_prompt: str, context: str) -> str:
    """直接返回模型原始文本，不做任何 JSON 解析。"""
    text = f"请根据以下信息完成任务。\n\n【上下文信息】\n{context}"
    messages = [
        {"role": "system", "content": sys_prompt.strip()},
        {"role": "user",   "content": text},
    ]
    return _call_ollama_raw(messages).strip()