"""
engine/tool_use.py
────────────────────────────────────────────────────────────────
工具路由器。

职责：
  1. 接收 (tool_name, tool_arguments, workspace_dir)
  2. 按工具名 import 对应模块，传参调用其 run() 函数
  3. 统一返回 {"status": ..., "new_image_path": ..., ...}

本文件不含任何业务逻辑，只做名称→模块的映射。
业务逻辑全部在 tools/ 下各自的脚本中。

【文件命名规范（由各工具脚本负责执行）】
  复原链式叠加：  <stem>_dehazed_derained_deblurred.png
  检测展示图：    <stem>_detected.png          ← 仅展示，不参与后续处理
  检测坐标文件：  <stem>_detected.txt          ← crop 读取坐标的来源
  裁剪输出：      <stem>_crop1.png / _crop2.png / _crop3.png
  局部增强叠加：  <stem>_crop1_sr.png
                  <stem>_crop1_bina127.png
                  <stem>_crop1_grey.png
────────────────────────────────────────────────────────────────
"""

import os
import sys
import logging
import importlib.util
from types import SimpleNamespace

logger = logging.getLogger(__name__)

# 项目根目录（engine/ 的上一级）
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

# ──────────────────────────────────────────────
# 权重 / 配置路径（按实际部署修改）
# ──────────────────────────────────────────────
WEIGHTS = {
    # DehazeFormer
    "dehaze"      : os.path.join(TOOLS_DIR, "DehazeFormer",  "weights", "dehazeformer-b.pth"),
    # Restormer
    "deblur"      : os.path.join(TOOLS_DIR, "Restormer",     "weights", "motion_deblurring.pth"),
    "denoise"     : os.path.join(TOOLS_DIR, "Restormer",     "weights", "real_denoising.pth"),
    "derain"      : os.path.join(TOOLS_DIR, "Restormer",     "weights", "deraining.pth"),
    # GroundingDINO
    "detect_cfg"  : os.path.join(TOOLS_DIR, "GroundingDINO", "groundingdino", "config",
                                 "GroundingDINO_SwinT_OGC.py"),
    "detect_ckpt" : os.path.join(TOOLS_DIR, "GroundingDINO", "weights",
                                 "groundingdino_swint_ogc.pth"),
    # Real-ESRGAN
    "sr"          : os.path.join(TOOLS_DIR, "Real-ESRGAN",   "weights", "RealESRGAN_x4plus.pth"),
}


# ══════════════════════════════════════════════
# 对外唯一入口
# ══════════════════════════════════════════════

def execute_tool(tool_name: str, tool_arguments: dict,
                 workspace_dir: str) -> dict:
    """
    工具路由主入口。

    工具名与所需参数对照：
    ┌─────────────────────┬───────────────────────────────────────────────────┐
    │ tool_name           │ tool_arguments 字段                               │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ dehaze              │ image_path: str                                   │
    │ deblur              │ image_path: str                                   │
    │ denoise             │ image_path: str                                   │
    │ derain              │ image_path: str                                   │
    │ detect              │ image_path: str, text_prompt: str (可选)          │
    │ crop                │ image_path: str, bbox: dict, crop_name: str       │
    │ super_resolution    │ image_path: str                                   │
    │ binarize            │ image_path: str, threshold: int (可选, 默认 127)  │
    │ grey                │ image_path: str                                   │
    │ search              │ keyword: str                                      │
    └─────────────────────┴───────────────────────────────────────────────────┘
    """
    os.makedirs(workspace_dir, exist_ok=True)
    img = tool_arguments.get("image_path", "")
    logger.info(f"[tool_use] ▶ {tool_name}")

    # ── 图像复原 ───────────────────────────────
    if tool_name == "dehaze":
        return _call_dehaze(img, workspace_dir)

    elif tool_name == "deblur":
        return _call_restormer("deblur", img, workspace_dir)

    elif tool_name == "denoise":
        return _call_restormer("denoise", img, workspace_dir)

    elif tool_name == "derain":
        return _call_restormer("derain", img, workspace_dir)

    # ── 检测 ───────────────────────────────────
    elif tool_name == "detect":
        return _call_detect(img, workspace_dir,
                            tool_arguments.get("text_prompt", None))

    # ── 裁剪 ───────────────────────────────────
    elif tool_name == "crop":
        from tools.OpenCV.crop import run as crop_run
        return crop_run(
            image_path    = img,
            workspace_dir = workspace_dir,
            bbox          = tool_arguments.get("bbox", {}),
            crop_name     = tool_arguments.get("crop_name", "crop1"),
        )

    # ── 局部增强 ───────────────────────────────
    elif tool_name == "super_resolution":
        return _call_sr(img, workspace_dir)

    elif tool_name == "binarize":
        from tools.OpenCV.binarize import run as binarize_run
        return binarize_run(
            image_path    = img,
            workspace_dir = workspace_dir,
            threshold     = tool_arguments.get("threshold", 127),
        )

    elif tool_name == "grey":
        from tools.OpenCV.grey import run as grey_run
        return grey_run(image_path=img, workspace_dir=workspace_dir)

    # ── 搜索 ───────────────────────────────────
    elif tool_name == "search":
        from tools.RAG.search import run as search_run
        keyword = tool_arguments.get("keyword", "")
        if not keyword:
            return _err("search 工具缺少 'keyword' 参数")
        return search_run(keyword)

    else:
        return _err(f"未知工具名: '{tool_name}'")


