#!/usr/bin/env bash
# ══════════════════════════════════════════════════
# SatVLALab 精简版 — 一键安装脚本（目标机器运行一次）
# 用法: bash setup.sh
# 说明: 精简版不携带 Python 环境和模型权重，
#       本脚本负责: 建 conda 环境 → 装依赖 → 下权重
#       → 装 Ollama+模型 → 装前端依赖
# ══════════════════════════════════════════════════
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
ENV_NAME="satvla"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SatVLALab 精简版安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. 检查 NVIDIA GPU ───────────────────────────
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
    echo "✅ NVIDIA GPU 检测到"
else
    echo "⚠️  未检测到 nvidia-smi，推理需要 NVIDIA GPU 和驱动（版本 ≥ 525）"
fi

# ── 2. 检查 conda / Node ─────────────────────────
if ! command -v conda >/dev/null 2>&1; then
    echo "❌ 未安装 conda。请先安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi
if command -v node >/dev/null 2>&1 && [ "$(node -v | sed 's/v\([0-9]*\).*/\1/')" -ge 18 ]; then
    echo "✅ Node.js $(node -v)"
else
    echo "❌ 需要 Node.js ≥ 18，请先安装（如: sudo apt install nodejs npm，或使用 nvm）"
    exit 1
fi

# ── 3. 创建 Python 环境（3.10 与预编译 _C.so 匹配）──
if conda env list | grep -q "^$ENV_NAME "; then
    echo "✅ conda 环境 $ENV_NAME 已存在"
else
    echo "📦 创建 conda 环境 $ENV_NAME (python=3.10)..."
    conda create -n "$ENV_NAME" python=3.10 -y
fi
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# ── 4. 安装依赖 ──────────────────────────────────
echo "📥 安装 PyTorch (CUDA 11.8，约 2.4GB 下载)..."
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --index-url https://download.pytorch.org/whl/cu118

echo "📥 安装其余依赖..."
pip install -r requirements.txt
# 国内网络 pip 慢时，改用清华镜像重试:
# pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

python -c "import torch; assert torch.cuda.is_available(), 'CUDA 不可用，请检查驱动'; print(f'✅ torch {torch.__version__} + CUDA OK')"

# ── 5. 下载模型权重 ──────────────────────────────
bash download_weights.sh

# ── 6. 安装 Ollama 并拉取 VLM 模型 ────────────────
if ! command -v ollama >/dev/null 2>&1; then
    echo "📥 安装 Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "🚀 启动 Ollama 服务..."
    systemctl start ollama 2>/dev/null || (nohup ollama serve >/dev/null 2>&1 &)
    sleep 3
fi
if curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:9b"; then
    echo "✅ qwen3.5:9b 模型已存在"
else
    echo "📥 拉取 VLM 模型 qwen3.5:9b（约 6.6GB）..."
    ollama pull qwen3.5:9b
fi

# ── 7. 安装前端依赖 ──────────────────────────────
echo "📥 安装前端依赖（npm install）..."
cd frontend-demo
npm install --no-fund --no-audit
cd "$ROOT"

# ── 8. 自检（含 GroundingDINO 编译扩展）────────────
export LD_LIBRARY_PATH="$("$(command -v python)" -c 'import os,torch;print(os.path.join(os.path.dirname(torch.__file__),"lib"))'):${LD_LIBRARY_PATH:-}"
python -c "
import sys; sys.path.insert(0, '$ROOT/multiagent/tools/GroundingDINO')
import groundingdino, groundingdino._C
print('✅ groundingdino + CUDA 编译扩展 OK')"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ 安装完成！启动: bash start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
