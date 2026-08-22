#!/usr/bin/env python3
"""
run_eval.py — bộ eval 6 tác vụ ảnh (T2I / Local / Global / Structure / RefGen /
MultiRef), 5 case mỗi tác vụ, chạy qua ComfyUI API thật.

Không phỏng đoán cấu trúc workflow: 5 case T2I dùng nguyên `W1_t2i_qwen2512.json`
làm khuôn; 20 case edit dùng nguyên `W3_product_edit.json` (1 ảnh vào) hoặc
`W4_user_edit_multiimage.json` (2 ảnh vào) làm khuôn — tức đúng cấu trúc node đã
verify trên máy thật ngày 22/08/2026 (xem docs/WORKFLOWS.md), chỉ thay ảnh/prompt.

Quy trình 2 giai đoạn vì các case edit CẦN ảnh do chính case T2I sinh ra làm input:
  1. `--stage base`  → chạy 5 case T2I, tải ảnh về, rồi COPY qua thư mục input/
     của ComfyUI trên máy chạy (qua SSH) với tên base_<key>.png
  2. `--stage edit`   → chạy 20 case edit, đọc ảnh base_<key>.png vừa có ở bước 1

    python3 run_eval.py --comfy http://HOST:PORT --token TOKEN --ssh "ssh -p PORT root@HOST" \\
        --comfy-input /workspace/ComfyUI/input --out ket_qua/ --stage base
    python3 run_eval.py --comfy http://HOST:PORT --token TOKEN \\
        --out ket_qua/ --stage edit
    python3 run_eval.py --score ket_qua/ket_qua.json
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
WORKFLOWS = HERE.parent.parent / "workflows"
EVALSET = HERE / "eval_set.json"

# Cả 6 tác vụ dùng CHUNG một workflow (workflows/W_qwen_6tasks.json);
# build() bật đúng nhánh theo task. Xem workflows/build.py.
sys.path.insert(0, str(WORKFLOWS))
from build import build  # noqa: E402


def req(comfy, token, path, data=None, timeout=30):
    url = comfy.rstrip("/") + path
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    r = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def submit(comfy, token, wf, client_id):
    out = req(comfy, token, "/prompt", {"prompt": wf, "client_id": client_id})
    if out.get("node_errors"):
        raise RuntimeError(f"node_errors: {out['node_errors']}")
    return out["prompt_id"]


def wait(comfy, token, pid, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = req(comfy, token, f"/history/{pid}", timeout=15)
        if pid in h:
            entry = h[pid]
            ms = entry["status"]["messages"]
            t0 = next(m[1]["timestamp"] for m in ms if m[0] == "execution_start")
            t1 = next((m[1]["timestamp"] for m in ms if m[0] == "execution_success"), None)
            secs = (t1 - t0) / 1000 if t1 else None
            return entry, secs
        time.sleep(2)
    raise TimeoutError(f"qua {timeout}s cho job {pid}")


def fetch(comfy, token, entry, dest: Path):
    for out in entry.get("outputs", {}).values():
        for img in out.get("images", []):
            q = urllib.parse.urlencode({
                "filename": img["filename"], "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output")})
            url = comfy.rstrip("/") + "/view?" + q
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            r = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(r, timeout=60) as resp:
                dest.write_bytes(resp.read())
            return True
    return False


def stage_base(args, evalset, skip_ids=None):
    """Case T2I: sinh ảnh nền, tải về, copy sang input/ ComfyUI qua SSH."""
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    local_bases = {}
    results = []

    cases = [c for c in evalset["cases"] if c["task"] == "T2I"]
    if skip_ids:
        cases = [c for c in cases if c["id"] not in skip_ids]
    for i, case in enumerate(cases, 1):
        wf = build("T2I", evalset["bases"][case["prompt_key"]], prefix=case["id"])
        print(f"  [base {i}/{len(cases)}] {case['id']} ({case['prompt_key']})", flush=True)
        pid = submit(args.comfy, args.token, wf, f"eval-{case['id']}")
        entry, secs = wait(args.comfy, args.token, pid, args.timeout)
        png = outdir / f"{case['id']}.png"
        fetch(args.comfy, args.token, entry, png)
        local_bases[case["prompt_key"]] = png
        results.append({**case, "image": png.name, "seconds": secs, "error": None})

    if args.ssh and args.comfy_input:
        for key, png in local_bases.items():
            dest = f"base_{key}.png"
            subprocess.run(
                f'cat "{png}" | {args.ssh} "cat > {args.comfy_input}/{dest}"',
                shell=True, check=True)
            print(f"  copied {png.name} -> {dest} (input/ ComfyUI)")
    else:
        print("  !! --ssh / --comfy-input trống — chưa copy ảnh nền sang input/ ComfyUI. "
              "Tự copy tay base_<key>.png rồi chạy --stage edit.")
    return results


def stage_edit(args, evalset, skip_ids=None):
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    results = []

    cases = [c for c in evalset["cases"] if c["task"] != "T2I"]
    if skip_ids:
        cases = [c for c in cases if c["id"] not in skip_ids]
    for i, case in enumerate(cases, 1):
        wf = build(case["task"], case["instruction"],
                   images=[f"base_{k}.png" for k in case["inputs"]],
                   prefix=case["id"])
        print(f"  [edit {i}/{len(cases)}] {case['id']} ({case['task']})", flush=True)
        try:
            pid = submit(args.comfy, args.token, wf, f"eval-{case['id']}")
            entry, secs = wait(args.comfy, args.token, pid, args.timeout)
            png = outdir / f"{case['id']}.png"
            fetch(args.comfy, args.token, entry, png)
            results.append({**case, "image": png.name, "seconds": secs, "error": None})
        except Exception as e:
            print(f"          LOI: {e}")
            results.append({**case, "image": None, "seconds": None, "error": str(e)})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy")
    ap.add_argument("--token", default="")
    ap.add_argument("--ssh", default="", help='vd: "ssh -p 20761 root@1.2.3.4"')
    ap.add_argument("--comfy-input", default="", help="duong dan input/ ComfyUI tren may chay")
    ap.add_argument("--out", default="ket_qua/")
    ap.add_argument("--stage", choices=["base", "edit", "all"], default="all")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--score")
    ap.add_argument("--only-new", action="store_true",
                     help="bo qua case da co trong ket_qua.json (id da ton tai) - "
                          "dung khi eval_set.json duoc them case moi, khong sinh lai case cu")
    args = ap.parse_args()

    if args.score:
        score(args.score)
        return

    evalset = json.loads(EVALSET.read_text(encoding="utf-8"))
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    doc_path = outdir / "ket_qua.json"
    # nap ket qua da co (chay tiep sau lan truoc, hoac lai --stage edit sau khi co --stage base)
    prior = json.loads(doc_path.read_text())["results"] if doc_path.exists() else []
    existing_ids = {r["id"] for r in prior}
    skip_ids = existing_ids if args.only_new else set()

    by_id = {r["id"]: r for r in prior}
    if args.stage in ("base", "all"):
        for r in stage_base(args, evalset, skip_ids):
            by_id[r["id"]] = r
        doc_path.write_text(json.dumps({"results": list(by_id.values())}, ensure_ascii=False, indent=2))
    if args.stage in ("edit", "all"):
        for r in stage_edit(args, evalset, skip_ids):
            by_id[r["id"]] = r

    order = [c["id"] for c in evalset["cases"]]
    results = [by_id[i] for i in order if i in by_id]
    doc_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    n_new = len(results) - len(prior)
    print(f"\nXong. {len(results)} case tong ({n_new} case moi vua chay), anh + ket_qua.json trong {outdir}/")


def score(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = doc["results"]
    from collections import defaultdict
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    print(f"{'Tac vu':<14}{'Case':>6}{'Anh OK':>8}{'Thoi gian TB':>14}")
    for task, rs in by_task.items():
        ok = sum(1 for r in rs if r.get("image"))
        secs = [r["seconds"] for r in rs if r.get("seconds")]
        avg = sum(secs) / len(secs) if secs else 0
        print(f"{task:<14}{len(rs):>6}{ok:>8}{avg:>13.1f}s")


if __name__ == "__main__":
    main()
