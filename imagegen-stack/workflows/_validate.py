#!/usr/bin/env python3
"""
_validate.py — đối chiếu mọi workflow JSON với schema node đã trích từ source ComfyUI.

Bắt lỗi tên node sai / tên tham số sai / link trỏ vào node không tồn tại NGAY TẠI ĐÂY,
thay vì phát hiện khi ComfyUI báo node đỏ trên máy thuê.

    python3 _validate.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA = HERE.parent.parent / "_workspace" / "node_schemas.md"

# Node dùng trong workflow nhưng chưa trích schema — khai báo tay, đã đối chiếu docs.
EXTRA = {
    "VAEEncode":            {"pixels", "vae"},
    "InvertMask":           {"mask"},
    "ImageCompositeMasked": {"destination", "source", "x", "y", "resize_source", "mask"},
    "ImageScale":           {"image", "upscale_method", "width", "height", "crop"},
    "LoraLoaderModelOnly":  {"model", "lora_name", "strength_model"},
}

# Giá trị hợp lệ cố định, lấy nguyên văn từ source
ENUMS = {
    ("CLIPLoader", "type"): {
        "stable_diffusion","stable_cascade","sd3","stable_audio","mochi","ltxv","pixart",
        "cosmos","lumina2","wan","hidream","chroma","ace","omnigen2","qwen_image",
        "hunyuan_image","flux2","ovis","longcat_image","cogvideox","lens","pixeldit",
        "ideogram4","boogu","krea2","joyimage","mage","minimax"},
    ("UNETLoader", "weight_dtype"): {"default","fp8_e4m3fn","fp8_e4m3fn_fast","fp8_e5m2"},
    ("SaveWEBM", "codec"): {"vp9","av1"},
    ("KSampler", "sampler_name"): {
        "euler","euler_cfg_pp","euler_ancestral","euler_ancestral_cfg_pp","heun","heunpp2",
        "exp_heun_2_x0","exp_heun_2_x0_sde","dpm_2","dpm_2_ancestral","lms","dpm_fast",
        "dpm_adaptive","dpmpp_2s_ancestral","dpmpp_2s_ancestral_cfg_pp","dpmpp_sde",
        "dpmpp_sde_gpu","dpmpp_2m","dpmpp_2m_cfg_pp","dpmpp_2m_sde","dpmpp_2m_sde_gpu",
        "dpmpp_2m_sde_heun","dpmpp_2m_sde_heun_gpu","dpmpp_3m_sde","dpmpp_3m_sde_gpu",
        "ddpm","lcm","ipndm","ipndm_v","deis","res_multistep","res_multistep_cfg_pp",
        "res_multistep_ancestral","res_multistep_ancestral_cfg_pp","gradient_estimation",
        "gradient_estimation_cfg_pp","er_sde","seeds_2","seeds_3","sa_solver",
        "sa_solver_pece","ddim","uni_pc","uni_pc_bh2"},
    ("KSampler", "scheduler"): {
        "simple","sgm_uniform","karras","exponential","ddim_uniform","beta","normal",
        "linear_quadratic","kl_optimal"},
}


def load_schema():
    """Đọc node_schemas.md → {class_type: set(ten_input)}."""
    if not SCHEMA.exists():
        sys.exit(f"Không tìm thấy {SCHEMA}")
    out = {}
    for blk in re.findall(r"```\n(class_type:.*?)```", SCHEMA.read_text(encoding="utf-8"), re.S):
        ct = re.search(r"class_type:\s*(\S+)", blk).group(1)
        keys = set()
        body = blk.split("inputs:", 1)
        if len(body) > 1:
            for line in body[1].splitlines():
                if line.startswith("returns:") or not line.strip():
                    if line.startswith("returns:"):
                        break
                    continue
                m = re.match(r"\s+(\w+):", line)
                if m:
                    keys.add(m.group(1))
        out[ct] = keys
    out.update(EXTRA)
    return out


def main():
    schema = load_schema()
    files = sorted(f for f in HERE.glob("*.json"))
    if not files:
        sys.exit("Không có workflow nào")

    total_err = 0
    for f in files:
        errs = []
        wf = json.loads(f.read_text(encoding="utf-8"))
        for nid, node in wf.items():
            ct = node.get("class_type")
            if ct not in schema:
                errs.append(f"node {nid}: class_type '{ct}' không có trong schema")
                continue
            allowed = schema[ct]
            for k, v in node.get("inputs", {}).items():
                if allowed and k not in allowed:
                    errs.append(f"node {nid} ({ct}): input '{k}' không hợp lệ "
                                f"— cho phép: {sorted(allowed)}")
                if (ct, k) in ENUMS and isinstance(v, str) and v not in ENUMS[(ct, k)]:
                    errs.append(f"node {nid} ({ct}): {k}='{v}' không nằm trong danh sách hợp lệ")
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    if v[0] not in wf:
                        errs.append(f"node {nid} ({ct}): input '{k}' trỏ tới node "
                                    f"'{v[0]}' không tồn tại")
        status = "OK  " if not errs else "LỖI"
        print(f"  [{status}] {f.name}  ({len(wf)} node)")
        for e in errs:
            print(f"          ✗ {e}")
        total_err += len(errs)

    print()
    if total_err:
        print(f"{total_err} lỗi. Sửa _generate.py rồi chạy lại.")
        sys.exit(1)
    print(f"Tất cả {len(files)} workflow hợp lệ so với schema trích từ source ComfyUI.")
    print("Lưu ý: đây là kiểm tra tĩnh — vẫn phải nạp thử vào ComfyUI thật để xác nhận.")


if __name__ == "__main__":
    main()
