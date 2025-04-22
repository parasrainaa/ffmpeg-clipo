import os
import json
import subprocess
import time
import logging
import argparse
import requests 
import sys 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOADS_DIR = "downloads"
OUTPUTS_DIR = "outputs"
ASSETS_DIR = "assets"

def parse_config(config_path):
    """Parses the input JSON configuration file."""
    logging.info(f"Parsing config file: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logging.info("Config parsed successfully.")
        if 'video_url' not in config or 'subtitle_url' not in config or 'render_config' not in config:
            logging.error("Config file missing required keys (video_url, subtitle_url, render_config).")
            return None
        return config
    except FileNotFoundError:
        logging.error(f"Config file not found at: {config_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from config file: {config_path}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while parsing config: {e}")
        return None

def download_file(url, destination_path):
    """Downloads a file from a URL to a local path."""
    logging.info(f"Attempting to download {url} to {destination_path}")
    try:
        response = requests.get(url, stream=True, timeout=30) # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded {url} to {destination_path}")
        return True
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while downloading {url}")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {url}: {e}")
        return False
    except OSError as e:
        logging.error(f"Error writing file to {destination_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during download: {e}")
        return False

def get_video_info(video_path):
    """Gets video properties (width, height, duration) using ffprobe."""
    logging.info(f"Getting video info for: {video_path}")
    if not os.path.exists(video_path):
        logging.error(f"Video file not found at: {video_path}")
        return None

    command = [
        'ffprobe', 
        '-v', 'error', 
        '-select_streams', 'v:0', 
        '-show_entries', 'stream=width,height,duration', 
        '-of', 'json', 
        video_path
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        try:
            data = json.loads(result.stdout)
            
            if not data.get('streams') or not data['streams'][0]:
                logging.error("ffprobe output missing 'streams' data.")
                return None
                
            stream_info = data['streams'][0]
            width = stream_info.get('width')
            height = stream_info.get('height')
            duration_str = stream_info.get('duration')
            
            if width is None or height is None or duration_str is None:
                logging.error("ffprobe output missing width, height, or duration.")
                return None

            duration = float(duration_str)
            
            info = {'width': width, 'height': height, 'duration': duration}
            logging.info(f"Video info retrieved: {info}")
            return info
            
        except json.JSONDecodeError:
            logging.error(f"Failed to decode ffprobe JSON output: {result.stdout}")
            return None
        except (KeyError, IndexError, ValueError) as e:
             logging.error(f"Error parsing ffprobe output structure: {e}. Output: {result.stdout}")
             return None
             
    except FileNotFoundError:
        logging.error("ffprobe command not found. Please ensure FFmpeg is installed and in your PATH.")
        return None
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe failed with error code {e.returncode}. Stderr: {e.stderr}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while running ffprobe: {e}")
        return None

def build_ffmpeg_command(config, video_info, input_video_path, input_srt_path):
    """Builds the complex FFmpeg command arguments as a list."""
    logging.info("Building FFmpeg command...")
    
    input_width = video_info['width']
    input_height = video_info['height']
    duration = video_info['duration']

    base_cmd = ['ffmpeg']
    inputs_args = ['-i', input_video_path] 
    filter_complex_parts = []
    maps_args = []
    output_options_args = []
    output_path = os.path.join(OUTPUTS_DIR, f"final_render.{config.get('output_format', 'mp4')}")
    
    current_v_stream = "[0:v]" 
    current_a_stream = "[0:a]" 
    next_input_idx = 1 

    
    if config.get('crop_mode') == 'center_crop' and input_width > input_height:
        logging.info("Applying center crop to 9:16")
        target_aspect_ratio = 9/16
        target_width = int(input_height * target_aspect_ratio)
        offset_x = int((input_width - target_width) / 2)
        crop_filter = f"{current_v_stream}crop=w={target_width}:h={input_height}:x={offset_x}:y=0[cropped]"
        filter_complex_parts.append(crop_filter)
        current_v_stream = "[cropped]"
    elif config.get('crop_mode'):
        logging.warning(f"Unsupported crop_mode: {config['crop_mode']}. Skipping crop.")

    # 2. Zoom (if specified)
    if config.get('zoom_effect'):
        logging.info("Applying slow zoom effect")
        zoom_rate = 0.05 
        # FIX: Added :eval=frame t
        # o allow using 't'
        zoom_filter = f"{current_v_stream}scale=w='iw*pow(1+{zoom_rate},t)':h='ih*pow(1+{zoom_rate},t)':eval=frame,crop=iw:ih[zoomed]"
        filter_complex_parts.append(zoom_filter)
        current_v_stream = "[zoomed]"

    # 3. Template Application
    template_id = config.get('template_id')
    if template_id:
        logging.info(f"Applying template: {template_id}")
        if template_id == 'template_1': 
            brand_asset = os.path.join(ASSETS_DIR, "brand_bar.png")
            if os.path.exists(brand_asset):
                inputs_args.extend(['-i', brand_asset]) 
                brand_stream = f"[{next_input_idx}:v]"
                next_input_idx += 1
                filter_complex_parts.append(f"{current_v_stream}{brand_stream}overlay=x=0:y=ih-overlay_h[bar_applied]") # Position using overlay_h
                current_v_stream = "[bar_applied]"
            else:
                logging.warning(f"Brand asset not found at {brand_asset}, applying color bar instead.")
                filter_complex_parts.append(f"{current_v_stream}drawbox=x=0:y=ih-50:w=iw:h=50:color=blue@0.7:t=fill[bar_applied]")
                current_v_stream = "[bar_applied]"
            
            filter_complex_parts.append(f"{current_v_stream}drawtext=text='Your Brand Here':x=(w-text_w)/2:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5[templated]")
            current_v_stream = "[templated]"

        elif template_id == 'template_2': 
            filter_complex_parts.append(f"{current_v_stream}drawbox=x=10:y=10:w=iw-20:h=ih-20:color=white:t=5[bordered]")
            current_v_stream = "[bordered]"
            
            watermark_asset = os.path.join(ASSETS_DIR, "watermark_logo.png")
            if os.path.exists(watermark_asset):
                inputs_args.extend(['-i', watermark_asset]) 
                watermark_stream = f"[{next_input_idx}:v]"
                next_input_idx += 1
                filter_complex_parts.append(f"{current_v_stream}{watermark_stream}overlay=x=iw-overlay_w-10:y=ih-overlay_h-10[templated]") 
                current_v_stream = "[templated]"
            else:
                 logging.warning(f"Watermark asset not found at {watermark_asset}, skipping watermark.")
                 filter_complex_parts.append(f"{current_v_stream}null[templated]")
                 current_v_stream = "[templated]"
        else:
            logging.warning(f"Unsupported template_id: {template_id}. Skipping template.")

    subtitle_style = config.get('subtitle_style')
    if subtitle_style:
        logging.info(f"Applying subtitle style: {subtitle_style}")
        style_map = {
            "bold_white_box": "FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF&,Bold=1,BorderStyle=3,OutlineColour=&H80000000&,BackColour=&H80000000&,MarginV=15",
            "yellow_bold": "FontName=Arial,FontSize=24,PrimaryColour=&H0000FFFF&,Bold=1,BorderStyle=1,Outline=1,MarginV=15",
        }
        force_style = style_map.get(subtitle_style)
        if force_style:
            subtitle_filter = f"{current_v_stream}subtitles=filename='{input_srt_path.replace('\\\\', '/').replace(':', '\\\\:')}':force_style='{force_style}'[subtitled]"
            filter_complex_parts.append(subtitle_filter)
            current_v_stream = "[subtitled]"
        else:
            logging.warning(f"Unsupported subtitle_style: {subtitle_style}. Skipping subtitles.")
            
    final_cmd = base_cmd + inputs_args 
    
    if filter_complex_parts:
        filter_complex_str = ";".join(filter_complex_parts)
        final_cmd.extend(['-filter_complex', filter_complex_str])
        final_v_stream = current_v_stream
        final_a_stream = "0:a?" 
    else:
        final_v_stream = "[0:v]"
        final_a_stream = "[0:a]"

    maps_args.extend(['-map', final_v_stream])
    maps_args.extend(['-map', final_a_stream])
    
    output_options_args.extend([
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_path
    ])

    full_command = final_cmd + maps_args + output_options_args 
    logging.info(f"Constructed FFmpeg command: {' '.join(full_command)}")
    return full_command

def run_command(cmd_list):
    """Runs a command using subprocess and logs output."""
    command_str = ' '.join(cmd_list)
    logging.info(f"Running FFmpeg command... (See full command log below)")
    logging.debug(f"Executing FFmpeg command: {command_str}") 

    try:
        # Run the command, capture output, check for errors
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False) # check=False to handle error manually

        if result.stdout:
            logging.debug(f"FFmpeg stdout:\n{result.stdout}")
        if result.stderr:
            # stderr often contains progress and info, log as debug unless error
            log_level = logging.ERROR if result.returncode != 0 else logging.DEBUG
            logging.log(log_level, f"FFmpeg stderr:\n{result.stderr}")

        if result.returncode != 0:
            logging.error(f"FFmpeg command failed with exit code {result.returncode}.")
            return False
        
        logging.info("FFmpeg command executed successfully.")
        return True

    except FileNotFoundError:
        logging.error("ffmpeg command not found. Please ensure FFmpeg is installed and in your PATH.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while running FFmpeg command: {e}")
        return False

