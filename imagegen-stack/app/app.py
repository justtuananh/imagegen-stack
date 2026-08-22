#!/usr/bin/env python3
"""
app.py — giao diện chat kiểu ChatGPT cho bộ workflow ảnh (Qwen-Image-2512 +
Qwen-Image-Edit-2511), chạy trên ComfyUI.

Người dùng gõ mô tả → ra ảnh. Gửi kèm ảnh (hoặc nói tiếp về ảnh vừa tạo) → sửa ảnh.
Lịch sử hội thoại được giữ: mỗi lượt sửa mặc định áp lên ẢNH MỚI NHẤT của phiên,
nên "tạo con mèo" → "thêm cái mũ" → "đổi nền thành bãi biển" nối tiếp nhau đúng ý.

Chạy TRÊN máy có ComfyUI (dùng cổng nội bộ 127.0.0.1:18188, không cần token):

    python3 app.py --share            # in ra link công khai *.gradio.live
    python3 app.py --port 7860        # chỉ chạy nội bộ
    python3 app.py --share --auth user:pass   # link công khai + mật khẩu
"""
import argparse
import asyncio
import json
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import aiohttp
import gradio as gr

HERE = Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / "workflows"
sys.path.insert(0, str(WORKFLOWS))
from build import build  # noqa: E402

COMFY = "http://127.0.0.1:18188"
COMFY_INPUT = Path("/workspace/ComfyUI/input")
SESSION_DIR = Path("/workspace/app_sessions")

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


def progress_text(label, why, step, total, elapsed):
    """Dòng trạng thái người dùng nhìn thấy trong lúc chờ."""
    secs = f"{elapsed:.0f}s"
    if total:
        frac = step / total
        width = 18
        bar = "█" * int(frac * width) + "░" * (width - int(frac * width))
        return (f"⏳ **{label}** — {why}\n\n"
                f"`{bar}` {frac*100:.0f}%  ·  bước {step}/{total}  ·  {secs}")
    return (f"⏳ **{label}** — {why}\n\n"
            f"Đang nạp model vào GPU…  ·  {secs}")


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


# ── xử lý một lượt chat ───────────────────────────────────────────────────────
def new_state():
    # `msgs` là lịch sử hiển thị do CHÍNH server giữ. Cố ý KHÔNG nhận Chatbot làm
    # đầu vào: nếu nhận, lịch sử phải đi vòng client→server và Gradio 6 sẽ bác bỏ
    # các tin nhắn dạng file (thiếu trường `meta`) — lỗi đã gặp thật ngày 22/08.
    return {"last_image": None, "turns": 0, "msgs": [], "gallery": []}


def status_line(state):
    n = len(state.get("gallery", []))
    if not state.get("last_image"):
        return "🆕 Chưa có ảnh nào — gõ mô tả để tạo ảnh đầu tiên."
    idx = state["gallery"].index(state["last_image"]) + 1 \
        if state["last_image"] in state["gallery"] else n
    return (f"🖼️ Đang thao tác trên **ảnh #{idx}**  ·  {n} ảnh trong phiên  ·  "
            f"*câu lệnh sửa tiếp theo sẽ áp lên ảnh này*")


