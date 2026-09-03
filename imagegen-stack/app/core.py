#!/usr/bin/env python3
"""
core.py — lớp lõi nói chuyện với ComfyUI, dùng chung cho mọi giao diện.

Tách ra từ app.py để giao diện Gradio (`app.py`) và giao diện web Auralis
(`../web/server.py`) dùng CHUNG một nguồn logic, không viết lại hai bản rồi lệch nhau.

Ở đây không có gì dính tới Gradio hay FastAPI — chỉ thuần ComfyUI + định tuyến tác vụ.

Đường dẫn mặc định theo layout máy vast.ai (/workspace/...). Chạy máy khác thì đặt
biến môi trường COMFY_URL, COMFY_INPUT, SESSION_DIR.
"""
import asyncio
import json
import os
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import aiohttp

HERE = Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / "workflows"
sys.path.insert(0, str(WORKFLOWS))
from build import build  # noqa: E402,F401  (re-export cho các giao diện dùng)

# Mặc định giữ đúng layout máy vast.ai; đặt biến môi trường để chạy nơi khác.
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:18188")
COMFY_INPUT = Path(os.environ.get("COMFY_INPUT", "/workspace/ComfyUI/input"))
SESSION_DIR = Path(os.environ.get("SESSION_DIR", "/workspace/app_sessions"))

# Kích thước chính thức của Qwen-Image (lấy từ model card, không tự đoán).
SIZES = {
    "Vuông 1:1 (1328×1328)":  (1328, 1328),
    "Ngang 16:9 (1664×928)":  (1664, 928),
    "Dọc 9:16 (928×1664)":    (928, 1664),
    "Ngang 4:3 (1472×1140)":  (1472, 1140),
    "Dọc 3:4 (1140×1472)":    (1140, 1472),
}

# Từ khoá cho biết người dùng đang muốn SỬA ảnh sẵn có chứ không tạo ảnh mới.
# Chỉ dùng khi chế độ = Tự động và trong phiên đã có ảnh.
EDIT_HINTS_VI = [
    "đổi", "thay", "xoá", "xóa", "bỏ", "thêm", "chuyển", "biến", "sửa", "chỉnh",
    "tăng", "giảm", "làm cho", "làm nó", "cho nó", "bớt", "ghép", "cắt", "quay",
    "zoom", "phóng to", "thu nhỏ", "nền thành", "màu thành", "lại thành",
]
EDIT_HINTS_EN = [
    "change", "replace", "remove", "delete", "add", "turn", "make", "convert",
    "edit", "swap", "crop", "zoom", "rotate", "keep", "put", "place",
]
# Từ khoá ép TẠO MỚI dù đang có ảnh trong phiên.
NEW_HINTS = [
    "tạo ảnh mới", "ảnh mới", "vẽ mới", "tạo một", "tạo 1", "sinh ảnh",
    "new image", "generate a", "create a", "draw a",
]


