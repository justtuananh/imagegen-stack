# imagegen-stack — sinh & sửa ảnh offline bằng Qwen-Image trên ComfyUI

Bộ công cụ chạy **hoàn toàn offline** trên một GPU RTX 5090 (32GB): sinh ảnh từ mô tả
tiếng Việt, sửa ảnh theo chỉ dẫn, ghép nhiều ảnh — kèm **giao diện chat** và **bộ đánh
giá 50 case** đo chất lượng thật của mô hình.

| | |
|---|---|
| **Sinh ảnh** | Qwen-Image-2512 (20B, Apache-2.0) |
| **Sửa ảnh** | Qwen-Image-Edit-2511 (20B, Apache-2.0) |
| **Chạy trên** | ComfyUI, RTX 5090 32GB, air-gapped |
| **Giao diện** | Gradio, kiểu chat |

---

## Bắt đầu nhanh

```bash
# 1. Sinh workflow (đã có sẵn W_qwen_6tasks.json, chỉ chạy khi muốn đổi tham số)
python3 imagegen-stack/workflows/_generate.py

# 2. Chạy giao diện chat — PHẢI chạy trên máy có ComfyUI
python3 imagegen-stack/app/app.py --share          # tạo link công khai
python3 imagegen-stack/app/app.py --auth user:pass # kèm mật khẩu
```

Dựng workflow trực tiếp không qua giao diện:

```bash
python3 imagegen-stack/workflows/build.py --task T2I \
    --prompt "Chân dung áo dài đỏ, tường vàng cũ" -o wf.json

python3 imagegen-stack/workflows/build.py --task MultiRef \
    --prompt "Place the cat from image 1 on the table in image 2" \
    --images cat.png table.png -o wf.json
```

---

## Một workflow, sáu tác vụ

Cả 6 tác vụ dùng chung **một file** `W_qwen_6tasks.json`; `build.py` bật đúng nhánh:

| `--task` | Việc | Ảnh vào |
|---|---|---|
| `T2I` | Sinh ảnh từ mô tả | 0 |
| `LocalEdit` | Sửa cục bộ (đổi màu, thêm/xoá vật) | 1 |
| `GlobalEdit` | Sửa toàn cục (mùa, ngày→đêm, phong cách) | 1 |
| `StructureEdit` | Đổi tư thế / góc máy / khung hình | 1 |
| `RefGen` | Giữ chủ thể, đổi bối cảnh | 1 |
| `MultiRef` | Ghép chủ thể từ 2 ảnh | 2 |

**Vì sao vẫn cần cắt nhánh:** ComfyUI chạy mọi node dẫn tới `SaveImage` và core không có
node rẽ nhánh. Để cả hai nhánh sống thì nó nạp đồng thời hai mô hình 20B → hết VRAM trên
32GB. `build.py` cắt nhánh không dùng — tương đương API của thao tác *bypass group* trong
giao diện ComfyUI.

---

## Kết quả đánh giá (50 case, chấm bằng mắt)

Ba tiêu chí, mỗi tiêu chí 0 / 0.5 / 1: **instruction** (làm đúng chỉ dẫn) ·
**preserve** (giữ nguyên phần không được đụng) · **quality** (không artifact).

| Tác vụ | Case | Instruction | Preserve | Quality |
|---|---:|---:|---:|---:|
| T2I | 7 | 92.9% | 100% | 100% |
| LocalEdit | 9 | 100% | 88.9% | 100% |
| GlobalEdit | 9 | 100% | 94.4% | 100% |
| **StructureEdit** | 9 | **38.9%** | 88.9% | 100% |
| RefGen | 8 | 100% | 87.5% | 100% |
| MultiRef | 8 | 93.8% | 81.2% | 100% |
| **Tổng** | **50** | **87%** | **90%** | **100%** |

### Ba điểm yếu đo được, không phải suy đoán

