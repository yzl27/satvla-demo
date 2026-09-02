#!/usr/bin/env bash
# ══════════════════════════════════════════════════
# SatVLALab 精简版 — 一键启动脚本
# 用法: bash start.sh
# 启动: Ollama(检查) + api_bridge(:8000) + Vite(:5174)
# ══════════════════════════════════════════════════
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p logs
ENV_NAME="satvla"

# ── 定位 conda 环境 Python ────────────────────────
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"
PY="$(command -v python)"
echo "ℹ️  使用 Python: $PY"

# ── 关键环境变量 ─────────────────────────────────
# 1) GroundingDINO 的 CUDA 扩展(.so)依赖 torch 动态库，必须加进库搜索路径
#    （按 torch 实际安装位置动态推导，不写死路径）
# 2) HF_ENDPOINT 用 hf-mirror 镜像：bert-base-uncased 首次运行时自动从镜像拉取
export LD_LIBRARY_PATH="$("$PY" -c 'import os,torch;print(os.path.join(os.path.dirname(torch.__file__),"lib"))'):${LD_LIBRARY_PATH:-}"
export HF_HOME="$ROOT/hf-cache"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export MULTIAGENT_PYTHON="$PY"

# ── 1. 检查 Ollama ───────────────────────────────
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "🚀 Ollama 未运行，尝试启动..."
    systemctl start ollama 2>/dev/null || (nohup ollama serve >logs/ollama.log 2>&1 &)
    for i in $(seq 1 10); do
        curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
        sleep 2
    done
fi
if curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:9b"; then
    echo "✅ Ollama + qwen3.5:9b 就绪"
else
    echo "⚠️  qwen3.5:9b 未安装，请先运行: ollama pull qwen3.5:9b"
fi

# ── 2. 启动后端桥接 api_bridge (:8000) ────────────
if [ -f logs/bridge.pid ] && kill -0 "$(cat logs/bridge.pid)" 2>/dev/null; then
    echo "✅ api_bridge 已在运行 (PID $(cat logs/bridge.pid))"
else
    echo "🚀 启动 api_bridge (:8000)..."
    nohup "$PY" multiagent/api_bridge.py >logs/bridge.log 2>&1 &
    echo $! >logs/bridge.pid
    sleep 2
    curl -s -o /dev/null http://localhost:8000/latest-report && echo "✅ api_bridge 启动成功" || echo "⚠️  api_bridge 可能启动失败，查看 logs/bridge.log"
fi

# ── 3. 启动前端 Vite (:5174) ─────────────────────
if [ -f logs/vite.pid ] && kill -0 "$(cat logs/vite.pid)" 2>/dev/null; then
    echo "✅ 前端已在运行 (PID $(cat logs/vite.pid))"
else
    echo "🚀 启动前端 Vite (:5174)..."
    (cd frontend-demo && nohup npm run dev -- --host >../logs/vite.log 2>&1 & echo $! >../logs/vite.pid)
    sleep 3
    curl -s -o /dev/null http://localhost:5174/ && echo "✅ 前端启动成功" || echo "⚠️  前端可能启动失败，查看 logs/vite.log"
fi

# ── 4. 访问地址 ──────────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🎯 浏览器打开: http://localhost:5174"
[ -n "$IP" ] && echo "    局域网访问: http://$IP:5174"
echo "    停止服务:   bash stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
