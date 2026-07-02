# OffSec Terminal Forge - Codebase Architecture Document (Updated)

## 1. Tracked Files and Their Specific Roles

Based on the latest codebase analysis (264 nodes, 485 edges), here are all tracked files and their inferred roles:

### Core Engine Modules (`engines/` directory)
- `engines/_fonts.py`: Font loading utility. Provides `load_fonts()` (or `_load_fonts` in dialogue generator) used by alien_generator and dialogue_generator for text rendering.
- `engines/ai_engine.py`: AI-related functionality (likely prompt handling, model interaction). Contains `main()` entry point.
- `engines/alien_generator.py`: Procedural alien world generation. Creates fractal noise maps and alien world images for OffSec visual assets.
- `engines/core_engine.py`: Base earth map processing and cyberpunk glitch effects application. Handles image transformation for map generation (RGB shift, scanlines, pixel sorting).
- `engines/dialogue_generator.py`: Dialogue and terminal output rendering. Generates visual dialogue assets from script data (chat bubbles, avatars, captcha frames).
- `engines/orchestrator.py`: Workflow coordination. Contains `main()` entry point and functions to run other engines (`run_ai_engine`, `run_dialogue_generator`). Notably, it does **not** directly call core_engine or alien_generator in the current call graph.

### Asset Directory
- `assets/`: Contains static resources including base map images (`map.png`), captcha-related assets, and font files.
- `assets/extract_captcha.py`: Utility for CAPTCHA image processing (likely used by dialogue generator for captcha frames).

### Configuration and Scripts
- `.github/workflows/*.yml`: GitHub Actions CI/CD workflows for various project components (AI Engine, Alien Maps, Core Engine, Orchestrator, etc.).
- `auto_sync.sh` / `resync.sh`: Synchronization scripts for asset management (likely pulling/pushing assets to/from storage).
- `requirements.txt`: Python package dependencies (Pillow for image processing, requests for HTTP calls).
- `Develop.md`, `README.md`, `WORKFLOW_DEBUGGING.md`: Documentation files.
- `set_github_secret.py`: Utility for managing GitHub repository secrets (encryption/decryption).
- `PROJECT_MEMORY.md`: This document – the codebase memory graph.

## 2. Function Call Chains

### 2.1 alien_generator.py
**Primary Purpose**: Generate procedural alien worlds and fractal noise maps for OffSec visual assets.

**Key Functions**:
- `generate_fractal_noise_map(width: int, height: int, seed: int) -> Image.Image`
  - Creates base fractal noise terrain using midpoint displacement or similar algorithm.
  - **Output**: PIL Image object (RGBA) used as foundation for alien worlds.
  - **Dependencies**: None (pure mathematical generation).
  
- `generate_alien_world(width: int = 1200, height: int = 800, save_to_disk: bool = True) -> None`
  - Main world generation function.
  - **Internal Calls**:
    - `generate_fractal_noise_map` (to create base terrain)
    - `_fonts.load_fonts` (via `_fonts` module) for text labeling of planets/features.
  - **Output**: Saves generated alien world image to disk (typically under `output/`).
  
- `generate_multiple_worlds(count: int = 1) -> list`
  - Batch generation wrapper.
  - **Internal Calls**: Repeatedly calls `generate_alien_world`.
  - **Output**: List of generated image file paths.

**Call Chain Summary**:
```
generate_multiple_worlds → generate_alien_world → [generate_fractal_noise_map, _fonts.load_fonts] → [PIL Image operations] → Saved Alien World Images
```

### 2.2 dialogue_generator.py
**Primary Purpose**: Render dialogue scripts as visual terminal-style images for OffSec assets (chat UI, avatars, speech bubbles, captcha frames).

**Key Functions** (selected for brevity; full list in graph):
- `_load_fonts() -> dict`
  - Loads multiple font sizes/styles for UI rendering.
  - **Output**: Dictionary mapping font names to `ImageFont.FreeTypeFont` objects.
  
- `_text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]`
  - Calculates width/height of rendered text.
  - **Input**: Drawing context, text string, font object.
  - **Output**: Tuple (width, height) in pixels.
  
- `_apply_scanlines(image: Image.Image) -> Image.Image`
  - Overlays horizontal scanline effect for retro monitor feel.
  - **Input**: PIL Image.
  - **Output**: Image with scanline overlay.
  