# ── ComfyUI API ───────────────────────────────────────────────────────────────
def _req(path, data=None, timeout=30):
    r = urllib.request.Request(
        COMFY + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def comfy_alive():
    try:
        _req("/system_stats", timeout=5)
        return True
    except Exception:
        return False


class ProgressWatcher:
    """Nghe websocket của ComfyUI để lấy tiến độ THẬT theo từng bước lấy mẫu.

    ComfyUI chỉ phát tiến độ qua websocket — REST không có endpoint nào cho biết
    đang ở bước mấy. Nghe hụt thì vẫn chạy bình thường, chỉ mất thanh tiến độ
    (rơi về đếm giây), nên lỗi ở đây không được phép làm hỏng việc sinh ảnh.
    """

    def __init__(self, client_id):
        self.client_id = client_id
        self.state = {"value": 0, "max": 0, "done": False, "error": None}
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._t = threading.Thread(target=lambda: asyncio.run(self._listen()), daemon=True)

    def start(self):
        self._t.start()
        self._ready.wait(timeout=3)   # nối xong mới gửi job, tránh hụt tin nhắn đầu

    def stop(self):
        self._stop.set()

    async def _listen(self):
        url = COMFY.replace("http://", "ws://") + f"/ws?clientId={self.client_id}"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.ws_connect(url, heartbeat=20) as ws:
                    self._ready.set()
                    async for msg in ws:
                        if self._stop.is_set():
                            break
                        if msg.type is not aiohttp.WSMsgType.TEXT:
                            continue
                        d = json.loads(msg.data)
                        kind, data = d.get("type"), d.get("data", {})
                        if kind == "progress":
                            self.state["value"] = data.get("value", 0)
                            self.state["max"] = data.get("max", 0)
                        elif kind == "executing" and data.get("node") is None:
                            self.state["done"] = True
                        elif kind == "execution_error":
                            self.state["error"] = data.get("exception_message")
        except Exception:
            pass          # mất websocket thì thôi, không ảnh hưởng việc sinh ảnh
        finally:
            self._ready.set()


def run_workflow(wf, timeout=600):
    """Generator. Trả ra ("tiến độ", bước, tổng_bước, giây) trong lúc chạy,
    rồi ("xong", đường_dẫn_ảnh, số_giây) khi hoàn tất."""
    cid = f"app-{uuid.uuid4().hex[:8]}"
    watcher = ProgressWatcher(cid)
    watcher.start()
    t_start = time.time()
    try:
        out = _req("/prompt", {"prompt": wf, "client_id": cid})
        if out.get("node_errors"):
            raise RuntimeError(f"ComfyUI từ chối graph: {out['node_errors']}")
        pid = out["prompt_id"]

        deadline = time.time() + timeout
        last_poll = 0.0
        while time.time() < deadline:
            if watcher.state["error"]:
                raise RuntimeError(watcher.state["error"])

            # hỏi /history thưa thôi (1.5s/lần), còn tiến độ thì cập nhật liên tục
            now = time.time()
            if now - last_poll < 1.5:
                yield ("tiến độ", watcher.state["value"], watcher.state["max"],
                       now - t_start)
                time.sleep(0.35)
                continue
            last_poll = now

            h = _req(f"/history/{pid}", timeout=15)
            if pid not in h:
                yield ("tiến độ", watcher.state["value"], watcher.state["max"],
                       now - t_start)
                continue
            entry = h[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                err = next((m[1] for m in msgs if m[0] == "execution_error"), {})
                raise RuntimeError(
                    f"{err.get('node_type', '?')}: {err.get('exception_message', 'lỗi không rõ')}")
            ms = status.get("messages", [])
            t0 = next((m[1]["timestamp"] for m in ms if m[0] == "execution_start"), None)
            t1 = next((m[1]["timestamp"] for m in ms if m[0] == "execution_success"), None)
            secs = (t1 - t0) / 1000 if t0 and t1 else None

            for o in entry.get("outputs", {}).values():
                for img in o.get("images", []):
                    q = urllib.parse.urlencode({
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output")})
                    with urllib.request.urlopen(COMFY + "/view?" + q, timeout=120) as r:
                        blob = r.read()
                    SESSION_DIR.mkdir(parents=True, exist_ok=True)
                    dest = SESSION_DIR / f"{uuid.uuid4().hex}.png"
                    dest.write_bytes(blob)
                    yield ("xong", dest, secs or (time.time() - t_start))
                    return
            raise RuntimeError("Chạy xong nhưng không có ảnh ra.")
        raise TimeoutError(f"Quá {timeout}s chưa xong.")
    finally:
        watcher.stop()


def stage_input(src: Path) -> str:
    """Copy ảnh vào input/ của ComfyUI, trả về tên file để LoadImage dùng."""
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    name = f"app_{uuid.uuid4().hex[:12]}.png"
    shutil.copyfile(src, COMFY_INPUT / name)
    return name


# ── quyết định nhánh ──────────────────────────────────────────────────────────
def pick_task(message, n_uploaded, last_image, mode):
    """Trả về (task, dùng_ảnh_cũ, giải_thích)."""
    low = (message or "").lower()

    if mode == "Tạo ảnh mới":
        return "T2I", False, "bạn chọn chế độ tạo ảnh mới"
    if mode == "Sửa ảnh":
        if n_uploaded >= 2:
            return "MultiRef", False, "ghép 2 ảnh bạn gửi lên"
        if n_uploaded == 1:
            return "LocalEdit", False, "sửa ảnh bạn gửi lên"
        if last_image:
            return "LocalEdit", True, "sửa ảnh gần nhất trong phiên"
        return "T2I", False, "chưa có ảnh nào để sửa nên tạo ảnh mới"

    # Tự động
    if n_uploaded >= 2:
        return "MultiRef", False, "bạn gửi 2 ảnh → ghép lại"
    if n_uploaded == 1:
        if last_image and any(k in low for k in ("ghép", "kết hợp", "combine", "cả hai", "image 2")):
            return "MultiRef", True, "ghép ảnh bạn gửi với ảnh gần nhất"
        return "LocalEdit", False, "bạn gửi 1 ảnh → sửa ảnh đó"
    if last_image:
        if any(k in low for k in NEW_HINTS):
            return "T2I", False, "bạn yêu cầu ảnh mới"
        if any(k in low for k in EDIT_HINTS_VI + EDIT_HINTS_EN):
            return "LocalEdit", True, "tiếp tục sửa ảnh gần nhất"
        return "T2I", False, "câu lệnh mô tả cảnh mới → tạo ảnh mới"
    return "T2I", False, "chưa có ảnh nào → tạo ảnh mới"
