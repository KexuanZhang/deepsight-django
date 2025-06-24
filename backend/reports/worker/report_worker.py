import os
import sys
import json
import logging
import tempfile
import multiprocessing
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# CRITICAL: Set comprehensive macOS forking safety environment variables
# These MUST be set before ANY imports that might trigger problematic libraries
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Additional macOS safety measures for various libraries
if sys.platform == "darwin":
    # PyTorch/OpenMP related
    os.environ["PYTHONDEVMODE"] = "0"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    # Prevent multiprocessing from using problematic methods
    os.environ["MULTIPROCESSING_START_METHOD"] = "spawn"

    # OpenCV related (if used)
    os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

    # CLIP/Vision model related
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Disable problematic TensorFlow/MLX behaviors on macOS
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    # Set multiprocessing start method early
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        # start_method already set, that's fine
        pass

# Django imports
import django
from django.conf import settings
from django.core.files.base import ContentFile

# Initialize Django if not already done
if not hasattr(settings, "DATABASES"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    django.setup()

from reports.models import Report
from reports.queue_service import report_queue_service
from notebooks.utils.file_storage import file_storage_service

logger = logging.getLogger(__name__)


def process_report_generation(report_id: int) -> Dict[str, Any]:
    """
    Main worker function for processing report generation jobs in Django.
    This function is executed by Django-RQ workers.
    """
    try:
        logger.info(
            f"Starting report generation for report {report_id} on platform: {sys.platform}"
        )

        # Get the report from database
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            error_msg = f"Report {report_id} not found"
            logger.error(error_msg)
            raise Exception(error_msg)

        # Update job status to running
        report.update_status(
            Report.STATUS_RUNNING, progress="Initializing report generation..."
        )

        # Create output directory following new storage structure
        from notebooks.utils.config import storage_config

        current_date = datetime.now()
        year_month = current_date.strftime('%Y-%m')
        
        # Get notebook_id if the report is associated with a notebook
        notebook_id = None
        if hasattr(report, 'notebooks') and report.notebooks:
            notebook_id = report.notebooks.pk
        
        job_output_dir = storage_config.get_report_path(
            user_id=report.user.pk,
            year_month=year_month,
            report_id=str(report.id),
            notebook_id=notebook_id  # Pass notebook_id to ensure correct path structure
        )

        # Clean the output directory to prevent duplicate files
        if job_output_dir.exists():
            try:
                import shutil

                # Remove existing directory and recreate it to ensure clean state
                shutil.rmtree(job_output_dir)
                logger.info(f"Cleaned existing output directory: {job_output_dir}")
            except Exception as e:
                logger.warning(
                    f"Could not clean output directory {job_output_dir}: {e}"
                )

        job_output_dir.mkdir(parents=True, exist_ok=True)

        # Process the request using direct import (no subprocess)
        result = generate_report_direct(report, job_output_dir)

        # Update job with final result
        report_queue_service.update_job_result(
            report.job_id, result, Report.STATUS_COMPLETED
        )

        logger.info(f"Report generation for report {report_id} completed successfully")
        return result

    except Exception as e:
        error_msg = f"Report generation failed: {str(e)}"
        logger.error(f"Report {report_id} failed: {error_msg}", exc_info=True)

        # Update job with error
        try:
            report = Report.objects.get(id=report_id)
            report_queue_service.update_job_error(report.job_id, error_msg)
        except Report.DoesNotExist:
            logger.error(
                f"Could not update error for report {report_id} - report not found"
            )

        # Re-raise for RQ to handle
        raise


def generate_report_direct(report: Report, output_dir: Path) -> Dict[str, Any]:
    """
    Generate report using direct import of DeepReportGenerator.
    Adapted for Django models and storage system.
    """
    try:
        logger.info(f"Starting direct report generation for report {report.id}")

        # Add deep_researcher_agent to Python path
        deep_researcher_path = (
            Path(__file__).parent.parent.parent / "deep_researcher_agent"
        )
        if str(deep_researcher_path) not in sys.path:
            sys.path.insert(0, str(deep_researcher_path))

        # Log library-specific safety measures
        logger.info(
            f"macOS safety env vars: OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')}, "
            f"KMP_DUPLICATE_LIB_OK={os.environ.get('KMP_DUPLICATE_LIB_OK')}"
        )

        # Import the report generator classes
        try:
            logger.info("Importing report generator modules...")
            from deep_report_generator import (
                DeepReportGenerator,
                ReportGenerationConfig,
                ModelProvider,
                RetrieverType,
                TimeRange,
            )
            from prompts import PromptType

            logger.info("Successfully imported report generator modules")
        except ImportError as e:
            logger.error(f"Failed to import report generator modules: {e}")
            raise Exception(f"Report generator import failed: {e}")

        # Update progress
        report_queue_service.update_job_progress(
            report.job_id, "Preparing configuration..."
        )

        # Prepare input data from knowledge base if needed
        input_data = prepare_input_data(report)

        # Create configuration
        config = create_report_config_direct(report, input_data, output_dir)

        # Update progress
        report_queue_service.update_job_progress(
            report.job_id, "Starting report generator..."
        )

        # Create report generator instance
        try:
            logger.info("Initializing DeepReportGenerator...")
            # Look for secrets.toml in the backend directory (correct location)
            backend_path = Path(
                __file__
            ).parent.parent.parent  # Go up from worker -> reports -> backend
            secrets_path = backend_path / "secrets.toml"

            # Check if secrets.toml exists in the expected location
            if not secrets_path.exists():
                logger.warning(
                    f"secrets.toml not found at {secrets_path}, trying deep_researcher_agent directory..."
                )
                # Fallback to the original location
                secrets_path = deep_researcher_path / "secrets.toml"

            logger.info(f"Using secrets.toml from: {secrets_path}")
            generator = DeepReportGenerator(secrets_path=str(secrets_path))
            logger.info("DeepReportGenerator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeepReportGenerator: {e}")
            raise Exception(f"Generator initialization failed: {e}")

        # Generate the report
        report_queue_service.update_job_progress(
            report.job_id, "Generating report content..."
        )

        try:
            logger.info("Starting report generation process...")
            result = generator.generate_report(config)
            logger.info("Report generation process completed")
        except Exception as e:
            logger.error(
                f"Report generation failed during generation: {e}", exc_info=True
            )
            raise Exception(f"Report generation process failed: {e}")

        if not result.success:
            error_msg = (
                result.error_message
                or "Report generation failed without specific error"
            )
            logger.error(f"Report generation unsuccessful: {error_msg}")
            raise Exception(error_msg)

        # Store the generated files using Django's file system
        stored_files = store_generated_files(report, result, output_dir)

        # Convert result to dictionary format expected by the API
        api_result = {
            "success": result.success,
            "report_id": report.id,
            "job_id": report.job_id,
            "article_title": result.article_title,
            "output_directory": str(output_dir),
            "generated_files": stored_files,
            "main_report_file": find_main_report_file(stored_files),
            "processing_logs": result.processing_logs or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store the main report content in the database
        if result.success and hasattr(result, "report_content"):
            api_result["report_content"] = result.report_content

        logger.info(f"Report generation completed successfully for report {report.id}")
        return api_result

    except Exception as e:
        logger.error(
            f"Error in generate_report_direct for report {report.id}: {e}",
            exc_info=True,
        )
        raise


def create_report_config_direct(
    report: Report, input_data: Dict[str, Any], output_dir: Path
) -> "ReportGenerationConfig":
    """
    Create ReportGenerationConfig object from Django Report model.
    """
    try:
        # Import the classes we need
        from deep_report_generator import (
            ReportGenerationConfig,
            ModelProvider,
            RetrieverType,
            TimeRange,
        )
        from prompts import PromptType
    except ImportError as e:
        logger.error(f"Failed to import configuration classes: {e}")
        raise Exception(f"Configuration import failed: {e}")

    # Map string values to enum values
    model_provider_map = {
        "openai": ModelProvider.OPENAI,
        "google": ModelProvider.GOOGLE,
    }

    retriever_map = {
        "tavily": RetrieverType.TAVILY,
        "brave": RetrieverType.BRAVE,
        "serper": RetrieverType.SERPER,
        "you": RetrieverType.YOU,
        "bing": RetrieverType.BING,
        "duckduckgo": RetrieverType.DUCKDUCKGO,
        "searxng": RetrieverType.SEARXNG,
        "azure_ai_search": RetrieverType.AZURE_AI_SEARCH,
    }

    time_range_map = {
        "day": TimeRange.DAY,
        "week": TimeRange.WEEK,
        "month": TimeRange.MONTH,
        "year": TimeRange.YEAR,
    }

    prompt_type_map = {"general": PromptType.GENERAL, "financial": PromptType.FINANCIAL}

    # Create configuration
    try:
        # Handle old_outline_path if old_outline content is provided
        old_outline_path = None
        if report.old_outline and report.old_outline.strip():
            # Create a temporary file for the old outline content
            temp_outline_file = tempfile.NamedTemporaryFile(
                mode="w", suffix="_old_outline.txt", delete=False
            )
            temp_outline_file.write(report.old_outline)
            temp_outline_file.close()
            old_outline_path = temp_outline_file.name
            logger.info(f"Created temporary old outline file: {old_outline_path}")

        config = ReportGenerationConfig(
            # Basic settings
            topic=report.topic,
            article_title=report.article_title,
            output_dir=str(output_dir),
            model_provider=model_provider_map.get(
                report.model_provider, ModelProvider.OPENAI
            ),
            retriever=retriever_map.get(report.retriever, RetrieverType.TAVILY),
            temperature=report.temperature,
            top_p=report.top_p,
            prompt_type=prompt_type_map.get(report.prompt_type, PromptType.GENERAL),
            # Generation flags
            do_research=report.do_research,
            do_generate_outline=report.do_generate_outline,
            do_generate_article=report.do_generate_article,
            do_polish_article=report.do_polish_article,
            remove_duplicate=report.remove_duplicate,
            post_processing=report.post_processing,
            # Search and generation parameters
            max_conv_turn=report.max_conv_turn,
            max_perspective=report.max_perspective,
            search_top_k=report.search_top_k,
            initial_retrieval_k=report.initial_retrieval_k,
            final_context_k=report.final_context_k,
            reranker_threshold=report.reranker_threshold,
            max_thread_num=report.max_thread_num,
            # Optional parameters
            time_range=time_range_map.get(report.time_range)
            if report.time_range
            else None,
            include_domains=report.include_domains,
            skip_rewrite_outline=report.skip_rewrite_outline,
            whitelist_domains=report.domain_list if report.domain_list else None,
            search_depth=report.search_depth,
            old_outline_path=old_outline_path,
            # Image path fixing
            selected_files_paths=report.selected_files_paths,
            # CSV processing
            csv_session_code=report.csv_session_code,
            csv_date_filter=report.csv_date_filter,
        )
    except Exception as e:
        logger.error(f"Failed to create report configuration: {e}")
        raise Exception(f"Configuration creation failed: {e}")

    # Process knowledge base content if provided
    if input_data.get("paper_files") or input_data.get("transcript_files"):
        try:
            # Process paper files
            if input_data.get("paper_files"):
                paper_temp_files = []
                for paper_file in input_data["paper_files"]:
                    content = paper_file.get("content", "")
                    filename = paper_file.get("filename", "paper.md")

                    if content.strip():  # Only process non-empty content
                        # Create temporary file for paper content
                        safe_filename = filename.replace(" ", "_").replace("/", "_")
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=f"_{safe_filename}", delete=False
                        ) as tmp_file:
                            tmp_file.write(content)
                            paper_temp_files.append(tmp_file.name)
                            logger.info(f"Created temp paper file: {tmp_file.name}")

                if paper_temp_files:
                    config.paper_path = paper_temp_files
                    logger.info(f"Added {len(paper_temp_files)} paper files to config")

            # Process transcript files
            if input_data.get("transcript_files"):
                transcript_temp_files = []
                for transcript_file in input_data["transcript_files"]:
                    content = transcript_file.get("content", "")
                    filename = transcript_file.get("filename", "transcript.md")

                    if content.strip():  # Only process non-empty content
                        # Create temporary file for transcript content
                        safe_filename = filename.replace(" ", "_").replace("/", "_")
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=f"_{safe_filename}", delete=False
                        ) as tmp_file:
                            tmp_file.write(content)
                            transcript_temp_files.append(tmp_file.name)
                            logger.info(
                                f"Created temp transcript file: {tmp_file.name}"
                            )

                if transcript_temp_files:
                    config.transcript_path = transcript_temp_files
                    logger.info(
                        f"Added {len(transcript_temp_files)} transcript files to config"
                    )

            # Process caption files
            if input_data.get("caption_files"):
                config.caption_files = input_data["caption_files"]
                logger.info(
                    f"Added {len(input_data['caption_files'])} caption files to config"
                )

        except Exception as e:
            logger.error(f"Failed to process input files: {e}")
            # Don't fail the entire job for this, just log the error

    return config


