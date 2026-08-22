# Khảo sát model <30B: text → ảnh + video, chạy offline
**Ngày:** 20/08/2026 · **Phương pháp:** 4 agent khảo sát song song (docs / benchmark / cộng đồng / arXiv) + đối chiếu chéo, các số liệu quan trọng được kiểm chứng trực tiếp từ nguồn gốc.

---

> ### ⚠️ ĐÍNH CHÍNH (20/08/2026, kiểm tra trực tiếp HF API)
> Báo cáo viết "bản 20B tháng 8/2025 là bản tải được duy nhất" — **sai**. Thực tế còn hai bản
> mới hơn, đều **Apache-2.0, open weights**:
> - **`Qwen/Qwen-Image-Edit-2511`** (17/12/2025 · 242.646 lượt tải) — thay cho 2509
> - **`Qwen/Qwen-Image-2512`** (30/12/2025 · 97.204 lượt tải) — thay cho Qwen-Image gốc
>
> Chỉ Qwen-Image **2.0 / 3.0** mới là API-only. Mọi khuyến nghị "Qwen-Image-Edit-2509" bên dưới
> nên đọc thành **2511**; phần VRAM/GGUF gần như không đổi (Q6_K 16.85 GB so với 16.82 GB).
>
> Đồng thời lấp một khoảng trống cũ: **`QuantStack/Wan2.2-TI2V-5B-GGUF` có thật** —
> Q8_0 chỉ **5.40 GB**, nên trên 5090 dùng thẳng fp16/Q8_0, khỏi cân nhắc quant.
>
> Danh sách file đã xác minh: `imagegen-stack/MODELS.md`

---

## 1. Tóm tắt điều hành

- **Không tồn tại** model <30B nào vừa sinh ảnh tĩnh vừa sinh video trong **một checkpoint** ở mức chất lượng dùng được. Cả 3 hướng khảo sát (benchmark / arXiv / model card) đều xác nhận độc lập.
- Model duy nhất đúng nghĩa "unified ảnh+video <30B" là **Emu3 (8B)** và **Show-o2 (7B)** — nhưng chất lượng thua xa model chuyên biệt, không có điểm VBench công bố. Nghiên cứu độc lập *GapEval* (arXiv 2602.02140) kết luận các model unified chỉ hợp nhất **ở bề mặt**.
- **Khuyến nghị: stack 2 model, tổng 25B** — `Qwen-Image-Edit-2509 (20B)` cho ảnh + `Wan2.2-TI2V-5B (5B)` cho video. Cả hai **Apache-2.0**, chạy offline hoàn toàn, vừa RTX 5090 32GB.
- **Rủi ro lớn nhất — tiếng Việt:** Qwen-Image **chỉ được huấn luyện render chữ Anh + Trung**. Có issue mở về **lỗi dấu tiếng Ba Lan** (ą/ć/ę/ł/ń) từ 30/09/2025, **maintainer chưa trả lời**. **Không tìm thấy bất kỳ test tiếng Việt nào.** Phải test trước khi cam kết.
- **Rủi ro thứ hai — RTX 5090:** Blackwell (sm_120) làm hỏng SageAttention, xformers, Nunchaku. Bắt buộc PyTorch cu12.8+/nightly. Đây là chi phí setup thật, không phải chuyện nhỏ.
- Wan **2.5 / 2.6 / 2.7 không có open weights** (đã kiểm tra HF API org `Wan-AI`) — chỉ tới 2.2. Qwen-Image **2.0 / 3.0 cũng chỉ có API**. Bản 20B tháng 8/2025 vẫn là bản tải được duy nhất.

---

## 2. Bối cảnh & tiêu chí chấm

| # | Tiêu chí | Trọng số | Lý do |
|---|---|---|---|
| T1 | Sinh ảnh + **sửa ảnh theo chỉ dẫn** | 25% | Yêu cầu cốt lõi |
| T2 | Sinh **video** từ text | 25% | Yêu cầu cốt lõi |
| T3 | Vừa **VRAM 32GB** (RTX 5090 đang có) | 20% | Ràng buộc phần cứng |
| T4 | **Offline / air-gapped** được | 15% | Ràng buộc bắt buộc |
| T5 | **Tiếng Việt** (prompt + render dấu) | 10% | Yêu cầu riêng |
| T6 | License + tổng ≤30B | 5% | Ràng buộc mềm |

