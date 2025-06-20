import os
import sys
import json
import logging
import tempfile
import multiprocessing
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# CRITICAL: Set comprehensive macOS forking safety environment variables
# These MUST be set before ANY imports that might trigger problematic libraries
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

# Additional macOS safety measures for various libraries
if sys.platform == 'darwin':
    # PyTorch/OpenMP related
    os.environ['PYTHONDEVMODE'] = '0'
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    
    # Prevent multiprocessing from using problematic methods
    os.environ['MULTIPROCESSING_START_METHOD'] = 'spawn'
    
    # OpenCV related (if used)
    os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'
    
    # CLIP/Vision model related
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Disable problematic TensorFlow/MLX behaviors on macOS
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    
    # Set multiprocessing start method early
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # start_method already set, that's fine
        pass

# Import application modules after environment setup
from app.core.config import settings
from app.services.storage.file_storage import file_storage_service
from app.services.extraction.url_extractor import url_feature_extractor
from app.models.reports import JobStatus

logger = logging.getLogger(__name__)

def process_report_generation(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main worker function for processing report generation jobs.
    This function is executed by RQ workers.
    
    Enhanced for macOS compatibility with comprehensive environment safety.
    """
    # Import here to avoid circular imports
    from app.services.queue_management.report_queue_service import report_queue
    
    try:
        logger.info(f"Starting report generation job {job_id} on platform: {sys.platform}")
        logger.info(f"Environment safety vars set: OBJC_DISABLE_INITIALIZE_FORK_SAFETY={os.environ.get('OBJC_DISABLE_INITIALIZE_FORK_SAFETY')}")
        
        # Update job status to running
        report_queue.update_job_progress(
            job_id, 
            "Initializing report generation...", 
            JobStatus.RUNNING
        )
        
        # Create output directory for this job
        job_output_dir = Path(settings.reports_output_dir) / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process the request using direct import (no subprocess)
        result = generate_report_direct(job_id, request_data, job_output_dir)
        
        # Update job with final result
        report_queue.update_job_result(job_id, result, JobStatus.COMPLETED)
        
        logger.info(f"Report generation job {job_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Report generation failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}", exc_info=True)
        
        # Update job with error
        report_queue.update_job_error(job_id, error_msg)
        
        # Re-raise for RQ to handle
        raise


def generate_report_direct(job_id: str, request_data: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Generate report using direct import of DeepReportGenerator (no subprocess)
    Enhanced with comprehensive macOS compatibility and library-specific safety.
    """
    # Import here to avoid circular imports
    from app.services.queue_management.report_queue_service import report_queue
    
    try:
        logger.info(f"Starting direct report generation for job {job_id}")
        
        # Add deep_researcher_agent to Python path
        deep_researcher_path = settings.deep_researcher_dir
        if str(deep_researcher_path) not in sys.path:
            sys.path.insert(0, str(deep_researcher_path))
        
        # Log library-specific safety measures
        logger.info(f"macOS safety env vars: OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')}, "
                   f"KMP_DUPLICATE_LIB_OK={os.environ.get('KMP_DUPLICATE_LIB_OK')}, "
                   f"MULTIPROCESSING_START_METHOD={os.environ.get('MULTIPROCESSING_START_METHOD')}")
        
        # Import the report generator classes with enhanced error handling
        try:
            # These imports might trigger PyTorch/CLIP/other problematic libraries
            logger.info("Importing report generator modules (this may take a moment on macOS)...")
            from deep_report_generator import (
                DeepReportGenerator, 
                ReportGenerationConfig,
                ModelProvider,
                RetrieverType,
                TimeRange
            )
            from prompts import PromptType
            logger.info("Successfully imported report generator modules")
        except ImportError as e:
            logger.error(f"Failed to import report generator modules: {e}")
            raise Exception(f"Report generator import failed: {e}")
        
        # Update progress
        report_queue.update_job_progress(job_id, "Preparing configuration...")
        
        # Prepare input data from knowledge base if needed
        input_data = prepare_input_data(job_id, request_data)
        
        # Add input data to request_data for configuration
        enhanced_request_data = request_data.copy()
        enhanced_request_data["input_data"] = input_data
        
        # Create configuration
        config = create_report_config_direct(job_id, enhanced_request_data, output_dir)
        
        # Update progress
        report_queue.update_job_progress(job_id, "Starting report generator...")
        
        # Create report generator instance with error handling
        try:
            logger.info("Initializing DeepReportGenerator...")
            generator = DeepReportGenerator(secrets_path=str(settings.secrets_path))
            logger.info("DeepReportGenerator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeepReportGenerator: {e}")
            raise Exception(f"Generator initialization failed: {e}")
        
        # Generate the report
        report_queue.update_job_progress(job_id, "Generating report content...")
        
        try:
            logger.info("Starting report generation process...")
            result = generator.generate_report(config)
            logger.info("Report generation process completed")
        except Exception as e:
            logger.error(f"Report generation failed during generation: {e}", exc_info=True)
            raise Exception(f"Report generation process failed: {e}")
        
        if not result.success:
            error_msg = result.error_message or "Report generation failed without specific error"
            logger.error(f"Report generation unsuccessful: {error_msg}")
            raise Exception(error_msg)
        
        # Convert result to dictionary format expected by the API
        api_result = {
            "success": result.success,
            "job_id": job_id,
            "article_title": result.article_title,
            "output_directory": result.output_directory,
            "generated_files": result.generated_files,
            "main_report_file": find_main_report_file(result.generated_files),
            "processing_logs": result.processing_logs or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Report generation completed successfully for job {job_id}")
        return api_result
        
    except Exception as e:
        logger.error(f"Error in generate_report_direct for job {job_id}: {e}", exc_info=True)
        raise


def create_report_config_direct(job_id: str, request_data: Dict[str, Any], output_dir: Path) -> 'ReportGenerationConfig':
    """
    Create ReportGenerationConfig object from request data
    Enhanced with better validation and error handling.
    """
    try:
        # Import the classes we need
        from deep_report_generator import (
            ReportGenerationConfig,
            ModelProvider,
            RetrieverType,
            TimeRange
        )
        from prompts import PromptType
    except ImportError as e:
        logger.error(f"Failed to import configuration classes: {e}")
        raise Exception(f"Configuration import failed: {e}")
    
    # Map string values to enum values with error handling
    model_provider_map = {
        "openai": ModelProvider.OPENAI,
        "google": ModelProvider.GOOGLE
    }
    
    retriever_map = {
        "tavily": RetrieverType.TAVILY,
        "brave": RetrieverType.BRAVE,
        "serper": RetrieverType.SERPER,
        "you": RetrieverType.YOU,
        "bing": RetrieverType.BING,
        "duckduckgo": RetrieverType.DUCKDUCKGO,
        "searxng": RetrieverType.SEARXNG,
        "azure_ai_search": RetrieverType.AZURE_AI_SEARCH
    }
    
    time_range_map = {
        "day": TimeRange.DAY,
        "week": TimeRange.WEEK,
        "month": TimeRange.MONTH,
        "year": TimeRange.YEAR
    }
    
    prompt_type_map = {
        "general": PromptType.GENERAL,
        "financial": PromptType.FINANCIAL
    }
    
    # Create configuration with validation
    try:
        config = ReportGenerationConfig(
            # Basic settings
            topic=request_data.get("topic"),
            article_title=request_data.get("article_title", "Research Report"),
            output_dir=str(output_dir),
            model_provider=model_provider_map.get(request_data.get("model_provider", "openai"), ModelProvider.OPENAI),
            retriever=retriever_map.get(request_data.get("retriever", "tavily"), RetrieverType.TAVILY),
            temperature=request_data.get("temperature", 0.2),
            top_p=request_data.get("top_p", 0.4),
            prompt_type=prompt_type_map.get(request_data.get("prompt_type", "general"), PromptType.GENERAL),
            
            # Generation flags
            do_research=request_data.get("do_research", True),
            do_generate_outline=request_data.get("do_generate_outline", True),
            do_generate_article=request_data.get("do_generate_article", True),
            do_polish_article=request_data.get("do_polish_article", True),
            remove_duplicate=request_data.get("remove_duplicate", True),
            post_processing=request_data.get("post_processing", True),
            
            # Search and generation parameters
            max_conv_turn=request_data.get("max_conv_turn", 3),
            max_perspective=request_data.get("max_perspective", 3),
            search_top_k=request_data.get("search_top_k", 10),
            initial_retrieval_k=request_data.get("initial_retrieval_k", 150),
            final_context_k=request_data.get("final_context_k", 20),
            reranker_threshold=request_data.get("reranker_threshold", 0.5),
            max_thread_num=request_data.get("max_thread_num", 10),
            
            # Optional parameters
            time_range=time_range_map.get(request_data.get("time_range")) if request_data.get("time_range") else None,
            include_domains=request_data.get("include_domains", False),
            skip_rewrite_outline=request_data.get("skip_rewrite_outline", False),
            
            # CSV processing
            csv_session_code=request_data.get("csv_session_code"),
            csv_date_filter=request_data.get("csv_date_filter"),
            
            # Video processing
            video_url=request_data.get("video_url"),
            video_path=request_data.get("video_path")
        )
    except Exception as e:
        logger.error(f"Failed to create report configuration: {e}")
        raise Exception(f"Configuration creation failed: {e}")
    
    # Process knowledge base content if provided
    input_data = request_data.get("input_data", {})
    
    # Handle file content
    if input_data.get("files_content"):
        try:
            # For now, we'll create temporary files for the content
            # In the future, this could be optimized to pass content directly
            temp_files = []
            for file_data in input_data["files_content"]:
                content = file_data.get("content", "")
                filename = file_data.get("filename", "file.txt")
                
                # Create temporary file with .md extension (deep_report_generator only accepts .txt or .md)
                safe_filename = filename.replace(" ", "_").replace("/", "_")
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f"_{safe_filename}.md", delete=False)
                temp_file.write(content)
                temp_file.close()
                temp_files.append(temp_file.name)
            
            if temp_files:
                if file_data.get("type") == "paper":
                    config.paper_path = temp_files
                else:
                    config.transcript_path = temp_files
        except Exception as e:
            logger.error(f"Failed to process file content: {e}")
            # Don't fail the entire job for this, just log the error
    
    return config


def find_main_report_file(generated_files: List[str]) -> Optional[str]:
    """
    Find the main report file from the list of generated files
    """
    for filename in generated_files:
        basename = os.path.basename(filename)
        if basename.endswith(('.md', '.html', '.pdf')) and 'polished' in basename.lower():
            return basename
        elif basename.endswith(('.md', '.html', '.pdf')) and 'report' in basename.lower():
            return basename
    
    # Fallback to any markdown file
    for filename in generated_files:
        if filename.endswith('.md'):
            return os.path.basename(filename)
    
    return None


def prepare_input_data(job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare input data from knowledge base files and URLs
    """
    from app.services.queue_management.report_queue_service import report_queue
    
    input_data = {
        "files_content": [],
        "urls_content": [],
        "video_content": None
    }
    
    file_storage = file_storage_service
    url_extractor = url_feature_extractor
    
    # Process selected files from knowledge base
    selected_file_ids = request_data.get("selected_file_ids", [])
    if selected_file_ids:
        report_queue.update_job_progress(job_id, f"Loading {len(selected_file_ids)} files from knowledge base...")
        
        for file_id in selected_file_ids:
            try:
                # Use asyncio.run for sync context since this worker function isn't async
                content = asyncio.run(file_storage.get_file_content(file_id))
                metadata = asyncio.run(file_storage.get_file_metadata(file_id))
                
                if content and metadata:
                    file_data = {
                        "id": file_id,
                        "filename": metadata.get("original_filename", "Unknown"),
                        "content": content,
                        "type": get_content_type(metadata.get("file_extension", "")),
                        "metadata": metadata
                    }
                    input_data["files_content"].append(file_data)
                    logger.info(f"Loaded file {file_id} for job {job_id}")
                else:
                    logger.warning(f"Could not load file {file_id} for job {job_id}")
                    
            except Exception as e:
                logger.error(f"Error loading file {file_id} for job {job_id}: {e}")
    
    # Process selected URLs from knowledge base
    selected_url_ids = request_data.get("selected_url_ids", [])
    if selected_url_ids:
        report_queue.update_job_progress(job_id, f"Loading {len(selected_url_ids)} URLs from knowledge base...")
        
        for url_id in selected_url_ids:
            try:
                content = asyncio.run(url_extractor.get_url_content(url_id))
                metadata = asyncio.run(url_extractor.get_url_metadata(url_id))
                
                if content and metadata:
                    url_data = {
                        "id": url_id,
                        "url": metadata.get("source_url", "Unknown"),
                        "content": content,
                        "type": "web_content",
                        "metadata": metadata
                    }
                    input_data["urls_content"].append(url_data)
                    logger.info(f"Loaded URL {url_id} for job {job_id}")
                else:
                    logger.warning(f"Could not load URL {url_id} for job {job_id}")
                    
            except Exception as e:
                logger.error(f"Error loading URL {url_id} for job {job_id}: {e}")
    
    # Process video URL if provided (for transcript generation)
    video_url = request_data.get("video_url")
    if video_url:
        report_queue.update_job_progress(job_id, "Processing video URL for transcript...")
        input_data["video_content"] = {
            "url": video_url,
            "type": "video_url"
        }
    
    # Process video file path if provided
    video_path = request_data.get("video_path")
    if video_path:
        report_queue.update_job_progress(job_id, "Processing video file for transcript...")
        input_data["video_content"] = {
            "path": video_path,
            "type": "video_file"
        }
    
    return input_data


def get_content_type(file_extension: str) -> str:
    """
    Determine content type based on file extension
    """
    ext = file_extension.lower()
    if ext == '.pdf':
        return 'paper'
    elif ext in ['.mp3', '.mp4', '.wav', '.m4a']:
        return 'transcript'
    elif ext in ['.txt', '.md']:
        return 'text'
    elif ext in ['.pptx', '.ppt']:
        return 'presentation'
    else:
        return 'other' 