def prepare_input_data(report: Report) -> Dict[str, Any]:
    """
    Prepare input data from the knowledge base based on selected file folder paths.
    Looks for _transcript.md and other relevant files in the provided folder paths.
    """
    input_data = {"paper_files": [], "transcript_files": [], "caption_files": []}

    try:
        # Process selected file folder paths
        if report.selected_files_paths:
            for folder_path in report.selected_files_paths:
                try:
                    folder_path_obj = Path(folder_path)
                    if not folder_path_obj.exists() or not folder_path_obj.is_dir():
                        logger.warning(
                            f"Folder path does not exist or is not a directory: {folder_path}"
                        )
                        continue

                    # Look for transcript files (both in root and subdirectories)
                    transcript_files = list(
                        folder_path_obj.glob("*_transcript.md")
                    ) + list(folder_path_obj.glob("**/*_transcript.md"))
                    for transcript_file in transcript_files:
                        try:
                            with open(transcript_file, "r", encoding="utf-8") as f:
                                content = f.read()

                            file_data = {
                                "content": content,
                                "filename": transcript_file.name,
                                "file_path": str(transcript_file),
                            }
                            input_data["transcript_files"].append(file_data)
                            logger.info(f"Loaded transcript file: {transcript_file}")
                        except Exception as e:
                            logger.warning(
                                f"Failed to read transcript file {transcript_file}: {e}"
                            )

                    # Look for other .md files (all non-transcript .md files are treated as paper files)
                    # Search both in root directory and subdirectories
                    all_md_files = list(folder_path_obj.glob("*.md")) + list(
                        folder_path_obj.glob("**/*.md")
                    )
                    other_md_files = [
                        f for f in all_md_files if not f.name.endswith("_transcript.md")
                    ]
                    for md_file in other_md_files:
                        try:
                            with open(md_file, "r", encoding="utf-8") as f:
                                content = f.read()

                            file_data = {
                                "content": content,
                                "filename": md_file.name,
                                "file_path": str(md_file),
                            }

                            # All .md files that are not _transcript.md are treated as paper files
                            input_data["paper_files"].append(file_data)
                            logger.info(f"Loaded paper file: {md_file}")
                        except Exception as e:
                            logger.warning(f"Failed to read file {md_file}: {e}")

                    # Look for caption files (JSON files with video metadata) in root and subdirectories
                    caption_files = list(folder_path_obj.glob("*.json")) + list(
                        folder_path_obj.glob("**/*.json")
                    )
                    for caption_file in caption_files:
                        if "caption" in caption_file.name.lower():
                            input_data["caption_files"].append(str(caption_file))
                            logger.info(f"Found caption file: {caption_file}")

                except Exception as e:
                    logger.warning(f"Failed to process folder path {folder_path}: {e}")
                    continue

        logger.info(
            f"Prepared input data: {len(input_data['paper_files'])} papers, "
            f"{len(input_data['transcript_files'])} transcripts, "
            f"{len(input_data['caption_files'])} caption files"
        )

        return input_data

    except Exception as e:
        logger.error(f"Error preparing input data for report {report.id}: {e}")
        return input_data


