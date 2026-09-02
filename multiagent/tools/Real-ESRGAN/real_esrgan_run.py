import glob
import os
from pathlib import Path
from types import SimpleNamespace
from typing import List

import cv2
from basicsr.archs.rrdbnet_arch import RRDBNet
from basicsr.utils.download_util import load_file_from_url
from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact

###############################################################################
# 1. 参数区 —— 可在此处或外部脚本覆盖
###############################################################################
DEFAULTS = dict(
    # ---------- 路径参数 ----------
    input_dir="",      # 输入：单张图片 或 目录（由流水线调用时传入实际路径）
    output_dir="results",    # 输出目录
    model_path=None,          # 自定义权重（None 自动下载）

    # ---------- 模型选择 ----------
    model_name="RealESRGAN_x4plus",  # 支持列表见 _get_model()

    # ---------- 推理参数 ----------
    outscale=4,               # 最终放大倍数（通常等于模型内置 scale）
    denoise_strength=0.5,     # 仅 general‑x4v3 有效
    tile=0,                   # >0 开启分片，避免显存 OOM
    tile_pad=10,
    pre_pad=0,
    half_precision=True,      # True = fp16；False = fp32
    gpu_id=None,              # None=自动/CPU；0/1/2 指定 GPU

    # ---------- 输出控制 ----------
    suffix="esrgan",            # 输出文件名后缀；"" 表示不加后缀
    ext_mode="auto",         # auto|jpg|png —— auto=保持输入后缀
    alpha_upsampler="realesrgan",  # alpha 通道上采：realesrgan|bicubic

    # ---------- 其他功能 ----------
    face_enhance=False,       # 调用 GFPGAN 人脸增强
)

REAL_ESRGAN_CONFIG = SimpleNamespace(**DEFAULTS)  # 可在外部覆盖属性

###############################################################################
# 2. 模型&权重工具函数
###############################################################################
def _get_model(name: str):
    name = name.split(".")[0]
    model = None
    netscale = None
    file_url: list[str] = []
    # x4 RRDBNet
    if name == "RealESRGAN_x4plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=4)
        netscale = 4
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        ]
    # x4 RRDBNet (无 GAN)
    elif name == "RealESRNet_x4plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=4)
        netscale = 4
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth",
        ]
    # 动漫 6‑Block
    elif name == "RealESRGAN_x4plus_anime_6B":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=6, num_grow_ch=32, scale=4)
        netscale = 4
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        ]
    # x2 RRDBNet
    elif name == "RealESRGAN_x2plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=2)
        netscale = 2
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        ]
    # AnimeVideo v3
    elif name == "realesr-animevideov3":
        model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64,
                                num_conv=16, upscale=4, act_type="prelu")
        netscale = 4
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth",
        ]
    # General x4 v3
    elif name == "realesr-general-x4v3":
        model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64,
                                num_conv=32, upscale=4, act_type="prelu")
        netscale = 4
        file_url = [
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth",
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
        ]
    else:
        raise ValueError(f"未知 model_name: {name}")
    return model, netscale, file_url

def _download_if_needed(urls: List[str], dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    paths = []
    for u in urls:
        f = dst / Path(u).name
        if not f.is_file():
            print(f"[Download] {f.name}")
            f = Path(load_file_from_url(u, model_dir=str(dst), progress=True, file_name=None))
        paths.append(str(f))
    return paths[0] if len(paths) == 1 else paths

###############################################################################
# 3. 主推理函数
###############################################################################
def real_esrgan_run(cfg):
    """按照 cfg 进行批量或单张超分推理。"""
    # 3‑1 解析模型与权重
    net, scale, urls = _get_model(cfg.model_name)
    root_dir = Path(__file__).parent if "__file__" in globals() else Path.cwd()
    weight_dir = root_dir / "weights"
    model_path = cfg.model_path or _download_if_needed(urls, weight_dir)

    # 3‑2 DNI 去噪权重
    dni = None
    if cfg.model_name == "realesr-general-x4v3" and cfg.denoise_strength != 1:
        assert isinstance(model_path, list), "general‑x4v3 需双权重列表"
        dni = [cfg.denoise_strength, 1 - cfg.denoise_strength]

    # 3‑3 创建 upsampler
    upsampler = RealESRGANer(
        scale=scale,
        model_path=model_path,
        dni_weight=dni,
        model=net,
        tile=cfg.tile,
        tile_pad=cfg.tile_pad,
        pre_pad=cfg.pre_pad,
        half=cfg.half_precision,
        gpu_id=cfg.gpu_id,
    )

    # 3‑4 (可选) GFPGAN 人脸增强
    face_enhancer = None
    if cfg.face_enhance:
        from gfpgan import GFPGANer
        face_enhancer = GFPGANer(
            model_path="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth",
            upscale=cfg.outscale,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=upsampler,
        )

    # 3‑5 准备输入列表
    input_dir = Path(cfg.input_dir)
    img_list = [str(input_dir)] if input_dir.is_file() else sorted(glob.glob(str(input_dir / "*")))
    if not img_list:
        raise FileNotFoundError(f"在 {cfg.input_dir} 未找到任何文件")

    # 3‑6 主循环
    for idx, img_path in enumerate(img_list):
        name, ext = os.path.splitext(os.path.basename(img_path))
        print(f"[{idx}] 处理 {name}{ext}")
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print("  [Skip] 无法读取")
            continue
        has_alpha = img.ndim == 3 and img.shape[2] == 4

        try:
            if face_enhancer:
                _, _, output = face_enhancer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
            else:
                output, _ = upsampler.enhance(img, outscale=cfg.outscale)
        except RuntimeError as e:
            print(f"  [Error] {e} —— 试试调小 tile")
            continue

        # # === 可选：把超分结果缩回原像素尺寸 ===
        # h0, w0 = img.shape[:2]
        # output = cv2.resize(output, (w0, h0), interpolation=cv2.INTER_LANCZOS4)

        # 3‑7 保存结果
        # ext_save = (
        #     ext[1:] if cfg.ext_mode == "auto" else cfg.ext_mode
        # )
        # if has_alpha:
        #     ext_save = "png"  # RGBA 强制 PNG
        # suffix = f"_{cfg.suffix}" if cfg.suffix else ""
        # parent = Path(input_dir).parent
        # save_path = parent / "temp" / f"{name}{suffix}.{ext_save}"
        save_path = cfg.output_dir
        cv2.imwrite(str(save_path), output)
        print(f"  [✓] 保存 {save_path}")

###############################################################################
# 4. CLI 入口（仍可 python minimal_realesrgan.py 直接跑）
###############################################################################
if __name__ == "__main__":
    real_esrgan_run(REAL_ESRGAN_CONFIG)