- `_draw_avatar(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, name: str, font) -> None`
  - Draws circular avatar with user's initials and color-coded background.
  - **Internal Calls**: `_color_for_name`, `_initials`, `_text_size`.
  
- `_draw_bubble(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, align: str, fonts: dict, user_name: str, decal: str) -> None`
  - Renders speech bubble with text, optionally attaching to an avatar.
  - **Internal Calls**: `_text_size`, `_draw_avatar`.
  
- `_build_chat_frame(visible: List[Dict], fonts: dict, width: int, height: int) -> Image.Image`
  - Assembles a full chat frame from multiple dialogue elements.
  - **Internal Calls**: `_draw_bubble` (repeated per message).
  - **Output**: Composite PIL Image of the chat UI.
  
- `_build_captcha_frame(fonts: dict, width: int, height: int) -> Image.Image`
  - Generates a CAPTCHA-like challenge image.
  - **Internal Calls**: `_apply_scanlines` (for distortion).
  - **Output**: CAPTCHA PIL Image.
  
- `generate_dialogue_from_script() -> None`
  - Main processing pipeline: loads script data, builds frames, saves images.
  - **Internal Calls**: `_load_background_map`, `_load_script`, `_load_fonts`, `_build_chat_frame`/`_build_captcha_frame`, `generate_alien_world` (for background), `_apply_scanlines`.
  - **Output**: Saved dialogue frames (PNG) in `output/dialogue/`.
  
- `main() -> None`
  - Entry point for dialogue generation workflow.
  - **Internal Calls**: `_load_background_map`, `_load_script`, `generate_dialogue_from_script`.
  
**Call Chain Summary** (high‑level):
```
main → _load_background_map → [_load_script, _load_fonts] 
      → generate_dialogue_from_script → [_build_chat_frame/_build_captcha_frame] 
          → [_draw_bubble → [_draw_avatar, _text_size, _color_for_name, _initials], _apply_scanlines] 
          → [PIL ImageDraw, alien_generator.generate_alien_world (for background)] 
          → Saved Dialogue Images
```

### 2.3 core_engine.py
**Primary Purpose**: Apply cyberpunk/offsec glitch effects to base earth map images (e.g., for alien world maps or UI backgrounds).

**Key Functions**:
- `load_base_image(image_path: str) -> Image.Image`
  - Loads image from disk and converts to RGBA.
  - **Input**: File path (defaults to `"assets/map.png"`).
  - **Output**: PIL Image object in RGBA mode.
  
- `apply_rgb_shift(image: Image.Image, shift: int = 10) -> Image.Image`
  - Creates RGB channel displacement glitch (red left, right shift; blue opposite).
  - **Input**: PIL Image, shift amount (default 10px).
  - **Output**: Image with shifted red/blue channels (green unchanged).
  
- `apply_scanlines(image: Image.Image, line_spacing: int = 4, line_brightness: float = 0.2) -> Image.Image`
  - Overlays monitor scanline effect.
  - **Input**: PIL Image, line spacing (px), brightness (0.0‑1.0).
  - **Output**: Image with semi‑transparent black horizontal lines.
  
- `apply_pixel_sort(image: Image.Image, mask_threshold: int = 128, sort_by: str = "hue") -> Image.Image`
  - Sorts pixels in each row by hue/saturation/value (or lightness) for a “datamosh” glitch.
  - **Input**: PIL Image, brightness threshold (0‑255), sort method.
  - **Output**: Image with rows of pixels sorted (creates directional streaks).
  
- `apply_glitch_effects(image: Image.Image) -> Image.Image`
  - Combines all three glitch effects in sequence with randomised parameters.
  - **Internal Calls**:
    - `apply_rgb_shift` (shift random 5‑15px)
    - `apply_scanlines` (spacing random 3‑6, brightness random 0.1‑0.4)
    - `apply_pixel_sort` (threshold random 100‑200, method random choice of hue/saturation/value)
  - **Output**: Fully glitched PIL Image.
  
- `main() -> None`
  - Entry point for map processing workflow.
  - **Internal Calls**:
    - `load_base_image("assets/map.png")`
    - `apply_glitch_effects()` on a copy of the base image.
    - Saves result to `"output/maps/glitched_map.png"` (creates directory if needed).
  - **Output**: Glitched map image file; console log confirming save location.

