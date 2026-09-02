import os
import torch
import torch.nn.functional as F
import cv2
import numpy as np
from glob import glob
from natsort import natsorted
from runpy import run_path
from skimage import img_as_ubyte
from tqdm import tqdm
from types import SimpleNamespace

############################################################
# 🔧 USER CONFIGURATION (去噪配置)
############################################################
DEFAULTS = dict(
    task="Real_Denoising", 
    input_dir="/home/990ep/wcj_datasets/HRSC_png/100000000.png",
    result_dir="./outputs/denoised/",
    weight_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights", "real_denoising.pth"),
    device="cuda",
    tile=None,
    tile_overlap=32
)
CONFIG = SimpleNamespace(**DEFAULTS)

def load_img(filepath):
    return cv2.cvtColor(cv2.imread(filepath), cv2.COLOR_BGR2RGB)

def save_img(filepath, img):
    cv2.imwrite(filepath, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

def get_image_files(input_dir):
    extensions = ["jpg", "JPG", "png", "PNG", "jpeg", "JPEG", "bmp", "BMP"]
    if any(input_dir.endswith(ext) for ext in extensions):
        return [input_dir]
    files = []
    for ext in extensions:
        files.extend(glob(os.path.join(input_dir, f"*.{ext}")))
    return natsorted(files)

def main():
    files = get_image_files(CONFIG.input_dir)
    if not files:
        raise FileNotFoundError(f"没有在 {CONFIG.input_dir} 找到任何图片！")
    
    out_dir = os.path.join(CONFIG.result_dir, CONFIG.task)
    os.makedirs(out_dir, exist_ok=True)
    device = torch.device(CONFIG.device)

    parameters = {
        "inp_channels": 3,
        "out_channels": 3,
        "dim": 48,
        "num_blocks": [4, 6, 6, 8],
        "num_refinement_blocks": 4,
        "heads": [1, 2, 4, 8],
        "ffn_expansion_factor": 2.66,
        "bias": False,
        "LayerNorm_type": "BiasFree",  # ⚠️ 必须是 BiasFree，否则去噪模型会报错！
        "dual_pixel_task": False,
    }
    
    restormer_arch = run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "basicsr", "models", "archs", "restormer_arch.py"))
    model = restormer_arch["Restormer"](**parameters)
    model.to(device)

    checkpoint = torch.load(CONFIG.weight_path, map_location=device)
    model.load_state_dict(checkpoint["params"], strict=True)
    model.eval()

    img_multiple_of = 8 
    with torch.no_grad():
        for file_ in tqdm(files, desc="Processing"):
            if device.type == "cuda":
                torch.cuda.ipc_collect()
                torch.cuda.empty_cache()

            img = load_img(file_)
            inp = torch.from_numpy(img.copy()).float().div(255.).permute(2, 0, 1).unsqueeze(0).to(device)

            h, w = inp.shape[2:]
            H = (h + img_multiple_of) // img_multiple_of * img_multiple_of
            W = (w + img_multiple_of) // img_multiple_of * img_multiple_of
            inp = F.pad(inp, (0, W - w, 0, H - h), mode="reflect")

            if CONFIG.tile is None:
                restored = model(inp)
            else:
                tile_size = min(CONFIG.tile, H, W)
                stride = tile_size - CONFIG.tile_overlap
                h_idx = list(range(0, H - tile_size, stride)) + [H - tile_size]
                w_idx = list(range(0, W - tile_size, stride)) + [W - tile_size]

                E, Wt = torch.zeros_like(inp), torch.zeros_like(inp)
                for hi in h_idx:
                    for wi in w_idx:
                        patch = inp[..., hi:hi + tile_size, wi:wi + tile_size]
                        out_p = model(patch)
                        E[..., hi:hi + tile_size, wi:wi + tile_size].add_(out_p)
                        Wt[..., hi:hi + tile_size, wi:wi + tile_size].add_(torch.ones_like(out_p))
                restored = E.div_(Wt)

            restored = restored[..., :h, :w].clamp(0, 1)
            restored = restored.permute(0, 2, 3, 1).cpu().numpy()[0]
            save_img(os.path.join(out_dir, os.path.splitext(os.path.basename(file_))[0] + ".png"), img_as_ubyte(restored))

if __name__ == '__main__':
    main()

def run(cfg):
    """tool_use.py 统一调用入口：将外部 cfg 注入 CONFIG，再执行 main()"""
    CONFIG.input_dir    = cfg.input_dir
    CONFIG.result_dir   = cfg.result_dir
    CONFIG.weight_path  = cfg.weight_path
    CONFIG.device       = cfg.device
    CONFIG.tile         = getattr(cfg, "tile", None)
    CONFIG.tile_overlap = getattr(cfg, "tile_overlap", 32)
    main()