> **Quy ước:** mọi con số VRAM đều ghi kèm *(quant, độ phân giải, số frame, có/không offload)*. Số thiếu ngữ cảnh được đánh dấu **"chưa xác minh"** — không suy diễn.

---

## 3. Top 5 ứng viên

Phần **ảnh** gần như đã chốt: `Qwen-Image-Edit-2509` là model <30B duy nhất có license Apache-2.0 + khả năng sửa ảnh theo chỉ dẫn mạnh. Khác biệt thật giữa 5 ứng viên nằm ở **động cơ video**.

---

### 🥇 #1 — Qwen-Image-Edit-2509 (20B) + Wan2.2-TI2V-5B (5B) — **tổng 25B**
**Kiểu:** stack 2 model (KHÔNG phải unified) · **License:** Apache-2.0 cả hai

| Hạng mục | Chi tiết |
|---|---|
| Tạo ảnh / sửa ảnh | Qwen-Image-Edit-2509 — 20B MMDiT, sửa đa ảnh (1–3 ảnh), giữ danh tính người, ControlNet depth/edge/pose tích hợp, sửa chữ trên ảnh (font/màu/chất liệu) |
| Video | Wan2.2-TI2V-5B — dense 5B, **T2V + I2V trong 1 checkpoint**, 720p/24fps |
| VRAM ảnh | GGUF Q6_K **16.8 GB** / Q4_K_M **13.1 GB** *(chỉ riêng DiT, chưa gồm text encoder Qwen2.5-VL 7B + VAE)*; Nunchaku INT4 ~**12 GB**, ~1.7s/ảnh 1024px trên 5090 *(nguồn vendor, chưa có bên thứ 3 xác nhận)* |
| VRAM video | Chính thức **24 GB** *(720p, `--offload_model True --convert_model_dtype`)*; bỏ offload → **≥80 GB** |
| Tốc độ video | ~**9 phút** cho clip 5s 720p trên RTX 4090 *(chính thức, không dùng LoRA tăng tốc)* |
| Tải về offline | Qwen-Image BF16 đầy đủ ~**58 GB**; Wan2.2-TI2V-5B ~**54 GB** (umT5-xxl 11.36 GB + VAE 2.81 GB). Đi đường GGUF giảm còn ~**35–40 GB** |
| **KHÔNG làm được** | ❌ Wan2.2-TI2V-5B **không sinh ảnh tĩnh** — "unified" ở đây chỉ là T2V+I2V<br>❌ Qwen-Image **không sinh video**<br>❌ Không model nào làm nét/upscale tốt — **phải thêm SeedVR2 hoặc SUPIR**<br>❌ Chưa có bằng chứng render được dấu tiếng Việt |

**Vì sao #1:** tổng đúng 25B (<30B), hai license Apache-2.0 sạch nhất (không giới hạn doanh thu, không giới hạn lãnh thổ), cả hai chạy vừa 32GB, hệ sinh thái GGUF/ComfyUI/Diffusers chín nhất.

---

### 🥈 #2 — Qwen-Image-Edit-2509 (20B) + Wan2.2-T2V/I2V-A14B (27B total / 14B active)
**Kiểu:** stack · **License:** Apache-2.0 cả hai

