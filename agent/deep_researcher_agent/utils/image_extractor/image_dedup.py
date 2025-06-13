import os
import shutil
import argparse
import time
from PIL import Image
import imagehash
import torch
import numpy as np
import open_clip
import json
import torch.backends.cudnn
import sys
import re
from pathlib import Path
import easyocr

def prepare_work_dir(src_dir: str, dst_dir: str) -> str:
    """
    Copy images from src_dir to dst_dir if dst_dir is specified,
    otherwise returns src_dir for in-place operations.
    """
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            src = os.path.join(src_dir, fname)
            dst = os.path.join(dst_dir, fname)
            if os.path.isfile(src):
                if fname.endswith("dedupe_log.json") and src_dir != dst_dir:
                    continue
                shutil.copy2(src, dst)
        return dst_dir
    return src_dir

def _load_clip_model_and_preprocessing(model_name="ViT-L-14-quickgelu", pretrained="dfn2b", device="cpu"):
    """ Helper to load CLIP model and preprocessing. """
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name, pretrained=pretrained
    )
    model.to(device).eval()
    return model, preprocess

def _get_embedding(image_path, model, preprocess, device):
    """ Helper to get a single image embedding. """
    img = Image.open(image_path).convert('RGB')
    tensor = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(tensor)
    img.close()
    if emb is None: 
         raise ValueError(f"Model returned None embedding for {image_path}.")
    emb = emb / emb.norm(dim=-1, keepdim=True) # Normalize
    return emb.cpu().numpy()[0]


