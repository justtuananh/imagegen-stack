#!/usr/bin/env python3
"""
_generate.py — sinh toàn bộ workflow ComfyUI dạng API-format.

Mọi tên node và tên tham số ở đây lấy từ _workspace/node_schemas.md, trích trực tiếp
từ source ComfyUI — không phỏng đoán.

Tham số sinh ảnh (steps/cfg/shift/sampler) gom hết vào khối P bên dưới: chỉnh một chỗ,
chạy lại script là toàn bộ workflow cập nhật theo.

    python3 _generate.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

# ── FILE MODEL ────────────────────────────────────────────────────────────────
M = {
    "t2i":      "qwen_image_2512_fp8_e4m3fn.safetensors",
    "edit":     "qwen_image_edit_2511_fp8mixed.safetensors",
    "video":    "wan2.2_ti2v_5B_fp16.safetensors",
    "clip_qwen": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    "clip_wan":  "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "vae_qwen":  "qwen_image_vae.safetensors",
    "vae_wan":   "wan2.2_vae.safetensors",
}

# ── THAM SỐ SINH ─────────────────────────────────────────────────────────────
# Lấy từ template chính thức trong Comfy-Org/workflow_templates, đối chiếu với
# model card + config gốc của tác giả. KHÔNG phải giá trị tự đoán.
#
#   image_qwen_Image_2512.json          → Qwen-Image-2512
#   image_qwen_image_edit_2511.json     → Qwen-Image-Edit-2511
#   video_wan2_2_5B_ti2v.json           → Wan2.2-TI2V-5B
P = {
    # Qwen-Image-2512: model card ghi num_inference_steps=50, true_cfg_scale=4.0 — khớp template.
    "qwen":      dict(steps=50, cfg=4.0, sampler="euler",  scheduler="simple", shift=3.1),
    "qwen_fast": dict(steps=4,  cfg=1.0, sampler="euler",  scheduler="simple", shift=3.1),

    # Qwen-Image-Edit-2511: template ghi 40 bước, nhưng note trong chính template nói
    # "Comfy tuned = 20 steps / cfg 4.0" cũng chạy tốt. Dùng 20 cho nhanh, đổi lên 40 nếu cần.
    "edit":      dict(steps=20, cfg=4.0, sampler="euler",  scheduler="simple", shift=3.1),
    "edit_fast": dict(steps=4,  cfg=1.0, sampler="euler",  scheduler="simple", shift=3.1),

    # Wan2.2-TI2V-5B: template ComfyUI dùng shift=8/steps=20; repo gốc Wan-AI dùng
    # shift=5.0/steps=50. Hai nguồn LỆCH NHAU — mặc định lấy bản ComfyUI (nhanh hơn),
    # đổi sang "wan_ref" nếu muốn bám đúng tham chiếu của tác giả.
    "wan":       dict(steps=20, cfg=5.0, sampler="uni_pc", scheduler="simple", shift=8.0),
    "wan_ref":   dict(steps=50, cfg=5.0, sampler="uni_pc", scheduler="simple", shift=5.0),
}

# LoRA tăng tốc. LƯU Ý: KHÔNG tồn tại Lightning LoRA cho Wan2.2-TI2V-5B —
# lightx2v đã thử và bỏ ("didn't get good results"), repo chỉ có bản A14B.
LORA = {
    "qwen": "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
    "edit": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
}

# Negative chính thức của Qwen (tiếng Trung, dùng nguyên văn trong template) +
# phần chống lệch văn hoá thêm vào cho bối cảnh Việt Nam.
NEG_QWEN_OFFICIAL = ("低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，"
                     "过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲")
NEG_QWEN_DRIFT = "chinese style, japanese style, qipao, kimono, chinese characters"
NEG_QWEN = NEG_QWEN_OFFICIAL + "，" + NEG_QWEN_DRIFT

# Negative chính thức của Wan (nguyên văn từ wan/configs/shared_config.py)
NEG_WAN = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，"
           "最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，"
           "画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，"
           "杂乱的背景，三条腿，背景人很多，倒着走")

# Qwen-Image-Edit-2511 dùng negative RỖNG theo quy ước (model card: negative_prompt=" ").
# Áp dụng cho CẢ W2C — bản cũ W2C dùng "blurry, low quality, distorted" là lệch quy ước.
NEG_EDIT = " "

VIDEO = dict(width=1280, height=704, length=121, fps=24.0)  # width/height BỘI SỐ 32


def qwen_base(unet, positive, negative, shift, lora=None):
    """Khối nạp model + encode prompt dùng chung cho mọi workflow Qwen.

    lora: tên file Lightning LoRA. Nếu truyền vào thì chèn LoraLoaderModelOnly
    (strength 1.0) — và PHẢI dùng kèm bộ tham số *_fast (steps=4, cfg=1).
    Ghép nhầm (LoRA + cfg 4 / steps 50) là nguyên nhân lỗi phổ biến nhất:
    ảnh ra vỡ khối, quá bão hoà.
    """
    base = {
        "1":  {"class_type": "UNETLoader",
               "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2":  {"class_type": "CLIPLoader",
               "inputs": {"clip_name": M["clip_qwen"], "type": "qwen_image"}},
        "3":  {"class_type": "VAELoader", "inputs": {"vae_name": M["vae_qwen"]}},
        "4":  {"class_type": "ModelSamplingAuraFlow",
               "inputs": {"model": ["1", 0], "shift": shift}},
        "5":  {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": positive}},
        "6":  {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": negative}},
    }
    if lora:
        base["20"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["1", 0], "lora_name": lora, "strength_model": 1.0}}
        base["4"]["inputs"]["model"] = ["20", 0]
    return base


def ksampler(node, model, pos, neg, latent, p, seed=0, denoise=1.0):
    return {node: {"class_type": "KSampler", "inputs": {
        "model": model, "positive": pos, "negative": neg, "latent_image": latent,
        "seed": seed, "steps": p["steps"], "cfg": p["cfg"],
        "sampler_name": p["sampler"], "scheduler": p["scheduler"], "denoise": denoise}}}


def W1():
    """Sinh ảnh cơ bản — Qwen-Image-2512."""
    p = P["qwen"]
    wf = qwen_base(M["t2i"],
                   "PROMPT_EN_HERE — do vi_prompt_layer.py sinh ra",
                   NEG_QWEN, p["shift"])
    wf["7"] = {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": 1328, "height": 1328, "batch_size": 1}}
    wf.update(ksampler("8", ["4", 0], ["5", 0], ["6", 0], ["7", 0], p))
    wf["9"]  = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    wf["10"] = {"class_type": "SaveImage",
                "inputs": {"images": ["9", 0], "filename_prefix": "W1_t2i"}}
    return wf


def W2A():
    """Poster để MODEL tự viết chữ Việt — workflow để ĐO, không phải để tin."""
    p = P["qwen"]
    wf = qwen_base(
        M["t2i"],
        'a clean minimal poster on a plain background, the text "TEXT_HERE" '
        'written clearly in large bold letters, centered, sharp typography',
        NEG_QWEN_OFFICIAL, p["shift"])
    wf["7"] = {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": 1024, "height": 1024, "batch_size": 1}}
    wf.update(ksampler("8", ["4", 0], ["5", 0], ["6", 0], ["7", 0], p))
    wf["9"]  = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    wf["10"] = {"class_type": "SaveImage",
                "inputs": {"images": ["9", 0], "filename_prefix": "W2A_native_text"}}
    return wf


def W2B():
    """Poster ghép chữ — ĐƯỜNG CHÍNH.

    Nền do model sinh (chừa chỗ trống), chữ do Pillow dựng, ComfyUI ghép lại.
    Chữ đúng 100% vì không đi qua model.

    Trước khi chạy:
      python3 ../vi/render_text.py --text "Khuyến mãi 50%" \\
          --out <ComfyUI>/input/vi_text.png --font ../vi/fonts/BeVietnamPro-Bold.ttf
    """
    p = P["qwen"]
    wf = qwen_base(M["t2i"],
                   "PROMPT_EN_HERE — mô tả cảnh, chừa khoảng trống cho chữ, no text",
                   NEG_QWEN, p["shift"])
    wf["7"] = {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": 1024, "height": 1328, "batch_size": 1}}
    wf.update(ksampler("8", ["4", 0], ["5", 0], ["6", 0], ["7", 0], p))
    wf["9"] = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    # lớp chữ: LoadImage trả (IMAGE, MASK); MASK của ComfyUI là 1-alpha nên phải đảo lại
    wf["11"] = {"class_type": "LoadImage", "inputs": {"image": "vi_text.png"}}
    wf["12"] = {"class_type": "InvertMask", "inputs": {"mask": ["11", 1]}}
    wf["13"] = {"class_type": "ImageCompositeMasked", "inputs": {
        "destination": ["9", 0], "source": ["11", 0],
        "x": 0, "y": 120, "resize_source": False, "mask": ["12", 0]}}
    wf["14"] = {"class_type": "SaveImage",
                "inputs": {"images": ["13", 0], "filename_prefix": "W2B_composite"}}
    return wf


def edit_workflow(prompt, prefix, n_images=1, lora=None):
    """Khung chung cho mọi workflow Qwen-Image-Edit-2511 (W2C, W3, W4).

    Bám đúng template chính thức `image_qwen_image_edit_2511.json` (đối chiếu trên
    ComfyUI thật ngày 22/08/2026). Bốn điểm dưới đây là nơi bản cũ lệch template và
    đã được đo là gây lỗi thật — đừng "đơn giản hoá" lại:

      (a) Node negative nhận Y HỆT vae + image1..N như node positive, chỉ khác prompt.
          Bản cũ chỉ truyền clip+prompt cho negative → ở cfg=4 guidance lấy hiệu giữa
          hai conditioning lệch cấu trúc → ảnh cháy màu, bệt như tranh vector, chỉ dẫn
          bị nuốt. Đo 4/4 phép thử đều dính; sửa xong hết ngay.
      (b) image1 đi qua FluxKontextImageScale TRƯỚC khi vào cả VAEEncode lẫn TextEncode.
          Ảnh test tình cờ đúng 1328x1328 nên chưa lộ, ảnh người dùng upload sẽ lộ.
          image2/3 đi thẳng, giống template.
      (c) Cả positive lẫn negative bọc qua FluxKontextMultiReferenceLatentMethod
          ("index_timestep_zero") trước KSampler — đây là node cho ghép nhiều ảnh.
      (d) CFGNorm(strength=1) đặt sau ModelSamplingAuraFlow, trước LoRA (nếu có).

    lora: tên file Lightning LoRA → chèn LoraLoaderModelOnly, PHẢI đi kèm P["edit_fast"].
    """
    p = P["edit_fast"] if lora else P["edit"]
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": M["edit"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": M["clip_qwen"], "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": M["vae_qwen"]}},
        "4": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": p["shift"]}},
        "21": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
    }
    model_out = ["21", 0]
    if lora:
        wf["20"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["21", 0], "lora_name": lora, "strength_model": 1.0}}
        model_out = ["20", 0]

    # ảnh vào: image1 là ảnh gốc (cũng là latent khởi đầu) → phải qua scale
    wf["11"] = {"class_type": "LoadImage", "inputs": {"image": "input1.png"}}
    wf["22"] = {"class_type": "FluxKontextImageScale", "inputs": {"image": ["11", 0]}}
    images = {"image1": ["22", 0]}
    for i in range(2, n_images + 1):
        nid = str(10 + i)
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": f"input{i}.png"}}
        images[f"image{i}"] = [nid, 0]

    # (a) positive và negative: cùng clip/vae/ảnh, chỉ khác prompt
    common = {"clip": ["2", 0], "vae": ["3", 0], **images}
    wf["5"] = {"class_type": "TextEncodeQwenImageEditPlus",
               "inputs": {**common, "prompt": prompt}}
    wf["6"] = {"class_type": "TextEncodeQwenImageEditPlus",
               "inputs": {**common, "prompt": NEG_EDIT}}
    # (c) bọc reference-latent method cho cả hai nhánh
    wf["23"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
        "conditioning": ["5", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["24"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
        "conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}}

    wf["7"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["22", 0], "vae": ["3", 0]}}
    wf.update(ksampler("8", model_out, ["23", 0], ["24", 0], ["7", 0], p))
    wf["9"]  = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    wf["10"] = {"class_type": "SaveImage",
                "inputs": {"images": ["9", 0], "filename_prefix": prefix}}
    return wf


def wan_workflow(prefix, with_start_image):
    """W5A (text→video) và W5B (ảnh→video) — chỉ khác nhau ở start_image."""
    p = P["wan"]
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": M["video"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": M["clip_wan"], "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": M["vae_wan"]}},
        "4": {"class_type": "ModelSamplingSD3",
              "inputs": {"model": ["1", 0], "shift": p["shift"]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0],
            "text": "PROMPT_EN_HERE — mô tả CHUYỂN ĐỘNG, không chỉ cảnh tĩnh"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0],
            "text": NEG_WAN}},
    }
    lat = {"vae": ["3", 0], "width": VIDEO["width"], "height": VIDEO["height"],
           "length": VIDEO["length"], "batch_size": 1}
    if with_start_image:
        # khung đầu: nối thẳng đầu ra của W1/W2B vào đây để biến poster thành video
        wf["11"] = {"class_type": "LoadImage", "inputs": {"image": "start_frame.png"}}
        # BẮT BUỘC resize: Qwen-Image xuất 1328x1328, không chia hết cho 32.
        # Đưa thẳng vào Wan22ImageToVideoLatent sẽ lỗi kích thước.
        wf["12"] = {"class_type": "ImageScale", "inputs": {
            "image": ["11", 0], "width": VIDEO["width"], "height": VIDEO["height"],
            "upscale_method": "lanczos", "crop": "center"}}
        lat["start_image"] = ["12", 0]
    wf["7"] = {"class_type": "Wan22ImageToVideoLatent", "inputs": lat}
    wf.update(ksampler("8", ["4", 0], ["5", 0], ["6", 0], ["7", 0], p))
    wf["9"]  = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    # SaveWEBM chứ không phải SaveVideo: SaveVideo.codec là DynamicCombo lồng nhau,
    # không viết tay được — phải export từ ComfyUI thật.
    wf["10"] = {"class_type": "SaveWEBM", "inputs": {
        "images": ["9", 0], "filename_prefix": prefix,
        "codec": "vp9", "fps": VIDEO["fps"], "crf": 32.0}}
    return wf


def W_ALL():
    """MỘT workflow cho cả 6 tác vụ ảnh — thay cho bộ W1 + W3 + W4 cũ.

    File chứa ĐỦ node của cả hai nhánh; `build.py` bật nhánh theo task người dùng
    chọn rồi mới gửi đi. Phải cắt nhánh không dùng vì ComfyUI chạy MỌI node dẫn
    tới SaveImage — để nguyên cả hai nhánh sẽ nạp cùng lúc 2 model 20B, chắc chắn
    hết VRAM trên 32GB.

    Nhánh A — T2I (Qwen-Image-2512, không ảnh vào):
        51 positive · 61 negative · 71 EmptySD3LatentImage
    Nhánh B — Edit (Qwen-Image-Edit-2511, 1..3 ảnh vào):
        21 CFGNorm · 11/12/13 LoadImage · 22 scale · 5/6 encode · 23/24 ref · 7 VAEEncode
    Dùng chung: 1 UNETLoader (đổi tên file model theo nhánh) · 2 CLIP · 3 VAE ·
        4 ModelSamplingAuraFlow · 8 KSampler · 9 VAEDecode · 10 SaveImage
    """
    pt, pe = P["qwen"], P["edit"]
    wf = {
        # ── dùng chung ────────────────────────────────────────────────────────
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": M["t2i"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": M["clip_qwen"], "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": M["vae_qwen"]}},
        "4": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": pt["shift"]}},

        # ── nhánh A: T2I ──────────────────────────────────────────────────────
        "51": {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": "PROMPT_HERE"}},
        "61": {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": NEG_QWEN}},
        "71": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": 1328, "height": 1328, "batch_size": 1}},

        # ── nhánh B: Edit ─────────────────────────────────────────────────────
        "21": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "11": {"class_type": "LoadImage", "inputs": {"image": "input1.png"}},
        "22": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["11", 0]}},
        "12": {"class_type": "LoadImage", "inputs": {"image": "input2.png"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": "input3.png"}},
    }
    common = {"clip": ["2", 0], "vae": ["3", 0],
              "image1": ["22", 0], "image2": ["12", 0], "image3": ["13", 0]}
    wf["5"] = {"class_type": "TextEncodeQwenImageEditPlus",
               "inputs": {**common, "prompt": "EDIT_INSTRUCTION_HERE"}}
    wf["6"] = {"class_type": "TextEncodeQwenImageEditPlus",
               "inputs": {**common, "prompt": NEG_EDIT}}
    wf["23"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
        "conditioning": ["5", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["24"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {
        "conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["7"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["22", 0], "vae": ["3", 0]}}

    # ── đuôi dùng chung (mặc định nối nhánh A; build.py đấu lại theo task) ────
    wf.update(ksampler("8", ["4", 0], ["51", 0], ["61", 0], ["71", 0], pt))
    wf["9"]  = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    wf["10"] = {"class_type": "SaveImage",
                "inputs": {"images": ["9", 0], "filename_prefix": "W_out"}}
    return wf


ALL = {
    "W_qwen_6tasks": W_ALL(),
}

if __name__ == "__main__":
    for name, wf in ALL.items():
        out = HERE / f"{name}.json"
        out.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {name}.json  ({len(wf)} node)")
