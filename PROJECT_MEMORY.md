# OffSec Terminal Forge - Codebase Architecture Document

## 1. Tracked Files and Their Specific Roles

Based on the codebase analysis, here are all tracked files and their inferred roles:

### Core Engine Modules (`engines/` directory)
- `engines/_fonts.py`: Font loading utility. Provides `load_fonts()` function used by alien_generator and dialogue_generator for text rendering.
- `engines/ai_engine.py`: AI-related functionality (specifics not detailed in graph). Contains `main()` entry point.
- `engines/alien_generator.py`: Procedural alien world generation. Creates fractal noise maps and alien world images for OffSec visual assets.
- `engines/core_engine.py`: Base earth map processing and cyberpunk glitch effects application. Handles image transformation for map generation.
- `engines/dialogue_generator.py`: Dialogue and terminal output rendering. Generates visual dialogue assets from script data.
- `engines/orchestrator.py`: Workflow coordination. Contains `main()` entry point and functions to run other engines (`run_ai_engine`, `run_dialogue_generator`).

### Asset Directory
- `assets/`: Contains static resources including base map images (`map.png`), captcha-related assets, and font files.
- `assets/extract_captcha.py`: Utility for CAPTCHA image processing.

### Configuration and Scripts
- `.github/workflows/*.yml`: GitHub Actions CI/CD workflows for various project components.
- `auto_sync.sh` / `resync.sh`: Synchronization scripts for asset management.
- `requirements.txt`: Python package dependencies (Pillow, requests).
- `Develop.md`, `README.md`, `WORKFLOW_DEBUGGING.md`: Documentation files.
- `set_github_secret.py`: Utility for managing GitHub repository secrets.

## 2. Function Call Chains

### 2.1 alien_generator.py
**Primary Purpose**: Generate procedural alien worlds and fractal noise maps for OffSec visual assets.

**Key Functions**:
- `generate_fractal_noise_map(width: int, height: int, seed: int) -> Image.Image`
  - Creates base fractal noise terrain
  - **Output**: PIL Image object used as foundation for alien worlds
  - **Dependencies**: None (pure mathematical generation)
  
- `generate_alien_world(width: int = 1200, height: int = 800, save_to_disk: bool = True) -> None`
  - Main world generation function
  - **Internal Calls**: 
    - `_fonts.load_fonts()` (for text labeling)
    - Likely uses `generate_fractal_noise_map` internally
  - **Output**: Saves generated alien world image to disk
  
- `generate_multiple_worlds(count: int = 1) -> list`
  - Batch generation wrapper
  - **Internal Calls**: Repeatedly calls `generate_alien_world`
  - **Output**: List of generated image paths

**Call Chain Summary**:
```
generate_multiple_worlds → generate_alien_world → [_fonts.load_fonts, generate_fractal_noise_map] → [PIL Image operations]
```

### 2.2 dialogue_generator.py
**Primary Purpose**: Render dialogue scripts as visual terminal-style images for OffSec assets.

**Key Functions**:
- `_extract_timestamp_from_filename(filename: str) -> str`
  - Parses timestamps from filenames for organizing dialogue assets
  - **Input**: Filename string
  - **Output**: Extracted timestamp string
  
- `_wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]`
  - Text wrapping for dialogue rendering
  - **Input**: Text, font object, maximum width
  - **Output**: List of wrapped text lines
  
- `_render_dialogue_image(script_data: Dict, output_path: str) -> None`
  - Core image rendering function
  - **Internal Calls**:
    - `_fonts.load_fonts()` (for terminal font)
    - `_wrap_text()` (for text layout)
    - PIL ImageDraw operations for terminal UI elements
  - **Output**: Saves rendered dialogue image to specified path
  
- `render_dialogues() -> List[str]`
  - Processes multiple dialogue scripts
  - **Internal Calls**: Repeatedly calls `_render_dialogue_image`
  - **Output**: List of generated dialogue image paths
  
- `main() -> None`
  - Entry point for dialogue generation workflow
  - **Internal Calls**: Likely calls `render_dialogues()`

**Call Chain Summary**:
```
main → render_dialogues → [_render_dialogue_image repeated] → [_fonts.load_fonts, _wrap_text, PIL ImageDraw] → [Dialogue Images]
```

### 2.3 core_engine.py
**Primary Purpose**: Apply cyberpunk/offsec glitch effects to base earth map images.

