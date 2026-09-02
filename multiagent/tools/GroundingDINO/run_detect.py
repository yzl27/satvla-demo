from typing import List, Tuple, Optional
from PIL import Image
import torch
from types import SimpleNamespace
from pathlib import Path

# -----------------------------------------------------------------------------
# Grounding‑DINO internal imports
# -----------------------------------------------------------------------------
import groundingdino.datasets.transforms as T
from groundingdino.models import build_model
from groundingdino.util.slconfig import SLConfig
from groundingdino.util.utils import clean_state_dict, get_phrases_from_posmap
from groundingdino.util.vl_utils import create_positive_map_from_span
from groundingdino.util.inference import annotate


# -----------------------------------------------------------------------------
# 默认参数（可 CLI 覆盖）
# -----------------------------------------------------------------------------
DEFAULTS = {
    "CONFIG_PATH": str((Path(__file__).resolve().parent / "groundingdino" / "config" / "GroundingDINO_SwinT_OGC.py")),
    "WEIGHTS_PATH": str((Path(__file__).resolve().parent / "weights" / "groundingdino_swint_ogc.pth")),
    "IMAGE_PATH": "",  # 由流水线调用时传入实际路径
    "OUTPUT_DIR": "outputs",
    "TEXT_PROMPT": (
        "military warship."
        "cargo ship."
        "supply ship."
        "ship island."
        "aircraft."
        "submarine."
        "warship tail number."
        "building on port."
        "crosswire."
        "white runway guide lines."
        "white landing spot."
    ),
    "TOKEN_SPANS": None,
    "TEXT_THRESHOLD": None,
    "BOX_THRESHOLD": 0.18,
    "AREA_THRESHOLD": 0.5,
    "IOU_THRESHOLD": 0.20,
    "DEVICE": "cuda",
}


CONFIG = SimpleNamespace(
    config_path = DEFAULTS["CONFIG_PATH"],
    ckpt_path = DEFAULTS["WEIGHTS_PATH"],
    image = DEFAULTS["IMAGE_PATH"],
    output_dir = DEFAULTS["OUTPUT_DIR"],
    text_prompt = DEFAULTS["TEXT_PROMPT"],
    token_spans = DEFAULTS["TOKEN_SPANS"],
    box_threshold = DEFAULTS["BOX_THRESHOLD"],
    text_threshold = DEFAULTS["TEXT_THRESHOLD"],
    area_threshold = DEFAULTS["AREA_THRESHOLD"],
    iou_threshold = DEFAULTS["IOU_THRESHOLD"],
    device = DEFAULTS["DEVICE"],
)


# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------
def auto_token_spans(prompt: str) -> List[List[List[int]]]:
    """按句号 `.` 自动切分短语并返回 [[[start, end]], ...]。"""
    spans: List[List[List[int]]] = []
    cursor = 0
    for seg in prompt.split("."):
        seg = seg.strip()
        if not seg:
            cursor += 1  # 跳过这个句点本身
            continue
        start = prompt.find(seg, cursor)
        end = start + len(seg)
        spans.append([[start, end]])
        cursor = end + 1  # 包含随后的 '.'
    return spans


