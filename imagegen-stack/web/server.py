#!/usr/bin/env python3
"""
server.py — backend cho giao diện web Auralis.

Mỏng có chủ đích: mọi thứ dính tới ComfyUI đều nằm ở `app/core.py` — cùng lớp lõi mà
giao diện Gradio (`app/app.py`) đang dùng. Ở đây chỉ có HTTP, hàng đợi job, và ánh xạ
"phong cách / khung ảnh" của giao diện sang tham số thật của model.

Mỗi chức năng nhìn thấy trên giao diện đều có một endpoint tương ứng bên dưới —
kể cả danh sách lựa chọn (phong cách, khung ảnh, gợi ý, hướng dẫn): chúng do server
phát ra để không phải khai hai lần rồi lệch nhau.

    COMFY_INPUT=~/ComfyUI/input SESSION_DIR=~/app_sessions \
        python3 -m uvicorn server:app --port 7860       # chạy từ trong web/

Số lượng ảnh 1/2/4 = ngần ấy lần gửi `/prompt` riêng, seed khác nhau — ảnh hiện dần
từng cái. KHÔNG dùng batch_size: mỗi ảnh xong là đẩy ngay cho người dùng thấy.
"""
import json
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))
sys.path.insert(0, str(HERE))

from core import (  # noqa: E402
    SESSION_DIR,
    SIZES,
    build,
    comfy_alive,
    pick_task,
    run_workflow,
    stage_input,
)
from content_vi import EDIT_CHIPS, FILTERS, HELP, QUOTES, SUGGESTIONS  # noqa: E402
from store import Store  # noqa: E402
from styles_vi import RATIO_CSS, RATIO_TO_SIZE, STYLE_SUFFIX, apply_style  # noqa: E402

app = FastAPI(title="Auralis")

UPLOADS = SESSION_DIR / "uploads"
STORE = Store(SESSION_DIR / "auralis.json")
JOBS = {}
JOBS_LOCK = threading.Lock()


class GenReq(BaseModel):
    prompt: str
    chat: str | None = None
    kind: str = "new"          # "new" | "edit"
    style: str = "Ảnh thật"
    ratio: str = "Vuông"
    count: int = 1
    images: list[str] = []     # ảnh người dùng đính kèm (id từ /api/upload)
    base_image: str | None = None   # ảnh sẵn có trong phiên, để sửa tiếp


def _resolve(img_id: str) -> Path:
    """id ảnh → đường dẫn thật. Chặn path traversal: chỉ nhận tên file trần."""
    name = Path(img_id).name
    for folder in (SESSION_DIR, UPLOADS):
        p = folder / name
        if p.is_file():
            return p
    raise HTTPException(404, f"Không có ảnh {name}")


# ── lựa chọn hiển thị trên giao diện ─────────────────────────────────────────
@app.get("/api/options")
def options():
    """Nguồn thật cho mọi danh sách lựa chọn trong giao diện.

    Để ở server vì phong cách và khung ảnh phải khớp với `styles_vi.py` và
    `core.SIZES`; khai lại bên JS là sớm muộn cũng lệch.
    """
    return {
        "styles": list(STYLE_SUFFIX.keys()),
        "ratios": [{"label": k, "ar": RATIO_CSS[k],
                    "size": SIZES[RATIO_TO_SIZE[k]]} for k in RATIO_TO_SIZE],
        "counts": [1, 2, 4],
        "editChips": EDIT_CHIPS,
        "filters": FILTERS,
        "suggestions": SUGGESTIONS,
        "help": HELP,
        "quotes": QUOTES,
    }


@app.get("/api/health")
def health():
    return {"comfy": comfy_alive()}


# ── cuộc trò chuyện ──────────────────────────────────────────────────────────
@app.get("/api/chats")
def list_chats():
    return {"chats": STORE.chats()}


@app.post("/api/chats")
def create_chat():
    return STORE.new_chat()


@app.patch("/api/chats/{cid}")
def rename_chat(cid: str, title: str = Body(..., embed=True)):
    c = STORE.rename_chat(cid, title)
    if not c:
        raise HTTPException(404, "Không có cuộc trò chuyện này")
    return c


@app.delete("/api/chats/{cid}")
def delete_chat(cid: str):
    STORE.delete_chat(cid)
    return {"ok": True}


@app.get("/api/chats/{cid}/messages")
def chat_messages(cid: str):
    return {"messages": STORE.messages(cid)}


# ── thư viện ảnh ─────────────────────────────────────────────────────────────
@app.get("/api/gallery")
def gallery(filter: str = "Tất cả"):
    return {"images": STORE.gallery(filter)}


@app.get("/api/image/{img_id}")
def image(img_id: str, download: int = 0):
    p = _resolve(img_id)
    headers = {"Content-Disposition": f'attachment; filename="{p.name}"'} if download else None
    return FileResponse(p, media_type="image/png", headers=headers)


