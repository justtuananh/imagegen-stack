# ComfyUI Node Schemas — extracted from actual source

Fetched from `raw.githubusercontent.com`, repo `comfyanonymous/ComfyUI`, branch `master`, and
`city96/ComfyUI-GGUF`, branch `main`, on 2026-08-20.

Note on class_type: Several of these files (`nodes_wan.py`, `nodes_qwen.py`, `nodes_sd3.py`,
`nodes_video.py`) use ComfyUI's newer `io.ComfyNode` / `define_schema()` registration style
instead of the old `INPUT_TYPES()` classmethod + `NODE_CLASS_MAPPINGS` dict. In that style the
`node_id="..."` string passed to `io.Schema(...)` **is** the registered node identifier — i.e.
it is exactly what goes in `class_type` in API-format JSON. These nodes have no separate
`NODE_CLASS_MAPPINGS` entry; registration happens by scanning each file's `ComfyExtension.get_node_list()`.
I verified each node_id-style class below actually appears in its file's `get_node_list()`.

Files that still use the old `INPUT_TYPES()`/`NODE_CLASS_MAPPINGS` style (`nodes.py`,
`nodes_model_advanced.py`, GGUF's `nodes.py`) are noted as such; for those, `class_type` is the
`NODE_CLASS_MAPPINGS` key (which equals the Python class name in every case checked here).

---

## 1. comfy_extras/nodes_wan.py

Fetch path used: `comfy_extras/nodes_wan.py` — 200 OK, matches what was requested.

Registration style: `io.ComfyNode` / `define_schema()`. `class_type` = `node_id`.

```
class_type: WanImageToVideo
source: comfy_extras/nodes_wan.py (io.ComfyNode, node_id="WanImageToVideo")
inputs:
  positive: CONDITIONING (required)
  negative: CONDITIONING (required)
  vae: VAE (required)
  width: INT default=832 min=16 max=MAX_RESOLUTION step=16
  height: INT default=480 min=16 max=MAX_RESOLUTION step=16
  length: INT default=81 min=1 max=MAX_RESOLUTION step=4
  batch_size: INT default=1 min=1 max=4096
  clip_vision_output: CLIP_VISION_OUTPUT (optional)
  start_image: IMAGE (optional)
returns: (CONDITIONING "positive", CONDITIONING "negative", LATENT "latent")
```

```
class_type: Wan22ImageToVideoLatent
source: comfy_extras/nodes_wan.py (io.ComfyNode, node_id="Wan22ImageToVideoLatent")
inputs:
  vae: VAE (required)
  width: INT default=1280 min=32 max=MAX_RESOLUTION step=32
  height: INT default=704 min=32 max=MAX_RESOLUTION step=32
  length: INT default=49 min=1 max=MAX_RESOLUTION step=4
  batch_size: INT default=1 min=1 max=4096
  start_image: IMAGE (optional)
returns: (LATENT,)
```

Note: `MAX_RESOLUTION` is a constant imported from `nodes.py` (currently `16384`). Note also that
`Wan22ImageToVideoLatent`'s width/height step is **32**, not 16 — different from `WanImageToVideo`
(step 16). Do not conflate the two.

Other `*ImageToVideo` classes exist in this file (not requested, listed only so you don't confuse
them with the two above): `WanCameraImageToVideo`, `WanSoundImageToVideo`,
`WanSoundImageToVideoExtend`, `WanHuMoImageToVideo`, `WanInfiniteTalkToVideo`. None of these are
`Wan22ImageToVideoLatent` or `WanImageToVideo`.

---

## 2. comfy_extras/nodes_qwen.py

Fetch path used: `comfy_extras/nodes_qwen.py` — 200 OK (primary path worked; the fallback
`comfy_extras/nodes_qwen_image.py` was NOT needed — that path 404s / does not exist).

Registration style: `io.ComfyNode` / `define_schema()`. `class_type` = `node_id`.

```
class_type: TextEncodeQwenImageEdit
source: comfy_extras/nodes_qwen.py (io.ComfyNode, node_id="TextEncodeQwenImageEdit")
inputs:
  clip: CLIP (required)
  prompt: STRING (required, multiline=True, dynamic_prompts=True)
  vae: VAE (optional)
  image: IMAGE (optional)
returns: (CONDITIONING,)
```

Single-image variant. Takes `image` (singular), and `vae` only to produce a `reference_latents`
conditioning value when both `vae` and `image` are supplied.

```
class_type: TextEncodeQwenImageEditPlus
source: comfy_extras/nodes_qwen.py (io.ComfyNode, node_id="TextEncodeQwenImageEditPlus")
inputs:
  clip: CLIP (required)
  prompt: STRING (required, multiline=True, dynamic_prompts=True)
  vae: VAE (optional)
  image1: IMAGE (optional)
  image2: IMAGE (optional)
  image3: IMAGE (optional)
returns: (CONDITIONING,)
```

Confirms your question directly: `TextEncodeQwenImageEdit` takes `clip`, `prompt`, optional `vae`,
optional singular `image`. `TextEncodeQwenImageEditPlus` takes `clip`, `prompt`, optional `vae`,
and up to three optional images: `image1`, `image2`, `image3` (not `images` plural, not a list
input). Both have exactly one output, `CONDITIONING`, unnamed (default display name).

This file also defines `EmptyQwenImageLayeredLatentImage` (node_id
`EmptyQwenImageLayeredLatentImage`, display name "Empty Qwen Image Layered Latent") — not
requested but present, for completeness: inputs `width` INT default=640 min=16 max=MAX_RESOLUTION
step=16, `height` INT default=640 (same bounds), `layers` INT default=3 min=0 max=MAX_RESOLUTION
step=1, `batch_size` INT default=1 min=1 max=4096; returns `(LATENT,)`.

---

## 3. comfy_extras/nodes_model_advanced.py

Fetch path used: `comfy_extras/nodes_model_advanced.py` — 200 OK.

Registration style: old-style `INPUT_TYPES()` classmethod + `NODE_CLASS_MAPPINGS` dict at bottom
of file. Confirmed mapping keys: `"ModelSamplingSD3": ModelSamplingSD3` and
`"ModelSamplingAuraFlow": ModelSamplingAuraFlow` — both keys equal the class name exactly.

```
class_type: ModelSamplingSD3
source: comfy_extras/nodes_model_advanced.py
inputs:
  model: MODEL (required)
  shift: FLOAT default=3.0 min=0.0 max=100.0 step=0.01
returns: (MODEL,)
```

```
class_type: ModelSamplingAuraFlow
source: comfy_extras/nodes_model_advanced.py
inputs:
  model: MODEL (required)
  shift: FLOAT default=1.73 min=0.0 max=100.0 step=0.01
returns: (MODEL,)
```

`ModelSamplingAuraFlow` is a Python subclass of `ModelSamplingSD3` (inherits `RETURN_TYPES`,
`patch()`), overriding only `INPUT_TYPES` (different default `shift`), `FUNCTION` (`patch_aura`
vs `patch`), and `CATEGORY`. Default `shift`: **SD3 = 3.0**, **AuraFlow = 1.73**.

---

## 4. nodes.py

Fetch path used: `nodes.py` (repo root) — 200 OK.

### CLIPLoader

Registration style: old-style. Verified directly in `nodes.py`'s `NODE_CLASS_MAPPINGS` dict
(line ~2106): `"CLIPLoader": CLIPLoader`. Also verified `"UNETLoader": UNETLoader`,
`"VAELoader": VAELoader`, `"KSampler": KSampler`, `"LoadImage": LoadImage`,
`"VAEDecode": VAEDecode`, `"SaveImage": SaveImage`, `"CLIPTextEncode": CLIPTextEncode` — every
key equals its class name exactly, no divergence for any node in this section.

```
class_type: CLIPLoader
source: nodes.py
inputs:
  clip_name: COMBO (required) — from folder_paths.get_filename_list("text_encoders")
  type: COMBO (required) — exact allowed values (verbatim from source), in order:
    ["stable_diffusion", "stable_cascade", "sd3", "stable_audio", "mochi", "ltxv", "pixart",
     "cosmos", "lumina2", "wan", "hidream", "chroma", "ace", "omnigen2", "qwen_image",
     "hunyuan_image", "flux2", "ovis", "longcat_image", "cogvideox", "lens", "pixeldit",
     "ideogram4", "boogu", "krea2", "joyimage", "mage", "minimax"]
  device: COMBO (optional, advanced) — ["default", "cpu"]
returns: (CLIP,)
```

Directly answers your question: the **Qwen-Image** value is exactly `"qwen_image"` and the
**Wan** value is exactly `"wan"` (both present verbatim in the list above, index order preserved
from source).

### UNETLoader

```
class_type: UNETLoader
source: nodes.py
inputs:
  unet_name: COMBO (required) — from folder_paths.get_filename_list("diffusion_models")
  weight_dtype: COMBO (required, advanced) — exact allowed values:
    ["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"]
returns: (MODEL,)
```

Reads from the `diffusion_models` model subfolder (which folder_paths maps to
`models/unet` + `models/diffusion_models` on disk — see folder_paths.py line 31:
`folder_names_and_paths["diffusion_models"] = ([models/unet, models/diffusion_models], ...)`).

### VAELoader

```
class_type: VAELoader
source: nodes.py
inputs:
  vae_name: COMBO (required) — dynamically built list: folder_paths.get_filename_list("vae")
    + matching video/image TAE approx-VAE files from "vae_approx" + the literal string
    "pixel_space" appended at the end. Not a fixed literal list — depends on files present.
returns: (VAE,)
```

### EmptySD3LatentImage

Not found in `nodes.py` — lives in `comfy_extras/nodes_sd3.py` instead (fetched that file to
confirm; 200 OK). Registration style: `io.ComfyNode`, `node_id="EmptySD3LatentImage"`.

```
class_type: EmptySD3LatentImage
source: comfy_extras/nodes_sd3.py (io.ComfyNode, node_id="EmptySD3LatentImage")
inputs:
  width: INT default=1024 min=16 max=MAX_RESOLUTION step=16
  height: INT default=1024 min=16 max=MAX_RESOLUTION step=16
  batch_size: INT default=1 min=1 max=4096
returns: (LATENT,)
```

### KSampler

```
class_type: KSampler
source: nodes.py
inputs:
  model: MODEL (required)
  seed: INT default=0 min=0 max=18446744073709551615 (0xffffffffffffffff) control_after_generate=True
  steps: INT default=20 min=1 max=10000
  cfg: FLOAT default=8.0 min=0.0 max=100.0 step=0.1 round=0.01
  sampler_name: COMBO (required) — comfy.samplers.KSampler.SAMPLERS (full list below)
  scheduler: COMBO (required) — comfy.samplers.KSampler.SCHEDULERS (full list below)
  positive: CONDITIONING (required)
  negative: CONDITIONING (required)
  latent_image: LATENT (required)
  denoise: FLOAT default=1.0 min=0.0 max=1.0 step=0.01
returns: (LATENT,)
```

`sampler_name` full option list (from `comfy/samplers.py`, `SAMPLER_NAMES = KSAMPLER_NAMES +
["ddim", "uni_pc", "uni_pc_bh2"]`), verbatim order:
```
["euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp", "heun", "heunpp2",
 "exp_heun_2_x0", "exp_heun_2_x0_sde", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast",
 "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
 "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu", "dpmpp_2m_sde_heun",
 "dpmpp_2m_sde_heun_gpu", "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v",
 "deis", "res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral",
 "res_multistep_ancestral_cfg_pp", "gradient_estimation", "gradient_estimation_cfg_pp", "er_sde",
 "seeds_2", "seeds_3", "sa_solver", "sa_solver_pece", "ddim", "uni_pc", "uni_pc_bh2"]
```

`scheduler` full option list (from `comfy/samplers.py`, `SCHEDULER_NAMES =
list(SCHEDULER_HANDLERS)`), verbatim order:
```
["simple", "sgm_uniform", "karras", "exponential", "ddim_uniform", "beta", "normal",
 "linear_quadratic", "kl_optimal"]
```

### LoadImage

```
class_type: LoadImage
source: nodes.py
inputs:
  image: COMBO (required, image_upload=True) — sorted filtered file listing of folder_paths.get_input_directory()
returns: (IMAGE, MASK)
```

### VAEDecode

```
class_type: VAEDecode
source: nodes.py
inputs:
  samples: LATENT (required)
  vae: VAE (required)
returns: (IMAGE,)
```

### SaveImage

```
class_type: SaveImage
source: nodes.py
inputs:
  images: IMAGE (required)
  filename_prefix: STRING default="ComfyUI"
  (hidden: prompt=PROMPT, extra_pnginfo=EXTRA_PNGINFO — not part of API-format "inputs" you set)
returns: (IMAGE,)   # RETURN_NAMES = ("images",); OUTPUT_NODE = True
```

### CLIPTextEncode

```
class_type: CLIPTextEncode
source: nodes.py
inputs:
  text: STRING (required, multiline=True, dynamicPrompts=True)
  clip: CLIP (required)
returns: (CONDITIONING,)
```

---

## 5. Video nodes — comfy_extras/nodes_video.py

Fetch path used: `comfy_extras/nodes_video.py` — 200 OK, exists as given.

Registration style: `io.ComfyNode` / `define_schema()`. `class_type` = `node_id`.

```
class_type: CreateVideo
source: comfy_extras/nodes_video.py (io.ComfyNode, node_id="CreateVideo")
inputs:
  images: IMAGE (required)
  fps: FLOAT default=30.0 min=1.0 max=120.0 step=1.0
  audio: AUDIO (optional)
  bit_depth: INT (optional) default=8 min=8 max=10 step=2
returns: (VIDEO,)
```
`images` expects a standard IMAGE batch tensor (list-of-frames IMAGE type, same IMAGE type as
everywhere else in ComfyUI — not a special video-image type). `audio` expects the AUDIO type
(dict-like with waveform/sample_rate, as produced by ComfyUI audio loader nodes). `fps` is a
plain FLOAT, not INT.

```
class_type: SaveVideo
source: comfy_extras/nodes_video.py (io.ComfyNode, node_id="SaveVideo")
inputs:
  video: VIDEO (required)
  filename_prefix: STRING default="video/ComfyUI"
  format: COMBO default="auto" — Types.VideoContainer.as_input() = ["auto", "mp4"]
  codec: DynamicCombo (required) — top-level options ["auto", "h264"]; when "h264" is chosen,
    a nested optional "encoding" DynamicCombo appears with options ["auto", "re-encode"]; when
    "re-encode" is chosen, a nested "crf" FLOAT (default=23.0 min=0.0 max=51.0 step=1.0) appears.
    NOTE: this is ComfyUI's newer DynamicCombo input type — its on-the-wire API-format JSON
    representation is NOT a plain string like other combos; it is a nested structure
    (e.g. {"codec": "auto"} or {"codec": "h264", "encoding": {"encoding": "re-encode", "crf": 23.0}}).
    If you are hand-authoring API JSON, verify the exact wire shape against a real
    ComfyUI-exported workflow before assuming plain-string "h264" will work — do not guess.
  (hidden: prompt, extra_pnginfo)
returns: (VIDEO,)
```

```
class_type: SaveWEBM
source: comfy_extras/nodes_video.py (io.ComfyNode, node_id="SaveWEBM", is_experimental=True)
inputs:
  images: IMAGE (required)
  filename_prefix: STRING default="ComfyUI"
  codec: COMBO (required) — ["vp9", "av1"]
  fps: FLOAT default=24.0 min=0.01 max=1000.0 step=0.01
  crf: FLOAT default=32.0 min=0 max=63.0 step=1
  (hidden: prompt, extra_pnginfo)
returns: (IMAGE,)   # OUTPUT_NODE = True; display name "images"
```

Confirms: `SaveWEBM` DOES exist (marked `is_experimental=True`), separate from `SaveVideo`. It
takes raw `images` (IMAGE batch) + `fps` directly — it does NOT take a `VIDEO` object like
`SaveVideo`/`CreateVideo` do.

---

## 6. city96/ComfyUI-GGUF — nodes.py

Fetch path used: `nodes.py` (repo root of ComfyUI-GGUF, branch `main`) — 200 OK.

Registration style: old-style `NODE_CLASS_MAPPINGS` dict, explicitly at bottom of file:

```python
NODE_CLASS_MAPPINGS = {
    "UnetLoaderGGUF": UnetLoaderGGUF,
    "CLIPLoaderGGUF": CLIPLoaderGGUF,
    "DualCLIPLoaderGGUF": DualCLIPLoaderGGUF,
    "TripleCLIPLoaderGGUF": TripleCLIPLoaderGGUF,
    "QuadrupleCLIPLoaderGGUF": QuadrupleCLIPLoaderGGUF,
    "UnetLoaderGGUFAdvanced": UnetLoaderGGUFAdvanced,
}
```
All keys equal their class names exactly (no divergence).

```
class_type: UnetLoaderGGUF
source: ComfyUI-GGUF/nodes.py
inputs:
  unet_name: COMBO (required) — folder_paths.get_filename_list("unet_gguf")
returns: (MODEL,)
```

```
class_type: UnetLoaderGGUFAdvanced
source: ComfyUI-GGUF/nodes.py (subclasses UnetLoaderGGUF)
inputs:
  unet_name: COMBO (required) — folder_paths.get_filename_list("unet_gguf")
  dequant_dtype: COMBO default="default" — ["default", "target", "float32", "float16", "bfloat16"]
  patch_dtype: COMBO default="default" — ["default", "target", "float32", "float16", "bfloat16"]
  patch_on_device: BOOLEAN default=False
returns: (MODEL,)
```

```
class_type: CLIPLoaderGGUF
source: ComfyUI-GGUF/nodes.py
inputs:
  clip_name: COMBO (required) — sorted(folder_paths.get_filename_list("clip") + get_filename_list("clip_gguf"))
  type: COMBO (required) — same list as core CLIPLoader's `type` (pulled directly from
    nodes.CLIPLoader.INPUT_TYPES()["required"]["type"] at runtime — i.e. identical option list to
    the core CLIPLoader documented in section 4 above, including "qwen_image" and "wan")
returns: (CLIP,)
```

```
class_type: DualCLIPLoaderGGUF
source: ComfyUI-GGUF/nodes.py
inputs:
  clip_name1: COMBO (required) — same file list as CLIPLoaderGGUF.clip_name
  clip_name2: COMBO (required) — same file list as CLIPLoaderGGUF.clip_name
  type: COMBO (required) — pulled from nodes.DualCLIPLoader.INPUT_TYPES()["required"]["type"]
    (verbatim: ["sdxl", "sd3", "flux", "hunyuan_video", "hidream", "hunyuan_image",
    "hunyuan_video_15", "kandinsky5", "kandinsky5_image", "ltxv", "newbie", "ace"])
returns: (CLIP,)
```

Note: `NODE_CLASS_MAPPINGS` does not include a plain `TripleCLIPLoaderGGUF`/`QuadrupleCLIPLoaderGGUF`
requested key — but you only asked about `CLIPLoaderGGUF`/`DualCLIPLoaderGGUF`, both present and
documented above; the Triple/Quadruple classes exist in source too for completeness but weren't
in your request list.

### Model subfolder GGUF reads from (unet vs diffusion_models)

Traced exactly through source:
- `UnetLoaderGGUF`/`Advanced` **list** filenames from the custom key `"unet_gguf"`, which
  `update_folder_names_and_paths("unet_gguf", ["diffusion_models", "unet"])` aliases to
  whichever of `diffusion_models`/`unet` is already registered in ComfyUI (i.e. the same physical
  directories the core `UNETLoader` uses: `models/unet` and `models/diffusion_models`), filtered
  to `.gguf` files only.
- But the actual load call is `folder_paths.get_full_path("unet", unet_name)` — literal key
  `"unet"`, not `"unet_gguf"`. In core `folder_paths.py`, `"unet"` is a **legacy alias** that
  internally maps to `"diffusion_models"` (see `folder_paths.py` line 112-113:
  `legacy = {"unet": "diffusion_models", "clip": "text_encoders"}`), which resolves to the same
  `models/unet` + `models/diffusion_models` directories. Net effect: GGUF unet files should be
  placed in `models/unet` or `models/diffusion_models`, same as regular UNETLoader.
- Symmetrically, `CLIPLoaderGGUF`/`DualCLIPLoaderGGUF` list from `"clip_gguf"` (aliased to
  `text_encoders`/`clip` dirs) but load via literal `"clip"`, which is a legacy alias for
  `"text_encoders"` — resolving to `models/text_encoders` + `models/clip`.

---

## Nodes you named that do NOT exist as named, or could not be verified as named

1. **`comfy_extras/nodes_qwen_image.py`** does not exist (404). The correct/only path is
   **`comfy_extras/nodes_qwen.py`**, which is where `TextEncodeQwenImageEdit` and
   `TextEncodeQwenImageEditPlus` actually live. No substitution needed — same class names, just
   the fallback path you gave was wrong and the primary path was right.
2. Everything else you asked for (`Wan22ImageToVideoLatent`, `WanImageToVideo`,
   `TextEncodeQwenImageEdit`, `TextEncodeQwenImageEditPlus`, `ModelSamplingAuraFlow`,
   `ModelSamplingSD3`, `CLIPLoader`, `UNETLoader`, `VAELoader`, `EmptySD3LatentImage`, `KSampler`,
   `LoadImage`, `VAEDecode`, `SaveImage`, `CLIPTextEncode`, `CreateVideo`, `SaveVideo`,
   `SaveWEBM`, `UnetLoaderGGUF`, `UnetLoaderGGUFAdvanced`, `CLIPLoaderGGUF`,
   `DualCLIPLoaderGGUF`) exists exactly as named — no silent substitutions were made.
3. One thing to flag, not a missing node but a caveat for hand-authoring: `EmptySD3LatentImage`
   is NOT in `nodes.py` as you assumed — it's in `comfy_extras/nodes_sd3.py`. Its `class_type`
   string is still exactly `EmptySD3LatentImage` (the file location doesn't affect the JSON
   `class_type` value, only where the source lives), so your API JSON does not need to change,
   only your mental model of where to find the source.

---

## Bổ sung 22/08/2026 — 3 node trong template `image_qwen_image_edit_2511.json` mà bộ workflow thiếu

Trích trực tiếp từ source ComfyUI trên máy RTX 5090 (`/workspace/ComfyUI`), không phỏng đoán.
Cả ba đều nằm trên đường edit của template chính thức; thiếu chúng là nguyên nhân lỗi cháy màu
và ghép ảnh thất bại đo được ngày 22/08.

```
class_type: FluxKontextImageScale
source: comfy_extras/nodes_flux.py (io.ComfyNode, node_id="FluxKontextImageScale")
inputs:
  image: IMAGE (required)
returns: IMAGE
note: resize ảnh về độ phân giải ưu tiên gần nhất cùng tỉ lệ (lanczos, crop center).
      Template đặt TRƯỚC cả VAEEncode lẫn TextEncodeQwenImageEditPlus cho image1.
```

```
class_type: FluxKontextMultiReferenceLatentMethod
source: comfy_extras/nodes_flux.py (io.ComfyNode, node_id="FluxKontextMultiReferenceLatentMethod", display_name="Edit Model Reference Method")
inputs:
  conditioning: CONDITIONING (required)
  reference_latents_method: COMBO ["offset", "index", "uxo/uno", "index_timestep_zero"] (required, advanced=True)
returns: CONDITIONING
note: template dùng "index_timestep_zero", bọc CẢ positive LẪN negative trước KSampler.
```

```
class_type: CFGNorm
source: comfy_extras/nodes_cfg.py (io.ComfyNode, node_id="CFGNorm")
inputs:
  model: MODEL (required)
  strength: FLOAT (required, default=1.0, min=0.0, max=100.0, step=0.01)
  pre_cfg: BOOLEAN (optional, default=False)
returns: MODEL (patched_model)
note: template đặt SAU ModelSamplingAuraFlow, TRƯỚC LoraLoaderModelOnly. strength=1.0.
```
