import os
import torch
import torch.nn.functional as F
import cv2
import numpy as np
from glob import glob
from tqdm import tqdm
from collections import OrderedDict
from types import SimpleNamespace

from models import *

############################################################
# 🔧 USER CONFIGURATION (极致精简版)
############################################################

DEFAULTS = dict(
    # ---------- 核心路径 ----------
    weight_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights", "dehazeformer-b.pth"),
    input_dir="/home/990ep/wcj_datasets/HRSC_png/100000004.png",       # 输入目录或单张图
    result_dir="./results/",  # 输出目录
    
    # ---------- 推理控制 ----------
    device="cuda",
    pad_multiple=16
)

CONFIG = SimpleNamespace(**DEFAULTS)

def get_image_files(input_dir):
    extensions = ["jpg", "JPG", "png", "PNG", "jpeg", "JPEG", "bmp", "BMP"]
    if any(input_dir.endswith(ext) for ext in extensions):
        return [input_dir]
    
    files = []
    for ext in extensions:
        files.extend(glob(os.path.join(input_dir, f"*.{ext}")))
    return files

def load_model_and_weights(cfg):
    device = torch.device(cfg.device)
    
    if not os.path.exists(cfg.weight_path):
        raise FileNotFoundError(f"找不到权重文件: {cfg.weight_path}")

    # 💡 魔法操作：直接从文件名 'dehazeformer-b.pth' 中提取架构名称 'dehazeformer-b'
    model_name = os.path.basename(cfg.weight_path).split('.')[0]
    print(f"==> 正在初始化模型架构: {model_name}")
    
    # 动态实例化模型
    network = eval(model_name.replace('-', '_'))()
    network.to(device)

    print(f"==> 正在加载权重: {cfg.weight_path}")
    state_dict = torch.load(cfg.weight_path, map_location=device)['state_dict']
    
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:] if k.startswith('module.') else k
        new_state_dict[name] = v

    network.load_state_dict(new_state_dict)
    network.eval()
    return network, device

def main():
    files = get_image_files(CONFIG.input_dir)
    if not files:
        raise FileNotFoundError(f"没有在 {CONFIG.input_dir} 找到任何图片！")
        
    os.makedirs(CONFIG.result_dir, exist_ok=True)

    network, device = load_model_and_weights(CONFIG)

    print(f"==> 开始处理图片，共 {len(files)} 张...")

    with torch.no_grad():
        for file_ in tqdm(files, desc="Dehazing"):
            img = cv2.imread(file_)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            img = img.astype(np.float32) / 255.0
            img = (img - 0.5) / 0.5 
            
            inp = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(device)
            
            h, w = inp.shape[2:]
            pad_h = (CONFIG.pad_multiple - h % CONFIG.pad_multiple) % CONFIG.pad_multiple
            pad_w = (CONFIG.pad_multiple - w % CONFIG.pad_multiple) % CONFIG.pad_multiple
            inp = F.pad(inp, (0, pad_w, 0, pad_h), mode='reflect')
            
            output = network(inp).clamp_(-1, 1)
            
            output = output[:, :, :h, :w]
            output = output * 0.5 + 0.5 
            
            out_img = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
            out_img = (out_img * 255).clip(0, 255).astype(np.uint8)
            out_img = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
            
            fname = os.path.basename(file_)
            save_path = os.path.join(CONFIG.result_dir, fname)
            cv2.imwrite(save_path, out_img)

    print(f"\n✅ 所有图片处理完毕！结果保存在: {CONFIG.result_dir}")

if __name__ == '__main__':
    main()

def run(cfg):
    """tool_use.py 统一调用入口：将外部 cfg 注入 CONFIG，再执行 main()"""
    CONFIG.weight_path  = cfg.weight_path
    CONFIG.input_dir    = cfg.input_dir
    CONFIG.result_dir   = cfg.result_dir
    CONFIG.device       = cfg.device
    CONFIG.pad_multiple = getattr(cfg, "pad_multiple", 16)
    main()