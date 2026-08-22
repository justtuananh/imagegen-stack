# Danh sách model đã xác minh (HF API, 20/08/2026)
Mọi dòng dưới đây đều đã kiểm tra tồn tại + dung lượng thật + license qua `huggingface.co/api/models`.

## ⚠️ SỬA BÁO CÁO: có bản mới hơn 2509

| Model | Ngày tạo | License | Downloads | Ghi chú |
|---|---|---|---|---|
| **Qwen/Qwen-Image-Edit-2511** | 2025-12-17 | apache-2.0 | 242.646 | **Mới hơn 2509** — dùng cái này |
| **Qwen/Qwen-Image-2512** | 2025-12-30 | apache-2.0 | 97.204 | Bản T2I mới, thay Qwen-Image gốc |
| Qwen/Qwen-Image-Edit-2509 | 2025-09 | apache-2.0 | — | Đã cũ, bỏ |

Báo cáo trước nói "bản 20B tháng 8/2025 là bản tải được duy nhất" → **sai**.
Qwen-Image 2.0/3.0 đúng là chỉ có API, nhưng dòng 25xx (2511/2512) vẫn open-weight Apache-2.0.

---

## Phương án A — fp8 native (khuyến nghị cho 5090 32GB, chất lượng cao hơn GGUF)

| File | GB | Repo | Đích |
|---|---|---|---|
| `qwen_image_2512_fp8_e4m3fn.safetensors` | 20.43 | Comfy-Org/Qwen-Image_ComfyUI | `models/diffusion_models/` |
| `qwen_image_edit_2511_fp8mixed.safetensors` | 20.53 | Comfy-Org/Qwen-Image-Edit_ComfyUI | `models/diffusion_models/` |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | 9.38 | Comfy-Org/Qwen-Image_ComfyUI | `models/text_encoders/` |
| `qwen_image_vae.safetensors` | 0.25 | Comfy-Org/Qwen-Image_ComfyUI | `models/vae/` |
| `wan2.2_ti2v_5B_fp16.safetensors` | 10.00 | Comfy-Org/Wan_2.2_ComfyUI_Repackaged | `models/diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.74 | Comfy-Org/Wan_2.2_ComfyUI_Repackaged | `models/text_encoders/` |
| `wan2.2_vae.safetensors` | 1.41 | Comfy-Org/Wan_2.2_ComfyUI_Repackaged | `models/vae/` |
| `seedvr2_ema_3b_fp8_e4m3fn.safetensors` | 3.39 | numz/SeedVR2_comfyUI | node pack SeedVR2 |
| `ema_vae_fp16.safetensors` | 0.50 | numz/SeedVR2_comfyUI | node pack SeedVR2 |

**Tổng ≈ 72.6 GB** (tất cả trong `split_files/...` của repo tương ứng)

> Lưu ý VRAM: DiT fp8 20.5 GB + text encoder 9.38 GB = 29.9 GB — sát 32 GB, nhưng ComfyUI
> giải phóng text encoder sau khi encode xong nên vẫn chạy được. Nếu OOM thì rơi về phương án B.

## Phương án B — GGUF (an toàn hơn, cần cho card 24GB)

| File | GB | Repo |
|---|---|---|
| `qwen-image-2512-Q6_K.gguf` | 16.82 | unsloth/Qwen-Image-2512-GGUF (apache-2.0) |
| `qwen-image-edit-2511-Q6_K.gguf` | 16.85 | unsloth/Qwen-Image-Edit-2511-GGUF (apache-2.0) |
| `Wan2.2-TI2V-5B-Q8_0.gguf` | **5.40** | QuantStack/Wan2.2-TI2V-5B-GGUF |

> Bảng GGUF đầy đủ: Q2_K 7.3 · Q4_K_M 13.2 · Q5_K_M 15.0 · **Q6_K 16.8** · Q8_0 21.8 GB
> Wan2.2-TI2V-5B: Q4_K_M 3.43 · Q5_K_M 3.81 · Q6_K 4.21 · **Q8_0 5.40 GB**
> → Video nhẹ đến mức trên 5090 cứ dùng thẳng Q8_0 hoặc fp16, không cần cân nhắc.
> (Khoảng trống "Wan2.2-TI2V-5B GGUF bị 401" trong báo cáo cũ: **đã lấp**.)

## LoRA tăng tốc (tuỳ chọn, đo A/B trước khi dùng)

| File | GB | Repo |
|---|---|---|
| `Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors` | 0.85 | lightx2v/Qwen-Image-Edit-2511-Lightning |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | 0.85 | (nt) |
| — | — | lightx2v/Qwen-Image-2512-Lightning |

## Node pack ComfyUI cần cài
- `city96/ComfyUI-GGUF` — chỉ cần nếu đi phương án B
- `numz/ComfyUI-SeedVR2_VideoUpscaler` — khâu làm nét (HTTP 200, repo còn sống)

## Môi trường máy thuê (bắt buộc)
- Python **3.11 hoặc 3.12** — KHÔNG dùng 3.13/3.14 (PyTorch chưa hỗ trợ)
- PyTorch **cu128+** (Blackwell sm_120)
- **Gỡ xformers**, chạy `--use-pytorch-cross-attention`
- **Không cài SageAttention** — dùng Triton + torch.compile
- Ổ đĩa: cần **≥ 150 GB** trống