def sequential_deep_dedupe(work_dir: str, threshold: float, device: str, model, preprocess):
    """
    Sequentially compare each image to the next using CLIP embeddings.
    Remove the latter if cosine similarity >= threshold.
    model and preprocess are passed in.
    """
    files = sorted([f for f in os.listdir(work_dir)
                    if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    removed_count = 0
    deep_logs = []

    if len(files) < 2: 
        return 0, deep_logs

    emb_prev = None
    initial_load_idx = 0
    while initial_load_idx < len(files):
        try:
            emb_prev = _get_embedding(os.path.join(work_dir, files[initial_load_idx]), model, preprocess, device)
            break 
        except Exception as e_initial:
            print(f"Warning: Error loading initial embedding for {files[initial_load_idx]} in sequential_deep_dedupe: {e_initial}. Removing from list.")
            files.pop(initial_load_idx) 
    
    if emb_prev is None or not files: 
        return 0, deep_logs
    
    files = files[initial_load_idx:] 
    if len(files) < 2: 
         return 0, deep_logs

    idx = 0 
    while idx < len(files) - 1:
        fname_prev = files[idx]
        fname_next = files[idx + 1]
        path_next = os.path.join(work_dir, fname_next)

        try:
            emb_next = _get_embedding(path_next, model, preprocess, device)
        except Exception as e_load_next:
            print(f"Warning: Error loading embedding for {fname_next} in sequential_deep_dedupe: {e_load_next}. Removing from list.")
            files.pop(idx + 1) 
            continue 

        sim = float(np.dot(emb_prev, emb_next))

        if sim >= threshold: 
            try:
                os.remove(path_next)
                removed_count += 1
                deep_logs.append({"file_prev": fname_prev, "file_next": fname_next, "cosine": sim, "removed": True, "removed_file": fname_next})
                files.pop(idx + 1) 
            except Exception as e_remove:
                print(f"Warning: Failed to remove {path_next}: {e_remove}")
                deep_logs.append({"file_prev": fname_prev, "file_next": fname_next, "cosine": sim, "removed": False, "removed_file": None, "error": f"Failed to remove {path_next}"})
                emb_prev = emb_next 
                idx += 1
        else: 
            deep_logs.append({"file_prev": fname_prev, "file_next": fname_next, "cosine": sim, "removed": False, "removed_file": None})
            emb_prev = emb_next 
            idx += 1          
    return removed_count, deep_logs


def global_pixel_dedupe(work_dir: str, max_distance: int):
    """
    Compares all images in work_dir with all other images using perceptual hash.
    If hash Hamming distance <= max_distance, removes one of them (the latter in sorted order).
    """
    files_names = sorted([f for f in os.listdir(work_dir)
                          if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    
    if len(files_names) < 2:
        return 0, []

    image_hashes = {} 
    valid_file_paths = [] 

    print(f"[Global Pixel Step] Loading and hashing {len(files_names)} images...")
    for fname in files_names:
        fpath = os.path.join(work_dir, fname)
        try:
            img = Image.open(fpath)
            image_hashes[fpath] = imagehash.dhash(img)
            img.close()
            valid_file_paths.append(fpath)
        except Exception as e:
            print(f"Warning: Error processing {fpath} for global pixel dedupe: {e}. Skipping.")
    
    if len(valid_file_paths) < 2: 
        return 0, []
        
    files_marked_for_removal = set() 
    global_pixel_logs = []

    print(f"[Global Pixel Step] Comparing {len(valid_file_paths)} images (all-pairs)...")
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
            if file_b_path not in image_hashes: 
                continue
            hash_b = image_hashes[file_b_path]
            dist = hash_a - hash_b
            log_entry = {"file_a": file_a_name, "file_b": file_b_name, "hamming": int(dist), "removed": False, "removed_file": None}
            if dist <= max_distance:
                log_entry["removed"] = True 
                log_entry["removed_file"] = file_b_name
                files_marked_for_removal.add(file_b_path)
            global_pixel_logs.append(log_entry)

    removed_count = 0
    if files_marked_for_removal:
        print(f"[Global Pixel Step] Removing {len(files_marked_for_removal)} identified duplicate files...")
    for fpath_to_remove in files_marked_for_removal:
        try:
            if os.path.exists(fpath_to_remove):
                os.remove(fpath_to_remove)
                removed_count += 1
        except Exception as e:
            print(f"Warning: Error removing {fpath_to_remove} during global pixel dedupe: {e}")
    return removed_count, global_pixel_logs


def global_deep_dedupe(work_dir: str, threshold: float, device: str, model, preprocess):
    """
    Compares all images in work_dir using CLIP embeddings.
    If cosine similarity >= threshold, removes one (the latter in sorted order).
    Model and preprocess are passed in.
    """
    files_names = sorted([f for f in os.listdir(work_dir)
                          if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    
    if len(files_names) < 2:
        return 0, []

    image_embeddings = {}
    valid_file_paths = []

    print(f"[Global Deep Step] Generating embeddings for {len(files_names)} images...")
    for fname in files_names:
        fpath = os.path.join(work_dir, fname)
        try:
            embedding = _get_embedding(fpath, model, preprocess, device)
            image_embeddings[fpath] = embedding
            valid_file_paths.append(fpath)
        except Exception as e:
            print(f"Warning: Error generating embedding for {fpath} in global_deep_dedupe: {e}. Skipping.")

    if len(valid_file_paths) < 2:
        print("[Global Deep Step] Not enough valid embeddings to compare.")
        return 0, []

    files_marked_for_removal = set()
    global_deep_logs = []

    print(f"[Global Deep Step] Comparing {len(valid_file_paths)} embeddings (all-pairs)...")
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
            if file_b_path not in image_embeddings:
                print(f"Internal Warning: {file_b_name} from valid_file_paths not found in image_embeddings. Skipping comparison with {file_a_name}.")
                continue
            
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

    removed_count = 0
    if files_marked_for_removal:
        print(f"[Global Deep Step] Removing {len(files_marked_for_removal)} identified duplicate files...")
    for fpath_to_remove in files_marked_for_removal:
        try:
            if os.path.exists(fpath_to_remove):
                os.remove(fpath_to_remove)
                removed_count += 1
        except Exception as e:
            print(f"Warning: Error removing {fpath_to_remove} during global deep dedupe: {e}")
            
    return removed_count, global_deep_logs


def text_ocr_filter_dedupe(work_dir: str, lang: str = "en", gpu: bool = True, min_words: int = 5):
    """
    Filter out images that contain less than min_words words/numbers using EasyOCR.
    This is the final filtering step.
    """
    files_names = sorted([f for f in os.listdir(work_dir)
                          if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    
    if len(files_names) == 0:
        return 0, []

    print(f"[Text OCR Filter Step] Analyzing {len(files_names)} images for text content...")
    
    try:
        reader = easyocr.Reader([lang], gpu=gpu)
        pattern = re.compile(r"[A-Za-z0-9]+")
    except Exception as e:
        print(f"Warning: Could not initialize EasyOCR reader: {e}. Skipping text OCR filtering.")
        return 0, []
    
    removed_count = 0
    text_ocr_logs = []
    
    # Supported image extensions
    exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}
    
    for fname in files_names:
        fpath = os.path.join(work_dir, fname)
        
        # Check if file has supported extension
        if not any(fname.lower().endswith(ext) for ext in exts):
            text_ocr_logs.append({"file": fname, "word_count": None, "contains_sufficient_text": True, "removed": False, "removed_file": None, "error": "Unsupported file format"})
            continue
            
        try:
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
                    print(f"Warning: Failed to remove {fpath}: {e_remove}")
                    log_entry["error"] = f"Failed to remove {fpath}"
            
            text_ocr_logs.append(log_entry)
            
        except Exception as e:
            print(f"Warning: Error processing {fpath} for text OCR filtering: {e}. Keeping the file.")
            text_ocr_logs.append({"file": fname, "word_count": None, "contains_sufficient_text": True, "removed": False, "removed_file": None, "error": str(e)})
    
    return removed_count, text_ocr_logs


def main():
    parser = argparse.ArgumentParser(
        description="4-step image deduplication: global pixel, sequential deep, global deep, text OCR filter."
    )
    parser.add_argument('input_dir', help='Directory of images to dedupe')
    parser.add_argument('--output-dir', help='Directory to copy images to before dedupe (default: in-place)')
    parser.add_argument('--pixel-threshold', type=int, default=3, help='Max Hamming distance for pixel dedupe')
    parser.add_argument('--sequential-deep-threshold', type=float, default=0.80, help='Cosine similarity threshold for sequential deep dedupe')
    parser.add_argument('--global-deep-threshold', type=float, default=0.85, help='Cosine similarity threshold for global deep dedupe')
    parser.add_argument('--device', type=str, default=None, help='Torch device: cuda, mps, or cpu (default: auto-detect)')
    parser.add_argument('--ocr-lang', default='en', help='Language code for EasyOCR')
    parser.add_argument('--ocr-gpu', action='store_true', default=True, help='Use GPU for OCR (default: True)')
    parser.add_argument('--min-words', type=int, default=5, help='Minimum word count to keep image')
    parser.add_argument('--deep-threshold', type=float, default=None, help='Deprecated: Use --sequential-deep-threshold and --global-deep-threshold instead')
    
    args = parser.parse_args()

    if not args.input_dir or not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found or not specified.")
        sys.exit(1) # Exit if input_dir is invalid

    if args.deep_threshold is not None:
        print(f"Warning: --deep-threshold is deprecated. Using {args.deep_threshold} for both sequential and global deep thresholds.")
        sequential_threshold = args.deep_threshold
        global_threshold = args.deep_threshold
    else:
        sequential_threshold = args.sequential_deep_threshold
        global_threshold = args.global_deep_threshold

    actual_work_dir = args.output_dir if args.output_dir else args.input_dir
    work_dir = prepare_work_dir(args.input_dir, args.output_dir)
    print(f"Working in: '{work_dir}' ({'Copied from input' if args.output_dir and args.output_dir != args.input_dir else 'In-place'})")

    torch.manual_seed(0)
    if hasattr(torch.backends, 'cudnn') and torch.backends.cudnn.is_available():
        torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False

    if args.device:
        device = args.device
        if device == 'cuda' and not torch.cuda.is_available(): device = 'cpu'; print("CUDA not available, using CPU.")
        elif device == 'mps' and (not hasattr(torch.backends, 'mps') or not torch.backends.mps.is_available() or not torch.backends.mps.is_built()): device = 'cpu'; print("MPS not available, using CPU.")
    else: 
        device = 'cuda' if torch.cuda.is_available() else ('mps' if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() and torch.backends.mps.is_built() else 'cpu')
    print(f"Using device: {device}")

    initial_file_count = len([f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    print(f"Initial image count: {initial_file_count}")
    if initial_file_count == 0: print("No images to process."); return

    print("Loading CLIP model for deep learning steps...")
    try:
        clip_model, clip_preprocess = _load_clip_model_and_preprocessing(device=device)
        print("CLIP model loaded successfully.")
    except Exception as e:
        print(f"FATAL: Could not load CLIP model: {e}. Deep learning steps will be skipped / may fail.")
        return
    
    logs_pix_global, logs_deep_seq, logs_deep_global, logs_text_ocr = [], [], [], []
    removed_pix_global, removed_deep_seq, removed_deep_global, removed_text_ocr = 0, 0, 0, 0

    # --- Step 1: Global Pixel Dedupe ---
    t_start = time.time()
    removed_pix_global, logs_pix_global = global_pixel_dedupe(work_dir, args.pixel_threshold)
    current_files_after_step1 = len([f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    print(f"[Step 1: Global Pixel] Removed {removed_pix_global} images in {time.time()-t_start:.2f}s. Files remaining: {current_files_after_step1}")

    # --- Step 2: Sequential Deep Dedupe ---
    t_start = time.time()
    removed_deep_seq, logs_deep_seq = sequential_deep_dedupe(work_dir, sequential_threshold, device, clip_model, clip_preprocess)
    current_files_after_step2 = len([f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    print(f"[Step 2: Sequential Deep] Removed {removed_deep_seq} images in {time.time()-t_start:.2f}s. Files remaining: {current_files_after_step2}")
    
    # --- Step 3: Global Deep Dedupe ---
    t_start = time.time()
    removed_deep_global, logs_deep_global = global_deep_dedupe(work_dir, global_threshold, device, clip_model, clip_preprocess)
    current_files_after_step3 = len([f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    print(f"[Step 3: Global Deep] Removed {removed_deep_global} images in {time.time()-t_start:.2f}s. Files remaining: {current_files_after_step3}")

    # --- Step 4: Text OCR Filter ---
    t_start = time.time()
    removed_text_ocr, logs_text_ocr = text_ocr_filter_dedupe(work_dir, args.ocr_lang, args.ocr_gpu, args.min_words)
    final_file_count = len([f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith("dedupe_log.json")])
    print(f"[Step 4: Text OCR Filter] Removed {removed_text_ocr} images in {time.time()-t_start:.2f}s. Files remaining: {final_file_count}")

    total_removed = initial_file_count - final_file_count

    print(f"\nTotal images removed: {total_removed}")
    print(f"Final image count: {final_file_count} (Initial: {initial_file_count})")

    log_path = os.path.join(actual_work_dir, "dedupe_log.json")
    try:
        with open(log_path, "w") as f:
            json.dump({
                "global_pixel": logs_pix_global,
                "sequential_deep": logs_deep_seq,
                "global_deep": logs_deep_global,
                "text_ocr_filter": logs_text_ocr,
                "summary": {
                    "input_directory": args.input_dir,
                    "output_directory": args.output_dir if args.output_dir else "In-place in input_dir",
                    "work_directory_processed": work_dir,
                    "initial_image_count": initial_file_count,
                    "removed_global_pixel": removed_pix_global,
                    "removed_sequential_deep": removed_deep_seq,
                    "removed_global_deep": removed_deep_global,
                    "removed_text_ocr_filter": removed_text_ocr,
                    "total_removed_calculated_by_sum": removed_pix_global + removed_deep_seq + removed_deep_global + removed_text_ocr,
                    "total_removed_final_count_diff": total_removed,
                    "final_image_count_on_disk": final_file_count,
                    "pixel_threshold": args.pixel_threshold,
                    "sequential_deep_threshold": sequential_threshold,
                    "global_deep_threshold": global_threshold,
                    "ocr_language": args.ocr_lang,
                    "ocr_gpu": args.ocr_gpu,
                    "min_words_threshold": args.min_words,
                    "device_used": device
                }
            }, f, indent=2)
        print(f"Deduplication log saved to: {log_path}")
    except Exception as e:
        print(f"Error writing log file to {log_path}: {e}")

if __name__ == '__main__':
    main()