def store_generated_files(report: Report, result, output_dir: Path) -> List[str]:
    """
    Store generated files using Django's file storage system.
    All files are stored directly in the r_{report_id} folder without any subfolders.
    Returns list of stored file paths.
    """
    stored_files = []

    try:
        if result.generated_files:
            for file_path in result.generated_files:
                try:
                    source_path = Path(file_path)
                    if source_path.exists() and source_path.is_file():
                        filename = source_path.name

                        # Note: Image path fixing is now done directly in storm_gen_article.md and storm_gen_article_polished.md
                        # during generation, so we no longer need to apply it during file storage
                        if source_path.name.endswith(".md") and (
                            "polished" in source_path.name.lower()
                            or "report" in source_path.name.lower()
                        ):
                            logger.info(
                                f"File {source_path.name} already has image paths fixed during generation"
                            )

                        # Check if this is a final Report file that's already in the output directory
                        if filename.startswith("Report_r_") and filename.endswith(
                            ".md"
                        ):
                            # The deep_report_generator already created this file in the output directory
                            # Don't duplicate it in Django storage, just record the path
                            notebook_id = report.notebooks.pk if report.notebooks else None
                            if notebook_id:
                                relative_path = f"Users/u_{report.user.pk}/n_{notebook_id}/report/{datetime.now().strftime('%Y-%m')}/r_{report.id}/{filename}"
                            else:
                                relative_path = f"Users/u_{report.user.pk}/report/{datetime.now().strftime('%Y-%m')}/r_{report.id}/{filename}"
                            stored_files.append(relative_path)
                            logger.info(
                                f"Report file already exists in output directory: {filename}"
                            )
                        else:
                            # For non-Report files (storm_gen_*.md, etc.), store them normally
                            # Read the file content
                            with open(source_path, "rb") as f:
                                file_content = f.read()

                            # Create a ContentFile
                            django_file = ContentFile(file_content)

                            # Record the path relative to the report folder (directly in r_{report_id})
                            notebook_id = report.notebooks.pk if report.notebooks else None
                            if notebook_id:
                                relative_path = f"Users/u_{report.user.pk}/n_{notebook_id}/report/{datetime.now().strftime('%Y-%m')}/r_{report.id}/{filename}"
                            else:
                                relative_path = f"Users/u_{report.user.pk}/report/{datetime.now().strftime('%Y-%m')}/r_{report.id}/{filename}"
                            stored_files.append(relative_path)
                            logger.info(
                                f"Stored file directly in report folder: {filename}"
                            )

                except Exception as e:
                    logger.warning(f"Failed to store file {file_path}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error storing generated files for report {report.id}: {e}")

    return stored_files


def find_main_report_file(generated_files: List[str]) -> Optional[str]:
    """
    Find the main report file from the list of generated files.
    """
    for filename in generated_files:
        basename = os.path.basename(filename)
        if (
            basename.endswith((".md", ".html", ".pdf"))
            and "polished" in basename.lower()
        ):
            return basename
        elif (
            basename.endswith((".md", ".html", ".pdf")) and "report" in basename.lower()
        ):
            return basename

    # Fallback to any markdown file
    for filename in generated_files:
        if filename.endswith(".md"):
            return os.path.basename(filename)

    return None
