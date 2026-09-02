#!/usr/bin/env bash
# ══════════════════════════════════════════════════
# SatVLALab 精简版 — 模型权重下载脚本
# 用法: bash download_weights.sh
# 下载全部推理所需权重到 multiagent/tools/ 对应位置
# ══════════════════════════════════════════════════
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p multiagent/tools/GroundingDINO/weights \
         multiagent/tools/Real-ESRGAN/weights \
         multiagent/tools/DehazeFormer/weights \
         multiagent/tools/Restormer/weights

# 下载函数: 依次尝试多个源，成功即停
fetch() {
    local dest="$1"; shift
    local ok=0
    for url in "$@"; do
        echo "⬇️  $url"
        if wget -c -q --show-progress -O "$dest" "$url"; then ok=1; break; fi
        echo "⚠️  该源失败，尝试下一个..."
    done
    if [ "$ok" != "1" ]; then
        echo "❌ 全部源均失败: $dest"
        echo "   请手动下载后放到该路径（文件名保持一致），或见 DEPLOY.md 常见问题。"
    else
        echo "✅ $dest ($(du -h "$dest" | cut -f1))"
    fi
}

echo "━━━ 1/5 GroundingDINO 检测权重 (662MB) ━━━"
fetch multiagent/tools/GroundingDINO/weights/groundingdino_swint_ogc.pth \
    "https://hf-mirror.com/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth" \
    "https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth" \
    "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth"

echo "━━━ 2/5 Real-ESRGAN 超分权重 (64MB) ━━━"
fetch multiagent/tools/Real-ESRGAN/weights/RealESRGAN_x4plus.pth \
    "https://hf-mirror.com/schwgHao/RealESRGAN_x4plus/resolve/main/RealESRGAN_x4plus.pth" \
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

echo "━━━ 3/5 DehazeFormer 去雾权重 (11MB) ━━━"
fetch multiagent/tools/DehazeFormer/weights/dehazeformer-b.pth \
    "https://github.com/IDKiro/DehazeFormer/releases/download/v1.0/dehazeformer-b.pth"

echo "━━━ 4/5 Restormer 去模糊权重 (64MB) ━━━"
fetch multiagent/tools/Restormer/weights/motion_deblurring.pth \
    "https://github.com/swz30/Restormer/releases/download/v1.0/motion_deblurring.pth"

echo "━━━ 5/5 Restormer 去噪/去雨权重 (128MB) ━━━"
fetch multiagent/tools/Restormer/weights/real_denoising.pth \
    "https://github.com/swz30/Restormer/releases/download/v1.0/real_denoising.pth"
fetch multiagent/tools/Restormer/weights/deraining.pth \
    "https://github.com/swz30/Restormer/releases/download/v1.0/deraining.pth"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 权重下载完成。检查:"
ls -lh multiagent/tools/*/weights/ 2>/dev/null | grep pth
echo
echo " 注意: bert-base-uncased（GroundingDINO 文字编码）
 无需手动下载——首次推理时自动从 hf-mirror 拉取
（start.sh 已设置 HF_ENDPOINT=hf-mirror.com）。"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
