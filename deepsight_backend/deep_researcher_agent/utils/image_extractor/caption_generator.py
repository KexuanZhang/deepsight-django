import os
import base64
import mimetypes
import argparse
import json
import sys
import toml
import re
from openai import OpenAI
from tqdm import tqdm

def to_data_url(path: str) -> str:
    """Read an image file and return data-URL string suitable for OpenAI vision models."""
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"

def caption(path: str, prompt: str = "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.", secrets_path=None) -> str:
    # Load API key from secrets.toml
    try:
        # Try using the provided secrets_path first
        if secrets_path and os.path.exists(secrets_path):
            secrets_file = secrets_path
        else:
            # Try multiple locations for secrets.toml
            possible_paths = [
                "secrets.toml",  # Current directory
                "../secrets.toml",  # Parent directory
                "../../secrets.toml",  # Two levels up
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "../secrets.toml"),  # Relative to script
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets.toml")  # Parent of script dir
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    secrets_file = path
                    break
            else:
                raise FileNotFoundError("Could not find secrets.toml in any expected location")
        
        with open(secrets_file, "r") as f:
            secrets = toml.load(f)
        api_key = secrets.get("OPENAI_API_KEY")
        
        # check environment variables as fallback
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
    except FileNotFoundError:
        print(f"Error: secrets.toml not found. Tried multiple paths. Please specify the correct path.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading secrets.toml: {e}", file=sys.stderr)
        sys.exit(1)

    if not api_key:
        print("Error: OPENAI_API_KEY not found in secrets.toml or environment variables.", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key)
    data_url = to_data_url(path)
    chat = client.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text",       "text": prompt},
                {"type": "image_url",  "image_url": {"url": data_url}},
            ],
        }],
        max_tokens=100,
    )
    return chat.choices[0].message.content.strip()

def main():
    parser = argparse.ArgumentParser(
        description="Generate captions for all .png images in a directory."
    )
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directory containing .png images to caption"
    )
    parser.add_argument(
        "--output-file",
        help="Path to the output JSON file. If not provided, will use <video_title>_caption.json"
    )
    parser.add_argument(
        "--prompt",
        default="Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
        help="Caption prompt to use for all images"
    )
    parser.add_argument(
        "--secrets-path",
        help="Path to the secrets.toml file containing the OPENAI_API_KEY"
    )
    args = parser.parse_args()

    # If output file is not provided, derive it from the images directory name
    if not args.output_file:
        # Get the parent directory name (which should be the video title)
        video_title = os.path.basename(os.path.normpath(args.images_dir))
        if video_title.endswith('_Dedup_Images'):
            video_title = video_title[:-12]  # Remove '_Dedup_Images' suffix
        elif video_title.endswith('_Images'):
            video_title = video_title[:-7]  # Remove '_Images' suffix
        args.output_file = f"{video_title}_caption.json"

    images = [
        f for f in os.listdir(args.images_dir)
        if f.lower().endswith(".png") and os.path.isfile(os.path.join(args.images_dir, f))
    ]

    results = []
    total_images = len(images)
    print(f"Starting caption generation for {total_images} images...")
    
    # Use tqdm for a dynamic progress bar
    for img in tqdm(images, desc="Generating captions", unit="image"):
        path = os.path.join(args.images_dir, img)
        caption_text = caption(path, args.prompt, args.secrets_path)
        figure_name = os.path.splitext(img)[0]
        results.append({
            "image_path": path,
            "figure_name": figure_name,
            "caption": caption_text
        })
        
    results.sort(key=lambda x: int(re.search(r'(\d+)', x['figure_name']).group(0)))
    
    with open(args.output_file, "w") as out_f:
        json.dump(results, out_f, indent=2)

    print(f"Wrote {len(results)} captions to {args.output_file}")

if __name__ == "__main__":
    main()