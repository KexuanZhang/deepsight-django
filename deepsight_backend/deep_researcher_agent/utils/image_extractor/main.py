import os
import argparse
import sys
import re
import json
import time
from yt_dlp import YoutubeDL
from .download_video import download_video
from .extract_image import extract_frames
from .image_dedup import prepare_work_dir, text_ocr_filter_dedupe, global_pixel_dedupe, sequential_deep_dedupe, global_deep_dedupe, _load_clip_model_and_preprocessing
from .caption_generator import main as generate_captions

def get_video_title_from_url(url, cookies_browser='chrome'):
    """Extract the title of the video from the URL using yt-dlp and return a cleaned version."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'cookiesfrombrowser': (cookies_browser,)
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        raw_title = info.get('title', None)
        if raw_title:
            return clean_title(raw_title)
        return None

def find_existing_video_file(video_title, output_dir='.'):
    """
    Find an existing video file in the output directory that matches the video title exactly.
    Since we now use cleaned titles consistently, we can do exact matching.
    
    Args:
        video_title: The cleaned title of the video
        output_dir: The directory to search in
        
    Returns:
        The path to the video file if found, None otherwise
    """
    # Look for exact match
    exact_path = os.path.join(output_dir, f"{video_title}.mp4")
    if os.path.exists(exact_path):
        return exact_path
    
    return None

def find_existing_path(base_name, suffix, is_dir=True, parent_dir='.'):
    """
    Find an existing directory or file that matches the expected name exactly.
    Since we now use cleaned titles consistently, we can do exact matching.
    
    Args:
        base_name: The base name (usually cleaned video title)
        suffix: The suffix to append to the base name (e.g., "_Images", "_Dedup_Images", "_caption.json")
        is_dir: Whether to look for a directory (True) or file (False)
        parent_dir: The parent directory to search in
        
    Returns:
        The path if found, None otherwise
    """
    # Look for exact match
    expected_name = f"{base_name}{suffix}"
    expected_path = os.path.join(parent_dir, expected_name)
    if os.path.exists(expected_path) and os.path.isdir(expected_path) == is_dir:
        return expected_path
                
    return None

def clean_title(title):
    """
    Clean the video title by replacing all spaces and non-alphanumeric characters with underscores.
    
    Args:
        title: The original video title
        
    Returns:
        The cleaned title with spaces and non-alphanumeric characters replaced by underscores
    """
    # Replace all non-alphanumeric characters (except for underscores) with underscores
    cleaned = re.sub(r'[^\w\d]', '_', title)
    # Replace consecutive underscores with a single underscore
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    return cleaned

def process_video(url=None, video_path=None, output_dir='.', extract_interval=8, pixel_threshold=3, 
                 sequential_deep_threshold=0.8, global_deep_threshold=0.85, device=None, caption_prompt="Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
                 cookies_browser='chrome', secrets_path=None, ocr_lang='en', ocr_gpu=True, min_words=5):
    """
    Process a video through the entire pipeline:
    1. Download video (if URL provided and not already downloaded)
    2. Extract frames (if not already extracted)
    3. Deduplicate images with 4-step process (if not already done):
       a. Global pixel dedupe - remove pixel-level duplicates
       b. Sequential deep dedupe - remove semantically similar adjacent images
       c. Global deep dedupe - remove remaining semantic duplicates
       d. Text OCR filter - remove images with insufficient text/numbers
    4. Generate captions (if not already generated)
    
    Args:
        url: URL of the video to process
        video_path: Path to a local video file
        output_dir: Directory to save output files
        extract_interval: Seconds between each extracted frame
        pixel_threshold: Max Hamming distance for pixel dedupe
        sequential_deep_threshold: Cosine similarity threshold for sequential deep dedupe
        global_deep_threshold: Cosine similarity threshold for global deep dedupe
        device: Torch device to use (cuda, mps, or cpu)
        caption_prompt: Prompt to use for caption generation
        cookies_browser: Browser to get cookies from
        secrets_path: Path to the secrets.toml file for API keys
        ocr_lang: Language code for EasyOCR
        ocr_gpu: Use GPU for OCR
        min_words: Minimum word count to keep image
    """
    # Determine the video path and title
    if video_path:
        # Use provided video path
        video_path = os.path.abspath(video_path)
        video_title = os.path.splitext(os.path.basename(video_path))[0]
        print(f"Using provided video: {video_path}")
    elif url:
        # Get video title for file naming
        print(f"Getting video information from URL: {url}")
        video_title = get_video_title_from_url(url, cookies_browser)
        if not video_title:
            print("Error: Could not retrieve video title.")
            return None
    else:
        print("Error: Either a video URL or a video path must be provided.")
        return None
    
    # Video title is already cleaned from get_video_title_from_url
    # First check if caption file already exists
    existing_caption_file = find_existing_path(video_title, "_caption.json", is_dir=False, parent_dir=output_dir)
    if existing_caption_file and os.path.exists(existing_caption_file):
        print(f"Caption file already exists at {existing_caption_file}, skipping all processing.")
        return existing_caption_file
    
    # If no caption file exists, continue with normal processing
    if url:
        # Find any existing file that might match the video title
        expected_video_path = os.path.join(output_dir, f"{video_title}.mp4")
        actual_video_path = find_existing_video_file(video_title, output_dir)
        
        # Step 1: Download video if it doesn't exist
        if actual_video_path:
            print(f"Video already exists at {actual_video_path}, skipping download.")
            video_path = actual_video_path
        else:
            print(f"Downloading video from {url} to {output_dir}")
            download_video(url, output_dir=output_dir, cookies_browser=cookies_browser, clean_filename=True)
            # After download, find the actual video file
            actual_video_path = find_existing_video_file(video_title, output_dir)
            if not actual_video_path:
                print(f"Error: Video file not found after download attempt.")
                return None
            video_path = actual_video_path
    
    # Find existing directories and files or use expected names with full paths
    # Use cleaned title for new folders and files
    expected_images_dir = os.path.join(output_dir, f"{video_title}_Images")
    expected_dedup_dir = os.path.join(output_dir, f"{video_title}_Dedup_Images")
    expected_captions_file = os.path.join(output_dir, f"{video_title}_caption.json")
    
    # Try to find existing directories and files
    images_dir = find_existing_path(video_title, "_Images", is_dir=True, parent_dir=output_dir) or expected_images_dir
    dedup_dir = find_existing_path(video_title, "_Dedup_Images", is_dir=True, parent_dir=output_dir) or expected_dedup_dir
    captions_file = find_existing_path(video_title, "_caption.json", is_dir=False, parent_dir=output_dir) or expected_captions_file
    
    # Step 2: Extract frames if images directory doesn't exist
    if os.path.exists(images_dir) and os.listdir(images_dir):
        print(f"Images directory {images_dir} already exists and contains files, skipping extraction.")
    else:
        print(f"Extracting frames from {video_path} to {images_dir}")
        extract_frames(video_path, extract_interval, images_dir)
    
    # Step 3: Deduplicate images if dedup directory doesn't exist
    if os.path.exists(dedup_dir) and os.listdir(dedup_dir):
        print(f"Dedup directory {dedup_dir} already exists and contains files, skipping deduplication.")
    else:
        print(f"Deduplicating images from {images_dir} to {dedup_dir}")
        # Prepare work directory (copy images to dedup_dir)
        prepare_work_dir(images_dir, dedup_dir)
        
        # Get device
        if device is None:
            import torch
            device = 'cuda' if torch.cuda.is_available() else ('mps' if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() and torch.backends.mps.is_built() else 'cpu')
        
        print(f"Using device: {device}")
        
        # Load CLIP model for deep deduplication steps
        print("Loading CLIP model for deep learning steps...")
        try:
            clip_model, clip_preprocess = _load_clip_model_and_preprocessing(device=device)
            print("CLIP model loaded successfully.")
        except Exception as e:
            print(f"Error: Could not load CLIP model: {e}. Using CPU instead.")
            device = 'cpu'
            try:
                clip_model, clip_preprocess = _load_clip_model_and_preprocessing(device=device)
            except Exception as e:
                print(f"Fatal: Could not load CLIP model on CPU either: {e}. Skipping deep deduplication.")
                clip_model, clip_preprocess = None, None
        
        # Initialize logs and removed counts
        logs_pix_global, logs_deep_seq, logs_deep_global, logs_text_ocr = [], [], [], []
        removed_pix_global, removed_deep_seq, removed_deep_global, removed_text_ocr = 0, 0, 0, 0
        
        # Record initial file count
        initial_file_count = len([f for f in os.listdir(dedup_dir) if os.path.isfile(os.path.join(dedup_dir, f)) and not f.endswith("dedupe_log.json")])
        
        # Step 1: Run global pixel deduplication
        print("Running global pixel-based deduplication...")
        t_start = time.time()
        removed_pix_global, logs_pix_global = global_pixel_dedupe(dedup_dir, pixel_threshold)
        print(f"Removed {removed_pix_global} images in global pixel-based deduplication in {time.time()-t_start:.2f}s.")
        
        # Step 2: Run sequential deep deduplication
        if clip_model and clip_preprocess:
            print(f"Running sequential deep deduplication using {device} (threshold: {sequential_deep_threshold})...")
            t_start = time.time()
            removed_deep_seq, logs_deep_seq = sequential_deep_dedupe(dedup_dir, sequential_deep_threshold, device, clip_model, clip_preprocess)
            print(f"Removed {removed_deep_seq} images in sequential deep deduplication in {time.time()-t_start:.2f}s.")
            
            # Step 3: Run global deep deduplication
            print(f"Running global deep deduplication using {device} (threshold: {global_deep_threshold})...")
            t_start = time.time()
            removed_deep_global, logs_deep_global = global_deep_dedupe(dedup_dir, global_deep_threshold, device, clip_model, clip_preprocess)
            print(f"Removed {removed_deep_global} images in global deep deduplication in {time.time()-t_start:.2f}s.")
        else:
            print("Skipping deep deduplication steps due to model loading failure.")
        
        # Step 4: Run text OCR filtering
        print(f"Running text OCR filtering (min words: {min_words})...")
        t_start = time.time()
        removed_text_ocr, logs_text_ocr = text_ocr_filter_dedupe(dedup_dir, ocr_lang, ocr_gpu, min_words)
        print(f"Removed {removed_text_ocr} images with insufficient text in {time.time()-t_start:.2f}s.")
        
        # Calculate final file count and total removed
        final_file_count = len([f for f in os.listdir(dedup_dir) if os.path.isfile(os.path.join(dedup_dir, f)) and not f.endswith("dedupe_log.json")])
        total_removed = initial_file_count - final_file_count
        
        print(f"\nTotal images removed: {total_removed}")
        print(f"Final image count: {final_file_count} (Initial: {initial_file_count})")
        
        # Save the deduplication log
        log_path = os.path.join(output_dir, f"{video_title}_dedupe_log.json")
        try:
            with open(log_path, "w") as f:
                json.dump({
                    "global_pixel": logs_pix_global,
                    "sequential_deep": logs_deep_seq,
                    "global_deep": logs_deep_global,
                    "text_ocr_filter": logs_text_ocr,
                    "summary": {
                        "input_directory": images_dir,
                        "output_directory": dedup_dir,
                        "work_directory_processed": dedup_dir,
                        "initial_image_count": initial_file_count,
                        "removed_global_pixel": removed_pix_global,
                        "removed_sequential_deep": removed_deep_seq,
                        "removed_global_deep": removed_deep_global,
                        "removed_text_ocr_filter": removed_text_ocr,
                        "total_removed_calculated_by_sum": removed_pix_global + removed_deep_seq + removed_deep_global + removed_text_ocr,
                        "total_removed_final_count_diff": total_removed,
                        "final_image_count_on_disk": final_file_count,
                        "pixel_threshold": pixel_threshold,
                        "sequential_deep_threshold": sequential_deep_threshold,
                        "global_deep_threshold": global_deep_threshold,
                        "ocr_language": ocr_lang,
                        "ocr_gpu": ocr_gpu,
                        "min_words_threshold": min_words,
                        "device_used": device
                    }
                }, f, indent=2)
            print(f"Deduplication log saved to: {log_path}")
        except Exception as e:
            print(f"Error writing log file to {log_path}: {e}")
    
    # Step 4: Generate captions if captions file doesn't exist
    print(f"Generating captions for images in {dedup_dir}")
    # Use sys.argv to pass arguments to caption_generator's main function
    sys_argv_backup = sys.argv
    caption_args = [
        'caption_generator.py',
        '--images-dir', dedup_dir,
        '--output-file', captions_file,
        '--prompt', caption_prompt
    ]
    
    if secrets_path:
        caption_args.extend(['--secrets-path', secrets_path])
    
    sys.argv = caption_args
    
    try:
        generate_captions()
    except Exception as e:
        print(f"Error generating captions: {e}")
        return None
    finally:
        sys.argv = sys_argv_backup
    
    return captions_file

def main():
    parser = argparse.ArgumentParser(
        description="Process a video through the entire pipeline: download, extract frames, deduplicate, and caption."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--video-url', help='Video URL to process')
    group.add_argument('--video-path', help='Local video file path to process')
    
    parser.add_argument('-o', '--output-dir', default='.',
                        help='Directory to save the downloaded video (default: current directory)')
    parser.add_argument('--extract-interval', type=float, default=8,
                        help='Seconds between each extracted frame')
    parser.add_argument('--pixel-threshold', type=int, default=3,
                        help='Max Hamming distance for pixel dedupe')
    parser.add_argument('--sequential-deep-threshold', type=float, default=0.80,
                        help='Cosine similarity threshold for sequential deep dedupe')
    parser.add_argument('--global-deep-threshold', type=float, default=0.85,
                        help='Cosine similarity threshold for global deep dedupe')
    parser.add_argument('--device', type=str, default=None,
                        help='Torch device: cuda, mps, or cpu')
    parser.add_argument('--caption-prompt', type=str, default="Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences.Add a tag at the end if you find <chart> or <table> in the image.",
                        help='Prompt to use for caption generation')
    parser.add_argument('--cookies-browser', type=str, default='chrome',
                        help='Browser to get cookies from (default: chrome)')
    parser.add_argument('--secrets-path', type=str, default=None,
                        help='Path to the secrets.toml file containing API keys')
    parser.add_argument('--ocr-lang', default='en',
                        help='Language code for EasyOCR')
    parser.add_argument('--ocr-gpu', action='store_true', default=True,
                        help='Use GPU for OCR (default: True)')
    parser.add_argument('--min-words', type=int, default=5,
                        help='Minimum word count to keep image')
    parser.add_argument('--deep-threshold', type=float, default=None,
                        help='Deprecated: Use --sequential-deep-threshold and --global-deep-threshold instead')
    
    args = parser.parse_args()
    
    if args.deep_threshold is not None:
        print(f"Warning: --deep-threshold is deprecated. Using {args.deep_threshold} for both sequential and global deep thresholds.")
        sequential_threshold = args.deep_threshold
        global_threshold = args.deep_threshold
    else:
        sequential_threshold = args.sequential_deep_threshold
        global_threshold = args.global_deep_threshold
    
    result = process_video(
        url=args.video_url,
        video_path=args.video_path,
        output_dir=args.output_dir,
        extract_interval=args.extract_interval,
        pixel_threshold=args.pixel_threshold,
        sequential_deep_threshold=sequential_threshold,
        global_deep_threshold=global_threshold,
        device=args.device,
        caption_prompt=args.caption_prompt,
        cookies_browser=args.cookies_browser,
        secrets_path=args.secrets_path,
        ocr_lang=args.ocr_lang,
        ocr_gpu=args.ocr_gpu,
        min_words=args.min_words
    )
    
    if result:
        print(f"Pipeline completed successfully. Captions saved to: {result}")
    else:
        print("Pipeline failed to complete.")

if __name__ == '__main__':
    main() 