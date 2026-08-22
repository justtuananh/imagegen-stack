#!/usr/bin/env python3
"""
run_vi_test.py — chạy bộ test chữ tiếng Việt qua ComfyUI API.

Đây là CỔNG QUYẾT ĐỊNH của cả dự án: đo xem Qwen-Image-2512 có render đúng
chữ Việt có dấu không. Kết quả quyết định dùng W2A (model tự viết) hay
W2B (ghép chữ) làm đường chính.

    # sinh ảnh cho cả 30 case
    python3 run_vi_test.py --comfy http://127.0.0.1:8188 --out ket_qua/

    # chấm điểm sau khi đã xem ảnh
    python3 run_vi_test.py --score ket_qua/ket_qua.json
"""
import argparse
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
WF = HERE.parent / "workflows" / "W2A_poster_text_native.json"
TESTSET = HERE / "vi_text_testset.json"

VERDICTS = ["dung", "sai_dau", "sai_chu", "khong_doc_duoc"]


def post(comfy, wf):
    req = urllib.request.Request(
        comfy.rstrip("/") + "/prompt",
        data=json.dumps({"prompt": wf}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["prompt_id"]


def wait(comfy, pid, timeout=900):
    """Chờ job xong. ComfyUI chạy tuần tự nên cứ hỏi /history."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    comfy.rstrip("/") + f"/history/{pid}", timeout=15) as r:
                h = json.load(r)
            if pid in h:
                return h[pid]
        except urllib.error.URLError:
            pass
        time.sleep(2)
    raise TimeoutError(f"Quá {timeout}s cho job {pid}")


def fetch(comfy, info, dest: Path):
    """Tải ảnh đầu ra về."""
    for out in info.get("outputs", {}).values():
        for img in out.get("images", []):
            q = urllib.parse.urlencode({
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output")})
            with urllib.request.urlopen(comfy.rstrip("/") + "/view?" + q, timeout=60) as r:
                dest.write_bytes(r.read())
            return True
    return False


def generate(args):
    ts = json.loads(TESTSET.read_text(encoding="utf-8"))
    base = json.loads(WF.read_text(encoding="utf-8"))
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)

    # tìm node prompt và node seed để thay giá trị
    pos_node = next(n for n, v in base.items()
                    if v["class_type"] == "CLIPTextEncode" and "TEXT_HERE" in v["inputs"]["text"])
    ks_node = next(n for n, v in base.items() if v["class_type"] == "KSampler")

    results = []
    for i, case in enumerate(ts["cases"], 1):
        text = unicodedata.normalize("NFC", case["text"])
        wf = json.loads(json.dumps(base))
        wf[pos_node]["inputs"]["text"] = ts["prompt_template"].format(text=text)
        wf[ks_node]["inputs"]["seed"] = args.seed

        print(f"  [{i:2d}/{len(ts['cases'])}] {case['id']}  {text!r}", flush=True)
        try:
            pid = post(args.comfy, wf)
            info = wait(args.comfy, pid, args.timeout)
            png = outdir / f"{case['id']}.png"
            ok = fetch(args.comfy, info, png)
            results.append({**case, "image": png.name if ok else None,
                            "verdict": None, "error": None if ok else "khong lay duoc anh"})
        except Exception as e:
            print(f"          LỖI: {e}")
            results.append({**case, "image": None, "verdict": None, "error": str(e)})

    doc = {"model": args.label, "seed": args.seed,
           "prompt_template": ts["prompt_template"], "results": results}
    (outdir / "ket_qua.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nXong. Ảnh ở {outdir}/")
    print(f"Giờ mở từng ảnh, điền \"verdict\" vào {outdir}/ket_qua.json")
    print(f"  giá trị hợp lệ: {' | '.join(VERDICTS)}")
    print(f"Rồi chạy: python3 run_vi_test.py --score {outdir}/ket_qua.json")


def score(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = doc["results"]
    unscored = [r for r in rows if r["verdict"] not in VERDICTS]
    if unscored:
        print(f"Còn {len(unscored)}/{len(rows)} case chưa chấm. "
              f"Điền 'verdict' cho hết rồi chạy lại.")
        return

    print(f"\nKẾT QUẢ — {doc['model']}\n")
    print(f"{'Tầng':<6}{'Nội dung':<34}{'Đúng':>6}{'Tổng':>6}{'Tỉ lệ':>9}")
    print("-" * 61)
    names = {1: "Dấu thanh cơ bản", 2: "Nguyên âm riêng (ă â ê ô ơ ư đ)",
             3: "Tổ hợp khó (ế ộ ữ ợ)", 4: "Câu thật"}
    tot_ok = 0
    for t in (1, 2, 3, 4):
        g = [r for r in rows if r["tier"] == t]
        ok = sum(1 for r in g if r["verdict"] == "dung")
        tot_ok += ok
        print(f"{t:<6}{names[t]:<34}{ok:>6}{len(g):>6}{ok/len(g)*100:>8.0f}%")
    print("-" * 61)
    print(f"{'':<40}{tot_ok:>6}{len(rows):>6}{tot_ok/len(rows)*100:>8.0f}%\n")

    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    for v in VERDICTS:
        if c[v]:
            print(f"  {v:<18}{c[v]:>3}")

    pct = tot_ok / len(rows)
    print()
    if pct >= 0.9:
        print("→ W2A dùng được. Vẫn nên giữ W2B cho chữ quan trọng.")
    elif pct >= 0.5:
        print("→ W2A không đáng tin. Dùng W2B làm đường chính.")
    else:
        print("→ W2A hỏng. Chỉ dùng W2B. Đúng như dự đoán từ khảo sát.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy", default="http://127.0.0.1:8188")
    ap.add_argument("--out", default="ket_qua")
    ap.add_argument("--label", default="Qwen-Image-2512")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--score", help="Chấm điểm file ket_qua.json đã điền verdict")
    a = ap.parse_args()
    score(a.score) if a.score else generate(a)
