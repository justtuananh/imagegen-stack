#!/usr/bin/env python3
"""
render_text.py — dựng chữ tiếng Việt có dấu thành PNG nền trong suốt.

Dùng cho workflow W2B: model sinh nền, Pillow lo phần chữ, ComfyUI ghép lại.
Chữ ra chính xác 100% vì không đi qua model sinh ảnh.

    python3 render_text.py --text "Khuyến mãi 50%" --out text.png \
        --font fonts/BeVietnamPro-Bold.ttf --size 120 --color "#FFFFFF"

Xuất PNG RGBA. Nạp vào ComfyUI bằng LoadImage → nối IMAGE và MASK vào
ImageCompositeMasked(destination=<ảnh nền>, source=<ảnh chữ>, mask=<mask>).
"""
import argparse
import sys
import unicodedata
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit("Thiếu Pillow. Cài: pip install Pillow")


def to_nfc(s: str) -> str:
    """Chuẩn hoá về NFC (ký tự dựng sẵn).

    Đây là bước BẮT BUỘC cho tiếng Việt. Chuỗi ở dạng NFD (dấu tách rời) trông
    giống hệt trên terminal nhưng nhiều font sẽ dựng sai — dấu bị lệch, chồng lên
    nhau, hoặc rơi ra ngoài ô ký tự. Ví dụ "ế" có thể là 1 code point (NFC) hoặc
    3 code point (NFD); chỉ NFC mới chắc chắn khớp glyph có sẵn trong font.
    """
    return unicodedata.normalize("NFC", s)


def check_font_coverage(font_path: str, text: str) -> list[str]:
    """Trả về danh sách ký tự mà font KHÔNG có glyph.

    Font thiếu glyph sẽ vẽ ra ô vuông rỗng (.notdef) — thường chỉ phát hiện được
    khi nhìn ảnh. Kiểm tra trước để hỏng thì hỏng ngay lúc chạy, không phải lúc giao hàng.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return []  # không có fontTools thì bỏ qua, không phải lỗi nghiêm trọng
    missing = []
    ttf = TTFont(font_path, fontNumber=0)
    cmaps = [t.cmap for t in ttf["cmap"].tables]
    for ch in set(text):
        if ch.isspace():
            continue
        if not any(ord(ch) in c for c in cmaps):
            missing.append(ch)
    return sorted(missing)


def render(text, font_path, size, color, stroke_width, stroke_color,
           shadow, padding, align, line_spacing):
    text = to_nfc(text)
    lines = text.split("\\n") if "\\n" in text else text.split("\n")

    missing = check_font_coverage(font_path, text)
    if missing:
        print(f"CẢNH BÁO: font thiếu glyph cho: {' '.join(missing)}", file=sys.stderr)
        print(f"  → đổi font khác. Font phải có subset 'vietnamese'.", file=sys.stderr)

    font = ImageFont.truetype(font_path, size)

    # đo từng dòng bằng chính font đó, không ước lượng
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    metrics = []
    for ln in lines:
        box = probe.textbbox((0, 0), ln, font=font, stroke_width=stroke_width)
        metrics.append((ln, box[2] - box[0], box[3] - box[1], box[0], box[1]))

    line_h = int(size * line_spacing)
    w = max(m[1] for m in metrics) + padding * 2
    h = line_h * len(lines) + padding * 2

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for i, (ln, lw, lh, ox, oy) in enumerate(metrics):
        if align == "center":
            x = (w - lw) // 2 - ox
        elif align == "right":
            x = w - padding - lw - ox
        else:
            x = padding - ox
        y = padding + i * line_h - oy
        draw.text((x, y), ln, font=font, fill=color,
                  stroke_width=stroke_width, stroke_fill=stroke_color)

    if shadow:
        # đổ bóng mềm phía sau, giúp chữ ghép vào ảnh trông tự nhiên hơn
        alpha = img.split()[3]
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(size // 20 or 1)))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 160))
        sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(size // 20 or 1)))
        out = Image.new("RGBA", (w, h + size // 12), (0, 0, 0, 0))
        out.alpha_composite(sh, (0, size // 12))
        out.alpha_composite(img, (0, 0))
        img = out

    return img


def main():
    ap = argparse.ArgumentParser(description="Dựng chữ tiếng Việt thành PNG trong suốt")
    ap.add_argument("--text", required=True, help='Chữ cần dựng. Xuống dòng bằng \\n')
    ap.add_argument("--out", required=True, help="Đường dẫn PNG xuất ra")
    ap.add_argument("--font", required=True, help="File .ttf/.otf có đủ dấu tiếng Việt")
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--color", default="#FFFFFF")
    ap.add_argument("--stroke-width", type=int, default=0)
    ap.add_argument("--stroke-color", default="#000000")
    ap.add_argument("--shadow", action="store_true", help="Thêm bóng đổ mềm")
    ap.add_argument("--padding", type=int, default=24)
    ap.add_argument("--align", choices=["left", "center", "right"], default="center")
    ap.add_argument("--line-spacing", type=float, default=1.25)
    a = ap.parse_args()

    if not Path(a.font).exists():
        sys.exit(f"Không tìm thấy font: {a.font}")

    img = render(a.text, a.font, a.size, a.color, a.stroke_width, a.stroke_color,
                 a.shadow, a.padding, a.align, a.line_spacing)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out)
    print(f"{a.out}  {img.width}x{img.height}  '{to_nfc(a.text)}'")


if __name__ == "__main__":
    main()