| Hạng mục | Chi tiết |
|---|---|
| Điểm mạnh | Chất lượng video **cao nhất** trong nhóm open-weight Apache-2.0. VBench ~85.0% (Wan2.2-T2V-A14B) — nhỉnh hơn HunyuanVideo |
| Kiến trúc | MoE 2 expert: expert *high-noise* lo bố cục (bước đầu), *low-noise* lo chi tiết (bước sau), chuyển đổi bằng ngưỡng SNR cứng. Mỗi expert ~14B → 27B tổng |
| VRAM chính thức | **≥80 GB** — Alibaba ghi thẳng là cần A100/H100, **không phải card consumer** |
| VRAM thực tế (cộng đồng) | GGUF trên RTX 4090, *720p / 81 frame / Lightning 4-step*: Q4_K_M ~**18 GB**/83s · Q5_K_M ~**20 GB**/85s · Q8_0 ~**26 GB**/95s *(độ tin cậy thấp, 1 nguồn)* |
| Cảnh báo | LoRA tăng tốc **Wan2.2-Lightning làm hỏng chuyển động** — nhiều người báo video thành "hình nền động", gần như tĩnh. Bỏ LoRA thì chậm gấp ~10 lần |
| **KHÔNG làm được** | ❌ Là **2 checkpoint riêng** — T2V-A14B chỉ text→video, I2V-A14B chỉ ảnh→video; muốn cả hai phải tải cả hai (27B × 2)<br>❌ Không sinh ảnh tĩnh, không upscale<br>❌ **Chưa ai báo cáo số đo thật trên RTX 5090** — đây là khoảng trống lớn nhất của khảo sát<br>❌ Vượt 30B nếu tính cả 2 biến thể |

**Vì sao không phải #1:** 27B tổng đã sát trần, cần quantize mạnh mới vừa 32GB, và tài liệu chính thức nói thẳng là 80GB.

---

### 🥉 #3 — Qwen-Image-Edit-2509 (20B) + HunyuanVideo-1.5 (8.3B) — **tổng 28.3B**
**Kiểu:** stack · **License:** Apache-2.0 + **Tencent Hunyuan Community License**

| Hạng mục | Chi tiết |
|---|---|
| Điểm mạnh | **Nhẹ VRAM nhất**: chính thức **14 GB** *(có bật model offloading)*. 480p/720p gốc, 1080p qua bước super-resolution riêng. Mặc định 121 frame |
| Tăng tốc | SSTA (Selective + Sliding Tile Attention) — nhanh hơn FlashAttention-3 **1.87×** ở 720p/10s |
| ⚠️ License | **KHÔNG phải Apache-2.0** (nhiều bài viết ghi sai). Thực tế: thương mại được nếu **<100 triệu MAU**, nhưng **loại trừ lãnh thổ EU / Anh / Hàn Quốc**; cấm dùng output để huấn luyện model cạnh tranh |
| **KHÔNG làm được** | ❌ Chỉ T2V + I2V, **không sinh ảnh tĩnh**<br>❌ Chất lượng video dưới Wan2.2-A14B<br>❌ Ràng buộc lãnh thổ — Việt Nam thì OK, nhưng nếu sau này bán sang EU thì vướng |

**Chọn khi:** VRAM là ràng buộc gắt nhất (card 16–24GB), hoặc cần chạy nhiều job video song song trên 1 card.

---

### #4 — LTX-2.3 (22B, video + audio đồng bộ) làm trục video
**Kiểu:** video-only · **License:** **LTX-2.x Community License** — trần doanh thu **10 triệu USD/năm**

| Hạng mục | Chi tiết |
|---|---|
| Điểm mạnh | **Nhanh nhất** nhóm (cộng đồng: nhanh hơn Wan2.2/Hunyuan ~3–4×). Sinh **video + audio đồng bộ** — duy nhất trong danh sách. Có bản FP8 và distilled 8-step chính thức, 62 bản quant cộng đồng. Elo cao trên Artificial Analysis T2V (LTX-2.5 Fast: 1210) |
| Tốc độ | LTX-Video 13B thế hệ trước: 1216×704, 88 frame ≈ **2 phút 8 giây** *(RTX 4090 bản 48GB, không offload)* |
| Yêu cầu | Python ≥3.12, **CUDA >12.7**, PyTorch ~2.7 — hợp Blackwell, nhưng kén môi trường |
| **KHÔNG làm được** | ❌ Không sinh ảnh tĩnh, không sửa ảnh<br>❌ **Chuyển động yếu** — bị chê nhiều nhất về mạch chuyển động ("như slideshow có lồng tiếng")<br>❌ Model card **không công bố con số VRAM nào** — chưa xác minh<br>❌ License có trần doanh thu; 22B là mức cao |

---

### #5 — Emu3 (8B) — *unified thật sự duy nhất, nhưng KHÔNG khuyến nghị*
**Kiểu:** **UNIFIED THẬT** — 1 checkpoint, text/ảnh/video chung một từ vựng token · **License:** Apache-2.0

