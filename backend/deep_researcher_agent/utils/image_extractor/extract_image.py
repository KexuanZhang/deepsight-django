import os
import argparse
import ffmpeg

def extract_frames(input_file: str, interval: float, output_dir: str):
    """
    Extract PNG screenshots from input_file every 'interval' seconds,
    saving them into output_dir/img_<sequence>.png.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "img_%04d.png")
    ffmpeg.input(input_file).output(
        output_path,
        vf=f"fps=1/{interval}"
    ).run()

def main():
    parser = argparse.ArgumentParser(
        description="Extract PNG frames from an MP4 at regular intervals using FFmpeg."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input MP4 video file"
    )
    parser.add_argument(
        "--extract-interval",
        type=float,
        default=8,
        help="Seconds between each extracted frame"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save extracted PNGs (default: <video_title>_Images)",
        default=None
    )

    args = parser.parse_args()

    # Derive video title from filename (without extension)
    video_title = os.path.splitext(os.path.basename(args.input_file))[0]
    # If no output_dir provided, use "<video_title>_Images"
    output_dir = args.output_dir if args.output_dir else f"{video_title}_Images"

    extract_frames(
        input_file=args.input_file,
        interval=args.extract_interval,
        output_dir=output_dir
    )

if __name__ == "__main__":
    main()