"""
styles_vi.py — 4 phong cách trong giao diện Auralis → đuôi prompt gửi cho model.

Backend không có khái niệm "phong cách"; nó chỉ nhận một câu prompt. Nên mỗi nút
phong cách chỉ đơn giản là nối thêm một đoạn mô tả tiếng Anh vào cuối prompt.

Viết bằng tiếng Anh vì Qwen-Image bám từ khoá tạo hình tiếng Anh sát hơn, trong khi
phần mô tả nội dung của người dùng vẫn để nguyên tiếng Việt (bộ eval 50 case đo được
prompt tiếng Việt cho T2I đạt 92.9%, nên không dịch phần đó).

Sửa thoải mái — đây là lời văn, không phải logic.
"""

STYLE_SUFFIX = {
    "Ảnh thật": "photorealistic, natural lighting, sharp focus, high detail",
    "Điện ảnh": "cinematic lighting, shallow depth of field, film grain, dramatic composition",
    "Tranh vẽ": "digital painting, visible brush strokes, painterly, illustrative",
    "3D": "3d render, soft studio lighting, subsurface scattering, octane render",
}

# Khung ảnh trong giao diện → tên kích thước trong core.SIZES.
# Thiết kế ghi 16/10 và 3/4 nhưng model chỉ có sẵn 16:9 và 9:16 — dùng số thật,
# và giao diện đặt aspect-ratio theo đúng số này để không hiện sai tỉ lệ.
RATIO_TO_SIZE = {
    "Vuông": "Vuông 1:1 (1328×1328)",
    "Ngang": "Ngang 16:9 (1664×928)",
    "Dọc":   "Dọc 9:16 (928×1664)",
}

RATIO_CSS = {"Vuông": "1/1", "Ngang": "1664/928", "Dọc": "928/1664"}


def apply_style(prompt: str, style: str) -> str:
    """Nối đuôi phong cách vào prompt. Phong cách lạ thì trả nguyên prompt."""
    suffix = STYLE_SUFFIX.get(style)
    return f"{prompt.strip()}, {suffix}" if suffix and prompt.strip() else prompt