| Hạng mục | Chi tiết |
|---|---|
| Vì sao có mặt | Đây là **câu trả lời đúng nghĩa đen** cho yêu cầu của bạn: một transformer 8B duy nhất, dự đoán token kế tiếp, tokenize **cả text, ảnh VÀ video** vào một vocab 184.622 (tokenizer SBER-MoVQGAN). Show-o2 (7B) là ứng viên tương đương duy nhất còn lại |
| **KHÔNG làm được** | ❌ **Không có điểm VBench công bố** cho phần video — không đo được<br>❌ Chất lượng ảnh chỉ ngang SDXL/DALL·E 3 (mốc 2024), thua Qwen-Image rất xa<br>❌ Không sửa ảnh theo chỉ dẫn, không làm nét<br>❌ Hệ sinh thái gần như chết: không GGUF, hỗ trợ ComfyUI/Diffusers rất hạn chế<br>❌ *GapEval* xếp nhóm này vào loại "hợp nhất bề mặt", tri thức giữa các modality rời rạc |

**Kết luận:** giữ để tham khảo/nghiên cứu. Đừng đưa vào production.

---

## 4. Bảng so sánh tổng hợp

| | #1 Qwen+Wan-5B | #2 Qwen+Wan-A14B | #3 Qwen+Hunyuan1.5 | #4 LTX-2.3 | #5 Emu3 |
|---|---|---|---|---|---|
| **Tổng params** | **25B** ✅ | 20+27B ⚠️ | 28.3B ✅ | 22B ✅ | **8B** ✅ |
| **Unified thật?** | Không | Không | Không | Không | **Có** |
| Tạo ảnh | ✅ | ✅ | ✅ | ❌ | ⚠️ yếu |
| Sửa ảnh chỉ dẫn | ✅ mạnh | ✅ mạnh | ✅ mạnh | ❌ | ❌ |
| Làm nét / upscale | ➕ cần SeedVR2 | ➕ cần SeedVR2 | ➕ cần SeedVR2 | ❌ | ❌ |
| Sinh video | ✅ 720p | ✅✅ tốt nhất | ✅ | ✅✅ + audio | ⚠️ yếu |
| VRAM video (thực tế) | 24 GB *(offload)* | 18–26 GB *(GGUF)* | **14 GB** *(offload)* | chưa xác minh | — |
| Vừa RTX 5090 32GB | ✅ thoải mái | ⚠️ phải quant | ✅ thoải mái | ✅ | ✅ |
| License | **Apache-2.0** | **Apache-2.0** | Tencent Community | Community, trần $10M | Apache-2.0 |
| Offline | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tiếng Việt render dấu | ⚠️ chưa xác minh | ⚠️ chưa xác minh | ⚠️ chưa xác minh | — | — |
| **Điểm tổng** | **8.6/10** | 7.8/10 | 7.5/10 | 6.0/10 | 3.5/10 |

**Bị loại (kèm lý do):**

| Model | Lý do loại |
|---|---|
| FLUX.2 [dev] | **32B — vượt trần**, và license **phi thương mại** |
| Qwen-Image 2.0 / 3.0 | **Chỉ có API, không có weights** → không chạy offline được |
| Wan 2.5 / 2.6 / 2.7 | **Không open weights** (đã kiểm tra HF org `Wan-AI`: mới nhất là 2.2 + Wan-Dancer-14B) |
| HunyuanImage 3.0 | **80B tổng** — vượt xa trần |
| SkyReels-V3, Bernini-R | Chỉ video, không sinh ảnh |
| BAGEL, OmniGen2, Janus-Pro, Lumina-DiMOO | Unified text+ảnh, **không có video** |
| SUPIR, 4x-UltraSharp | Chỉ upscale, và **phi thương mại** |

---

## 5. Framework & pipeline