@app.delete("/api/image/{img_id}")
def delete_image(img_id: str):
    p = _resolve(img_id)
    p.unlink(missing_ok=True)
    STORE.forget_image(p.name)
    return {"ok": True}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    UPLOADS.mkdir(parents=True, exist_ok=True)
    name = f"up_{uuid.uuid4().hex[:12]}.png"
    (UPLOADS / name).write_bytes(await file.read())
    return {"id": name}


# ── sinh ảnh ─────────────────────────────────────────────────────────────────
def _worker(job_id: str, req: GenReq, chat: str, ai_id: str):
    q = JOBS[job_id]["q"]

    def emit(ev):
        q.put(ev)

    try:
        uploaded = [_resolve(i) for i in req.images]
        base = _resolve(req.base_image) if req.base_image else None
        mode = {"new": "Tạo ảnh mới", "edit": "Sửa ảnh"}.get(req.kind, "Tự động")

        task, use_last, why = pick_task(
            req.prompt, len(uploaded), str(base) if base else None, mode)

        # Ảnh vào cho từng nhánh — cùng quy tắc với app.py
        images = []
        if task == "MultiRef":
            if use_last and base and uploaded:
                images = [stage_input(uploaded[0]), stage_input(base)]
            elif len(uploaded) >= 2:
                images = [stage_input(uploaded[0]), stage_input(uploaded[1])]
            else:
                task = "LocalEdit"
        if task == "LocalEdit":
            src = base if (use_last and base) else (uploaded[0] if uploaded else base)
            if src is None:
                task = "T2I"
            else:
                images = [stage_input(src)]

        prompt = apply_style(req.prompt, req.style) if task == "T2I" else req.prompt
        w, h = SIZES[RATIO_TO_SIZE.get(req.ratio, "Vuông 1:1 (1328×1328)")]
        n = max(1, min(4, int(req.count)))

        emit({"type": "start", "task": task, "why": why, "count": n,
              "ar": RATIO_CSS.get(req.ratio, "1/1"), "chat": chat, "messageId": ai_id})

        for i in range(n):
            seed = int(time.time() * 1000) % 2_147_483_647 + i * 7919
            wf = build(task, prompt, images=images, prefix="auralis",
                       seed=seed, width=w, height=h)
            for ev in run_workflow(wf):
                if JOBS[job_id]["cancel"]:
                    emit({"type": "cancelled"})
                    return
                if ev[0] == "tiến độ":
                    _, step, total, elapsed = ev
                    emit({"type": "progress", "index": i, "step": step,
                          "total": total, "elapsed": round(elapsed, 1)})
                else:
                    _, out_path, secs = ev
                    img_id = Path(out_path).name
                    STORE.append_image(chat, ai_id, img_id)   # lưu ngay, không đợi hết bộ
                    emit({"type": "image", "index": i, "id": img_id,
                          "seconds": round(secs or 0, 1)})
        emit({"type": "done"})
    except Exception as e:
        emit({"type": "error", "message": str(e)})
    finally:
        # Job hỏng/huỷ giữa chừng thì bỏ luôn tin nhắn AI rỗng, đừng để rác trong store.
        STORE.drop_if_empty(chat, ai_id)
        emit(None)   # sentinel đóng SSE


@app.post("/api/generate")
def generate(req: GenReq):
    if not req.prompt.strip():
        raise HTTPException(400, "Chưa có mô tả")
    if not comfy_alive():
        raise HTTPException(503, "Không kết nối được ComfyUI ở cổng 18188")

    chat = STORE.ensure_chat(req.chat)
    n = max(1, min(4, int(req.count)))
    meta = (f"sửa ảnh · {n} phương án" if req.kind == "edit"
            else f"{req.style} · {req.ratio} · {n} ảnh")
    STORE.add_message(chat, {"role": "user", "text": req.prompt,
                             "meta": meta, "attach": req.images})
    ai = STORE.add_message(chat, {
        "role": "ai", "kind": req.kind, "prompt": req.prompt, "style": req.style,
        "ar": RATIO_CSS.get(req.ratio, "1/1"), "images": []})

    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {"q": queue.Queue(), "cancel": False}
    threading.Thread(target=_worker, args=(job_id, req, chat, ai["id"]), daemon=True).start()
    return {"job": job_id, "chat": chat, "messageId": ai["id"]}


@app.post("/api/cancel/{job_id}")
def cancel(job_id: str):
    if job_id in JOBS:
        JOBS[job_id]["cancel"] = True
    return {"ok": True}


@app.get("/api/progress/{job_id}")
def progress(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job không tồn tại")
    q = JOBS[job_id]["q"]

    def stream():
        while True:
            try:
                ev = q.get(timeout=120)
            except queue.Empty:
                break
            if ev is None:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        with JOBS_LOCK:
            JOBS.pop(job_id, None)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


app.mount("/", StaticFiles(directory=str(HERE / "static"), html=True), name="static")
