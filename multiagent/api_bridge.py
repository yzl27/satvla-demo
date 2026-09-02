"""
api_bridge.py
────────────────────────────────────────────────────────────────
FastAPI 后端桥接服务，连接 multiagent 推理后端与前端 React UI。

功能：
  1. WebSocket /ws/mission：接收前端启动指令，运行 run.py 并实时
     将 stdout 广播给前端（日志流）
  2. 静态挂载 /workspace：前端可直接访问 workspace 下生成的图片
  3. GET /latest-report：返回最新任务的 FINAL_SOAP_REPORT.txt 内容

启动方式：
  cd <部署目录>/multiagent
  python api_bridge.py   # 或使用 start.sh 一键启动
────────────────────────────────────────────────────────────────
"""

import asyncio
import os

from cot_stream_builder import CoTStreamBuilder

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# 推理子进程所用 Python：
#   1) 部署包自带环境 runtime-env（推荐，自包含）
#   2) 环境变量 MULTIAGENT_PYTHON 指定
#   3) 兜底：当前解释器
RUNTIME_ENV_PYTHON = os.path.join(BASE_DIR, "runtime-env", "bin", "python")
if os.path.isfile(RUNTIME_ENV_PYTHON):
    INFER_PYTHON = RUNTIME_ENV_PYTHON
elif os.environ.get("MULTIAGENT_PYTHON"):
    INFER_PYTHON = os.environ["MULTIAGENT_PYTHON"]
else:
    import sys
    INFER_PYTHON = sys.executable

app.mount("/workspace", StaticFiles(directory=WORKSPACE_DIR), name="workspace")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/latest-report")
async def get_latest_report():
    """返回最近一次任务的 FINAL_SOAP_REPORT.txt 内容"""
    task_dirs = sorted(
        [d for d in os.listdir(WORKSPACE_DIR) if d.startswith("task_")],
        reverse=True,
    )
    for task in task_dirs:
        report_path = os.path.join(WORKSPACE_DIR, task, "FINAL_SOAP_REPORT.txt")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                return {"content": f.read(), "task_id": task}
    return {"content": None, "task_id": None}


@app.websocket("/ws/mission")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        if data.get("action") != "start":
            return

        image_path = data.get("image_path", "").strip()

        cot_builder = CoTStreamBuilder()

        # 使用项目自带 runtime-env（或 INFER_PYTHON 兜底）运行 run.py
        cmd = [INFER_PYTHON, "-u", "run.py"]
        if image_path:
            cmd.append(image_path)

        # asyncio 异步子进程：逐行读取不阻塞事件循环，保证 WebSocket 实时推送
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=BASE_DIR,
        )

        async for raw_line in process.stdout:
            line = raw_line.decode(errors="replace").rstrip("\n")
            if line:
                await websocket.send_json({"type": "log", "content": line})
                snap = cot_builder.feed_line(line)
                await websocket.send_json(
                    {
                        "type": "cot_graph",
                        "revision": snap["revision"],
                        "task_id": snap.get("task_id"),
                        "nodes": snap["nodes"],
                        "edges": snap["edges"],
                    }
                )

        await process.wait()

        # 任务完成后，发送 SOAP 报告内容
        task_dirs = sorted(
            [d for d in os.listdir(WORKSPACE_DIR) if d.startswith("task_")],
            reverse=True,
        )
        for task in task_dirs:
            report_path = os.path.join(WORKSPACE_DIR, task, "FINAL_SOAP_REPORT.txt")
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_content = f.read()
                await websocket.send_json(
                    {"type": "report", "content": report_content, "task_id": task}
                )
                break

        await websocket.send_json({"type": "system", "content": "MISSION_COMPLETED"})

    except WebSocketDisconnect:
        print("[api_bridge] Client disconnected")
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
