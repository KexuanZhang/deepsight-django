"""
Upload processing worker for DeepSight backend.

This worker handles heavy file processing operations that are too slow for immediate response:
- OCR processing for scanned documents
- Advanced audio processing and transcription
- Video processing and extraction
- Batch file conversions
- File format optimization
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
import asyncio
import io
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

# Set macOS safety environment variables
if sys.platform == 'darwin':
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from app.core.config import settings
from app.services.storage.file_storage import file_storage_service
from app.services.storage.content_index import content_indexing_service
from app.services.upload.file_validator import FileValidator

logger = logging.getLogger(__name__)


def process_ocr(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process OCR extraction for scanned documents"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting OCR processing for job {job_id}")
        upload_queue.update_job_progress(job_id, "Initializing OCR processing...", "processing")
        
        file_id = request_data.get("file_id")
        if not file_id:
            raise ValueError("file_id is required for OCR processing")
        
        # Get file from storage
        file_storage = file_storage_service
        file_path = asyncio.run(file_storage.get_file_path(file_id))
        file_metadata = asyncio.run(file_storage.get_file_metadata(file_id))
        
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_id}")
        
        upload_queue.update_job_progress(job_id, "Running OCR extraction...", "processing")
        
        # Process based on file type
        file_extension = file_metadata.get('file_extension', '').lower()
        
        if file_extension == '.pdf':
            result = _process_pdf_ocr(file_path, file_metadata, job_id)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            result = _process_image_ocr(file_path, file_metadata, job_id)
        else:
            raise ValueError(f"OCR not supported for file type: {file_extension}")
        
        upload_queue.update_job_progress(job_id, "Indexing OCR results...", "processing")
        
        # Update file storage with OCR results
        content_indexing = content_indexing_service
        asyncio.run(content_indexing.index_content(
            file_id=file_id,
            content=result['extracted_text'],
            metadata=file_metadata,
            processing_stage="ocr"
        ))
        
        # Update file storage with enhanced content
        asyncio.run(file_storage.update_file_content(
            file_id=file_id,
            content=result['extracted_text'],
            processing_result=result
        ))
        
        final_result = {
            "job_id": job_id,
            "file_id": file_id,
            "processing_type": "ocr",
            "extracted_text": result['extracted_text'],
            "confidence_score": result.get('confidence_score', 0.0),
            "page_count": result.get('page_count', 1),
            "processing_time": result.get('processing_time', 0),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"OCR processing completed successfully for job {job_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in OCR processing job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


def process_advanced_audio(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process advanced audio analysis and transcription"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting advanced audio processing for job {job_id}")
        upload_queue.update_job_progress(job_id, "Initializing audio processing...", "processing")
        
        file_id = request_data.get("file_id")
        if not file_id:
            raise ValueError("file_id is required for audio processing")
        
        # Get file from storage
        file_storage = file_storage_service
        file_path = asyncio.run(file_storage.get_file_path(file_id))
        file_metadata = asyncio.run(file_storage.get_file_metadata(file_id))
        
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_id}")
        
        upload_queue.update_job_progress(job_id, "Transcribing audio...", "processing")
        
        # Perform advanced audio processing
        result = _process_audio_transcription(file_path, file_metadata, job_id)
        
        upload_queue.update_job_progress(job_id, "Analyzing audio features...", "processing")
        
        # Add audio analysis
        audio_analysis = _analyze_audio_features(file_path, job_id)
        result.update(audio_analysis)
        
        upload_queue.update_job_progress(job_id, "Indexing transcription...", "processing")
        
        # Update file storage and indexing
        content_indexing = content_indexing_service
        asyncio.run(content_indexing.index_content(
            file_id=file_id,
            content=result['transcription'],
            metadata=file_metadata,
            processing_stage="advanced_audio"
        ))
        
        asyncio.run(file_storage.update_file_content(
            file_id=file_id,
            content=result['transcription'],
            processing_result=result
        ))
        
        final_result = {
            "job_id": job_id,
            "file_id": file_id,
            "processing_type": "advanced_audio",
            "transcription": result['transcription'],
            "language": result.get('language', 'unknown'),
            "confidence": result.get('confidence', 0.0),
            "duration": result.get('duration', 0.0),
            "audio_features": result.get('audio_features', {}),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Advanced audio processing completed successfully for job {job_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in advanced audio processing job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


def process_video(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process video files for metadata, frames, and audio extraction"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting video processing for job {job_id}")
        upload_queue.update_job_progress(job_id, "Initializing video processing...", "processing")
        
        file_id = request_data.get("file_id")
        if not file_id:
            raise ValueError("file_id is required for video processing")
        
        # Get file from storage
        file_storage = file_storage_service
        file_path = asyncio.run(file_storage.get_file_path(file_id))
        file_metadata = asyncio.run(file_storage.get_file_metadata(file_id))
        
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_id}")
        
        upload_queue.update_job_progress(job_id, "Extracting video metadata...", "processing")
        
        # Extract video metadata
        video_info = _extract_video_metadata(file_path, job_id)
        
        upload_queue.update_job_progress(job_id, "Extracting audio track...", "processing")
        
        # Extract audio if present
        audio_result = _extract_video_audio(file_path, job_id)
        if audio_result:
            video_info.update(audio_result)
        
        upload_queue.update_job_progress(job_id, "Generating video preview...", "processing")
        
        # Generate thumbnails/preview
        preview_result = _generate_video_preview(file_path, job_id)
        video_info.update(preview_result)
        
        # Combine all extracted content for indexing
        combined_content = ""
        if video_info.get('transcription'):
            combined_content += f"Audio Transcription:\n{video_info['transcription']}\n\n"
        if video_info.get('metadata'):
            combined_content += f"Video Metadata: {json.dumps(video_info['metadata'], indent=2)}"
        
        if combined_content:
            upload_queue.update_job_progress(job_id, "Indexing video content...", "processing")
            
            content_indexing = content_indexing_service
            asyncio.run(content_indexing.index_content(
                file_id=file_id,
                content=combined_content,
                metadata=file_metadata,
                processing_stage="video_processing"
            ))
            
            asyncio.run(file_storage.update_file_content(
                file_id=file_id,
                content=combined_content,
                processing_result=video_info
            ))
        
        final_result = {
            "job_id": job_id,
            "file_id": file_id,
            "processing_type": "video_processing",
            "video_info": video_info,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Video processing completed successfully for job {job_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in video processing job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


def process_batch_conversion(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process batch file format conversions"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting batch conversion for job {job_id}")
        upload_queue.update_job_progress(job_id, "Initializing batch conversion...", "processing")
        
        file_ids = request_data.get("file_ids", [])
        target_format = request_data.get("target_format")
        
        if not file_ids:
            raise ValueError("file_ids are required for batch conversion")
        if not target_format:
            raise ValueError("target_format is required for batch conversion")
        
        results = []
        file_storage = file_storage_service
        
        for i, file_id in enumerate(file_ids):
            upload_queue.update_job_progress(
                job_id, 
                f"Converting file {i+1} of {len(file_ids)}...", 
                "processing",
                int((i / len(file_ids)) * 100)
            )
            
            try:
                file_path = asyncio.run(file_storage.get_file_path(file_id))
                file_metadata = asyncio.run(file_storage.get_file_metadata(file_id))
                
                if file_path and os.path.exists(file_path):
                    conversion_result = _convert_file_format(file_path, target_format, file_metadata)
                    results.append({
                        "file_id": file_id,
                        "status": "success",
                        "result": conversion_result
                    })
                else:
                    results.append({
                        "file_id": file_id,
                        "status": "error",
                        "error": "File not found"
                    })
                    
            except Exception as e:
                logger.error(f"Error converting file {file_id}: {e}")
                results.append({
                    "file_id": file_id,
                    "status": "error",
                    "error": str(e)
                })
        
        successful_conversions = len([r for r in results if r["status"] == "success"])
        
        final_result = {
            "job_id": job_id,
            "processing_type": "batch_conversion",
            "target_format": target_format,
            "total_files": len(file_ids),
            "successful_conversions": successful_conversions,
            "failed_conversions": len(file_ids) - successful_conversions,
            "results": results,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Batch conversion completed for job {job_id}: {successful_conversions}/{len(file_ids)} successful")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in batch conversion job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


def process_generic_upload(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generic upload processing for unsupported specific operations"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting generic upload processing for job {job_id}")
        upload_queue.update_job_progress(job_id, "Processing upload...", "processing")
        
        file_id = request_data.get("file_id")
        processing_type = request_data.get("processing_type", "generic")
        
        # Basic file validation and metadata extraction
        file_storage = file_storage_service
        file_metadata = asyncio.run(file_storage.get_file_metadata(file_id))
        
        final_result = {
            "job_id": job_id,
            "file_id": file_id,
            "processing_type": processing_type,
            "status": "completed",
            "message": f"Generic processing completed for {processing_type}",
            "metadata": file_metadata,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Generic upload processing completed for job {job_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in generic upload processing job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


def process_batch_files(job_id: str, file_ids: List[str], processing_type: str) -> Dict[str, Any]:
    """Process multiple files in batch"""
    from app.services.queue_management.upload_queue_service import upload_queue
    
    try:
        logger.info(f"Starting batch file processing for job {job_id}")
        upload_queue.update_job_progress(job_id, f"Processing {len(file_ids)} files...", "processing")
        
        results = []
        file_storage = file_storage_service
        
        for i, file_id in enumerate(file_ids):
            upload_queue.update_job_progress(
                job_id,
                f"Processing file {i+1} of {len(file_ids)}...",
                "processing",
                int((i / len(file_ids)) * 100)
            )
            
            try:
                # Create individual request for each file
                individual_request = {
                    "file_id": file_id,
                    "processing_type": processing_type
                }
                
                # Process based on type
                if processing_type == "ocr":
                    result = process_ocr(f"{job_id}_{i}", individual_request)
                elif processing_type == "advanced_audio":
                    result = process_advanced_audio(f"{job_id}_{i}", individual_request)
                elif processing_type == "video_processing":
                    result = process_video(f"{job_id}_{i}", individual_request)
                else:
                    result = process_generic_upload(f"{job_id}_{i}", individual_request)
                
                results.append({
                    "file_id": file_id,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file_id} in batch: {e}")
                results.append({
                    "file_id": file_id,
                    "status": "error",
                    "error": str(e)
                })
        
        successful_processes = len([r for r in results if r["status"] == "success"])
        
        final_result = {
            "job_id": job_id,
            "processing_type": f"batch_{processing_type}",
            "total_files": len(file_ids),
            "successful_processes": successful_processes,
            "failed_processes": len(file_ids) - successful_processes,
            "results": results,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Batch processing completed for job {job_id}: {successful_processes}/{len(file_ids)} successful")
        return final_result
        
    except Exception as e:
        logger.error(f"Error in batch file processing job {job_id}: {e}")
        upload_queue.update_job_error(job_id, str(e))
        raise


# Helper functions for specific processing operations

def _process_pdf_ocr(file_path: str, file_metadata: Dict, job_id: str) -> Dict[str, Any]:
    """Process PDF with OCR using Tesseract"""
    try:
        import pytesseract
        import fitz  # PyMuPDF
        from PIL import Image
        
        doc = fitz.open(file_path)
        extracted_text = ""
        confidence_scores = []
        
        for page_num in range(doc.page_count):
            logger.debug(f"Processing page {page_num + 1} of {doc.page_count} for job {job_id}")
            
            page = doc[page_num]
            # Convert page to image
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            
            # Process with Tesseract
            image = Image.open(io.BytesIO(img_data))
            page_text = pytesseract.image_to_string(image)
            extracted_text += f"\n=== Page {page_num + 1} ===\n{page_text}\n"
            
            # Get confidence score
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                if confidences:
                    confidence_scores.append(sum(confidences) / len(confidences))
            except:
                confidence_scores.append(50.0)  # Default confidence
        
        doc.close()
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "extracted_text": extracted_text.strip(),
            "confidence_score": avg_confidence,
            "page_count": doc.page_count,
            "processing_time": 0  # Could add timing
        }
        
    except ImportError:
        raise Exception("OCR dependencies not installed. Please install pytesseract and PIL.")
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")


def _process_image_ocr(file_path: str, file_metadata: Dict, job_id: str) -> Dict[str, Any]:
    """Process image with OCR"""
    try:
        import pytesseract
        from PIL import Image
        
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image)
        
        # Get confidence
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        except:
            avg_confidence = 50.0
        
        return {
            "extracted_text": extracted_text.strip(),
            "confidence_score": avg_confidence,
            "page_count": 1,
            "processing_time": 0
        }
        
    except ImportError:
        raise Exception("OCR dependencies not installed. Please install pytesseract and PIL.")
    except Exception as e:
        raise Exception(f"Image OCR processing failed: {str(e)}")


def _process_audio_transcription(file_path: str, file_metadata: Dict, job_id: str) -> Dict[str, Any]:
    """Process audio transcription using Whisper"""
    try:
        import whisper
        
        # Load Whisper model
        model = whisper.load_model("base")
        
        # Transcribe
        result = model.transcribe(file_path)
        
        return {
            "transcription": result["text"],
            "language": result.get("language", "unknown"),
            "confidence": 0.85,  # Whisper doesn't provide confidence, use default
            "segments": result.get("segments", [])
        }
        
    except ImportError:
        raise Exception("Whisper not installed. Please install openai-whisper.")
    except Exception as e:
        raise Exception(f"Audio transcription failed: {str(e)}")


def _analyze_audio_features(file_path: str, job_id: str) -> Dict[str, Any]:
    """Analyze audio features like duration, format, etc."""
    try:
        import subprocess
        
        # Use ffprobe to get audio info
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            format_info = info.get('format', {})
            
            return {
                "audio_features": {
                    "duration": float(format_info.get('duration', 0)),
                    "bit_rate": format_info.get('bit_rate'),
                    "format_name": format_info.get('format_name'),
                    "size": format_info.get('size')
                }
            }
        else:
            return {"audio_features": {}}
            
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return {"audio_features": {}}
    except Exception as e:
        logger.warning(f"Audio feature analysis failed: {e}")
        return {"audio_features": {}}


def _extract_video_metadata(file_path: str, job_id: str) -> Dict[str, Any]:
    """Extract video metadata using ffprobe"""
    try:
        import subprocess
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return {"metadata": info}
        else:
            return {"metadata": {}}
            
    except Exception as e:
        logger.warning(f"Video metadata extraction failed: {e}")
        return {"metadata": {}}


def _extract_video_audio(file_path: str, job_id: str) -> Dict[str, Any]:
    """Extract audio track from video and transcribe"""
    try:
        import subprocess
        import tempfile
        
        # Extract audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            cmd = [
                'ffmpeg', '-i', file_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', temp_audio.name, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(temp_audio.name):
                # Transcribe the extracted audio
                transcription_result = _process_audio_transcription(temp_audio.name, {}, job_id)
                
                # Clean up temp file
                os.unlink(temp_audio.name)
                
                return transcription_result
            else:
                if os.path.exists(temp_audio.name):
                    os.unlink(temp_audio.name)
                return {}
                
    except Exception as e:
        logger.warning(f"Video audio extraction failed: {e}")
        return {}


def _generate_video_preview(file_path: str, job_id: str) -> Dict[str, Any]:
    """Generate video thumbnails/preview"""
    try:
        import subprocess
        
        # Generate a single thumbnail at 10% of video duration
        output_path = f"/tmp/thumb_{job_id}.jpg"
        
        cmd = [
            'ffmpeg', '-i', file_path, '-ss', '00:00:10',
            '-vframes', '1', '-q:v', '2', output_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return {"preview_generated": True, "thumbnail_path": output_path}
        else:
            return {"preview_generated": False}
            
    except Exception as e:
        logger.warning(f"Video preview generation failed: {e}")
        return {"preview_generated": False}


def _convert_file_format(file_path: str, target_format: str, file_metadata: Dict) -> Dict[str, Any]:
    """Convert file to target format"""
    try:
        # This is a placeholder for file format conversion
        # Implementation would depend on the specific formats supported
        
        source_format = file_metadata.get('file_extension', '').lower()
        
        return {
            "source_format": source_format,
            "target_format": target_format,
            "status": "conversion_not_implemented",
            "message": f"Conversion from {source_format} to {target_format} is not yet implemented"
        }
        
    except Exception as e:
        raise Exception(f"File conversion failed: {str(e)}") 