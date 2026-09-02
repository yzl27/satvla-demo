"""
tools/OpenCV/binarize.py
────────────────────────────────────────────────────────────────
固定阈值或 Otsu 自动阈值二值化。

输入：image_path, threshold (0 = Otsu 自动)
输出：<stem>_bina<threshold>.png  或  <stem>_binaOtsu.png

输出为三通道图（BGR），方便后续流水线统一处理。
────────────────────────────────────────────────────────────────
"""

import os
import logging
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)


def run(image_path: str, workspace_dir: str,
        threshold: int = 127) -> dict:
    """
    参数：
      image_path    — 输入图像路径
      workspace_dir — 输出目录
      threshold     — 二值化阈值（0–255）；传 0 则使用 Otsu 自动阈值

    返回：
      {"status": "success", "new_image_path": str}
      {"status": "error",   "message": str}
    """
    img = cv2.imread(image_path)
    if img is None:
        return _err(f"无法读取图片: {image_path}")

    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    threshold = int(threshold)

    if threshold == 0:
        # Otsu 自动阈值
        _, bina = cv2.threshold(
            grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        tag = "binaOtsu"
    else:
        _, bina = cv2.threshold(grey, threshold, 255, cv2.THRESH_BINARY)
        tag = f"bina{threshold}"

    # 单通道 → 三通道，保持流水线一致性
    bina_bgr = cv2.cvtColor(bina, cv2.COLOR_GRAY2BGR)

    stem     = Path(image_path).stem
    out_path = os.path.join(workspace_dir, f"{stem}_{tag}.png")
    os.makedirs(workspace_dir, exist_ok=True)
    cv2.imwrite(out_path, bina_bgr)

    logger.info(f"[binarize] threshold={threshold if threshold else 'Otsu'} → {out_path}")
    return {"status": "success", "new_image_path": out_path}


def _err(msg: str) -> dict:
    logger.error(f"[binarize] {msg}")
    return {"status": "error", "message": msg, "new_image_path": ""}