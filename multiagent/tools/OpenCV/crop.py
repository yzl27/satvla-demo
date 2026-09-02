"""
tools/OpenCV/crop.py
────────────────────────────────────────────────────────────────
按 BBox 坐标裁剪图像。

输入：image_path, bbox(x1/y1/x2/y2), crop_name
输出：<stem>_<crop_name>.png  e.g. 1718_dehazed_crop1.png

坐标越界会自动 clamp，面积为零时返回 error。
────────────────────────────────────────────────────────────────
"""

import os
import logging
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)


def run(image_path: str, workspace_dir: str,
        bbox: dict, crop_name: str = "crop1") -> dict:
    """
    参数：
      image_path    — 待裁剪图像路径（应为标注前的图）
      workspace_dir — 输出目录
      bbox          — {"x1": int, "y1": int, "x2": int, "y2": int}
      crop_name     — 输出后缀标识，如 "crop1"、"crop2"

    返回：
      {"status": "success", "new_image_path": str}
      {"status": "error",   "message": str}
    """
    img = cv2.imread(image_path)
    if img is None:
        return _err(f"无法读取图片: {image_path}")

    h, w = img.shape[:2]

    # 坐标 clamp（双重保险，state_machine 已做过一次）
    x1 = max(0, min(int(bbox.get("x1", 0)), w))
    y1 = max(0, min(int(bbox.get("y1", 0)), h))
    x2 = max(0, min(int(bbox.get("x2", w)), w))
    y2 = max(0, min(int(bbox.get("y2", h)), h))

    if x2 <= x1 or y2 <= y1:
        return _err(
            f"裁剪坐标无效（面积为零）: "
            f"x1={x1} y1={y1} x2={x2} y2={y2}，图像尺寸 {w}×{h}"
        )

    crop = img[y1:y2, x1:x2]
    stem     = Path(image_path).stem
    out_path = os.path.join(workspace_dir, f"{stem}_{crop_name}.png")
    os.makedirs(workspace_dir, exist_ok=True)
    cv2.imwrite(out_path, crop)

    logger.info(f"[crop] [{x1},{y1},{x2},{y2}] → {out_path}")
    return {"status": "success", "new_image_path": out_path}


def _err(msg: str) -> dict:
    logger.error(f"[crop] {msg}")
    return {"status": "error", "message": msg, "new_image_path": ""}