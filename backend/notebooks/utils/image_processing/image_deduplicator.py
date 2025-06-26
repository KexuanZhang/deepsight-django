"""
Image deduplication using pixel-level and semantic similarity methods.
"""

import os
import shutil
import time
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image
import imagehash

logger = logging.getLogger(__name__)

def prepare_work_dir(source_dir: str, work_dir: str):
    """
    Copy all images from source_dir to work_dir for processing.
    
    Args:
        source_dir: Source directory containing images
        work_dir: Working directory for deduplication
    """
    try:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        shutil.copytree(source_dir, work_dir)
        logger.info(f"Prepared work directory: {work_dir}")
    except Exception as e:
        logger.error(f"Failed to prepare work directory: {e}")
        raise

def setup_cuda_environment():
    """
    Setup CUDA environment for Linux servers to avoid cuDNN issues.
    """
    try:
        import torch
        
        # Set environment variables to avoid cuDNN version mismatch
        os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
        
        # Disable cuDNN benchmark for more stable results
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        
        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info(f"CUDA setup completed. Available GPUs: {torch.cuda.device_count()}")
            logger.info(f"Current CUDA device: {torch.cuda.current_device()}")
            logger.info(f"CUDA version: {torch.version.cuda}")
        
    except Exception as e:
        logger.warning(f"CUDA environment setup warning: {e}")

def get_optimal_device(force_device: Optional[str] = None) -> str:
    """
    Get the optimal device for computation with proper error handling.
    
    Args:
        force_device: Force a specific device (cuda, cpu, mps)
        
    Returns:
        Device string to use
    """
    try:
        import torch
        
        if force_device:
            if force_device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                return "cpu"
            elif force_device == "mps" and not torch.backends.mps.is_available():
                logger.warning("MPS requested but not available, falling back to CPU")
                return "cpu"
            return force_device
        
        # Auto-detect best device
        if torch.cuda.is_available():
            # Setup CUDA environment for stability
            setup_cuda_environment()
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
            
    except Exception as e:
        logger.warning(f"Device detection failed: {e}, using CPU")
        return "cpu"

def load_clip_model_and_preprocessing(device: Optional[str] = None):
    """
    Load CLIP model and preprocessing for semantic similarity using open_clip_torch.

    Args:
        device: Device to load model on (cuda, mps, cpu). Auto-detect if None.

    Returns:
        Tuple of (model, preprocess_function, actual_device_used)
    """
    try:
        import torch
        import open_clip

        # Get optimal device
        actual_device = get_optimal_device(device)
        logger.info(f"Loading CLIP model on device: {actual_device}")

        # Load model using open_clip
        model, _, preprocess = open_clip.create_model_and_transforms('ViT-L-14-quickgelu', pretrained='dfn2b')
        
        # Move model to device with error handling
        try:
            model = model.to(actual_device)
            model.eval()
            
            # Test model on device with a dummy tensor
            if actual_device != "cpu":
                test_tensor = torch.randn(1, 3, 224, 224).to(actual_device)
                with torch.no_grad():
                    _ = model.encode_image(test_tensor)
                test_tensor = None  # Clean up
                
        except Exception as device_error:
            logger.warning(f"Failed to use {actual_device}: {device_error}, falling back to CPU")
            actual_device = "cpu"
            model = model.to(actual_device)
            model.eval()

        logger.info(f"CLIP model loaded successfully on {actual_device}")
        return model, preprocess, actual_device

    except ImportError:
        logger.error("OpenCLIP not available. Install with: pip install open_clip_torch")
        raise ImportError("OpenCLIP not available. Install with: pip install open_clip_torch")
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        raise

