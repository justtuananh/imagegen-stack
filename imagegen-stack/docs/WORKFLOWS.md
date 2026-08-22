# Bộ workflow tiếng Việt — hướng dẫn dùng

## Kết luận nghiên cứu quyết định thiết kế này

Hai agent khảo sát độc lập cho cùng một kết luận:

| Phát hiện | Nguồn |
|---|---|
| Qwen chỉ tuyên bố hỗ trợ render chữ **Anh + Trung**. Không nơi nào nhắc tiếng Việt | Blog Qwen, README GitHub, model card 2512 |
| **Lỗi dấu Ba Lan VẪN CÒN trên Qwen-Image-2512** (thảo luận 01/2026, maintainer chưa trả lời) | HF Space `Qwen/Qwen-Image-2512` discussion #2 |
| Issue gốc mở 30/09/2025, đến nay chưa ai sửa | `QwenLM/Qwen-Image#161` |
| Cộng đồng Việt: *"hiện tại công cụ hỗ trợ tiếng Trung và tiếng Anh, chưa hỗ trợ tiếng Việt"* | congdongai.vn |
| Bộ mở rộng prompt của Qwen phân loại **nhị phân**: có CJK → nhánh Trung, còn lại → nhánh Anh. Prompt Việt bị xử lý như tiếng Anh, **không dịch** | `prompt_utils.py` |
| Wan2.2-TI2V-5B model card ghi `language: en, zh` | HF model card |
| **Không tồn tại LoRA tiếng Việt nào** cho render chữ | Tìm HF API |

→ **Không đặt cược vào việc model biết viết tiếng Việt.** W2B (ghép chữ) là đường chính,
lớp dịch prompt là bắt buộc chứ không phải tuỳ chọn.

---

## Chọn workflow nào

Từ 22/08/2026 chỉ còn **MỘT workflow duy nhất**: `workflows/W_qwen_6tasks.json`.
Cả 6 tác vụ ảnh dùng chung file này; chọn nhánh bằng `workflows/build.py --task`.

| Tác vụ | `--task` | Ảnh vào | Nhánh chạy |
|---|---|---|---|
| Sinh ảnh từ mô tả | `T2I` | 0 | Qwen-Image-2512, 50 bước |
| Sửa cục bộ (đổi màu, xoá/thêm vật) | `LocalEdit` | 1 | Qwen-Image-Edit-2511, 20 bước |
| Sửa toàn cục (mùa, ngày→đêm, phong cách) | `GlobalEdit` | 1 | ↑ |
| Sửa cấu trúc (tư thế, góc máy, khung hình) | `StructureEdit` | 1 | ↑ |
| Giữ chủ thể, đổi bối cảnh | `RefGen` | 1 | ↑ |
| Ghép chủ thể từ 2 ảnh | `MultiRef` | 2 | ↑ |

```bash
python3 workflows/build.py --task T2I --prompt "Chân dung áo dài đỏ..." -o wf.json
python3 workflows/build.py --task MultiRef --prompt "Place the cat from image 1 ..." \
    --images base_cat.png base_cafe.png -o wf.json
```

**Vì sao vẫn phải cắt nhánh chứ không để nguyên một graph chạy thẳng:** ComfyUI chạy
MỌI node dẫn tới `SaveImage` và core không có node rẽ nhánh. Để cả hai nhánh sống thì
nó nạp đồng thời Qwen-Image-2512 (20B) và Qwen-Image-Edit-2511 (20B) → hết VRAM trên
32GB. `build.py` cắt nhánh không dùng — đúng tương đương API của "bypass group" trong GUI.

Bốn tác vụ edit 1-ảnh (`LocalEdit`/`GlobalEdit`/`StructureEdit`/`RefGen`) sinh ra graph
**giống hệt nhau**, chỉ khác nội dung chỉ dẫn — tách tên task là để chấm điểm eval theo
nhóm, không phải vì cấu trúc khác nhau.

| Việc khác | Cách làm |
|---|---|
| Chữ Việt lên video | `vi/burn_text_video.sh` *(ffmpeg, không phải workflow)* |

