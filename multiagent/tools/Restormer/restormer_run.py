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
from pathlib import Path
from types import SimpleNamespace

############################################################
# 🔧 USER CONFIGURATION
############################################################
DEFAULTS = {
    # Task options: Motion_Deblurring | Single_Image_Defocus_Deblurring | Deraining | Real_Denoising | Gaussian_Color_Denoising
    "task": "Motion_Deblurring",
    # Path to a single image **or** directory containing multiple images
    "input_dir": "",  # 由流水线调用时传入实际路径
    # Folder where restored images will be saved
    "output_dir": "./demo/restored/ship_restormer.png",
    # For large‑image tiling. None = use full‑res at once.
    "tile": None,            # e.g. 720
    "tile_overlap": 32,      # overlap in pixels between tiles
    # "cuda" to force GPU, "cpu" to force CPU, "auto" to pick automatically
    "device": "cuda",
}
RESTORMER_CONFIG = SimpleNamespace(**DEFAULTS)

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def load_img(filepath):
    return cv2.cvtColor(cv2.imread(filepath), cv2.COLOR_BGR2RGB)

def save_img(filepath, img):
    cv2.imwrite(filepath, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

def load_gray_img(filepath):
    return np.expand_dims(cv2.imread(filepath, cv2.IMREAD_GRAYSCALE), axis=2)

def save_gray_img(filepath, img):
    cv2.imwrite(filepath, img)

# ------------------------------------------------------------------
# Map task → weights + parameter tweaks
# ------------------------------------------------------------------
def restomer_run(cfg):
    def get_weights_and_parameters(task, parameters):
        if task == "Motion_Deblurring":
            weights = os.path.join("Motion_Deblurring", "pretrained_models", "motion_deblurring.pth")
        elif task == "Single_Image_Defocus_Deblurring":
            weights = os.path.join("Defocus_Deblurring", "pretrained_models", "single_image_defocus_deblurring.pth")
        elif task == "Deraining":
            weights = os.path.join("Deraining", "pretrained_models", "deraining.pth")
        elif task == "Real_Denoising":
            weights = os.path.join("Denoising", "pretrained_models", "real_denoising.pth")
            parameters["LayerNorm_type"] = "BiasFree"
        elif task == "Gaussian_Color_Denoising":
            weights = os.path.join("Denoising", "pretrained_models", "gaussian_color_denoising_blind.pth")
            parameters["LayerNorm_type"] = "BiasFree"
        elif task == "Gaussian_Gray_Denoising":
            weights = os.path.join("Denoising", "pretrained_models", "gaussian_gray_denoising_blind.pth")
            parameters.update({"inp_channels": 1, "out_channels": 1, "LayerNorm_type": "BiasFree"})
        else:
            raise ValueError(f"Unknown task: {task}")
        return weights, parameters

    # ------------------------------------------------------------------
    # Prepare file list
    # ------------------------------------------------------------------
    task = cfg.task
    inp_dir = cfg.input_dir
    tile = cfg.tile
    tile_step = cfg.tile_overlap

    extensions = ["jpg", "JPG", "png", "PNG", "jpeg", "JPEG", "bmp", "BMP"]
    if any(inp_dir.endswith(ext) for ext in extensions):
        files = [inp_dir]
    else:
        files = []
        for ext in extensions:
            files.extend(glob(os.path.join(inp_dir, f"*.{ext}")))
        files = natsorted(files)

    if not files:
        raise FileNotFoundError(f"No images found in {inp_dir}")

    # ------------------------------------------------------------------
    # Load model architecture & weights
    # ------------------------------------------------------------------
    parameters = {
        "inp_channels": 3,
        "out_channels": 3,
        "dim": 48,
        "num_blocks": [4, 6, 6, 8],
        "num_refinement_blocks": 4,
        "heads": [1, 2, 4, 8],
        "ffn_expansion_factor": 2.66,
        "bias": False,
        "LayerNorm_type": "WithBias",
        "dual_pixel_task": False,
    }
    weights, parameters = get_weights_and_parameters(task, parameters)
    weights = os.path.join(Path(__file__).parent, weights)
    print(os.path.join("basicsr", "models", "archs", "restormer_arch.py"))
    restormer_arch_path = os.path.join(Path(__file__).parent, "basicsr/models/archs/restormer_arch.py")
    restormer_arch = run_path(restormer_arch_path)
    model = restormer_arch["Restormer"](**parameters)

    # ---------------- device selection ----------------
    if cfg.device == "cpu":
        device = torch.device("cpu")
    elif cfg.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available!")
        device = torch.device("cuda")
    else:  # auto
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.to(device)

    checkpoint = torch.load(weights, map_location=device)
    model.load_state_dict(checkpoint["params"], strict=True)
    model.eval()

    img_multiple_of = 8
    print(f"\n ==> Running {task} on {device} with weights {weights}\n ")

    # ------------------------------------------------------------------
    # Inference loop
    # ------------------------------------------------------------------
    with torch.no_grad():
        for file_ in tqdm(files, desc="Processing"):
            if device.type == "cuda":
                torch.cuda.ipc_collect(); torch.cuda.empty_cache()

            # ---------- Load image ----------
            img = load_gray_img(file_) if task == "Gaussian_Gray_Denoising" else load_img(file_)
            inp  = torch.from_numpy(img.copy()).float().div(255.).permute(2, 0, 1).unsqueeze(0).to(device)

            # ---------- Padding ----------
            h, w = inp.shape[2:]
            H = (h + img_multiple_of) // img_multiple_of * img_multiple_of
            W = (w + img_multiple_of) // img_multiple_of * img_multiple_of
            inp = F.pad(inp, (0, W - w, 0, H - h), mode="reflect")

            # ---------- Forward pass ----------
            if tile is None:
                restored = model(inp)
            else:
                tile_size = min(tile, H, W)
                if tile_size % 8 != 0:
                    raise ValueError("tile size must be multiple of 8")
                stride = tile_size - tile_step
                h_idx = list(range(0, H - tile_size, stride)) + [H - tile_size]
                w_idx = list(range(0, W - tile_size, stride)) + [W - tile_size]

                E = torch.zeros_like(inp)
                Wt = torch.zeros_like(inp)
                for hi in h_idx:
                    for wi in w_idx:
                        patch = inp[..., hi:hi + tile_size, wi:wi + tile_size]
                        out_p = model(patch)
                        mask  = torch.ones_like(out_p)
                        E[..., hi:hi + tile_size, wi:wi + tile_size].add_(out_p)
                        Wt[..., hi:hi + tile_size, wi:wi + tile_size].add_(mask)
                restored = E.div_(Wt)

            # ---------- Unpad & save ----------
            restored = restored[..., :h, :w].clamp(0, 1)
            restored = restored.permute(0, 2, 3, 1).cpu().numpy()[0]
            restored = img_as_ubyte(restored)

            # base = Path(cfg.input_dir).stem
            # parent = Path(cfg.input_dir).parent
            # save_path = parent / "temp" / f"{base}_restormer.png"
            save_path = cfg.output_dir

            if task == "Gaussian_Gray_Denoising":
                save_gray_img(save_path, restored)
            else:
                save_img(save_path, restored)

        print(f"\nRestored images saved in → {save_path}\n")

if __name__ == "__main__":
    restomer_run(RESTORMER_CONFIG)
