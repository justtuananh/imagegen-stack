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

Đường dẫn mặc định theo layout máy vast.ai (/workspace/...). Chạy máy khác thì đặt
biến môi trường COMFY_URL, COMFY_INPUT, SESSION_DIR:

    COMFY_INPUT=~/ComfyUI/input SESSION_DIR=~/app_sessions python3 app.py
"""
import argparse
import sys
from pathlib import Path

import gradio as gr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Lõi ComfyUI dùng chung với giao diện web Auralis (../web/server.py) — sửa ở
# core.py là cả hai giao diện cùng đổi, không có bản thứ hai để lệch.
from core import (  # noqa: E402
    SESSION_DIR,
    SIZES,
    build,
    comfy_alive,
    pick_task,
    run_workflow,
    stage_input,
)


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