def load_image(path: str) -> Tuple[Image.Image, torch.Tensor]:
    img = Image.open(path).convert("RGB")
    t = T.Compose([
        T.RandomResize([800], max_size=1333),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    tensor, _ = t(img, None)
    return img, tensor


def load_model(cfg: str, ckpt: str, device: str = "cuda"):
    args = SLConfig.fromfile(cfg)
    args.device = device
    model = build_model(args)
    state = torch.load(ckpt, map_location="cpu")
    model.load_state_dict(clean_state_dict(state["model"]), strict=False)
    model.eval()
    return model.to(device)


@torch.no_grad()
def get_grounding_output(
    model: torch.nn.Module,
    image: torch.Tensor,
    caption: str,
    box_th: float,
    text_th: Optional[float],
    token_spans: Optional[List[List[List[int]]]] = None,
    device: str = "cuda",
    with_logits: bool = True,
):
    assert text_th is not None or token_spans is not None, "text_th 和 token_spans 不能同时为 None"

    caption = caption.lower().strip()
    if not caption.endswith("."):
        caption += "."

    model, image = model.to(device), image.to(device)
    out = model(image[None], captions=[caption])
    logits = out["pred_logits"].sigmoid()[0]
    boxes = out["pred_boxes"][0]

    if token_spans is None:
        scores = logits.max(1)[0]
        m = scores > box_th
        boxes_f = boxes[m].cpu()
        logits_f = logits[m]
        phrases = []
        tok = model.tokenizer
        tokenized = tok(caption)
        for log in logits_f:
            phrase = get_phrases_from_posmap(log > text_th, tokenized, tok)
            if with_logits:
                phrases.append(f"{phrase}({log.max().item():.3f})")
            else:
                phrases.append(phrase)
        return boxes_f, phrases

    # token_spans 模式
    pos_map = create_positive_map_from_span(model.tokenizer(caption), token_spans).to(device)
    logits_p = pos_map @ logits.T
    all_boxes, all_phrases = [], []
    for span, row in zip(token_spans, logits_p):
        phrase_txt = caption[span[0][0]:span[0][1]].strip()
        sel = row > box_th
        all_boxes.append(boxes[sel])
        if with_logits:
            all_phrases.extend([f"{phrase_txt}({sc:.3f})" for sc in row[sel]])
        else:
            all_phrases.extend([phrase_txt for _ in range(sel.sum().item())])
    boxes_cat = torch.cat(all_boxes, 0).cpu() if all_boxes else torch.empty((0, 4))
    return boxes_cat, all_phrases


# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------
import re
import torchvision.ops as ops
from torchvision.ops import box_convert
import numpy as np
import cv2
import matplotlib.pyplot as plt




def run(args):
    prompt = args.text_prompt
    spans = args.token_spans if args.token_spans is not None else auto_token_spans(prompt)

    if spans and args.text_threshold is not None:
        print("[Info] token_spans 已指定，自动忽略 text_threshold")
        args.text_threshold = None

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    model = load_model(args.config_path, args.ckpt_path, args.device)
    pil_img, img_tensor = load_image(args.image)

    boxes_cxcywh, phrases = get_grounding_output(
        model, img_tensor, prompt, args.box_threshold, args.text_threshold, spans, args.device
    )

    score_pat = re.compile(r"\((0?\.\d+)\)")
    scores = [float(score_pat.search(p).group(1)) if score_pat.search(p) else 0 for p in phrases]
    scores_t = torch.tensor(scores)

    # 过滤掉面积过大的框
    areas = boxes_cxcywh[:, 2] * boxes_cxcywh[:, 3]
    mask = areas < args.area_threshold
    boxes_cxcywh = boxes_cxcywh[mask]
    phrases = [phrases[i] for i, keep in enumerate(mask) if keep]
    scores_t = scores_t[mask]

    boxes_xyxy = box_convert(boxes_cxcywh, in_fmt="cxcywh", out_fmt="xyxy")
    keep = ops.nms(boxes_xyxy, scores_t, args.iou_threshold)
    boxes_cxcywh, boxes_xyxy, scores_t = boxes_cxcywh[keep], boxes_xyxy[keep], scores_t[keep]
    phrases = [phrases[i] for i in keep]

    # 注释掉自带括号里的 logits
    phrases_no_score = [re.sub(r"\(0?\.\d+\)", "", p).strip() for p in phrases]
    annot = annotate(np.array(pil_img)[:, :, ::-1].copy(), boxes_cxcywh, scores_t.tolist(), phrases_no_score)

    base = Path(args.image).stem
    out_img = Path(args.output_dir) / f"{base}_annotated.png"
    out_txt = Path(args.output_dir) / f"{base}_boxes.txt"
    cv2.imwrite(str(out_img), annot)
    print(f"[✓] 保存标注图: {out_img}")

    w, h = pil_img.size
    with open(out_txt, "w", encoding="utf-8") as f:
        for b, s, ph in zip(boxes_xyxy, scores_t.tolist(), phrases_no_score):
            x1, y1, x2, y2 = (b * torch.tensor([w, h, w, h])).int().tolist()
            f.write(f"{ph.strip()} {s:.3f} {x1} {y1} {x2} {y2}\n")
    print(f"[✓] 保存坐标文件: {out_txt}")

    try:
        plt.figure(figsize=(8, 8))
        plt.imshow(cv2.cvtColor(annot, cv2.COLOR_BGR2RGB))
        plt.axis("off")
        plt.show()
    except Exception:
        pass


# # -----------------------------------------------------------------------------
# # CLI 解析
# # -----------------------------------------------------------------------------
# def parse_args():
#     parser = argparse.ArgumentParser("GroundingDINO token‑spans runner (auto spans)")
#     parser.add_argument("-c", "--config_path", default=DEFAULTS["CONFIG_PATH"])
#     parser.add_argument("-p", "--ckpt_path", default=DEFAULTS["WEIGHTS_PATH"])
#     parser.add_argument("-i", "--image", default=DEFAULTS["IMAGE_PATH"])
#     parser.add_argument("-o", "--output_dir", default=DEFAULTS["OUTPUT_DIR"])
#     parser.add_argument("-t", "--text_prompt", default=DEFAULTS["TEXT_PROMPT"])
#     parser.add_argument("--token_spans", type=lambda s: eval(s) if s else None, default=None)
#     parser.add_argument("--box_threshold", type=float, default=DEFAULTS["BOX_THRESHOLD"])
#     parser.add_argument("--text_threshold", type=float, default=DEFAULTS["TEXT_THRESHOLD"])
#     parser.add_argument("--iou_threshold", type=float, default=DEFAULTS["IOU_THRESHOLD"])
#     parser.add_argument("--device", choices=["cpu", "cuda"], default=DEFAULTS["DEVICE"])

#     if "ipykernel" in sys.modules or hasattr(sys, "ps1"):
#         return parser.parse_known_args()[0]
#     return parser.parse_args()


if __name__ == "__main__":
    run(CONFIG)