#!/usr/bin/env python3
"""
build.py — chọn nhánh của workflow duy nhất `W_qwen_6tasks.json` theo tác vụ.

Cả 6 tác vụ ảnh dùng CHUNG một file workflow. File đó chứa đủ node của cả hai
nhánh; hàm `build()` bật nhánh phù hợp rồi cắt phần còn lại trước khi gửi sang
ComfyUI.

VÌ SAO PHẢI CẮT: ComfyUI chạy MỌI node dẫn tới SaveImage — không có node rẽ
nhánh trong core. Để nguyên cả hai nhánh thì nó nạp cùng lúc Qwen-Image-2512
(20B) và Qwen-Image-Edit-2511 (20B) → chắc chắn hết VRAM trên RTX 5090 32GB.
Cắt nhánh ở đây chính là tương đương API của thao tác "bypass group" trong GUI.

    # dùng như thư viện
    from build import build
    wf = build("MultiRef", "Place the cat from image 1 ...",
               images=["base_cat.png", "base_sapa.png"], prefix="mref_07")

    # dùng như lệnh
    python3 build.py --task T2I --prompt "Chân dung áo dài đỏ..." -o wf.json
    python3 build.py --task LocalEdit --prompt "Change her ao dai to blue" \\
        --images base_portrait.png -o wf.json
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent
WORKFLOW = HERE / "W_qwen_6tasks.json"

# Model + tham số theo nhánh. Lấy từ _generate.py (P["qwen"] / P["edit"]),
# giữ đồng bộ nếu bên đó đổi.
BRANCH = {
    "t2i":  dict(unet="qwen_image_2512_fp8_e4m3fn.safetensors",  steps=50, cfg=4.0),
    "edit": dict(unet="qwen_image_edit_2511_fp8mixed.safetensors", steps=20, cfg=4.0),
}

# 6 tác vụ → nhánh nào, cần mấy ảnh vào.
# 4 tác vụ edit 1-ảnh khác nhau ở NỘI DUNG chỉ dẫn, không khác cấu trúc node.
TASKS = {
    "T2I":           dict(branch="t2i",  n_images=0),
    "LocalEdit":     dict(branch="edit", n_images=1),
    "GlobalEdit":    dict(branch="edit", n_images=1),
    "StructureEdit": dict(branch="edit", n_images=1),
    "RefGen":        dict(branch="edit", n_images=1),
    "MultiRef":      dict(branch="edit", n_images=2),
}

# Node chỉ thuộc một nhánh — nhánh kia không dùng thì cắt.
T2I_ONLY = ["51", "61", "71"]
EDIT_ONLY = ["21", "11", "22", "12", "13", "5", "6", "23", "24", "7"]


def build(task, prompt, images=None, prefix="out", seed=0, width=1328, height=1328):
    """Trả về API-format graph đã bật đúng nhánh cho `task`.

    task    : một trong TASKS ("T2I", "LocalEdit", ... "MultiRef")
    prompt  : mô tả cảnh (T2I) hoặc chỉ dẫn sửa (5 tác vụ còn lại)
    images  : tên file ảnh trong input/ của ComfyUI; số lượng phải khớp n_images
    prefix  : filename_prefix của SaveImage
    """
    if task not in TASKS:
        raise ValueError(f"task khong hop le: {task!r} — chon trong {list(TASKS)}")
    spec = TASKS[task]
    images = list(images or [])
    if len(images) != spec["n_images"]:
        raise ValueError(
            f"{task} can dung {spec['n_images']} anh vao, nhan duoc {len(images)}")

    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    b = BRANCH[spec["branch"]]
    wf["1"]["inputs"]["unet_name"] = b["unet"]
    wf["8"]["inputs"].update(seed=seed, steps=b["steps"], cfg=b["cfg"])
    wf["10"]["inputs"]["filename_prefix"] = prefix

    if spec["branch"] == "t2i":
        for nid in EDIT_ONLY:
            wf.pop(nid, None)
        wf["51"]["inputs"]["text"] = prompt
        wf["71"]["inputs"].update(width=width, height=height)
        wf["8"]["inputs"].update(model=["4", 0], positive=["51", 0],
                                 negative=["61", 0], latent_image=["71", 0])
    else:
        for nid in T2I_ONLY:
            wf.pop(nid, None)
        wf["5"]["inputs"]["prompt"] = prompt
        wf["11"]["inputs"]["image"] = images[0]
        # Gỡ đúng số node ảnh thừa, và gỡ luôn tham chiếu tới chúng trong CẢ hai
        # node encode — bỏ sót một bên là lỗi "ảnh ghép sai" đã gặp ngày 22/08.
        for i in (2, 3):
            key, nid = f"image{i}", str(10 + i)
            if i <= len(images):
                wf[nid]["inputs"]["image"] = images[i - 1]
            else:
                wf.pop(nid, None)
                wf["5"]["inputs"].pop(key, None)
                wf["6"]["inputs"].pop(key, None)
        wf["8"]["inputs"].update(model=["21", 0], positive=["23", 0],
                                 negative=["24", 0], latent_image=["7", 0])
    return wf


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, choices=list(TASKS))
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--images", nargs="*", default=[],
                    help="ten file anh trong input/ cua ComfyUI")
    ap.add_argument("--prefix", default="out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-o", "--out", help="ghi ra file, khong co thi in ra stdout")
    args = ap.parse_args()

    wf = build(args.task, args.prompt, args.images, args.prefix, args.seed)
    text = json.dumps(wf, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"{args.task}: {len(wf)} node -> {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