**Call Chain Summary**:
```
main → load_base_image → apply_glitch_effects → 
       [apply_rgb_shift, apply_scanlines, apply_pixel_sort] → 
       Glitched Map Image (saved to output/maps/glitched_map.png)
```

## 3. Dependencies, Inputs, and Outputs

### 3.1 Module Dependencies
- **Pillow (PIL)**: Core image processing library used across:
  - `_fonts.py`: Text rendering and font loading.
  - `alien_generator.py`: Image creation (fractal noise, alien world drawing).
  - `dialogue_generator.py`: All UI drawing (chat bubbles, avatars, captcha, scanlines).
  - `core_engine.py`: All glitch effect implementations (RGB shift, scanlines, pixel sort).
  
- **Requests**: Detected in the graph but not directly used in the three focal modules. Likely employed in:
  - `ai_engine.py`: For API calls to LLMs or external services.
  - `orchestrator.py`: For webhook notifications or remote task triggering.

### 3.2 Inputs and Outputs by Module

#### alien_generator.py
- **Inputs**:
  - Integer parameters: width, height, seed, count.
  - Boolean flag: `save_to_disk`.
  - Font resources (via `_fonts.load_fonts`).
- **Outputs**:
  - PIL Image objects (fractal noise, alien world composites).
  - Saved image files (PNG) in output directories (e.g., `output/alien_worlds/`).
  - Lists of file paths (for batch operations).

#### dialogue_generator.py
- **Inputs**:
  - Script data dictionaries (dialogue lines, speaker names, decals).
  - Background map (optionally generated by `alien_generator.generate_alien_world`).
  - Font resources (via `_fonts.load_fonts`).
  - Text strings, layout parameters (width, height, alignment).
- **Outputs**:
  - Formatted text strings (wrapped lines) – internal.
  - Rendered dialogue frames (PNG) – saved to `output/dialogue/`.
  - Lists of generated image file paths.
  - Intermediate PIL Images (charts, avatars, bubbles) used in composition.

#### core_engine.py
- **Inputs**:
  - Base earth map image (`assets/map.png` – default, but configurable via argument).
  - Glitch effect parameters (randomised internally; could be made configurable).
- **Outputs**:
  - Processed PIL Image objects after each effect stage (internal).
  - Final glitched map image saved to `output/maps/glitched_map.png`.
  - Console output confirming the save location.

### 3.3 Data Flow Summary (Updated)
1. **alien_generator.py** creates base visual assets (fractal noise → alien worlds) using procedural algorithms; may optionally feed generated worlds into dialogue_generator as backgrounds.
2. **dialogue_generator.py** assembles chat/UI components (avatars, bubbles, captcha) using fonts and optional alien backgrounds, applying scanlines for retro feel; outputs final dialogue frames.
3. **core_engine.py** takes a base map (e.g., `assets/map.png`) and applies cyberpunk glitch effects (RGB shift, scanlines, pixel sorting) to produce stylised map images for use in assets or UI.
4. **Shared Resource**: Both alien_generator and dialogue_generator depend on `_fonts.py` for text rendering; dialogue_generator may also call alien_generator for background generation.
5. **Output Destination**: All generated assets are saved under appropriate subdirectories of `output/` (e.g., `output/maps/`, `output/dialogue/`, `output/alien_worlds/`), ready for use in workflows or downstream processes.

## 4. Architectural Notes
- The three focal modules (`alien_generator`, `dialogue_generator`, `core_engine`) form the core asset generation pipeline, each with a distinct visual focus (procedural worlds, UI/dialogue, glitched maps).
- Entry points exist in `ai_engine`, `core_engine`, `dialogue_generator`, and `orchestrator` for standalone execution.
- No direct call chains were observed among the three focal modules in the current graph (they operate independently, sharing only the `_fonts` utility). However, `dialogue_generator` **does** invoke `alien_generator.generate_alien_world` to obtain background imagery, creating an indirect link.
- The orchestrator currently coordinates `ai_engine` and `dialogue_generator` but does **not** invoke `core_engine` or `alien_generator`; those are likely called directly via their own `main()` functions or via workflow triggers.
- All image manipulation is heavily reliant on the Pillow library, confirming the project’s focus on procedural and post‑processed visual assets for the OffSec Terminal Forge aesthetic.

---
*Document generated from the live codebase memory graph (264 nodes, 485 edges) using the codebase‑memory MCP tools. Reflects the state after the recent implementation of `engines/core_engine.py` and its integration.*