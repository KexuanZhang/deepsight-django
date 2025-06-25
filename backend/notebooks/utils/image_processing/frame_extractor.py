"""
Frame extraction from video files using FFmpeg.
"""

import os
import ffmpeg
import logging

logger = logging.getLogger(__name__)

def extract_frames(input_file: str, interval: float, output_dir: str):
    """
    Extract PNG screenshots from input_file every 'interval' seconds,
    saving them into output_dir/img_<sequence>.png.
    
    Args:
        input_file: Path to the input video file
        interval: Seconds between each extracted frame
        output_dir: Directory to save extracted PNGs
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "img_%04d.png")
        
        logger.info(f"Extracting frames from {input_file} every {interval} seconds to {output_dir}")
        
        ffmpeg.input(input_file).output(
            output_path,
            vf=f"fps=1/{interval}"
        ).run(overwrite_output=True, quiet=True)
        
        # Count extracted frames
        frame_count = len([f for f in os.listdir(output_dir) if f.startswith("img_") and f.endswith(".png")])
        logger.info(f"Successfully extracted {frame_count} frames")
        
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        raise Exception(f"Frame extraction failed: {str(e)}")
