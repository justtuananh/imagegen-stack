# Orchestrator direct verifications (primary sources, fetched 2026-08-20)

## CONFLICTS RESOLVED — corrections to gatherer claims

| # | Gatherer claim | Verdict | Primary source |
|---|---|---|---|
| C1 | web-022: HunyuanVideo-1.5 is **Apache-2.0** | **WRONG.** It is the **Tencent Hunyuan Community License**: commercial OK below 100M MAU, but territory **excludes EU / UK / South Korea**; outputs may not train competing models. | raw.githubusercontent.com/Tencent-Hunyuan/HunyuanVideo-1.5/main/LICENSE |
| C2 | web-020/021: LTX-2 / 2.5 is **Apache-2.0** (19B) | **WRONG.** License = **"LTX-2.x Community License Agreement"**, with a **US$10M annual-revenue cap** (above that requires a paid Commercial Use Agreement). HF card for LTX-2.3 tags `ltx-2-community-license-agreement`. LTX-2.3 = **22B** (not 19B), released 2026-03-05. | github.com/Lightricks/LTX-2/blob/main/LICENSE.md ; huggingface.co/Lightricks/LTX-2.3 |
| C3 | web-017: Wan 2.7 open-weight status "contested" | **RESOLVED: NOT open.** HF API listing of the `Wan-AI` org shows the newest public repos are the **Wan2.2 series** (T2V-A14B, I2V-A14B, TI2V-5B, S2V-14B, Animate-14B) plus `Wan-Dancer-14B` (2026-07-17). **No Wan2.5 / 2.6 / 2.7 repo exists.** Wan 2.5+ is Bailian-cloud/API only. | huggingface.co/api/models?author=Wan-AI |

## CONFIRMED (fetched directly, agrees with gatherers)

- **Qwen-Image-Edit-2509** — 20B, **Apache-2.0**, image editing only (single + multi-image, 1–3 images optimal), ControlNet depth/edge/pose built in, text editing with font/colour/material control. **No video.** Model card states no VRAM figure.
- **Wan2.2-TI2V-5B** — 5B dense, **Apache-2.0**, T2V **and** I2V in one checkpoint at 720p/24fps. **Does not emit still images.** Official: "at least **24GB VRAM** (e.g. RTX 4090)" *with* `--offload_model True --convert_model_dtype`; ~**9 min for a 5s 720p clip** on a 4090. Without offload → **≥80GB**.
- **HunyuanVideo-1.5** — 8.3B, T2V + I2V only (no T2I). Official minimum **14GB VRAM with model offloading enabled**; 480p/720p native, 1080p via a super-resolution pass; default 121 frames.
- **Qwen-Image GGUF (QuantStack)** — Q2_K 7.06 / Q3_K_M 9.68 / Q4_K_M 13.1 / Q5_K_M 14.9 / Q6_K 16.8 / Q8_0 21.8 GB (**DiT only — excludes the Qwen2.5-VL 7B text encoder and VAE**).

## KEY NEGATIVE FINDING (triangulated: web + academic + docs all agree)
No open-weight model <30B emits **both still images and video** from one checkpoint at competitive quality (Aug 2026).
- Wan2.2-TI2V-5B "unified" = T2V+I2V only, still video-only output.
- SkyReels-V3, Bernini-R, LTX-2.x, HunyuanVideo-1.5 = video-only.
- BAGEL, OmniGen2, Janus-Pro, Lumina-DiMOO = text+image only, **no video**.
- Emu3 (8B) and Show-o2 (1.5B/7B) are the ONLY two genuinely sharing weights across image+video — but both are far below specialist quality and have no published VBench score.
- Independent study **GapEval (arXiv 2602.02140)**: unified models show "surface-level unification", disjoint cross-modal knowledge.
=> The report must recommend a **stack**, and say so plainly.

## HARDWARE
RTX 5090 32GB ≈ RTX PRO 6000 Blackwell 96GB on per-image throughput (same GB202 die, 170/192 vs 192/192 SMs); PRO 6000 ~US$8–9.2k and only worth it to keep several models resident at once.