1. **Đếm số lượng sai, lặp lại** — khi chỉ dẫn yêu cầu số lượng chính xác ("3 ghế → 5
   ghế", "3 ghế → 2 ghế"), mô hình thường trả về sai. Dính 4/50 case (`loc_03`, `glo_02`,
   `str_03`, `str_06`). Đây là giới hạn thật, không phải nhiễu ngẫu nhiên.
2. **Đổi góc máy gần như không hoạt động** — `str_07` (góc thấp), `str_08` (zoom/crop),
   `str_09` (góc 3/4) đều cho ra ảnh giữ nguyên góc gốc. Đây là lý do StructureEdit chỉ
   được 38.9%. Cân nhắc kỹ trước khi dùng cho use-case xoay góc camera.
3. **Giữ danh tính đôi khi trượt** — `ref_08` đổi hoàn toàn màu/vằn lông con mèo dù chỉ
   dẫn ghi rõ *"same fur pattern"*.

Chi tiết từng case: [`tests/task_eval/eval_set.json`](imagegen-stack/tests/task_eval/eval_set.json)
· điểm số: [`ket_qua/ket_qua.json`](imagegen-stack/tests/task_eval/ket_qua/ket_qua.json)
· ảnh kết quả: `tests/task_eval/ket_qua/`

### Chạy lại / mở rộng bộ eval

```bash
# chạy toàn bộ
python3 run_eval.py --comfy http://127.0.0.1:18188 --out ket_qua/ --stage all

# thêm case mới vào eval_set.json rồi chỉ chạy phần mới, không đụng case cũ
python3 run_eval.py --comfy http://127.0.0.1:18188 --out ket_qua/ \
    --stage all --only-new
```

---

## Giao diện

Có **hai** giao diện, dùng chung lớp lõi `app/core.py` (ComfyUI + định tuyến tác vụ):

### 1. Auralis — giao diện web (khuyến nghị)

Dựng theo bản thiết kế Claude Design "Auralis — Chatbot sinh ảnh". Frontend tĩnh
(`web/static/`) + backend FastAPI mỏng (`web/server.py`).

```bash
cd imagegen-stack/web
COMFY_INPUT=~/ComfyUI/input SESSION_DIR=~/app_sessions \
    python3 -m uvicorn server:app --port 7860
```

- **Nền sáng / tối**, sidebar thu gọn được, thư viện ảnh + lightbox
- **Tiến độ thật theo từng bước** lấy qua websocket ComfyUI (không phải thanh giả)
- **Nhiều ảnh một lượt** (1/2/4) — mỗi ảnh là một lần gửi `/prompt` riêng nên hiện dần
- **Hội thoại & ảnh lưu ở server** (`web/store.py`), không phải localStorage
- Phong cách sinh ảnh khai ở `web/styles_vi.py`, chữ nghĩa ở `web/content_vi.py`

API (mỗi chức năng trên giao diện có một endpoint):

| Nhóm | Endpoint |
|---|---|
| Trò chuyện | `GET POST /api/chats` · `PATCH DELETE /api/chats/{id}` · `GET /api/chats/{id}/messages` |
| Ảnh | `GET /api/gallery` · `GET /api/image/{id}[?download=1]` · `DELETE /api/image/{id}` · `POST /api/upload` |
| Sinh ảnh | `POST /api/generate` · `GET /api/progress/{job}` (SSE) · `POST /api/cancel/{job}` |
| Khác | `GET /api/options` · `GET /api/health` |

### 2. Gradio — giao diện cũ

Chat kiểu ChatGPT: gõ mô tả để tạo ảnh, gửi ảnh 📎 hoặc nói tiếp để sửa, gửi 2 ảnh để ghép.

- **Nhớ ngữ cảnh** — "tạo con mèo" → "thêm cái mũ" → "đổi nền thành bãi biển" nối tiếp
  nhau trên cùng một ảnh
