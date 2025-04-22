🚀 Clipo AI – FFmpeg Render Engine Internship
Assignment
Assignment Title: Build a Prototype Render Engine Using FFmpeg
Duration: 3–5 days
Expected Output: Working code with demo + GitHub repo + README
🎯 Objective
Simulate Clipo AI’s backend rendering engine. Given a video, subtitles, and render
configuration (e.g. template ID, subtitle style, crop/zoom), write a Python script that
processes the input using FFmpeg and outputs a polished video ready for platforms like
Instagram Reels.
📥 Input Format
Your script should accept the following inputs (via function arguments or a local JSON file):
json
{
"video_url": "https://example.com/video.mp4"
,
"subtitle_url": "https://example.com/subtitles.srt"
"render_config": {
"template_id": "template_1"
,
"subtitle_style": "bold_white_box"
,
"crop_mode": "center_crop"
,
"zoom_effect": true,
"output_format": "mp4"
,
}
}
📦 Expected Functionality
✅ 1. Download Video & Subtitle
●
Use Python (requests or aiohttp) to download video and subtitle files from
provided URLs.
●
Save them to a local working directory.
✅ 2. Template Application
●
Implement at least two hardcoded templates:
○
template_1: Add branding bar (image or solid color) + top overlay text
○
template_2: Add border + small watermark (Clipo logo or dummy image)
Use FFmpeg’s overlay/drawtext filter as needed.
✅ 3. Subtitle Styling
●
Parse .srt file.
●
●
Apply chosen style (e.g. white text with background, yellow bold, etc.)
Burn subtitles into video using FFmpeg.
✅ 4. Crop & Zoom
●
●
If "crop_mode" is "center_crop":
○
Convert landscape video to vertical (9:16) by center cropping
If "zoom_effect": true, apply slow zoom-in across duration
✅ 5. Render Final Output
●
Combine all steps into a single render using FFmpeg.
Output must be in .mp4 (or as per config) and saved locally as:
/outputs/final_render.mp4
✅ Bonus Features (Optional but Valued)
●
●
●
Add intro_clip_url and outro_clip_url support (prepend and append)
Generate a preview thumbnail (frame at 5s)
Log FFmpeg commands and render time
📂 Submission Guidelines
1. Share a GitHub repo with:
○
○
○
○
render_engine.py (main script)
Sample input (JSON) file
Downloaded samples + Output video
README.md that explains:
■ Assumptions made
■ Template logic
■ FFmpeg command examples used
2. Make sure the repo is clean and easy to run for reviewers
🏁 Evaluation Criteria
Area Description
✅ FFmpeg
Usage
Filters, subtitle burning, cropping, transitions
✅ Modularity Clear structure and reusable functions
✅ Realism Does it resemble a Clipo-style use case?
✅ Output Quality Clean video with styling, subtitles, effects
✅
Clear steps and code explanation in README
Documentation