| Framework | Dùng khi | Rủi ro offline |
|---|---|---|
| **ComfyUI** ⭐ | Ghép ảnh→sửa→upscale→video trong 1 graph. Hỗ trợ GGUF (ComfyUI-GGUF của city96), có node cho mọi model ở trên | ⚠️ ComfyUI-Manager và custom node **mặc định gọi internet** — phải bật network mode offline; xung đột dependency giữa các node là nguyên nhân hỏng cài đặt phổ biến nhất |
| **Diffusers** | Đưa lên production, gọi bằng code, ổn định | Phải tự cấu hình offload. `HF_HUB_OFFLINE` **không đáng tin** — nên trỏ trực tiếp đường dẫn local |
| **DiffSynth-Studio** | Apache-2.0, hỗ trợ đủ Qwen-Image + Wan + Hunyuan + LTX-2 + CogVideoX. Có offload theo từng layer (repo claim chạy Qwen-Image trong 4GB VRAM — *chưa nêu độ phân giải/tốc độ*) | Cộng đồng nhỏ hơn |
| **WanGP** | Chỉ chạy Wan, giao diện đơn giản, tự quản offload | Hẹp, ít plugin |

**Chọn quantization:**

| Mức | Kết luận |
|---|---|
| **BF16** | Chuẩn tham chiếu. Cần ~80GB cho Wan-A14B |
| **FP8 / INT8** | ✅ **Gần như không mất chất lượng.** Nghiên cứu độc lập trên DiT: INT8 W8A8 ≈ FP8 về CLIP/PickScore, khoảng tin cậy chứa 0 |
| **GGUF Q8_0 / Q6_K** | ✅ Điểm ngọt. Q8_0 gần như không phân biệt được với FP8 ở 480–720p |
| **GGUF Q5_K_M** | ✅ Ngưỡng an toàn thấp nhất |
| **GGUF Q4 trở xuống** | ⚠️ **Có vấn đề thật.** Qwen-Image-Edit-2509 GGUF dưới Q5 từng bị lỗi "ghosting" — chồng ảnh gốc lên output ở ~70% quá trình khử nhiễu (8+ người báo, publisher đã sửa 18/10/2025). Khoảng cách 8-bit→4-bit rơi vào **chi tiết mảnh và độ chính xác chữ** (LPIPS 0.243 INT8 vs 0.277 GGUF-Q4) |
| **Nunchaku / SVDQuant INT4** | ✅ Ngoại lệ — hút outlier vào nhánh low-rank 16-bit. FLUX.1: 22.2→6.1 GiB (giảm 3.6×), FID 19.9 (INT4) vs 20.3 (BF16). Hỗ trợ Qwen-Image. ⚠️ Cài trên 5090 hay lỗi |

**Làm nét / upscale (bắt buộc bổ sung — không model chính nào làm được):**

| Model | VRAM / tốc độ | License |
|---|---|---|
| **SeedVR2 (3B)** ⭐ | 768px → 2K khoảng **30–60s** trên RTX 4090; khuyến nghị 24GB, bản FP8 chạy được 12GB. Khôi phục **1 bước** (chưng cất đối kháng) — ảnh và video | **Apache-2.0** ✅ |
| SUPIR | Chạy được tile tới 3072×3072 trên 24GB; hay bị tràn sang RAM hệ thống → cực chậm | ⚠️ **Phi thương mại** |
| Real-ESRGAN | Rất nhẹ, nhanh, không cần GPU lớn. *(Lưu ý: "6B" trong `x4plus_anime_6B` là số residual block, KHÔNG phải 6 tỉ tham số)* | **BSD-3** ✅ |
| 4x-UltraSharp | 63.9 MB, chỉ upscale | ⚠️ CC-BY-NC-SA (phi thương mại) |

---

## 6. VRAM & GPU khuyến nghị

| Kịch bản | Cấu hình chạy được | Ghi chú |
|---|---|---|
| **24 GB** (RTX 4090 / 3090) | Qwen-Image GGUF **Q4_K_M–Q5_K_M** + Wan2.2-TI2V-5B *(bật offload)* hoặc HunyuanVideo-1.5 + SeedVR2 FP8 | Wan2.1-14B **không nén** thì 4090 OOM ở 720p, 3090 OOM cả 480p. Bắt buộc quantize |
| **32 GB** (RTX 5090 — bạn đang có) ⭐ | Qwen-Image GGUF **Q6_K / Q8_0** hoặc Nunchaku INT4 + Wan2.2-TI2V-5B, hoặc Wan2.2-A14B GGUF Q5_K_M/Q8_0 + SeedVR2 3B | Đủ chạy toàn bộ #1 và phần lớn #2. **Không cần nâng cấp** |
| **80 GB** (A100 / H100) | Toàn bộ BF16, kể cả Wan2.2-A14B nguyên bản, không offload | Wan2.1-T2V-14B full precision: H100 **85s** (480p) / **284s** (720p) mỗi clip 5s; A100 **170s / 523s** |

