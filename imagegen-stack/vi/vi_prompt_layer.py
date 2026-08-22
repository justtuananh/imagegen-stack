#!/usr/bin/env python3
"""
vi_prompt_layer.py — chuyển prompt tiếng Việt thành prompt model hiểu được.

VÌ SAO CẦN LỚP NÀY (không phải cho đẹp):

1. Bộ mở rộng prompt chính thức của Qwen-Image (`prompt_utils.py`) phân loại ngôn ngữ
   theo kiểu nhị phân: có ký tự CJK → nhánh tiếng Trung, còn lại → nhánh tiếng Anh.
   Prompt tiếng Việt rơi vào nhánh tiếng Anh và bị xử lý NHƯ THỂ nó là tiếng Anh —
   không hề được dịch.
2. Model card của Wan2.2-TI2V-5B ghi metadata `language: en, zh`. Không có tiếng Việt.
3. Chữ tiếng Việt có dấu gần như chắc chắn bị model render sai (lỗi dấu Ba Lan vẫn
   còn nguyên trên Qwen-Image-2512 tính tới 01/2026). Nên phần chữ cần hiện trên ảnh
   phải được TÁCH RA khỏi prompt, không đưa cho model, rồi ghép lại bằng W2B.

Lớp này làm 2 việc:
  - Tách chuỗi trong "..." ra thành phần chữ sẽ ghép sau (render_text.py lo)
  - Dịch + mở rộng phần mô tả cảnh sang tiếng Anh qua endpoint OpenAI-compatible
    (llama.cpp / vLLM / Ollama — chạy local, không ra internet)

    python3 vi_prompt_layer.py --prompt 'poster cà phê, chữ "Khuyến mãi 50%", phong cách tối giản'
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.request

SYSTEM = (
    "You rewrite Vietnamese image-generation prompts into English prompts for a "
    "diffusion model. Rules:\n"
    "1. Translate faithfully. Do not invent subjects that were not mentioned.\n"
    "2. Expand into a concrete visual description: subject, composition, lighting, "
    "style, camera, mood.\n"
    "3. Preserve Vietnamese cultural specificity precisely. Use explicit terms such as "
    "'Vietnamese ao dai', 'Vietnamese conical hat (non la)', 'Hanoi Old Quarter', "
    "'Vietnamese pho', 'Vietnamese woman'. Never let it drift to Chinese or Japanese "
    "aesthetics — say 'Vietnamese' explicitly when people or places are involved.\n"
    "4. NEVER include any literal text to be written in the image. If the user asked "
    "for words on the image, instead describe empty space reserved for them, e.g. "
    "'clean empty banner area at the top, no text'.\n"
    "5. Output ONLY the English prompt. No preamble, no quotes, no explanation."
)

NEGATIVE_DEFAULT = (
    "text, watermark, signature, letters, words, caption, logo, blurry, low quality, "
    "distorted, extra fingers, deformed hands"
)


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def extract_text_layers(prompt: str):
    """Tách các chuỗi trong dấu ngoặc kép ra khỏi prompt.

    Đây là phần chữ người dùng muốn hiện TRÊN ảnh. Không đưa cho model —
    model sẽ viết sai dấu. Trả về cho render_text.py dựng rồi ghép bằng W2B.
    """
    layers = re.findall(r'["“”\'](.+?)["“”\']', prompt)
    cleaned = re.sub(r'["“”\'](.+?)["“”\']', "___", prompt)
    return [nfc(t) for t in layers], cleaned


def translate(scene: str, endpoint: str, model: str, timeout: int = 120) -> str:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": nfc(scene)},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }).encode()
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("LLM_API_KEY", "no-key")},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip()


def main():
    ap = argparse.ArgumentParser(description="Prompt tiếng Việt → prompt tiếng Anh cho model")
    ap.add_argument("--prompt", required=True, help='Prompt VI. Chữ cần hiện trên ảnh đặt trong "..."')
    ap.add_argument("--endpoint", default=os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:8003/v1"),
                    help="Endpoint OpenAI-compatible chạy local")
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL", "qwen2.5-instruct"))
    ap.add_argument("--no-translate", action="store_true",
                    help="Chỉ tách phần chữ, không gọi LLM (để test offline)")
    ap.add_argument("--json", action="store_true", help="Xuất JSON cho script khác dùng")
    a = ap.parse_args()

    text_layers, scene = extract_text_layers(a.prompt)

    if a.no_translate:
        english = scene
        note = "chưa dịch (--no-translate)"
    else:
        try:
            english = translate(scene, a.endpoint, a.model)
            note = "đã dịch"
        except Exception as e:
            english = scene
            note = f"DỊCH THẤT BẠI ({e}) — dùng nguyên văn, chất lượng sẽ kém"
            print(f"CẢNH BÁO: {note}", file=sys.stderr)

    out = {
        "prompt_vi": nfc(a.prompt),
        "prompt_en": english,
        "negative": NEGATIVE_DEFAULT,
        "text_layers": text_layers,
        "status": note,
    }

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"[prompt cho model]\n{english}\n")
        print(f"[negative]\n{NEGATIVE_DEFAULT}\n")
        if text_layers:
            print("[chữ sẽ ghép bằng W2B — KHÔNG đưa cho model]")
            for t in text_layers:
                print(f"  • {t}")
        else:
            print("[không có chữ cần ghép]")


if __name__ == "__main__":
    main()