# ══════════════════════════════════════════════
# 各深度学习工具的调用封装
# （路由层负责构建 cfg，不含推理逻辑）
# ══════════════════════════════════════════════

def _call_dehaze(image_path: str, workspace_dir: str) -> dict:
    """构建 DehazeFormer cfg，调用 run_dehaze.run()"""
    tool_dir = os.path.join(TOOLS_DIR, "DehazeFormer")
    _syspath(tool_dir)
    try:
        from run_dehaze import run as dehaze_run  # type: ignore
    except ImportError as e:
        return _err(f"导入 run_dehaze 失败: {e}")
 
    from pathlib import Path
    stem     = Path(image_path).stem
    out_path = os.path.join(workspace_dir, f"{stem}_dehazed.png")
 
    # run_dehaze 输出文件名与输入同名，用临时子目录隔离，防止覆盖原图
    import tempfile
    with tempfile.TemporaryDirectory(dir=workspace_dir, prefix="dehaze_tmp_") as tmp_dir:
        cfg = SimpleNamespace(
            weight_path  = WEIGHTS["dehaze"],
            input_dir    = image_path,
            result_dir   = tmp_dir,
            device       = "cuda",
            pad_multiple = 16,
        )
        try:
            dehaze_run(cfg)
        except Exception as e:
            return _err(f"dehaze 推理失败: {e}")
 
        raw_out = os.path.join(tmp_dir, os.path.basename(image_path))
        if not os.path.exists(raw_out):
            raw_out = os.path.join(tmp_dir, stem + ".png")
        if not os.path.exists(raw_out):
            return _err(f"dehaze 输出文件未找到，期望: {raw_out}")
        os.replace(raw_out, out_path)
 
    return {"status": "success", "new_image_path": out_path}


def _call_restormer(tool_name: str, image_path: str,
                    workspace_dir: str) -> dict:
    """
    分别调用三个独立的 Restormer 脚本。
    每个脚本有各自的 CONFIG 与 main()，通过 importlib 动态加载避免模块名冲突。
    """
    script_map = {
        #  tool_name : (脚本文件名,      task 子目录名,       输出后缀)
        "deblur" : ("run_deblur",  "Motion_Deblurring", "_deblurred"),
        "denoise": ("run_denoise", "Real_Denoising",    "_denoised"),
        "derain" : ("run_derain",  "Deraining",         "_derained"),
    }
    script_name, task_dir, suffix = script_map[tool_name]
    tool_dir = os.path.join(TOOLS_DIR, "Restormer")
    _syspath(tool_dir)

    try:
        mod = _load_module(script_name,
                           os.path.join(tool_dir, f"{script_name}.py"))
    except Exception as e:
        return _err(f"导入 {script_name} 失败: {e}")

    # 覆盖模块级 CONFIG（三个脚本各自独立，不会互相污染）
    mod.CONFIG.input_dir   = image_path
    mod.CONFIG.result_dir  = workspace_dir
    mod.CONFIG.weight_path = WEIGHTS[tool_name]
    mod.CONFIG.device      = "cuda"

    try:
        mod.main()
    except Exception as e:
        return _err(f"{tool_name} 推理失败: {e}")

    from pathlib import Path
    stem     = Path(image_path).stem
    raw_out  = os.path.join(workspace_dir, task_dir, f"{stem}.png")
    out_path = os.path.join(workspace_dir, f"{stem}{suffix}.png")

    if not os.path.exists(raw_out):
        return _err(f"{tool_name} 输出文件未找到，期望: {raw_out}")

    os.replace(raw_out, out_path)
    _rmdir_if_empty(os.path.join(workspace_dir, task_dir))
    return {"status": "success", "new_image_path": out_path}


