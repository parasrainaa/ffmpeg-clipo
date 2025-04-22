# Clipo AI - FFmpeg Render Engine Assignment

Prototype render engine using Python and FFmpeg.

## Setup

1.  **Install FFmpeg:** Ensure `ffmpeg` and `ffprobe` are installed and available in your system's PATH.
2.  **Install Python:** A recent version of Python 3 is required.
3.  **Install Dependencies:** Use `uv` for package management.
    ```bash
    # Install uv (see https://github.com/astral-sh/uv)
    # Example: pip install uv

    # Install project dependencies (this creates .venv and installs requests)
    uv sync
    ```

## Usage

```bash
python render_engine.py input.json
```

This script processes a video based on parameters defined in the input JSON file. It downloads the necessary video and subtitle files, applies specified transformations and templates using FFmpeg, and saves the result to the `outputs` directory.

## Assumptions

The script operates under the following assumptions:

*   **Environment:** `ffmpeg` and `ffprobe` are installed and accessible via the system's PATH (as per Setup). Python 3 and the `requests` library are installed.
*   **Input JSON:** A valid JSON file path is provided as a command-line argument. This file must contain `video_url`, `subtitle_url`, and `render_config` keys with appropriate values.
*   **Network:** Internet access is required to download files specified by `video_url` and `subtitle_url`.
*   **File System:** The script needs permissions to create `downloads/` and `outputs/` directories (if they don't exist) and write files within them. The `assets/` directory should exist if using templates that require specific image assets (e.g., `brand_bar.png`, `watermark_logo.png`). The script attempts to handle missing asset files gracefully (e.g., by drawing a colored box instead of an image overlay).
*   **Media:** Input video files are expected to contain standard video and audio streams. Subtitle files are expected to be in valid `.srt` format.

## Template Logic

The rendering process applies filters sequentially based on the `render_config` using FFmpeg's `-filter_complex`.

*   **`crop_mode: "center_crop"`:**
    *   Applies only if the input video is wider than tall.
    *   Calculates the width required for a 9:16 aspect ratio based on the video's height.
    *   Uses the `crop` filter to extract the central vertical slice: `crop=w={target_width}:h={input_height}:x={offset_x}:y=0`.
*   **`zoom_effect: true`:**
    *   Applies a slow, continuous zoom-in effect.
    *   Uses the `scale` filter with time-based expressions (`scale=w='iw*pow(1+0.05,t)':h='ih*pow(1+0.05,t)':eval=frame`) combined with `crop=iw:ih` to maintain dimensions while zooming into the center.
*   **`template_id: "template_1"`:**
    *   **Branding Bar:** Overlays `assets/brand_bar.png` at the bottom (`overlay=x=0:y=ih-overlay_h`). If missing, draws a 50px high semi-transparent blue bar (`drawbox=...:color=blue@0.7:...`).
    *   **Top Text:** Adds "Your Brand Here" near the top center with a white font and semi-transparent black background box (`drawtext=text='Your Brand Here':...`).
*   **`template_id: "template_2"`:**
    *   **Border:** Draws a 5px thick white border inset by 10px (`drawbox=x=10:y=10:w=iw-20:h=ih-20:color=white:t=5`).
    *   **Watermark:** Overlays `assets/watermark_logo.png` in the bottom-right corner (`overlay=x=iw-overlay_w-10:y=ih-overlay_h-10`). Skipped if the image is missing.
*   **`subtitle_style`:**
    *   Burns subtitles using the `subtitles` filter and `force_style`.
    *   `"bold_white_box"`: White bold text, semi-transparent black background box. (`force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF&,Bold=1,BorderStyle=3,OutlineColour=&H80000000&,BackColour=&H80000000&,MarginV=15'`)
    *   `"yellow_bold"`: Yellow bold text with a standard outline. (`force_style='FontName=Arial,FontSize=24,PrimaryColour=&H0000FFFF&,Bold=1,BorderStyle=1,Outline=1,MarginV=15'`)

## FFmpeg Command Example

The script constructs and executes an FFmpeg command based on the input configuration. For a configuration using `center_crop`, `zoom_effect`, `template_1` (with `brand_bar.png` present), and `bold_white_box` subtitles, the generated command might look similar to this:

```bash
# Note: Line breaks added for readability
ffmpeg -i downloads/video.mp4 -i assets/brand_bar.png \\
-filter_complex "[0:v]crop=w=WIDTH:h=HEIGHT:x=X_OFFSET:y=0[cropped];\
[cropped]scale=w='iw*pow(1+0.05,t)':h='ih*pow(1+0.05,t)':eval=frame,crop=iw:ih[zoomed];\
[zoomed][1:v]overlay=x=0:y=ih-overlay_h[bar_applied];\
[bar_applied]drawtext=text='Your Brand Here':x=(w-text_w)/2:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5[templated];\
[templated]subtitles=filename='downloads/subtitles.srt':force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF&,Bold=1,BorderStyle=3,OutlineColour=&H80000000&,BackColour=&H80000000&,MarginV=15'[subtitled]" \\
-map "[subtitled]" -map "0:a?" \\
-c:v libx264 -pix_fmt yuv420p -preset medium -crf 23 \\
-c:a aac -b:a 128k \\
-y outputs/final_render.mp4
```
*(Note: `WIDTH`, `HEIGHT`, and `X_OFFSET` in the `crop` filter are calculated based on the input video dimensions. The subtitle filename path might be escaped differently depending on the OS.)*