def respond(message, state, mode, size_label, seed, steps_override):
    """message là dict của MultimodalTextbox: {"text": ..., "files": [...]}"""
    state = state or new_state()
    history = state["msgs"]
    text = (message.get("text") or "").strip()
    files = [Path(f) for f in (message.get("files") or [])]

    history.append({"role": "user", "content": text or "(gửi ảnh)"})
    for f in files:
        history.append({"role": "user", "content": {"path": str(f)}})

    if not text and not files:
        history.append({"role": "assistant", "content": "Bạn nhập mô tả hoặc gửi ảnh lên nhé."})
        yield history, state, gr.update(), gr.update(), gr.update()
        return

    if not comfy_alive():
        history.append({"role": "assistant",
                        "content": "❌ Không kết nối được ComfyUI ở 127.0.0.1:18188. "
                                   "Kiểm tra service `comfyui` còn chạy không."})
        yield history, state, gr.update(), gr.update(), gr.update()
        return

    task, use_last, why = pick_task(text, len(files), state.get("last_image"), mode)

    if not text:
        text = "Describe and keep this image, improve quality." if task != "T2I" else ""
    if task == "T2I" and not text:
        history.append({"role": "assistant", "content": "Bạn mô tả ảnh muốn tạo giúp mình."})
        yield history, state, gr.update(), gr.update(), gr.update()
        return

    label = {"T2I": "Tạo ảnh mới", "LocalEdit": "Sửa ảnh", "MultiRef": "Ghép 2 ảnh"}[task]
    history.append({"role": "assistant",
                    "content": progress_text(label, why, 0, 0, 0)})
    yield history, state, gr.update(), gr.update(), gr.update()

    try:
        # gom danh sách ảnh vào theo nhánh
        images = []
        if task == "MultiRef":
            if use_last:
                images = [stage_input(files[0]), stage_input(Path(state["last_image"]))]
            else:
                images = [stage_input(files[0]), stage_input(files[1])]
        elif task == "LocalEdit":
            src = Path(state["last_image"]) if use_last else files[0]
            images = [stage_input(src)]

        w, h = SIZES[size_label]
        wf = build(task, text, images=images, prefix="app",
                   seed=int(seed), width=w, height=h)
        if steps_override and int(steps_override) > 0:
            wf["8"]["inputs"]["steps"] = int(steps_override)

        out_path = secs = None
        for ev in run_workflow(wf):
            if ev[0] == "tiến độ":
                _, step, total, elapsed = ev
                history[-1] = {"role": "assistant",
                               "content": progress_text(label, why, step, total, elapsed)}
                yield history, state, gr.update(), gr.update(), gr.update()

            else:
                _, out_path, secs = ev
    except Exception as e:
        history[-1] = {"role": "assistant", "content": f"❌ Lỗi: {e}"}
        yield history, state, gr.update(), gr.update(), gr.update()
        return

    state["last_image"] = str(out_path)
    state["turns"] = state.get("turns", 0) + 1
    state["gallery"].append(str(out_path))

    took = f"{secs:.0f}s" if secs else "?"
    history[-1] = {"role": "assistant", "content": f"✅ {label} xong ({took})."}
    history.append({"role": "assistant", "content": {"path": str(out_path)}})
    yield (history, state, gr.update(value=str(out_path)),
           gr.update(value=list(state["gallery"])), gr.update(value=status_line(state)))


def pick_from_gallery(state, evt: gr.SelectData):
    """Bấm vào ảnh trong thư viện → chọn nó làm ảnh để sửa tiếp."""
    state = state or new_state()
    gal = state.get("gallery", [])
    if evt.index is not None and 0 <= evt.index < len(gal):
        state["last_image"] = gal[evt.index]
    return state, gr.update(value=state["last_image"]), status_line(state)


def reset():
    s = new_state()
    return [], s, None, [], status_line(s)


CSS = """
/* Chuẩn ngắm: 1920×1080. Giới hạn 1680px để dòng chat không dài quá khó đọc,
   nhưng vẫn rộng gấp rưỡi mặc định của Gradio. */
.gradio-container {max-width: 1680px !important; margin: 0 auto !important;
                   padding: 0.4rem 1.2rem !important;}
footer {display: none !important;}

/* Chat cao theo cửa sổ. Trên 1080p còn ~640px cho khung chat. */
#chatbox {height: calc(100vh - 300px) !important; min-height: 360px;}

/* ẢNH TRONG CHAT: to hẳn lên (trước đây bị bó 520px) */
#chatbox img {max-width: min(720px, 92%) !important; height: auto !important;
              border-radius: 12px; cursor: zoom-in;}

/* Thanh chọn chế độ: kiểu segmented control, nằm ngay cạnh ô nhập */
#modebar {flex: 0 0 auto;}
#modebar fieldset {border: none !important; padding: 0 !important;}
#modebar .wrap {display: flex !important; gap: 6px !important;}
#modebar label {border: 1px solid var(--border-color-primary) !important;
                border-radius: 999px !important; padding: 5px 14px !important;
                margin: 0 !important; cursor: pointer; font-size: 0.9em;
                white-space: nowrap; transition: all .12s;}
#modebar label:hover {border-color: var(--color-accent) !important;}
#modebar input:checked + span, #modebar label:has(input:checked) {
    background: var(--color-accent) !important; color: #fff !important;
    border-color: var(--color-accent) !important;}

/* dòng trạng thái nhỏ, không chiếm chỗ */
#statusline p {margin: 2px 0 !important; font-size: 0.88em; opacity: .85;}

/* thư viện ảnh phiên */
#gal {height: calc(100vh - 260px) !important; min-height: 400px;}

@media (max-width: 1100px) {
  .gradio-container {padding: 0.25rem 0.6rem !important;}
  #chatbox {height: calc(100vh - 340px) !important;}
  #chatbox img {max-width: 100% !important;}
  #head-sub {display: none;}
}
"""

