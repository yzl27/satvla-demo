"""
engine/state_machine.py
────────────────────────────────────────────────────────────────
五阶段智能体工作流主控循环。

阶段划分：
  ① 全局质检员  — 图像复原 + 目标检测，输出 Doc1_Global.json
  ② 战术指挥官  — BBox 排序，输出 Doc2_Queue.json
  ③ 局部特种兵  — 逐目标精细提取，输出 Doc3_Details.json
  ④ 情报提炼官  — 关键词提炼 + RAG 检索，输出 Doc4_Search.json
  ⑤ 首席报告官  — SOAP 报告生成，输出 FINAL_SOAP_REPORT.txt

容错体系：
  - 阶段一：复原工具调用次数上限保护（MAX_RESTORATION_CALLS）
  - 阶段一：VLM 幻觉 / 未知工具名 → 兜底 break
  - 阶段二：0 个目标 → 跳过二三四，直接注入提示进阶段五
  - 阶段二：目标 <3 → Task Stack 动态裁剪，不强制凑数
  - 阶段二：BBox 坐标越界 → max/min 自动修正
  - 阶段三：局部工具调用次数上限保护（MAX_LOCAL_CALLS）
  - 全局：VLM 返回 tool_name="error" → 记录并跳过当前阶段
────────────────────────────────────────────────────────────────
"""

import os
import json
import time
import logging
from typing import Optional

from vlm.vlm_utils import call_qwen_with_json, call_qwen_text_only, call_raw_text
from engine.tool_use import execute_tool

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 路径配置
# ──────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR    = os.path.join(BASE_DIR, "memory")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")

PROMPT_GLOBAL     = os.path.join(MEMORY_DIR, "prompt_global.txt")
PROMPT_COMMANDER  = os.path.join(MEMORY_DIR, "prompt_commander.txt")
PROMPT_SPECIALIST = os.path.join(MEMORY_DIR, "prompt_specialist.txt")
PROMPT_EXTRACTOR  = os.path.join(MEMORY_DIR, "prompt_extractor.txt")
PROMPT_REPORTER   = os.path.join(MEMORY_DIR, "prompt_reporter.txt")

# 安全上限
MAX_RESTORATION_CALLS = 5   # 阶段一：最多调用几次复原工具
MAX_LOCAL_CALLS       = 4   # 阶段三：每个 crop 最多调用几次局部工具


# ══════════════════════════════════════════════
# 档案管理工具函数
# ══════════════════════════════════════════════

def save_memory(doc_name: str, data: dict, task_id: str) -> None:
    """将阶段性成果存档为 JSON"""
    path = os.path.join(WORKSPACE_DIR, task_id, f"{doc_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[档案] 已保存 {doc_name}.json")