def generate_thumbnail(video_path, thumb_path, timestamp="5"):
    """Generates a thumbnail from the video."""
    logging.info(f"Generating thumbnail for {video_path} at {timestamp}s")
    pass

def main():
    parser = argparse.ArgumentParser(description="Clipo AI FFmpeg Render Engine Prototype")
    parser.add_argument("config_json", help="Path to the input JSON configuration file.")
    args = parser.parse_args()

    logging.info("--- Render Engine Start ---")

    config = parse_config(args.config_json)
    if config is None:
        logging.error("Failed to parse configuration. Exiting.")
        sys.exit(1)


    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    logging.info(f"Ensured directories '{DOWNLOADS_DIR}' and '{OUTPUTS_DIR}' exist.")

    video_ext = os.path.splitext(config['video_url'])[-1] if len(os.path.splitext(config['video_url'])[-1]) > 1 else ".mp4"
    video_filename = "input_video" + video_ext
    srt_filename = "input_subtitles.srt" # Standard name for downloaded file
    video_path = os.path.join(DOWNLOADS_DIR, video_filename)
    srt_path = os.path.join(DOWNLOADS_DIR, srt_filename) # Path where subtitle will be downloaded

    logging.info("--- Starting Downloads ---")
    if not download_file(config['video_url'], video_path):
        logging.error("Failed to download video file. Exiting.")
        sys.exit(1)

    if not download_file(config['subtitle_url'], srt_path):
        logging.error("Failed to download subtitle file. Exiting.")
        sys.exit(1)
        
        
    logging.info("--- Downloads Finished ---")
    logging.info("--- Getting Video Info ---")
    video_info = get_video_info(video_path)
    if video_info is None:
        logging.error("Failed to get video info. Exiting.")
        sys.exit(1)

    logging.info("--- Building FFmpeg Command ---")
    render_config = config.get('render_config', {}) 
    ffmpeg_cmd = build_ffmpeg_command(render_config, video_info, video_path, srt_path)
    if ffmpeg_cmd is None:
        logging.error("Failed to build FFmpeg command. Exiting.")
        sys.exit(1)

    logging.info("--- Starting FFmpeg Render ---")
    start_time = time.time()
    success = run_command(ffmpeg_cmd)
    end_time = time.time()
    
    if success:
        logging.info(f"--- Render Finished Successfully in {end_time - start_time:.2f} seconds. ---")
    else:
        logging.error("--- Render Failed. --- Exiting.")
        sys.exit(1)

    output_format = render_config.get('output_format', 'mp4')
    output_video_path = os.path.join(OUTPUTS_DIR, f"final_render.{output_format}")
    thumb_path = os.path.join(OUTPUTS_DIR, "thumbnail.jpg")
    # generate_thumbnail(output_video_path, thumb_path) 

    logging.info("--- Render Engine Finished Successfully ---") 

if __name__ == "__main__":
    main() # Call the main workflow 