with gr.Blocks(title="Tạo & sửa ảnh", fill_height=True) as demo:
    state = gr.State(new_state)

    # Tuỳ chọn nâng cao ở thanh bên — CHỈ những thứ hiếm dùng. Chế độ đã được
    # đưa ra ngoài, cạnh ô nhập, vì đó là thứ bấm nhiều nhất.
    with gr.Sidebar(open=False, position="right"):
        gr.Markdown("### ⚙️ Tuỳ chọn nâng cao")
        size = gr.Dropdown(list(SIZES), value=list(SIZES)[0], label="Khung ảnh",
                           info="Chỉ áp dụng khi tạo ảnh mới.")
        seed = gr.Number(value=0, precision=0, label="Seed",
                         info="Cùng seed + cùng prompt → ra cùng ảnh.")
        steps = gr.Number(value=0, precision=0, label="Số bước (0 = mặc định)",
                          info="Mặc định: tạo mới 50, sửa 20.")
        gr.Markdown("---")
        current = gr.Image(label="Ảnh đang thao tác", height=240, interactive=False)
        clear = gr.Button("🗑️ Cuộc trò chuyện mới", variant="secondary")

    gr.Markdown(
        "### 🎨 Tạo & sửa ảnh"
        "<div id='head-sub' style='font-size:0.9em;opacity:0.72;margin-top:-4px'>"
        "Gõ mô tả để tạo · gửi ảnh 📎 hoặc nói tiếp để sửa · gửi 2 ảnh để ghép"
        " · ⚙️ góc phải cho khung ảnh / seed / số bước</div>")

    with gr.Tabs():
        with gr.Tab("💬 Trò chuyện"):
            chat = gr.Chatbot(elem_id="chatbox", show_label=False, resizable=True,
                              watermark=None)
            status = gr.Markdown(status_line(new_state()), elem_id="statusline")
            with gr.Row(equal_height=True):
                mode = gr.Radio(["Tự động", "Tạo ảnh mới", "Sửa ảnh"],
                                value="Tự động", show_label=False,
                                elem_id="modebar", container=False, scale=0)
                box = gr.MultimodalTextbox(
                    file_types=["image"], file_count="multiple", show_label=False,
                    placeholder="Mô tả ảnh muốn tạo, hoặc gửi ảnh + nói muốn sửa gì…",
                    submit_btn=True, stop_btn=True, autofocus=True,
                    container=False, scale=1)

        with gr.Tab("🖼️ Ảnh trong phiên"):
            gr.Markdown("Bấm vào một ảnh để **chọn nó làm ảnh sửa tiếp theo**. "
                        "Bấm lần nữa để xem ảnh cỡ lớn.")
            gallery = gr.Gallery(elem_id="gal", show_label=False, columns=4,
                                 object_fit="contain", preview=False,
                                 allow_preview=True)

    # Xoá ô nhập NGAY khi gửi, trước khi sinh ảnh (queue=False để chạy tức thì,
    # không xếp hàng sau job GPU). Nội dung được cất vào `pending` rồi mới đưa
    # cho respond — nếu đọc thẳng từ ô nhập thì lúc đó nó đã bị xoá rồi.
    # KHÔNG khoá ô nhập trong lúc chạy: người dùng phải gõ/đổi chế độ/xem thư
    # viện được trong lúc chờ. Lệnh gửi thêm sẽ tự xếp hàng.
    pending = gr.State()
    outputs = [chat, state, current, gallery, status]
    box.submit(
        lambda m: (m, gr.update(value=None)), [box], [pending, box], queue=False,
    ).then(respond, [pending, state, mode, size, seed, steps], outputs)

    gallery.select(pick_from_gallery, [state], [state, current, status])
    clear.click(reset, None, outputs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", action="store_true", help="tạo link công khai *.gradio.live")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--auth", default="", help='bảo vệ bằng mật khẩu, dạng "user:pass"')
    args = ap.parse_args()

    auth = tuple(args.auth.split(":", 1)) if args.auth else None
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    demo.queue(max_size=20).launch(
        server_name="0.0.0.0", server_port=args.port, css=CSS,
        theme=gr.themes.Soft(primary_hue="blue"),
        # BẮT BUỘC: ảnh sinh ra nằm ngoài thư mục làm việc, không khai báo ở đây
        # thì Gradio 6 chặn (InvalidPathError) và giao diện không hiện được ảnh nào.
        allowed_paths=[str(SESSION_DIR)],
        share=args.share, auth=auth, quiet=False, show_error=True)
