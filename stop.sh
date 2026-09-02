#!/usr/bin/env bash
# ══════════════════════════════════════════════════
# SatVLALab 前端演示 — 停止脚本
# 用法: bash stop.sh
# 停止 api_bridge 与 Vite 前端（不动 Ollama 服务）
# ══════════════════════════════════════════════════
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

for name in bridge vite; do
    if [ -f "logs/$name.pid" ]; then
        pid=$(cat "logs/$name.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && echo "✅ 已停止 $name (PID $pid)"
        else
            echo "ℹ️  $name 未在运行"
        fi
        rm -f "logs/$name.pid"
    fi
done

# 兜底：按进程特征清理（仅匹配本项目路径）
pkill -f "multiagent/api_bridge.py" 2>/dev/null && echo "✅ 清理残留 api_bridge 进程"
pkill -f "frontend-demo.*vite" 2>/dev/null && echo "✅ 清理残留 vite 进程"

echo "完成。Ollama 服务保持运行，如需停止: sudo systemctl stop ollama"