- **Chọn nhánh tự động** theo câu lệnh, hoặc bấm nút chế độ để ép
- **Tiến độ thật theo từng bước** lấy qua websocket của ComfyUI
- **Tab thư viện** — bấm ảnh bất kỳ để quay lại sửa tiếp từ ảnh đó

> **Lưu ý VRAM:** Qwen-Image 20B fp8 cần ~30GB VRAM trống. Nếu máy đang chạy service
> LLM khác (vLLM/SGLang thường chiếm sẵn ~90% VRAM), ComfyUI sẽ chết giữa chừng khi
> lấy mẫu mà **không in traceback**. Kiểm tra trước bằng `nvidia-smi`.

---

## Ghi chú về tiếng Việt

Qwen-Image chỉ được huấn luyện render chữ **Anh + Trung**; lỗi dấu (tiếng Ba Lan) vẫn còn
mở tới 01/2026 và **không tìm thấy bất kỳ test tiếng Việt nào** từ cộng đồng.

Bộ eval này đo được:

- **Prompt tiếng Việt để *tạo ảnh* dùng tốt** — 92.9% (7 case T2I đều viết bằng tiếng Việt)
- **Chỉ dẫn *sửa ảnh* nên viết tiếng Anh** — đó là cách 43 case edit đã được kiểm chứng;
  tiếng Việt cho việc sửa **chưa được đo**
- **Render chữ tiếng Việt lên ảnh chưa kiểm chứng** — bộ test ở `tests/vi_text_testset.json`
  còn nguyên, chưa chạy

Chi tiết khảo sát: [`BAO_CAO_MODEL_ANH_VIDEO.md`](BAO_CAO_MODEL_ANH_VIDEO.md)

---

## Cấu trúc

```
imagegen-stack/
├── app/app.py                    giao diện Gradio
├── workflows/
│   ├── W_qwen_6tasks.json        workflow duy nhất, đủ 6 tác vụ
│   ├── build.py                  chọn nhánh theo task
│   ├── _generate.py              sinh lại workflow từ tham số gốc
│   └── _validate.py              đối chiếu với schema ComfyUI
├── tests/task_eval/              bộ eval 50 case + kết quả + ảnh
├── docs/WORKFLOWS.md             hướng dẫn chi tiết
├── vi/                           lớp prompt tiếng Việt, render chữ bằng Pillow
└── MODELS.md                     danh sách file model đã xác minh trên HF

_workspace/node_schemas.md        schema node ComfyUI trích thẳng từ source
BAO_CAO_MODEL_ANH_VIDEO.md        khảo sát model <30B sinh ảnh + video
```

## Yêu cầu

ComfyUI · Python 3.11/3.12 · GPU ≥ 32GB VRAM ·
model Qwen-Image-2512 + Qwen-Image-Edit-2511 (xem `MODELS.md`)

Phụ thuộc Python của repo nằm ở `requirements.txt` (4 gói; phần còn lại là thư viện chuẩn):

```bash
pip install -r requirements.txt
```

App chạy venv riêng, tách khỏi venv của ComfyUI — nó chỉ gọi HTTP/websocket, không cần torch.

### Đường dẫn cấu hình bằng biến môi trường

`app.py` mặc định theo layout máy vast.ai (`/workspace/...`). Chạy ở máy khác thì đặt:

| Biến | Mặc định |
|---|---|
| `COMFY_URL` | `http://127.0.0.1:18188` |
| `COMFY_INPUT` | `/workspace/ComfyUI/input` |
| `SESSION_DIR` | `/workspace/app_sessions` |

```bash
COMFY_INPUT=~/ComfyUI/input SESSION_DIR=~/app_sessions python3 imagegen-stack/app/app.py
```

---

## Triển khai trên máy GPU thuê mới — step by step

Áp dụng khi thuê lại GPU (vd vast.ai) từ đầu, máy trống hoàn toàn.

### 1. Thuê máy
- Image đã dùng và xác nhận chạy tốt: **`vastai/comfy:v0.30.0-cuda-13.2-py312`**
  (ComfyUI + Jupyter + Caddy proxy cài sẵn, không cần tự cài ComfyUI).
