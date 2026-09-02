"""
tools/OpenCV/grey.py
────────────────────────────────────────────────────────────────
彩色图转灰度图。

某些场景下灰度图更利于 VLM 识别舷号、文字、纹理细节。

输入：image_path
输出：<stem>_grey.png（三通道灰度，方便后续流水线统一处理）
────────────────────────────────────────────────────────────────
"""

import os
import logging
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)


def run(image_path: str, workspace_dir: str) -> dict:
    """
    参数：
      image_path    — 输入图像路径
      workspace_dir — 输出目录

    返回：
      {"status": "success", "new_image_path": str}
      {"status": "error",   "message": str}
    """
    img = cv2.imread(image_path)
    if img is None:
        return _err(f"无法读取图片: {image_path}")

    grey     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    grey_bgr = cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)

    stem     = Path(image_path).stem
    out_path = os.path.join(workspace_dir, f"{stem}_grey.png")
    os.makedirs(workspace_dir, exist_ok=True)
    cv2.imwrite(out_path, grey_bgr)

    logger.info(f"[grey] → {out_path}")
    return {"status": "success", "new_image_path": out_path}


def _err(msg: str) -> dict:
    logger.error(f"[grey] {msg}")
    return {"status": "error", "message": msg, "new_image_path": ""}