# Research Plan — Model <30B: text -> image + video, offline

## Hard constraints (from user)
- Params < 30B (total). Open-weights only, fully AIR-GAPPED (no API calls, no phone-home).
- Input: text. Output: IMAGE **and** VIDEO.
- Image tasks required: generation, instruction-based editing, upscaling/restoration ("làm nét").
- GPU targets to cover: RTX 5090 32GB (owned), RTX 4090/3090 24GB, A100/H100 80GB.
- Vietnamese: prompt understanding + rendering Vietnamese text WITH DIACRITICS on the image.
- Prefer a truly unified model; a 2-3 model stack is an acceptable fallback.
- Deliverable: Vietnamese report, 8 sections, exactly 5 ranked candidates. Concise.

## Sub-questions by angle

### Q1 — Truly unified text->image+video models <30B
Wan2.2-TI2V-5B, SkyReels-V3 (14B/19B), BAGEL-7B, OmniGen2, Lumina-DiMOO, Emu3, Show-o2,
Janus-Pro, any 2026 releases. Which ACTUALLY emit both image and video from one checkpoint?

### Q2 — Image generation + instruction editing <30B
Qwen-Image (20B MMDiT), Qwen-Image-Edit-2509, FLUX.2 [dev], FLUX.1 Kontext, Step1X-Edit,
HiDream-I1/E1, Lumina-Image 2.0, Chroma. Quality on GenEval / ImgEdit / GEdit-Bench.

### Q3 — Video generation <30B
Wan 2.2 T2V-A14B / I2V-A14B / TI2V-5B, Wan 2.5/2.7 if open, LTX-Video 13B (0.9.8/2),
HunyuanVideo 13B, CogVideoX-5B, SkyReels-V3, Mochi-1, Open-Sora 2.0. VBench scores.

### Q4 — Upscale / restore / "làm nét"
SUPIR, SeedVR2 (3B/7B), Real-ESRGAN, 4x-UltraSharp, Flux/Qwen tile-upscale workflows,
video upscalers (SeedVR2 video, Topaz alternatives OSS). VRAM + speed.

### Q5 — Serving frameworks
ComfyUI (native + GGUF city96 + Nunchaku/SVDQuant), Diffusers, DiffSynth-Studio,
xDiT / Ray multi-GPU, TensorRT, sage-attention/flash-attn, block-swap & CPU offload.
Which is realistic for an air-gapped bundle?

### Q6 — VRAM measured, by quantization
For each candidate: BF16 / FP8 / Q8_0 / Q6_K / Q5_K_M / Q4_K_M. MUST record
(quant, resolution, frames, offload on/off). Speed: s/step or total s per image / per 5s video.
Blackwell RTX 5090 specifics: CUDA 12.8+, PyTorch build, known breakages.

### Q7 — License + air-gap feasibility
Apache-2.0 vs non-commercial vs restricted. Total weight download size (GB) per candidate,
incl. text encoder (Qwen2.5-VL 7B, T5-XXL, umT5) and VAE.

### Q8 — Vietnamese
Prompt understanding in VI; rendering Vietnamese diacritics as text inside generated images.
Qwen-Image is claimed strong at CJK+multilingual text — verify for Vietnamese specifically.

## Angle assignment
- docs-researcher   -> Q1,Q2,Q3,Q4,Q5,Q7 (HF model cards, GitHub, ComfyUI docs, GGUF repos)
- web-researcher    -> Q1,Q2,Q3,Q7 (leaderboards, benchmarks, release dates, licenses)
- community-researcher -> Q3,Q4,Q5,Q6,Q8 (real-world VRAM/speed, 5090 issues, VI text tests)
- academic-researcher  -> Q1,Q2,Q3 (arXiv: architectures, unified gen, quant-vs-quality ablations)

## Claim schema
Each claim: {id, question, claim, evidence, source_url, source_type, date, confidence, caveats}
Any VRAM number WITHOUT (quant, resolution, offload) must be marked caveat="unqualified".