- GPU **≥ 32GB VRAM** — đã kiểm chứng trên **RTX 5090 32GB** (phương án fp8, xem `MODELS.md`
  phương án A). Card 24GB thì bắt buộc đổi sang phương án B (GGUF Q6_K trong `MODELS.md`),
  khi đó phải cài thêm node pack `city96/ComfyUI-GGUF`.
- Ổ đĩa trống **≥ 150GB** (model fp8 riêng ảnh ~50.6GB, cộng buffer).
- ComfyUI trên image này tự khởi động sẵn với `COMFYUI_ARGS=--disable-auto-launch
  --disable-xformers --port 18188 --enable-cors-header` — không cần tự set.

### 2. Kết nối
- Lấy IP/port thật (đổi mỗi lần tạo máy mới): `vastai show instances --raw`.
- SSH vào máy bằng `ssh_host`/`ssh_port` trong kết quả trên.
- Gọi ComfyUI **qua cổng nội bộ sau khi đã SSH vào**: `http://127.0.0.1:18188` —
  không cần token, không đi qua Caddy public.
- **Không gọi thẳng cổng public** (map từ 8188) từ máy ngoài — nó nằm sau Caddy, đòi
  Basic/Bearer `OPEN_BUTTON_TOKEN` (đọc bằng `env | grep OPEN_BUTTON_TOKEN` trên máy đó),
  và việc nhét token vào lệnh curl chạy ở máy điều khiển thường bị chặn bởi bộ lọc an toàn.

### 3. Tải model
- Theo đúng bảng file + đích trong `MODELS.md` (phương án A cho ≥32GB): 4 file vào
  `models/diffusion_models/`, `models/text_encoders/`, `models/vae/`.
- **Không cần cài thêm node pack nào** cho workflow hiện tại — `W_qwen_6tasks.json` chỉ
  dùng node lõi ComfyUI (`UNETLoader`, `CLIPLoader`, `VAELoader`, `KSampler`,
  `FluxKontextImageScale`, `FluxKontextMultiReferenceLatentMethod`, `CFGNorm`,
  `ModelSamplingAuraFlow`, `TextEncodeQwenImageEditPlus`, ...). Node pack GGUF chỉ cần nếu
  đi phương án B.
- Kiểm tra môi trường đúng theo `MODELS.md`: Python 3.11/3.12 (không 3.13/3.14), PyTorch
  cu128+ (Blackwell sm_120), gỡ xformers, không cài SageAttention.

### 4. Copy code
- Copy nguyên thư mục `imagegen-stack/` từ nguồn (`103.130.219.238:/root/Image`) sang máy
  thuê — máy thuê chỉ là bản sao tạm, không sửa code trực tiếp ở đó.

### 5. Chạy & "load" workflow
- Workflow **không nạp tay vào ComfyUI GUI** — `workflows/build.py` sinh JSON từ
  `W_qwen_6tasks.json` theo `--task` (cắt nhánh không dùng) rồi gửi thẳng qua API
  `POST /prompt`. Chỉ mở GUI ComfyUI khi cần soi bằng mắt lúc debug.
- Chạy giao diện chat (cách dùng chính): `python3 imagegen-stack/app/app.py --share`
  (hoặc `--auth user:pass`) — app tự gọi `127.0.0.1:18188`, không cần cấu hình gì thêm.
- Dựng + gửi workflow tay để test API: xem lệnh ở mục "Bắt đầu nhanh".

### 6. Kiểm tra trước khi tin kết quả
```bash
curl -s http://127.0.0.1:18188/system_stats          # ComfyUI đã lên, trả JSON có comfyui_version
python3 imagegen-stack/workflows/_validate.py         # đối chiếu workflow với schema (không thay chạy thật)
```
Muốn đo lại chất lượng thật: chạy bộ eval 50 case (mục "Chạy lại / mở rộng bộ eval" ở trên).