> **Đã gỡ 22/08/2026:** `W1`, `W3`, `W4` gộp vào `W_qwen_6tasks`; `W2A/W2B/W2C`
> (render chữ Việt) và `W5A/W5B` (video Wan2.2) xoá theo yêu cầu thu gọn còn một
> workflow. Cần lại thì khôi phục bằng `_generate.py` (các hàm dựng vẫn còn nguyên).

---

## Quy trình poster có chữ Việt (W2B) — đường chính

```
prompt tiếng Việt
   │  vi_prompt_layer.py  ← tách chữ trong "..." ra, dịch phần cảnh sang tiếng Anh
   ├──────────────► prompt_en (mô tả cảnh, chừa chỗ trống, no text)
   └──────────────► text_layers = ["Khuyến mãi 50%"]
                          │
   W1/W2B sinh nền        │  render_text.py: Pillow + font đủ dấu → PNG alpha
        │                 │
        └────► ImageCompositeMasked ◄────┘
                     │
                 SaveImage        chữ đúng 100%
```

Chạy:
```bash
# 1. xử lý prompt
python3 vi/vi_prompt_layer.py --json \
  --prompt 'poster quán cà phê, chữ "Khuyến mãi 50%" ở giữa, phong cách tối giản'

# 2. dựng lớp chữ
python3 vi/render_text.py --text "Khuyến mãi 50%" \
  --out <ComfyUI>/input/vi_text.png \
  --font vi/fonts/BeVietnamPro-Bold.ttf --size 120 --shadow

# 3. nạp W2B_poster_text_composite.json vào ComfyUI, điền prompt_en, chạy
```

---

## Tham số — nguồn gốc từng con số

Tất cả lấy từ template chính thức `Comfy-Org/workflow_templates`, đối chiếu model card
và config gốc của tác giả. Sửa ở khối `P` trong `workflows/_generate.py` rồi chạy lại script.

| Model | sampler / scheduler | steps | cfg | shift | Nguồn |
|---|---|---|---|---|---|
| Qwen-Image-2512 | euler / simple | 50 | 4.0 | 3.1 | template + model card khớp nhau |
| ↳ Lightning 4-step | euler / simple | 4 | 1.0 | 3.1 | template |
| Qwen-Image-Edit-2511 | euler / simple | 20 | 4.0 | 3.1 | template ghi 40, note trong template nói 20 cũng tốt |
| ↳ Lightning 4-step | euler / simple | 4 | 1.0 | 3.1 | template |
| Wan2.2-TI2V-5B | uni_pc / simple | 20 | 5.0 | 8.0 | **template ComfyUI** |
| ↳ bản tham chiếu | uni_pc / simple | 50 | 5.0 | 5.0 | **repo gốc Wan-AI** — lệch với trên |

⚠️ **Ghép nhầm LoRA là lỗi phổ biến nhất.** Lightning LoRA phải đi kèm `cfg=1, steps=4`.
Để nguyên `cfg=4, steps=50` với LoRA đã nạp → ảnh vỡ khối, quá bão hoà.

⚠️ **Không có Lightning LoRA cho Wan2.2-TI2V-5B.** lightx2v đã thử và bỏ
("didn't get good results"). Repo của họ chỉ có bản A14B. Đừng đi tìm.
Các báo cáo "Lightning làm hỏng chuyển động" là nói về A14B (kiến trúc 2 expert),
không áp dụng cho TI2V-5B dense.

---

## Ràng buộc kỹ thuật

| Điều | Chi tiết |
|---|---|
| Kích thước video | `width`/`height` phải **chia hết cho 32** (VAE nén 4×32×32). Native 1280×704 hoặc 704×1280 |
| Độ dài video | `length=121` frame @ 24fps ≈ 5 giây |
| Nối ảnh → video | Qwen xuất 1328×1328, **không chia hết cho 32** → W5B đã chèn sẵn `ImageScale` về 1280×704 |
| Negative của Edit-2511 | Để **rỗng** (`" "`) theo quy ước model card — không phải bỏ sót |
| Negative của Qwen/Wan | Dùng nguyên văn tiếng Trung từ template chính thức, đã thêm phần chống lệch văn hoá |
| Chuẩn hoá chữ | Mọi chuỗi tiếng Việt phải **NFC**. NFD trông giống hệt nhưng dựng sai dấu |
| `SaveVideo` | `codec` là `DynamicCombo` lồng nhau, **không viết tay được** → dùng `SaveWEBM` |