def _call_detect(image_path: str, workspace_dir: str,
                 text_prompt: str = None) -> dict:
    """构建 GroundingDINO cfg，调用 run_detect.run()"""
    tool_dir = os.path.join(TOOLS_DIR, "GroundingDINO")
    _syspath(tool_dir)
    try:
        from run_detect import run as detect_run, DEFAULTS  # type: ignore
    except ImportError as e:
        return _err(f"导入 run_detect 失败: {e}")
    
    combined_prompt = f"{text_prompt.rstrip('.')}.{DEFAULTS['TEXT_PROMPT']}" if text_prompt else DEFAULTS["TEXT_PROMPT"]

    cfg = SimpleNamespace(
        config_path    = WEIGHTS["detect_cfg"],
        ckpt_path      = WEIGHTS["detect_ckpt"],
        image          = image_path,
        output_dir     = workspace_dir,
        text_prompt    = combined_prompt,
        token_spans    = None,
        box_threshold  = DEFAULTS["BOX_THRESHOLD"],
        text_threshold = DEFAULTS["TEXT_THRESHOLD"],
        area_threshold = DEFAULTS["AREA_THRESHOLD"],
        iou_threshold  = DEFAULTS["IOU_THRESHOLD"],
        device         = DEFAULTS["DEVICE"],
    )
    try:
        detect_run(cfg)
    except Exception as e:
        return _err(f"detect 推理失败: {e}")

    from pathlib import Path
    stem      = Path(image_path).stem
    raw_annot = os.path.join(workspace_dir, f"{stem}_annotated.png")
    raw_txt   = os.path.join(workspace_dir, f"{stem}_boxes.txt")
    out_annot = os.path.join(workspace_dir, f"{stem}_detected.png")
    out_txt   = os.path.join(workspace_dir, f"{stem}_detected.txt")

    if not os.path.exists(raw_txt):
        return _err(f"detect 坐标文件未找到: {raw_txt}")

    if os.path.exists(raw_annot):
        os.replace(raw_annot, out_annot)
    if raw_txt != out_txt:
        os.replace(raw_txt, out_txt)

    found_targets = _parse_detect_txt(out_txt)
    logger.info(f"[detect] 解析到 {len(found_targets)} 个目标")

    return {
        "status"        : "success",
        "new_image_path": image_path,   # ← 裁剪仍用标注前的原图
        "annotated_path": out_annot,    # 展示用
        "txt_path"      : out_txt,
        "found_targets" : found_targets,
    }


def _call_sr(image_path: str, workspace_dir: str) -> dict:
    """构建 Real-ESRGAN cfg，调用 run_sr.run()"""
    tool_dir = os.path.join(TOOLS_DIR, "Real-ESRGAN")
    _syspath(tool_dir)
    try:
        from run_sr import run as sr_run  # type: ignore
    except ImportError as e:
        return _err(f"导入 run_sr 失败: {e}")
 
    from pathlib import Path
    stem     = Path(image_path).stem
    out_path = os.path.join(workspace_dir, f"{stem}_sr.png")
 
    # Real-ESRGAN 输出文件名与输入同名（suffix=""），若输出目录与输入目录相同
    # 会直接覆盖原始 crop 图。用独立临时子目录隔离输出，完成后再移到正确位置。
    import tempfile
    with tempfile.TemporaryDirectory(dir=workspace_dir, prefix="sr_tmp_") as tmp_dir:
        cfg = SimpleNamespace(
            input_path       = image_path,
            output_dir       = tmp_dir,   # 输出到临时目录，不污染 workspace
            model_path       = WEIGHTS["sr"],
            model_name       = "RealESRGAN_x4plus",
            outscale         = 4,
            denoise_strength = 0.5,
            tile             = 0,
            tile_pad         = 10,
            pre_pad          = 0,
            half_precision   = True,
            gpu_id           = None,
            suffix           = "",
            ext_mode         = "png",
            alpha_upsampler  = "realesrgan",
            face_enhance     = False,
        )
        try:
            sr_run(cfg)
        except Exception as e:
            return _err(f"super_resolution 推理失败: {e}")
 
        raw_out = os.path.join(tmp_dir, f"{stem}.png")
        if not os.path.exists(raw_out):
            return _err(f"sr 输出文件未找到，期望: {raw_out}")
        os.replace(raw_out, out_path)   # 从临时目录移到 workspace，原图安全
 
    return {"status": "success", "new_image_path": out_path}


# ══════════════════════════════════════════════
# 内部辅助函数
# ══════════════════════════════════════════════

def _err(msg: str) -> dict:
    logger.error(f"[tool_use] ✗ {msg}")
    return {"status": "error", "message": msg, "new_image_path": ""}


def _syspath(path: str) -> None:
    """将目录加入 sys.path（避免重复添加）"""
    if path not in sys.path:
        sys.path.insert(0, path)


def _load_module(name: str, filepath: str):
    """
    从绝对路径动态加载模块。
    Restormer 三个脚本文件名不同，用此方式各自独立加载，
    避免 Python 模块缓存导致 CONFIG 互相覆盖。
    """
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None:
        raise ImportError(f"找不到模块: {filepath}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_detect_txt(txt_path: str) -> list:
    """
    解析 GroundingDINO 输出的 _detected.txt。
    格式（每行）：<label> <score> <x1> <y1> <x2> <y2>
    返回：
      [{"id": "box_0", "label": str, "score": float,
        "x1": int, "y1": int, "x2": int, "y2": int}, ...]
    """
    targets = []
    if not os.path.exists(txt_path):
        return targets
    with open(txt_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            # 从右切出 5 个数值字段，保留 label 中可能含有的空格
            parts = line.rsplit(" ", 5)
            if len(parts) < 6:
                continue
            targets.append({
                "id"   : f"box_{i}",
                "label": parts[0],
                "score": float(parts[1]),
                "x1"   : int(parts[2]),
                "y1"   : int(parts[3]),
                "x2"   : int(parts[4]),
                "y2"   : int(parts[5]),
            })
    return targets


def _rmdir_if_empty(path: str) -> None:
    """清理 Restormer 自动生成的空任务子目录"""
    try:
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
    except OSError:
        pass