def global_pixel_dedupe(work_dir: str, max_distance: int) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Compare all images in work_dir with all other images using perceptual hash.
    If hash Hamming distance <= max_distance, removes one of them (the latter in sorted order).
    
    Args:
        work_dir: Directory containing images to deduplicate
        max_distance: Maximum Hamming distance for considering images as duplicates
        
    Returns:
        Tuple of (removed_count, logs)
    """
    try:
        files_names = sorted([f for f in os.listdir(work_dir)
                              if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")], reverse=True)
        
        if len(files_names) < 2:
            return 0, []
        
        logger.info(f"Starting global pixel deduplication on {len(files_names)} images")
        
        # Compute hashes for all images
        image_hashes = {}
        valid_file_paths = []
        
        for fname in files_names:
            fpath = os.path.join(work_dir, fname)
            try:
                with Image.open(fpath) as img:
                    img_hash = imagehash.dhash(img)
                    image_hashes[fpath] = img_hash
                    valid_file_paths.append(fpath)
            except Exception as e:
                logger.warning(f"Could not process image {fname}: {e}")
        
        # Compare all pairs and mark for removal
        files_marked_for_removal = set()
        global_pixel_logs = []
        
        for i in range(len(valid_file_paths)):
            file_a_path = valid_file_paths[i]
            if file_a_path in files_marked_for_removal:
                continue
                
            file_a_name = os.path.basename(file_a_path)
            hash_a = image_hashes[file_a_path]
            
            for j in range(i + 1, len(valid_file_paths)):
                file_b_path = valid_file_paths[j]
                if file_b_path in files_marked_for_removal:
                    continue
                    
                file_b_name = os.path.basename(file_b_path)
                hash_b = image_hashes[file_b_path]
                dist = hash_a - hash_b
                
                log_entry = {
                    "file_a": file_a_name, 
                    "file_b": file_b_name, 
                    "hamming": int(dist), 
                    "removed": False, 
                    "removed_file": None
                }
                
                if dist <= max_distance:
                    log_entry["removed"] = True
                    log_entry["removed_file"] = file_b_name
                    files_marked_for_removal.add(file_b_path)
                
                global_pixel_logs.append(log_entry)
        
        # Remove marked files
        removed_count = 0
        for file_path in files_marked_for_removal:
            try:
                os.remove(file_path)
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")
        
        logger.info(f"Global pixel deduplication completed: removed {removed_count} images")
        return removed_count, global_pixel_logs

    except Exception as e:
        logger.error(f"Global pixel deduplication failed: {e}")
        raise

def sequential_deep_dedupe(work_dir: str, threshold: float, device: str, model, preprocess) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Sequentially compare each image to the next using CLIP embeddings.
    Remove the latter if cosine similarity >= threshold.

    Args:
        work_dir: Directory containing images
        threshold: Cosine similarity threshold for removal
        device: Device for model inference
        model: CLIP model
        preprocess: CLIP preprocessing function

    Returns:
        Tuple of (removed_count, logs)
    """
    try:
        import torch

        files = sorted([f for f in os.listdir(work_dir)
                        if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")], reverse=True)

        removed_count = 0
        deep_logs = []

        if len(files) < 2:
            return 0, deep_logs

        logger.info(f"Starting sequential deep deduplication on {len(files)} images")

        idx = 0
        while idx < len(files) - 1:
            fname_prev = files[idx]
            fname_next = files[idx + 1]
            path_prev = os.path.join(work_dir, fname_prev)
            path_next = os.path.join(work_dir, fname_next)

            try:
                # Load and preprocess images
                img_prev = Image.open(path_prev).convert('RGB')
                img_next = Image.open(path_next).convert('RGB')

                # Ensure tensors are on the correct device
                input_prev = preprocess(img_prev).unsqueeze(0)
                input_next = preprocess(img_next).unsqueeze(0)
                
                # Move tensors to device with error handling
                try:
                    input_prev = input_prev.to(device)
                    input_next = input_next.to(device)
                except Exception as device_error:
                    logger.warning(f"Device transfer failed: {device_error}, using CPU")
                    input_prev = input_prev.to("cpu")
                    input_next = input_next.to("cpu")
                    # Move model to CPU if needed
                    if next(model.parameters()).device != torch.device("cpu"):
                        model = model.to("cpu")

                # Get embeddings using open_clip
                with torch.no_grad():
                    emb_prev = model.encode_image(input_prev)
                    emb_next = model.encode_image(input_next)

                    # Normalize embeddings
                    emb_prev = emb_prev / emb_prev.norm(dim=-1, keepdim=True)
                    emb_next = emb_next / emb_next.norm(dim=-1, keepdim=True)

                    # Calculate cosine similarity - ensure tensors are on same device
                    if emb_prev.device != emb_next.device:
                        emb_next = emb_next.to(emb_prev.device)
                    
                    sim = float(torch.dot(emb_prev.squeeze(), emb_next.squeeze()))

                # Clean up GPU memory
                del input_prev, input_next, emb_prev, emb_next
                if device != "cpu":
                    torch.cuda.empty_cache()

                log_entry = {
                    "file_prev": fname_prev,
                    "file_next": fname_next,
                    "cosine": sim,
                    "removed": False,
                    "removed_file": None
                }

                if sim >= threshold:
                    try:
                        os.remove(path_next)
                        removed_count += 1
                        log_entry["removed"] = True
                        log_entry["removed_file"] = fname_next
                        files.pop(idx + 1)  # Remove from list
                    except Exception as e_remove:
                        logger.warning(f"Failed to remove {path_next}: {e_remove}")
                        log_entry["error"] = f"Failed to remove {path_next}"
                        idx += 1
                else:
                    idx += 1

                deep_logs.append(log_entry)

            except Exception as e:
                logger.warning(f"Error processing {fname_prev} and {fname_next}: {e}")
                idx += 1

        logger.info(f"Sequential deep deduplication completed: removed {removed_count} images")
        return removed_count, deep_logs

    except Exception as e:
        logger.error(f"Sequential deep deduplication failed: {e}")
        raise

def global_deep_dedupe(work_dir: str, threshold: float, device: str, model, preprocess) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Compare all images in work_dir using CLIP embeddings.
    If cosine similarity >= threshold, removes one (the latter in sorted order).

    Args:
        work_dir: Directory containing images
        threshold: Cosine similarity threshold for removal
        device: Device for model inference
        model: CLIP model
        preprocess: CLIP preprocessing function

    Returns:
        Tuple of (removed_count, logs)
    """
    try:
        import torch

        files_names = sorted([f for f in os.listdir(work_dir)
                              if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")], reverse=True)

        if len(files_names) < 2:
            return 0, []

        logger.info(f"Starting global deep deduplication on {len(files_names)} images")

        # Compute embeddings for all images
        image_embeddings = {}
        valid_file_paths = []

        for fname in files_names:
            fpath = os.path.join(work_dir, fname)
            try:
                img = Image.open(fpath).convert('RGB')
                input_tensor = preprocess(img).unsqueeze(0)
                
                # Move tensor to device with error handling
                try:
                    input_tensor = input_tensor.to(device)
                except Exception as device_error:
                    logger.warning(f"Device transfer failed for {fname}: {device_error}, using CPU")
                    input_tensor = input_tensor.to("cpu")
                    # Move model to CPU if needed
                    if next(model.parameters()).device != torch.device("cpu"):
                        model = model.to("cpu")

                with torch.no_grad():
                    embedding = model.encode_image(input_tensor)
                    embedding = embedding / embedding.norm(dim=-1, keepdim=True)
                    # Move to CPU for storage to save GPU memory
                    image_embeddings[fpath] = embedding.squeeze().cpu().numpy()
                    valid_file_paths.append(fpath)
                
                # Clean up GPU memory
                del input_tensor, embedding
                if device != "cpu":
                    torch.cuda.empty_cache()

            except Exception as e:
                logger.warning(f"Could not process image {fname}: {e}")

        # Compare all pairs and mark for removal
        files_marked_for_removal = set()
        global_deep_logs = []

        for i in range(len(valid_file_paths)):
            file_a_path = valid_file_paths[i]
            if file_a_path in files_marked_for_removal:
                continue

            file_a_name = os.path.basename(file_a_path)
            emb_a = image_embeddings[file_a_path]

            for j in range(i + 1, len(valid_file_paths)):
                file_b_path = valid_file_paths[j]
                if file_b_path in files_marked_for_removal:
                    continue

                file_b_name = os.path.basename(file_b_path)
                emb_b = image_embeddings[file_b_path]

                sim = float(np.dot(emb_a, emb_b))

                log_entry = {
                    "file_a": file_a_name,
                    "file_b": file_b_name,
                    "cosine": sim,
                    "removed": False,
                    "removed_file": None
                }

                if sim >= threshold:
                    log_entry["removed"] = True
                    log_entry["removed_file"] = file_b_name
                    files_marked_for_removal.add(file_b_path)

                global_deep_logs.append(log_entry)

        # Remove marked files
        removed_count = 0
        for file_path in files_marked_for_removal:
            try:
                os.remove(file_path)
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        logger.info(f"Global deep deduplication completed: removed {removed_count} images")
        return removed_count, global_deep_logs

    except Exception as e:
        logger.error(f"Global deep deduplication failed: {e}")
        raise

def text_ocr_filter_dedupe(work_dir: str, min_words: int, ocr_lang: str = 'en', ocr_gpu: bool = True) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Remove images that don't contain sufficient text/numbers using OCR.

    Args:
        work_dir: Directory containing images
        min_words: Minimum number of words/numbers required to keep image
        ocr_lang: Language code for EasyOCR
        ocr_gpu: Whether to use GPU for OCR

    Returns:
        Tuple of (removed_count, logs)
    """
    try:
        import easyocr

        files_names = sorted([f for f in os.listdir(work_dir)
                              if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")], reverse=True)

        if len(files_names) == 0:
            return 0, []

        logger.info(f"Starting text OCR filter on {len(files_names)} images")

        try:
            reader = easyocr.Reader([ocr_lang], gpu=ocr_gpu)
        except Exception as ocr_error:
            logger.warning(f"Failed to initialize OCR with GPU: {ocr_error}, falling back to CPU")
            reader = easyocr.Reader([ocr_lang], gpu=False)

        # Pattern to match words and numbers
        pattern = re.compile(r"[A-Za-z0-9]+")

        removed_count = 0
        text_ocr_logs = []

        for fname in files_names:
            fpath = os.path.join(work_dir, fname)

            try:
                # Perform OCR
                recognized = reader.readtext(fpath, detail=0)  # list of text strings
                # Count words/numbers based on regex
                word_count = sum(len(pattern.findall(text)) for text in recognized)

                log_entry = {
                    "file": fname,
                    "word_count": word_count,
                    "contains_sufficient_text": word_count >= min_words,
                    "removed": False,
                    "removed_file": None
                }

                if word_count < min_words:
                    try:
                        os.remove(fpath)
                        removed_count += 1
                        log_entry["removed"] = True
                        log_entry["removed_file"] = fname
                    except Exception as e_remove:
                        logger.warning(f"Failed to remove {fpath}: {e_remove}")
                        log_entry["error"] = f"Failed to remove {fpath}"

                text_ocr_logs.append(log_entry)

            except Exception as e:
                logger.warning(f"OCR failed for {fname}: {e}")
                # Keep the image if OCR fails
                text_ocr_logs.append({
                    "file": fname,
                    "word_count": 0,
                    "contains_sufficient_text": False,
                    "removed": False,
                    "removed_file": None,
                    "error": f"OCR failed: {str(e)}"
                })

        logger.info(f"Text OCR filter completed: removed {removed_count} images")
        return removed_count, text_ocr_logs

    except ImportError:
        logger.error("EasyOCR not available. Install with: pip install easyocr")
        raise ImportError("EasyOCR not available. Install with: pip install easyocr")
    except Exception as e:
        logger.error(f"Text OCR filter failed: {e}")
        raise