def load_memory(doc_name: str, task_id: str) -> dict:
    """读取阶段性成果，文件不存在时返回空 dict"""
    path = os.path.join(WORKSPACE_DIR, task_id, f"{doc_name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def read_prompt(prompt_path: str) -> str:
    """读取 memory/*.txt 提示词，文件缺失时返回警告字符串"""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    name = os.path.basename(prompt_path)
    logger.warning(f"[提示词] 缺失文件: {name}，将使用占位警告。")
    return f"【警告：缺失提示词文件 {name}，请在 memory/ 目录下创建它。】"


# ══════════════════════════════════════════════
# BBox 坐标越界修正（阶段二容错）
# ══════════════════════════════════════════════

def _clamp_bbox(bbox: dict, img_w: int, img_h: int) -> dict:
    """
    将 BBox 坐标强制裁剪在图像边界内。
    支持格式：{"x1": ..., "y1": ..., "x2": ..., "y2": ...}
    """
    return {
        **bbox,
        "x1": max(0, min(int(bbox.get("x1", 0)), img_w)),
        "y1": max(0, min(int(bbox.get("y1", 0)), img_h)),
        "x2": max(0, min(int(bbox.get("x2", img_w)), img_w)),
        "y2": max(0, min(int(bbox.get("y2", img_h)), img_h)),
    }


def _get_image_size(image_path: str) -> tuple[int, int]:
    """返回 (width, height)，读取失败时返回 (9999, 9999) 保证不误截断"""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return (9999, 9999)


# ══════════════════════════════════════════════
# 主工作流
# ══════════════════════════════════════════════

def run_agent_workflow(initial_image_path: str) -> str:
    """
    五阶段智能体工作流入口。

    参数：
      initial_image_path — 原始输入图片的绝对或相对路径

    返回：
      最终报告文件的绝对路径
    """

    # ── 初始化工作区 ──────────────────────────────
    task_id         = time.strftime("task_%Y%m%d_%H%M%S")
    task_workspace  = os.path.join(WORKSPACE_DIR, task_id)
    os.makedirs(task_workspace, exist_ok=True)

    # 图片已由 run.py 拷入工作区，直接使用传入路径
    current_image_path = initial_image_path
    logger.info(f"🚀 启动任务: {task_id} | 输入图: {current_image_path}")

    # ── 用于阶段五注入提示的全局 Flag ────────────────
    # 若阶段二检测到 0 目标，此字段非空，阶段五将据此调整报告模板
    no_target_hint: Optional[str] = None

    # ==========================================================
    # 🟢 阶段一：全局质检员
    # ==========================================================
    logger.info("\n" + "═"*50)
    logger.info("🟢 阶段一：全局质检与环境评估")
    logger.info("═"*50)

    sys_prompt_global = read_prompt(PROMPT_GLOBAL)
    restoration_count = 0      # 复原工具调用计数器（安全上限保护）
    detected_bboxes   = []     # 本阶段最终检测结果
    # 操作历史：记录每一步复原操作，下一轮拼入 context 防止重复调用
    restoration_history: list[str] = []
    # VLM 每轮观察的完整记录（caption + reasoning），全部保存进 Doc1
    vlm_observations_s1: list[dict] = []

    while True:
        # ── 检查安全上限 ──
        if restoration_count >= MAX_RESTORATION_CALLS:
            logger.warning(
                f"⚠️  复原工具已连续调用 {restoration_count} 次，"
                "强制触发 detect，防止无限循环。"
            )
            tool_name = "detect"
            tool_args = {"classes": ["目标"]}
        else:
            # 构建上下文：告知 VLM 已做过哪些复原，当前看到的是处理后的图
            remaining = MAX_RESTORATION_CALLS - restoration_count
            if restoration_history:
                history_str = "\n".join(restoration_history)
                context_str = (
                    f"【已完成的预处理步骤（请勿重复）】\n{history_str}\n\n"
                    f"你现在看到的图像是经过上述处理后的结果。"
                    f"剩余可用复原工具次数: {remaining} 次。"
                    f"{'若图像已足够清晰，请直接调用 detect。' if remaining <= 1 else ''}"
                )
            else:
                context_str = None  # 第一次观察，无需附加历史

            logger.info(f"🤖 [VLM·阶段一] 正在观察图像...")
            response  = call_qwen_with_json(
                sys_prompt  = sys_prompt_global,
                image_path  = current_image_path,
                context     = context_str,
                stage_name  = "阶段一"
            )
            tool_name = response.get("tool_name", "error")
            tool_args = response.get("tool_arguments", {})
            logger.info(f"🖼️  [VLM·描述] {response.get('image_caption', '(无)')}")
            logger.info(f"💭 [VLM·思考] {response.get('reasoning', '(无)')}")
            logger.info(f"🛠️  [VLM·决策] tool={tool_name}, args={tool_args}")
            vlm_observations_s1.append({
                "step"         : restoration_count + 1,
                "image_path"   : current_image_path,
                "image_caption": response.get("image_caption", ""),
                "reasoning"    : response.get("reasoning", ""),
                "tool_name"    : tool_name,
            })

        # ── 图像复原分支 ──────────────────────────────
        if tool_name in ("dehaze", "denoise", "derain", "deblur"):
            logger.info(f"⚙️  [工具] 执行图像复原: {tool_name}")
            tool_result = execute_tool(
                tool_name       = tool_name,
                tool_arguments  = {"image_path": current_image_path},
                workspace_dir   = task_workspace
            )
            if tool_result.get("status") == "success":
                current_image_path = tool_result["new_image_path"]
                restoration_count += 1
                restoration_history.append(
                    f"第{restoration_count}步: 调用 {tool_name} → 成功，"
                    f"当前图: {current_image_path}"
                )
                logger.info(f"✅ [工具] 复原成功 → 新图: {current_image_path}")
            else:
                restoration_history.append(
                    f"第{restoration_count+1}步: 调用 {tool_name} → 失败，"
                    "请勿再次调用此工具。"
                )
                logger.error(f"❌ [工具] {tool_name} 执行失败: {tool_result.get('message')}")
                break

        # ── 目标检测分支（跳出阶段一循环）────────────────
        elif tool_name == "detect":
            classes = tool_args.get("classes", ["舰船", "建筑", "车辆", "飞机"])
            logger.info(f"⚙️  [工具] 执行 GroundingDINO 检测，目标类别: {classes}")
            tool_result = execute_tool(
                tool_name       = "detect",
                tool_arguments  = {
                    "image_path": current_image_path,
                    "classes"   : classes
                },
                workspace_dir   = task_workspace
            )
            detected_bboxes = tool_result.get("found_targets", [])
            logger.info(f"✅ [工具] 检测完成，共发现 {len(detected_bboxes)} 个目标。")

            # 存档 Doc1
            save_memory("Doc1_Global", {
                "final_global_image"  : current_image_path,
                "restoration_steps"   : restoration_count,
                "restoration_history" : restoration_history,
                "vlm_observations"    : vlm_observations_s1,   # 每轮 caption + reasoning 完整记录
                "global_caption"      : response.get("image_caption", ""),
                "global_reasoning"    : response.get("reasoning", ""),
                "detected_bboxes"     : detected_bboxes
            }, task_id)
            break

        # ── VLM 错误或幻觉兜底：统一强制执行 detect ──────
        elif tool_name in ("error", "none") or tool_name not in (
            "dehaze", "denoise", "derain", "deblur", "detect"
        ):
            logger.warning(
                f"⚠️  [VLM] 输出无效工具名: '{tool_name}'，"
                "强制执行 detect 以保证流水线继续。"
            )
            tool_result = execute_tool(
                tool_name      = "detect",
                tool_arguments = {"image_path": current_image_path},
                workspace_dir  = task_workspace
            )
            detected_bboxes = tool_result.get("found_targets", [])
            logger.info(f"✅ [工具] 强制检测完成，共发现 {len(detected_bboxes)} 个目标。")
            save_memory("Doc1_Global", {
                "final_global_image"  : current_image_path,
                "restoration_steps"   : restoration_count,
                "restoration_history" : restoration_history,
                "vlm_observations"    : vlm_observations_s1,
                "global_caption"      : "",
                "global_reasoning"    : f"VLM 输出无效工具名 '{tool_name}'，已强制执行 detect。",
                "detected_bboxes"     : detected_bboxes
            }, task_id)
            break

    # ==========================================================
    # 🟡 阶段二：战术指挥官
    # ==========================================================
    logger.info("\n" + "═"*50)
    logger.info("🟡 阶段二：目标优先级排序")
    logger.info("═"*50)

    doc1         = load_memory("Doc1_Global", task_id)
    bboxes_raw   = doc1.get("detected_bboxes", [])
    img_w, img_h = _get_image_size(current_image_path)

    # ── 坐标越界修正（容错③）──────────────────────────
    bboxes = [_clamp_bbox(b, img_w, img_h) for b in bboxes_raw]

    # ── 容错①：0 个目标 → 跳过二三四 ────────────────────
    if not bboxes:
        logger.warning("⚠️  [容错①] 0 个目标，直接跳转阶段五生成常规安全报告。")
        no_target_hint = "由于画面中未检测到任何有效目标，请直接生成无目标的常规安全报告。"
        save_memory("Doc2_Queue", {"queue": [], "reason": "no_targets"}, task_id)
        save_memory("Doc3_Details", {}, task_id)
        save_memory("Doc4_Search", {"result": "无检索信息（无目标）"}, task_id)

    else:
        logger.info(f"🤖 [VLM·阶段二] 基于 {len(bboxes)} 个目标进行排序...")
        sys_prompt_commander = read_prompt(PROMPT_COMMANDER)

        # 构建上下文：将修正后的 BBox 列表传给 VLM
        bbox_context = json.dumps(bboxes, ensure_ascii=False, indent=2)

        response = call_qwen_text_only(
            sys_prompt = sys_prompt_commander,
            context    = f"以下是检测到的目标列表（坐标已修正）：\n{bbox_context}",
            stage_name = "阶段二"
        )
        logger.info(f"💭 [VLM·思考] {response.get('reasoning', '(无)')}")

        # VLM 应在 tool_arguments 中返回排好序的 target_ids 列表
        raw_queue = response.get("tool_arguments", {}).get("target_queue", [])

        # ── 容错②：动态裁剪，最多取 Top 3 ────────────────
        top_queue = raw_queue[:3]
        if len(top_queue) == 0:
            # VLM 没给队列，把所有 BBox id 按顺序用上（上限 3 个）
            top_queue = [b.get("id", f"box_{i}") for i, b in enumerate(bboxes[:3])]
            logger.warning(f"⚠️  [容错②] VLM 未返回队列，自动使用前 {len(top_queue)} 个目标。")
        else:
            logger.info(f"✅ [阶段二] 确定优先级队列（共 {len(top_queue)} 个）: {top_queue}")

        # ── 为队列中每个目标执行裁剪，生成 crop 图 ──────────
        # 建立 id → bbox 的映射表，方便查找坐标
        bbox_map = {b.get("id", f"box_{i}"): b for i, b in enumerate(bboxes)}

        queue_with_crops = []
        for idx, target_id in enumerate(top_queue):
            bbox = bbox_map.get(target_id)
            if bbox is None:
                logger.warning(f"⚠️  队列中 {target_id} 在 BBox 列表里找不到，跳过。")
                continue

            logger.info(f"✂️  [工具] 裁剪 crop{idx+1}: {target_id} BBox={bbox}")
            crop_result = execute_tool(
                tool_name      = "crop",
                tool_arguments = {
                    "image_path" : current_image_path,
                    "bbox"       : bbox,
                    "crop_name"  : f"crop{idx+1}"
                },
                workspace_dir  = task_workspace
            )
            if crop_result.get("status") == "success":
                queue_with_crops.append({
                    "target_id" : target_id,
                    "bbox"      : bbox,
                    "crop_path" : crop_result["new_image_path"]
                })
                logger.info(f"✅ [工具] 裁剪成功 → {crop_result['new_image_path']}")
            else:
                logger.error(f"❌ [工具] 裁剪 {target_id} 失败: {crop_result.get('message')}")

        save_memory("Doc2_Queue", {"queue": queue_with_crops}, task_id)

    # ==========================================================
    # 🟠 阶段三：局部特种兵
    # ==========================================================
    logger.info("\n" + "═"*50)
    logger.info("🟠 阶段三：局部精细化情报提取")
    logger.info("═"*50)

    queue             = load_memory("Doc2_Queue", task_id).get("queue", [])
    extracted_details = {}

    if not queue:
        logger.info("⏭️  队列为空，跳过阶段三。")
    else:
        sys_prompt_specialist = read_prompt(PROMPT_SPECIALIST)

        for item in queue:
            target_id       = item["target_id"]
            local_crop_path = item["crop_path"]
            logger.info(f"\n🎯 开始处理目标: {target_id} | 图: {local_crop_path}")

            local_call_count = 0  # 局部工具调用计数（安全上限）
            # 操作历史：记录每一步调用了什么工具、结果如何，下一轮拼入 context
            action_history: list[str] = []
            # VLM 每轮观察的完整记录（caption + reasoning），全部保存进 Doc3
            vlm_observations_s3: list[dict] = []

            while True:
                # 安全上限检查：超限后强制让 VLM 对当前图像做一次最终总结
                if local_call_count >= MAX_LOCAL_CALLS:
                    logger.warning(
                        f"⚠️  {target_id} 局部工具已调用 {local_call_count} 次，"
                        "强制进行最终观察并提交情报。"
                    )
                    history_str = "\n".join(action_history)
                    forced_context = (
                        f"当前目标ID: {target_id}\n"
                        f"【本目标操作历史】\n{history_str}\n\n"
                        "工具调用次数已达上限，你不能再调用任何工具。"
                        "请仔细观察当前图像，结合以上所有操作历史，"
                        "将你能识别到的所有细节（包括无法确认的模糊信息也请如实描述）"
                        "通过 finish_target 提交。"
                    )
                    logger.info(f"🤖 [VLM·阶段三·强制总结] {target_id}...")
                    forced_response = call_qwen_with_json(
                        sys_prompt = sys_prompt_specialist,
                        image_path = local_crop_path,
                        context    = forced_context,
                        stage_name = f"阶段三·{target_id}·强制总结"
                    )
                    intel = forced_response.get("tool_arguments", {}).get("extracted_info", "")
                    if not intel:
                        intel = forced_response.get("extracted_info", "")
                    if not intel:
                        intel = forced_response.get("reasoning", "(强制总结无输出)")
                    vlm_observations_s3.append({
                        "step"         : local_call_count + 1,
                        "image_path"   : local_crop_path,
                        "image_caption": forced_response.get("image_caption", ""),
                        "reasoning"    : forced_response.get("reasoning", ""),
                        "tool_name"    : "finish_target (forced)",
                    })
                    extracted_details[target_id] = {
                        "caption"          : forced_response.get("image_caption", ""),
                        "intel"            : f"[已达调用上限·强制总结] {intel}",
                        "action_history"   : action_history,
                        "vlm_observations" : vlm_observations_s3,
                    }
                    logger.info(f"🖼️  [{target_id}] 强制总结描述: {forced_response.get('image_caption', '(无)')}")
                    logger.info(f"✅ [{target_id}] 强制总结完成: {intel}")
                    break

                # 构建局部上下文：
                #   - 已完成的其他目标记录（跨目标记忆）
                #   - 本目标本轮的操作历史（防止重复调用同一工具）
                remaining = MAX_LOCAL_CALLS - local_call_count
                history_str = (
                    "\n".join(action_history)
                    if action_history
                    else "（本目标尚未调用过任何工具，这是第一次观察）"
                )
                local_context = (
                    f"当前目标ID: {target_id}\n"
                    f"已完成的其他目标记录: {json.dumps(extracted_details, ensure_ascii=False)}\n\n"
                    f"【本目标操作历史（请勿重复已做过的操作）】\n{history_str}\n\n"
                    f"剩余可用工具调用次数: {remaining} 次（含本次）。"
                    f"{'若仍无法识别有效信息，请直接调用 finish_target 提交现有情报。' if remaining <= 1 else ''}"
                )

                logger.info(f"🤖 [VLM·阶段三] 分析 {target_id}，第 {local_call_count+1} 次...")
                response = call_qwen_with_json(
                    sys_prompt = sys_prompt_specialist,
                    image_path = local_crop_path,
                    context    = local_context,
                    stage_name = f"阶段三·{target_id}"
                )
                tool_name = response.get("tool_name", "error")
                tool_args = response.get("tool_arguments", {})
                logger.info(f"🖼️  [VLM·描述] {response.get('image_caption', '(无)')}")
                logger.info(f"💭 [VLM·思考] {response.get('reasoning', '(无)')}")
                logger.info(f"🛠️  [VLM·决策] tool={tool_name}")
                vlm_observations_s3.append({
                    "step"         : local_call_count + 1,
                    "image_path"   : local_crop_path,
                    "image_caption": response.get("image_caption", ""),
                    "reasoning"    : response.get("reasoning", ""),
                    "tool_name"    : tool_name,
                })

                # ── 局部超分 ──
                if tool_name == "super_resolution":
                    logger.info("⚙️  [工具] 执行 Real-ESRGAN 超分辨率...")
                    sr_result = execute_tool(
                        tool_name      = "super_resolution",
                        tool_arguments = {"image_path": local_crop_path},
                        workspace_dir  = task_workspace
                    )
                    if sr_result.get("status") == "success":
                        local_crop_path = sr_result["new_image_path"]
                        local_call_count += 1
                        action_history.append(
                            f"第{local_call_count}步: 调用 super_resolution → 图像已放大4倍，"
                            f"当前图: {local_crop_path}"
                        )
                        logger.info(f"✅ [工具] 超分成功 → {local_crop_path}")
                    else:
                        local_call_count += 1
                        action_history.append(
                            f"第{local_call_count}步: 调用 super_resolution → 失败（显存不足），"
                            "请勿再次调用超分，改用其他工具或直接提交情报。"
                        )
                        logger.error(f"❌ [工具] 超分失败: {sr_result.get('message')}")

                # ── 二值化 ──
                elif tool_name == "binarize":
                    threshold = tool_args.get("threshold", 127)
                    logger.info(f"⚙️  [工具] 执行二值化，threshold={threshold}...")
                    bz_result = execute_tool(
                        tool_name      = "binarize",
                        tool_arguments = {"image_path": local_crop_path, "threshold": threshold},
                        workspace_dir  = task_workspace
                    )
                    if bz_result.get("status") == "success":
                        local_crop_path = bz_result["new_image_path"]
                        local_call_count += 1
                        action_history.append(
                            f"第{local_call_count}步: 调用 binarize(threshold={threshold}) → "
                            f"已二值化，当前图: {local_crop_path}"
                        )
                        logger.info(f"✅ [工具] 二值化成功 → {local_crop_path}")
                    else:
                        local_call_count += 1
                        action_history.append(f"第{local_call_count}步: 调用 binarize → 失败。")
                        logger.error(f"❌ [工具] 二值化失败: {bz_result.get('message')}")

                # ── 灰度化 ──
                elif tool_name == "grey":
                    logger.info("⚙️  [工具] 执行灰度化...")
                    gr_result = execute_tool(
                        tool_name      = "grey",
                        tool_arguments = {"image_path": local_crop_path},
                        workspace_dir  = task_workspace
                    )
                    if gr_result.get("status") == "success":
                        local_crop_path = gr_result["new_image_path"]
                        local_call_count += 1
                        action_history.append(
                            f"第{local_call_count}步: 调用 grey → 已转灰度，当前图: {local_crop_path}"
                        )
                        logger.info(f"✅ [工具] 灰度化成功 → {local_crop_path}")
                    else:
                        local_call_count += 1
                        action_history.append(f"第{local_call_count}步: 调用 grey → 失败。")
                        logger.error(f"❌ [工具] 灰度化失败: {gr_result.get('message')}")

                # ── 完成当前目标（跳出小循环）──
                elif tool_name == "finish_target":
                    intel = response.get("tool_arguments", {}).get("extracted_info", "")
                    if not intel:
                        intel = response.get("extracted_info", "(VLM 未返回具体情报)")
                    extracted_details[target_id] = {
                        "caption"          : response.get("image_caption", ""),
                        "intel"            : intel,
                        "action_history"   : action_history,
                        "vlm_observations" : vlm_observations_s3,  # 每轮 caption + reasoning 完整记录
                    }
                    logger.info(f"🖼️  [{target_id}] 最终描述: {response.get('image_caption', '(无)')}")
                    logger.info(f"✅ [{target_id}] 情报提取完成: {intel}")
                    break

                # ── VLM 错误兜底 ──
                elif tool_name == "error":
                    logger.error(f"❌ [VLM] {target_id} 返回 error，记录为空情报并跳过。")
                    extracted_details[target_id] = "(VLM 解析失败，无情报)"
                    break

                else:
                    logger.warning(f"⚠️  [VLM] 幻觉工具名: '{tool_name}'，忽略并继续。")
                    local_call_count += 1
                    action_history.append(
                        f"第{local_call_count}步: 输出了无效工具名 '{tool_name}'，已忽略，"
                        "请从工具箱中选择合法工具名。"
                    )
                    if local_call_count >= MAX_LOCAL_CALLS:
                        extracted_details[target_id] = "(反复幻觉，强制退出)"
                        break

    save_memory("Doc3_Details", extracted_details, task_id)

    # ==========================================================
    # 🔵 阶段四：情报提炼官
    # ==========================================================
    logger.info("\n" + "═"*50)
    logger.info("🔵 阶段四：关键词提炼与 RAG 检索")
    logger.info("═"*50)

    doc3 = load_memory("Doc3_Details", task_id)

    if not doc3:
        logger.info("⏭️  无局部细节，跳过检索阶段。")
        save_memory("Doc4_Search", {"result": "无检索信息（无目标细节）"}, task_id)
    else:
        sys_prompt_extractor = read_prompt(PROMPT_EXTRACTOR)
        context_for_extractor = (
            f"【全局环境描述（来自阶段一）】\n"
            f"{json.dumps(doc1, ensure_ascii=False)}\n\n"
            f"【局部细节情报（来自阶段三）】\n"
            f"{json.dumps(doc3, ensure_ascii=False)}"
        )

        logger.info("🤖 [VLM·阶段四] 提炼搜索关键词...")
        response = call_qwen_text_only(
            sys_prompt = sys_prompt_extractor,
            context    = context_for_extractor,
            stage_name = "阶段四"
        )
        logger.info(f"💭 [VLM·思考] {response.get('reasoning', '(无)')}")

        keyword = response.get("tool_arguments", {}).get("keyword", "")
        if not keyword:
            # 兼容 VLM 把关键词放在顶层的情况
            keyword = response.get("keyword", "")

        if keyword:
            logger.info(f"🔍 [工具] 静默执行 RAG 搜索: '{keyword}'")
            search_result_raw = execute_tool(
                tool_name      = "search",
                tool_arguments = {"keyword": keyword},
                workspace_dir  = task_workspace
            )
            search_text = search_result_raw.get("result", "搜索无结果")
            logger.info(f"✅ [工具] 检索完成，结果长度: {len(search_text)} 字符")
        else:
            logger.warning("⚠️  VLM 未返回有效关键词，跳过搜索。")
            keyword     = "(无)"
            search_text = "VLM 未生成关键词，无法检索。"

        save_memory("Doc4_Search", {
            "keyword" : keyword,
            "result"  : search_text
        }, task_id)

    # ==========================================================
    # 🟣 阶段五：首席报告官
    # ==========================================================
    logger.info("\n" + "═"*50)
    logger.info("🟣 阶段五：生成最终 SOAP 情报报告")
    logger.info("═"*50)

    sys_prompt_reporter = read_prompt(PROMPT_REPORTER)

    # 汇总全部阶段档案
    final_context_data = {
        "Global"  : load_memory("Doc1_Global", task_id),
        "Details" : load_memory("Doc3_Details", task_id),
        "Search"  : load_memory("Doc4_Search",  task_id),
    }

    # 若因无目标跳过了中间三阶段，在 context 里注入提示
    if no_target_hint:
        final_context_data["special_instruction"] = no_target_hint

    final_context_str = json.dumps(final_context_data, ensure_ascii=False, indent=2)

    logger.info("🤖 [VLM·阶段五] 撰写 SOAP 报告...")
    # 阶段五直接获取纯文本，不走任何 JSON 解析或重试
    try:
        final_report = call_raw_text(
            sys_prompt = sys_prompt_reporter,
            context    = final_context_str,
        )
        if not final_report:
            final_report = "(报告生成失败：模型返回空内容)"
    except Exception as e:
        logger.error(f"❌ [阶段五] 报告生成异常: {e}")
        final_report = f"(报告生成失败：{e})"

    # 落盘
    report_path = os.path.join(WORKSPACE_DIR, task_id, "FINAL_SOAP_REPORT.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"任务ID: {task_id}\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(final_report)

    logger.info(f"🎉 任务圆满结束！报告已保存至: {report_path}")
    return report_path


# ──────────────────────────────────────────────
# 测试入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    image = sys.argv[1] if len(sys.argv) > 1 else "raw_satellite_image_2026.jpg"
    run_agent_workflow(image)