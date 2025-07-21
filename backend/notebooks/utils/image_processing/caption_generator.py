"""
Caption generation for images using OpenAI's vision models.
"""

import os
import base64
import mimetypes
import json
import re
import logging
from typing import List, Dict, Any, Optional
from tqdm import tqdm

logger = logging.getLogger(__name__)

def to_data_url(path: str) -> str:
    """Read an image file and return data-URL string suitable for OpenAI vision models."""
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"

def generate_caption_for_image(
    image_path: str, 
    prompt: str = "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
    api_key: Optional[str] = None
) -> str:
    """
    Generate a caption for a single image using OpenAI's vision model.
    
    Args:
        image_path: Path to the image file
        prompt: Prompt for caption generation
        api_key: OpenAI API key (will try to get from environment if not provided)
        
    Returns:
        Generated caption text
    """
    try:
        from openai import OpenAI
        
        # Get API key
        if not api_key:
            api_key = load_api_key_from_settings()

        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or provide api_key parameter.")
        
        client = OpenAI(api_key=api_key)
        data_url = to_data_url(image_path)
        
        chat = client.chat.completions.create(
            model="gpt-4.1-mini",  # Using the latest vision model
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=100,
        )
        
        return chat.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Caption generation failed for {image_path}: {e}")
        return f"Caption generation failed: {str(e)}"

def generate_captions_for_directory(
    images_dir: str,
    output_file: str,
    prompt: str = "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate captions for all PNG images in a directory.
    
    Args:
        images_dir: Directory containing PNG images to caption
        output_file: Path to save the captions JSON file
        prompt: Caption prompt to use for all images
        api_key: OpenAI API key
        
    Returns:
        List of caption results
    """
    try:
        if not os.path.exists(images_dir):
            raise FileNotFoundError(f"Images directory not found: {images_dir}")
        
        # Find all PNG images
        images = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith(".png") and os.path.isfile(os.path.join(images_dir, f))
        ]
        
        if not images:
            logger.warning(f"No PNG images found in {images_dir}")
            return []
        
        results = []
        total_images = len(images)
        logger.info(f"Starting caption generation for {total_images} images...")
        
        # Use tqdm for progress bar
        for img in tqdm(images, desc="Generating captions", unit="image"):
            image_path = os.path.join(images_dir, img)
            caption_text = generate_caption_for_image(image_path, prompt, api_key)
            
            results.append({
                "image_path": image_path,
                "caption": caption_text
            })
        
        # Sort results by image number (extracted from filename)
        try:
            results.sort(key=lambda x: int(re.search(r'(\d+)', os.path.basename(x['image_path'])).group(0)))
        except (AttributeError, ValueError):
            # If sorting fails, keep original order
            logger.warning("Could not sort results by image number")
        
        # Save results to file
        with open(output_file, "w") as out_f:
            json.dump(results, out_f, indent=2)
        
        logger.info(f"Generated {len(results)} captions and saved to {output_file}")
        return results
        
    except Exception as e:
        logger.error(f"Caption generation for directory failed: {e}")
        raise

def load_api_key_from_settings() -> Optional[str]:
    """
    Try to load OpenAI API key from various sources.

    Returns:
        API key if found, None otherwise
    """
    # Try environment variable first
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Try to load from settings
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            return settings.OPENAI_API_KEY
    except Exception:
        pass

    # Try to load from secrets.toml at project root
    try:
        import toml
        # Get the project root directory (4 levels up from this file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        secrets_path = os.path.join(project_root, "secrets.toml")

        if os.path.exists(secrets_path):
            with open(secrets_path, "r") as f:
                secrets = toml.load(f)
            api_key = secrets.get("OPENAI_API_KEY")
            if api_key:
                return api_key

        # Fallback to relative paths for compatibility
        possible_paths = [
            "secrets.toml",
            "../secrets.toml",
            "../../secrets.toml",
            "../../../secrets.toml",
            "../../../../secrets.toml"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    secrets = toml.load(f)
                api_key = secrets.get("OPENAI_API_KEY")
                if api_key:
                    return api_key
    except Exception:
        pass

    return None
