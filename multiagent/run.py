"""
run.py
────────────────────────────────────────────────────────────────
项目总入口。

用法：
  python run.py <图片路径>
  python run.py /path/to/image.png

功能：
  1. 检查输入图片是否存在
  2. 将图片以时间戳重命名拷入 workspace/task_xxx/
  3. 调用 state_machine.run_agent_workflow() 启动五阶段流水线
  4. 打印最终报告路径
────────────────────────────────────────────────────────────────
"""

import os
import sys
import shutil
import time
import logging

logging.basicConfig(
    level  = logging.INFO,
    format = "%(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")

# ── 默认图片路径（命令行不传参数时使用）──────
DEFAULT_IMAGE_PATH = os.path.join(BASE_DIR, "data", "100000007.png")


def main():
    # ── 参数解析：命令行优先，否则用默认路径 ──
    if len(sys.argv) >= 2:
        input_path = os.path.abspath(sys.argv[1])
    else:
        input_path = os.path.abspath(DEFAULT_IMAGE_PATH)
        logger.info(f"未传入路径，使用默认图片: {input_path}")

    if not os.path.isfile(input_path):
        logger.error(f"图片文件不存在: {input_path}")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
        logger.error(f"不支持的图片格式: {ext}，请使用 png/jpg/jpeg/bmp")
        sys.exit(1)

    # ── 初始化工作区，以时间戳命名输入图 ─────
    task_id       = time.strftime("task_%Y%m%d_%H%M%S")
    task_dir      = os.path.join(WORKSPACE_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    timestamp     = time.strftime("%Y%m%d%H%M%S")
    staged_input  = os.path.join(task_dir, f"{timestamp}{ext}")
    shutil.copy2(input_path, staged_input)

    logger.info(f"输入图片: {input_path}")
    logger.info(f"工作区:   {task_dir}")
    logger.info(f"时间戳图: {staged_input}")

    # ── 启动五阶段流水线 ──────────────────────
    from engine.state_machine import run_agent_workflow
    report_path = run_agent_workflow(staged_input)

    # ── 完成 ──────────────────────────────────
    print("\n" + "=" * 60)
    print(f"✅ 任务完成")
    print(f"📄 报告路径: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()