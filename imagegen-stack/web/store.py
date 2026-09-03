"""
store.py — nơi cất hội thoại + ảnh của Auralis.

Giao diện có hội thoại, thư viện ảnh, đổi tên/xoá cuộc trò chuyện. Trước đây mấy
thứ đó chỉ nằm trong localStorage của trình duyệt: đổi máy là mất, và thư viện ảnh
không khớp với ảnh thật đang nằm trong SESSION_DIR. Ở đây server giữ mới là nguồn thật.

Một file JSON + một khoá là đủ: đây là app một người dùng chạy cạnh ComfyUI trên cùng
máy, không phải dịch vụ nhiều người. Ghi kiểu atomic (ghi tạm rồi đổi tên) để tắt máy
giữa chừng không mất sạch dữ liệu.
"""
import json
import threading
import time
import uuid
from pathlib import Path


def _uid(p):
    return p + uuid.uuid4().hex[:9]


def now_ms():
    return int(time.time() * 1000)


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.data = {"chats": [], "messages": {}}
        self._load()

    # ── đĩa ──────────────────────────────────────────────────────────────
    def _load(self):
        try:
            self.data = json.loads(self.path.read_text("utf-8"))
            self.data.setdefault("chats", [])
            self.data.setdefault("messages", {})
        except Exception:
            pass          # chưa có file, hoặc file hỏng → bắt đầu rỗng

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)

    # ── cuộc trò chuyện ──────────────────────────────────────────────────
    def chats(self):
        with self.lock:
            return sorted(self.data["chats"], key=lambda c: -c.get("ts", 0))

    def new_chat(self, title="Trò chuyện mới"):
        with self.lock:
            c = {"id": _uid("c"), "title": title, "ts": now_ms()}
            self.data["chats"].append(c)
            self.data["messages"][c["id"]] = []
            self._save()
            return c

    def rename_chat(self, cid, title):
        with self.lock:
            for c in self.data["chats"]:
                if c["id"] == cid:
                    c["title"] = title
                    self._save()
                    return c
            return None

    def delete_chat(self, cid):
        with self.lock:
            self.data["chats"] = [c for c in self.data["chats"] if c["id"] != cid]
            self.data["messages"].pop(cid, None)
            self._save()

    def ensure_chat(self, cid):
        """Trả về cid hợp lệ; tự tạo cuộc trò chuyện nếu client gửi id lạ."""
        with self.lock:
            if cid and any(c["id"] == cid for c in self.data["chats"]):
                return cid
            return self.new_chat()["id"]

    # ── tin nhắn ─────────────────────────────────────────────────────────
    def messages(self, cid):
        with self.lock:
            return list(self.data["messages"].get(cid, []))

    def add_message(self, cid, msg):
        with self.lock:
            msg.setdefault("id", _uid(msg.get("role", "m")[0]))
            msg.setdefault("ts", now_ms())
            self.data["messages"].setdefault(cid, []).append(msg)
            # cuộc trò chuyện mới thì lấy luôn câu đầu làm tên
            if msg.get("role") == "user":
                for c in self.data["chats"]:
                    if c["id"] == cid and c["title"] == "Trò chuyện mới":
                        t = (msg.get("text") or "").strip()
                        c["title"] = (t[:46] + "…") if len(t) > 46 else (t or c["title"])
            self._save()
            return msg

    def append_image(self, cid, msg_id, image_id):
        """Gắn một ảnh vừa xong vào tin nhắn AI — gọi ngay khi từng ảnh ra lò."""
        with self.lock:
            for m in self.data["messages"].get(cid, []):
                if m["id"] == msg_id:
                    m.setdefault("images", []).append(image_id)
                    self._save()
                    return m
            return None

    def drop_if_empty(self, cid, msg_id):
        """Xoá tin nhắn AI không ra được ảnh nào (job lỗi hoặc bị huỷ).

        Không dọn thì store đọng lại những tin nhắn rỗng vô hình trên giao diện
        nhưng vẫn nằm trong file JSON mãi mãi.
        """
        with self.lock:
            msgs = self.data["messages"].get(cid, [])
            for i, m in enumerate(msgs):
                if m["id"] == msg_id and m.get("role") == "ai" and not m.get("images"):
                    del msgs[i]
                    self._save()
                    return True
            return False

    # ── thư viện ─────────────────────────────────────────────────────────
    def gallery(self, kind_filter="Tất cả"):
        with self.lock:
            out = []
            for cid, msgs in self.data["messages"].items():
                for m in msgs:
                    if m.get("role") != "ai":
                        continue
                    for i, img in enumerate(m.get("images", [])):
                        out.append({
                            "id": img, "mid": m["id"], "chat": cid,
                            "ar": m.get("ar", "1/1"), "prompt": m.get("prompt", ""),
                            "kind": m.get("kind", "new"), "style": m.get("style", ""),
                            "ts": m.get("ts", 0),
                            "badge": ("bản sửa " if m.get("kind") == "edit" else "ảnh ") + str(i + 1),
                        })
            if kind_filter == "Ảnh mới":
                out = [g for g in out if g["kind"] != "edit"]
            elif kind_filter == "Bản sửa":
                out = [g for g in out if g["kind"] == "edit"]
            return sorted(out, key=lambda g: -g["ts"])

    def forget_image(self, image_id):
        """Gỡ ảnh khỏi mọi tin nhắn (dùng khi xoá ảnh khỏi thư viện)."""
        with self.lock:
            for msgs in self.data["messages"].values():
                for m in msgs:
                    if image_id in m.get("images", []):
                        m["images"].remove(image_id)
            self._save()