### ⚠️ RTX 5090 (Blackwell sm_120) — bắt buộc đọc

Đây là phần khảo sát có **bằng chứng mạnh nhất**: 5 repo GitHub độc lập xác nhận (pytorch#167244, FramePack#550, Fooocus#3862, SageAttention#291/#244, Nunchaku#226).

| Vấn đề | Cách xử lý |
|---|---|
| PyTorch bản stable **thiếu kernel sm_120** → `CUDA error: no kernel image is available` | Dùng PyTorch **cu12.8+** (nhiều người dùng nightly cu130) |
| **SageAttention** hỏng nhiều kiểu: wheel dựng sẵn crash (`sageattention._qattn_sm89`); build từ source lỗi LLVM `sm_120 not recognized` | Thay bằng **Triton + torch.compile + SDPA gốc của PyTorch**. Cộng đồng ước tính mất ~35% tốc độ so với SageAttention chạy được |
| **xformers** chỉ có wheel tới RTX 40-series, cài vào là **âm thầm hạ cấp PyTorch nightly** | Gỡ hẳn xformers, chạy `--disable-xformers --use-pytorch-cross-attention` |
| **Nunchaku**: `AssertionError: Unsupported SM 120` | Cần PyTorch ≥2.7 + CUDA ≥12.8. Vẫn hay lỗi — đừng phụ thuộc vào INT4 Nunchaku trong kế hoạch |

**Về việc mua thêm GPU:** RTX PRO 6000 Blackwell 96GB (~8.000–9.200 USD) có throughput ảnh **gần như bằng** RTX 5090 (cùng die GB202, 192 vs 170 SM). Chỉ đáng mua nếu cần giữ nhiều model **cùng lúc** trong VRAM để tránh nạp lại. **Với khối lượng công việc này, 5090 32GB là đủ.**

---

## 7. Khuyến nghị triển khai

### Stack đề xuất (bundle air-gapped)

```
[Ảnh]     Qwen-Image-Edit-2509  GGUF Q6_K      ~16.8 GB
          + Qwen2.5-VL-7B text encoder          ~16 GB   (bắt buộc, chưa nằm trong GGUF)
          + VAE                                  ~0.3 GB
[Video]   Wan2.2-TI2V-5B  (FP8 hoặc GGUF)       ~5-11 GB
          + umT5-xxl encoder                    ~11.4 GB
          + Wan2.2 VAE                           ~2.8 GB
[Làm nét] SeedVR2-3B (FP8)                       ~3-6 GB
[Runtime] ComfyUI + ComfyUI-GGUF + node deps      ~5 GB
────────────────────────────────────────────────────────
TỔNG TẢI VỀ                                   ~60-75 GB
```
*(Nếu chạy BF16 đầy đủ: Qwen-Image ~58 GB + Wan2.2-TI2V-5B ~54 GB ≈ **112 GB**)*

### Thứ tự thực hiện

1. **Test tiếng Việt TRƯỚC — đây là cổng quyết định.** Chạy Qwen-Image sinh 20 ảnh có chữ Việt có dấu ("Tuyển dụng kỹ sư", "Hội nghị thường niên"…). Nếu sai dấu → chuyển sang **ghép chữ bằng lớp riêng** (sinh ảnh không chữ, rồi overlay text bằng PIL/ImageMagick với font Việt). Cách này cho kết quả chữ **chính xác 100%** và loại bỏ rủi ro lớn nhất của cả dự án.
2. **Dựng môi trường 5090 trước khi tải model.** PyTorch cu12.8+, bỏ xformers, không dùng SageAttention. Xác nhận `torch.cuda.is_available()` và chạy được 1 ảnh SDXL rồi mới đi tiếp.
3. Cài Qwen-Image-Edit-2509 GGUF Q6_K → kiểm tra sửa ảnh theo chỉ dẫn.
4. Cài Wan2.2-TI2V-5B → benchmark thật trên 5090 (chưa ai công bố số này, bạn sẽ là người đo đầu tiên).
5. Thêm SeedVR2 cho khâu làm nét.
6. Đóng gói: bật network mode **offline** cho ComfyUI-Manager, trỏ đường dẫn model **tuyệt đối** thay vì dựa vào `HF_HUB_OFFLINE`.

### Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| **Chữ tiếng Việt sai dấu** | 🔴 Cao | Test ở bước 1. Có sẵn phương án overlay text — coi như model chỉ lo phần hình |
| **Dependency 5090 (sm_120)** | 🔴 Cao | Dựng môi trường trước, chốt phiên bản, đóng băng bằng Docker image |
| Không có số đo Wan2.2 trên 5090 | 🟡 Vừa | Tự benchmark ở bước 4; dự phòng là HunyuanVideo-1.5 (14GB) |
| ComfyUI gọi mạng khi air-gapped | 🟡 Vừa | Bật offline mode, đường dẫn tuyệt đối, test trong container không có mạng |
| LoRA Lightning làm hỏng chuyển động | 🟡 Vừa | Đo cả 2 chế độ (có/không LoRA) rồi hãy chọn |
| Chất lượng tụt ở GGUF Q4 | 🟢 Thấp | Dùng Q6_K trở lên — 32GB VRAM của bạn thừa sức |

---

## 8. Nguồn tham khảo

**Model card & repo chính thức**
- Qwen-Image / Qwen-Image-Edit-2509 — huggingface.co/Qwen/Qwen-Image-Edit-2509 · arXiv 2508.02324
- Wan2.2 (TI2V-5B, T2V/I2V-A14B) — huggingface.co/Wan-AI · github.com/Wan-Video/Wan2.2 · (Wan2.1: arXiv 2503.20314)
- HunyuanVideo-1.5 — github.com/Tencent-Hunyuan/HunyuanVideo-1.5 (+ LICENSE)
- LTX-2 / LTX-2.3 — github.com/Lightricks/LTX-2 (LICENSE.md) · huggingface.co/Lightricks/LTX-2.3
- Emu3 — BAAI · Show-o2 · SkyReels-V3 (arXiv 2601.17323)
- SeedVR2 · SUPIR (CVPR 2024) · Real-ESRGAN

**Nghiên cứu**
- GapEval — arXiv 2602.02140 (unified models chỉ "hợp nhất bề mặt")
- SVDQuant / Nunchaku — ICLR 2025
- SVDQuant+GPTQ cho Wan2.2-I2V W4A4 — arXiv 2605.27003 (giảm 59.3% VRAM, VBench giảm 0.9%)

**Vấn đề thực tế**
- Lỗi dấu tiếng Ba Lan: github.com/QwenLM/Qwen-Image/issues/161 (mở 30/09/2025, chưa có phản hồi)
- RTX 5090 sm_120: pytorch/pytorch#167244 · SageAttention#291, #244 · Nunchaku#226 · FramePack#550
- Bảng quant GGUF: huggingface.co/QuantStack/Qwen-Image-GGUF

**Benchmark**
- Artificial Analysis T2I / T2V / Image Editing Arena (chụp 19/08/2026)
- VBench / VBench-2.0 (Vchitect)

---

### Giới hạn của báo cáo này

- **Chưa có số đo thật của Wan2.2-A14B trên RTX 5090** ở bất kỳ đâu — khoảng trống lớn nhất.
- **Không tìm thấy bất kỳ test tiếng Việt nào** cho mọi model trong danh sách. Bằng chứng duy nhất là gián tiếp (tiếng Ba Lan).
- Reddit (r/StableDiffusion, r/comfyui) **không truy cập được** — số liệu cộng đồng lấy từ GitHub issues, HF discussions, HN và blog độc lập.
- Con số Nunchaku 1.7s/ảnh trên 5090 đến từ **blog của chính vendor**, chưa có bên thứ ba lặp lại.
- Điểm VBench-2.0 dạng số không lấy được (leaderboard Gradio không render).