---

## Đường edit (W2C / W3 / W4) — 4 node bắt buộc, đo được trên RTX 5090 (22/08/2026)

Bản đầu của ba workflow edit **lệch template chính thức ở 4 chỗ** và đã được đo là hỏng thật:
cả 4/4 phép thử sửa ảnh ra **cháy màu, bệt như tranh vector, chỉ dẫn bị nuốt**. Sau khi
bám đúng template `image_qwen_image_edit_2511.json`, cùng prompt + seed cho ảnh chân thực và
chỉ dẫn đổi tư thế chạy đúng. Chi tiết nằm trong docstring `edit_workflow()` của `_generate.py`.

| # | Node | Vì sao bắt buộc |
|---|---|---|
| a | Negative nhận **cùng `vae` + `image1..N`** như positive | Thiếu → cfg=4 lấy hiệu hai conditioning lệch cấu trúc → cháy màu. **Lỗi nặng nhất** |
| b | `FluxKontextImageScale` trước `VAEEncode` + `TextEncode` cho image1 | Chuẩn hoá kích thước ảnh upload. Ảnh test tình cờ 1328×1328 nên chưa lộ |
| c | `FluxKontextMultiReferenceLatentMethod` (`index_timestep_zero`) bọc **cả pos lẫn neg** | Node cho ghép nhiều ảnh tham chiếu |
| d | `CFGNorm` (strength 1) sau `ModelSamplingAuraFlow`, trước LoRA | Ổn định guidance |

⚠️ **`_validate.py` KHÔNG bắt được lỗi (a)** — nó chỉ soi tên node/tham số/enum, cả 8 workflow
đều "hợp lệ" trước lẫn sau khi sửa. Lỗi nối dây sai-nhưng-hợp-lệ chỉ lộ khi chạy máy thật.

Giới hạn thật của model sau khi workflow đã đúng (n=1 mỗi loại, cùng ảnh gốc):
- ✅ Local edit (đổi màu áo), global edit (ngày→đêm), **đổi tư thế người** — chạy đúng
- ❌ **Đổi góc máy** — model dựng lại ảnh gốc, không đổi. Cần ControlNet depth/pose
- ✅ **Multi-ref ghép người từ ảnh 1 vào cảnh ảnh 2** — fail 3 lần với workflow cũ, chạy đúng
  ngay lần đầu với workflow mới (giữ nón, áo, quần; khớp ánh sáng). Node (c) là thứ còn thiếu.

Số đo sau tối ưu (fp8, RTX 5090): edit 1 ảnh **41,7 s**, ghép 2 ảnh **68,5 s**; VRAM đỉnh
29,8 GB. Ảnh ra 1024×1024 do `FluxKontextImageScale` chọn độ phân giải ưu tiên — nhanh hơn
và là hành vi đúng của template, không phải lỗi.

## Kiểm tra trước khi chạy máy thật

```bash
python3 workflows/_validate.py   # đối chiếu mọi workflow với schema trích từ source
```
Kiểm tra tĩnh: tên node, tên tham số, giá trị enum, link trỏ đúng node.
**Không thay thế** việc nạp thử vào ComfyUI thật.

## Cổng quyết định

```bash
python3 tests/run_vi_test.py --comfy http://127.0.0.1:8188 --out ket_qua/
# xem ảnh, điền "verdict" vào ket_qua/ket_qua.json
python3 tests/run_vi_test.py --score ket_qua/ket_qua.json
```
30 case, 4 tầng độ khó. Ra bảng tỉ lệ đúng theo từng tầng.

## Template chính thức nên đối chiếu

Trong ComfyUI: **Workflow → Browse Templates**. Nếu workflow ở đây lỗi, mở template gốc để so:

| Model | File template |
|---|---|
| Qwen-Image-2512 | `image_qwen_Image_2512.json` |
| Qwen-Image-Edit-2511 | `image_qwen_image_edit_2511.json` |
| Wan2.2 TI2V-5B (T2V+I2V chung 1 graph) | `video_wan2_2_5B_ti2v.json` |
| Inpaint vùng chữ (mạnh hơn W2C, cần tải thêm ControlNet) | `image_qwen_image_instantx_inpainting_controlnet.json` |