**Key Functions**:
- `load_base_image(image_path: str) -> Image.Image`
  - Loads and converts base map to RGBA
  - **Input**: File path to base earth map
  - **Output**: PIL Image object in RGBA format
  
- `apply_rgb_shift(image: Image.Image, shift: int = 10) -> Image.Image`
  - Creates RGB channel displacement glitch
  - **Input**: PIL Image, shift amount
  - **Output**: Image with shifted red/blue channels
  
- `apply_scanlines(image: Image.Image, line_spacing: int = 4, line_brightness: float = 0.2) -> Image.Image`
  - Overlays monitor scanline effect
  - **Input**: PIL Image, line spacing, brightness
  - **Output**: Image with scanline overlay
  
- `apply_pixel_sort(image: Image.Image, mask_threshold: int = 128, sort_by: str = 'hue') -> Image.Image`
  - Sorts pixels by hue/saturation/value for datamosh effect
  - **Input**: PIL Image, threshold, sort method
  - **Output**: Image with sorted pixel rows
  
- `apply_glitch_effects(image: Image.Image) -> Image.Image`
  - Combines all glitch effects in sequence
  - **Internal Calls**:
    - `apply_rgb_shift()` (random shift 5-15px)
    - `apply_scanlines()` (random spacing 3-6, brightness 0.1-0.4)
    - `apply_pixel_sort()` (random threshold 100-200, random sort method)
  - **Output**: Fully glitched PIL Image
  
- `main() -> None`
  - Entry point for map processing workflow
  - **Internal Calls**:
    - `load_base_image("assets/map.png")`
    - `apply_glitch_effects()` on copied image
    - Saves result to `output/maps/glitched_map.png`
  - **Output**: Glitched map image saved to output directory

**Call Chain Summary**:
```
main → load_base_image → apply_glitch_effects → [apply_rgb_shift, apply_scanlines, apply_pixel_sort] → [Glitched Map Image]
```

## 3. Dependencies, Inputs, and Outputs

### 3.1 Module Dependencies
- **Pillow (PIL)**: Used across all image-processing modules:
  - `_fonts.py`: For font loading and text rendering
  - `alien_generator.py`: For image creation and manipulation
  - `dialogue_generator.py`: For dialogue image rendering
  - `core_engine.py**: For all glitch effect applications
  
- **Requests**: Detected in graph but not directly used in the three focal modules. Likely used in:
  - `ai_engine.py`: For API interactions
  - `orchestrator.py`: For webhook or external service communication

### 3.2 Inputs and Outputs by Module

#### alien_generator.py
- **Inputs**: 
  - Integer parameters (width, height, seed, count)
  - Boolean flags (save_to_disk)
  - Font resources (via _fonts)
- **Outputs**:
  - PIL Image objects (fractal noise, alien worlds)
  - Saved image files in output directories
  - Lists of file paths (for batch operations)

#### dialogue_generator.py
- **Inputs**:
  - Script data dictionaries (dialogue content)
  - Filename strings (for timestamp extraction)
  - Font resources (via _fonts)
  - Text strings and layout parameters
- **Outputs**:
  - List of formatted text strings (_wrap_text)
  - Rendered dialogue images (PNG format)
  - Lists of output file paths
  - Generated dialogue asset collections

#### core_engine.py
- **Inputs**:
  - Base earth map image (`assets/map.png`)
  - Glitch effect parameters (randomized within ranges)
- **Outputs**:
  - Processed PIL Image objects at each effect stage
  - Final glitched map image saved to `output/maps/glitched_map.png`
  - Console output confirming save location

### 3.3 Data Flow Summary
1. **alien_generator.py** generates base visual assets (aliens, terrains) using procedural algorithms
2. **dialogue_generator.py** creates narrative assets by rendering text as terminal-style visuals
3. **core_engine.py** post-processes base maps with cyberpunk glitch effects for OffSec aesthetic
4. **Shared Resource**: Both alien_generator and dialogue_generator depend on `_fonts.py` for text rendering
5. **Output Destination**: All generated assets saved to appropriate output directories for use in workflows

## Architectural Notes
- The three focal modules (_fonts, alien_generator, dialogue_generator, core_engine) form the core asset generation pipeline
- Entry points exist in ai_engine, core_engine, dialogue_generator, and orchestrator for standalone execution
- No direct call chains observed between the three focal modules in the current architecture graph
- Orchestrator appears to coordinate ai_engine and dialogue_generator but not core_engine (based on available boundary data)
- All image processing is heavily dependent on the Pillow library for image creation and manipulation