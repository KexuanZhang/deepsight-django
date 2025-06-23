import os
import sys

if sys.platform == 'darwin':  # macOS
    # Core macOS forking safety
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

    # PyTorch/OpenMP/MKL safety
    os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('MKL_NUM_THREADS', '1')
    os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

    # Disable MPS completely due to Metal Performance Shaders kernel compilation issues
    os.environ.setdefault('PYTORCH_MPS_HIGH_WATERMARK_RATIO', '0.0')
    os.environ.setdefault('PYTORCH_DISABLE_MPS', '1')

    # Library-specific safety
    os.environ.setdefault('OPENCV_LOG_LEVEL', 'SILENT')
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

import glob
import json
import logging
import pathlib
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from knowledge_storm import (
    STORMWikiLMConfigs,
    STORMWikiRunner,
    STORMWikiRunnerArguments,
)
from knowledge_storm.lm import OpenAIModel, GoogleModel
from knowledge_storm.rm import (
    BraveRM,
    TavilySearchRM,
    SerperRM,
    YouRM,
    BingSearch,
    DuckDuckGoSearchRM,
    SearXNG,
    AzureAISearch,
)
from knowledge_storm.storm_wiki.modules.retriever import get_whitelisted_domains, is_valid_source
from knowledge_storm.utils import (
    FileIOHelper,
    QueryLogger,
    load_api_key,
    truncate_filename,
)
from utils.paper_processing import (
    clean_paper_content,
    copy_paper_images,
    extract_figure_data,
    parse_paper_title,
)
from utils.post_processing import process_file
from prompts import PromptType, configure_prompts

# Get the directory where the script is located
SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()

# Add parent directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


class ModelProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"


class RetrieverType(str, Enum):
    TAVILY = "tavily"
    BRAVE = "brave"
    SERPER = "serper"
    YOU = "you"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    AZURE_AI_SEARCH = "azure_ai_search"


class TimeRange(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass
class ReportGenerationConfig:
    """Configuration for report generation."""
    
    # Basic settings
    output_dir: str = "results/api"
    max_thread_num: int = 10
    model_provider: ModelProvider = ModelProvider.OPENAI
    retriever: RetrieverType = RetrieverType.TAVILY
    temperature: float = 0.2
    top_p: float = 0.4
    prompt_type: PromptType = PromptType.GENERAL
    
    # Generation flags
    do_research: bool = True
    do_generate_outline: bool = True
    do_generate_article: bool = True
    do_polish_article: bool = True
    remove_duplicate: bool = True
    post_processing: bool = True
    
    # Search and generation parameters
    max_conv_turn: int = 3
    max_perspective: int = 3
    search_top_k: int = 10
    initial_retrieval_k: int = 150
    final_context_k: int = 20
    reranker_threshold: float = 0.5
    
    # Optional parameters
    time_range: Optional[TimeRange] = None
    include_domains: bool = False
    whitelist_domains: Optional[List[str]] = None
    search_depth: str = "basic"  # "basic" or "advanced" for TavilySearchRM
    old_outline_path: Optional[str] = None
    skip_rewrite_outline: bool = False
    
    # Content inputs
    topic: Optional[str] = None
    article_title: str = "StormReport"
    transcript_path: Optional[List[str]] = None
    paper_path: Optional[List[str]] = None
    csv_path: Optional[str] = None
    author_json: Optional[str] = None
    caption_files: Optional[List[str]] = None
    
    # CSV processing options (for non-interactive API use)
    csv_session_code: Optional[str] = None
    csv_date_filter: Optional[str] = None  # Format: YYYY-MM-DD


@dataclass
class ReportGenerationResult:
    """Result of report generation."""
    
    success: bool
    article_title: str
    output_directory: str
    generated_files: List[str]
    error_message: Optional[str] = None
    processing_logs: List[str] = None


class DeepReportGenerator:
    """Class-based report generator optimized for API usage."""
    
    def __init__(self, secrets_path: str = "secrets.toml"):
        """Initialize the report generator.
        
        Args:
            secrets_path: Path to the secrets.toml file containing API keys
        """
        self.secrets_path = secrets_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_api_keys(self):
        """Load API keys from secrets.toml file."""
        try:
            load_api_key(toml_file_path=self.secrets_path)
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            raise
    
    def _setup_language_models(self, config: ReportGenerationConfig) -> STORMWikiLMConfigs:
        """Setup language model configurations based on provider."""
        lm_configs = STORMWikiLMConfigs()
        
        if config.model_provider == ModelProvider.GOOGLE:
            return self._setup_google_models(config, lm_configs)
        elif config.model_provider == ModelProvider.OPENAI:
            return self._setup_openai_models(config, lm_configs)
        else:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")
    
    def _setup_openai_models(self, config: ReportGenerationConfig, lm_configs: STORMWikiLMConfigs) -> STORMWikiLMConfigs:
        """Setup OpenAI language models."""
        openai_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        # Check if OPENAI_API_KEY is loaded
        if not openai_kwargs["api_key"]:
            raise ValueError("OPENAI_API_KEY not found. Please set it in secrets.toml or environment variables.")
        
        # Model names for OpenAI
        conversation_model_name = "gpt-4.1-mini"
        outline_gen_model_name = "gpt-4.1"
        generation_model_name = "gpt-4.1"
        conceptualize_model_name = "gpt-4.1-nano"
        
        # Configure OpenAI language models
        conv_simulator_lm = OpenAIModel(
            model=conversation_model_name, max_tokens=500, **openai_kwargs
        )
        question_asker_lm = OpenAIModel(
            model=conversation_model_name, max_tokens=500, **openai_kwargs
        )
        outline_gen_lm = OpenAIModel(
            model=outline_gen_model_name, max_tokens=5000, **openai_kwargs
        )
        article_gen_lm = OpenAIModel(
            model=generation_model_name, max_tokens=3000, **openai_kwargs
        )
        article_polish_lm = OpenAIModel(
            model=generation_model_name, max_tokens=20000, **openai_kwargs
        )
        topic_improver_lm = OpenAIModel(
            model=generation_model_name, max_tokens=500, **openai_kwargs
        )

        
        lm_configs.set_conv_simulator_lm(conv_simulator_lm)
        lm_configs.set_question_asker_lm(question_asker_lm)
        lm_configs.set_outline_gen_lm(outline_gen_lm)
        lm_configs.set_article_gen_lm(article_gen_lm)
        lm_configs.set_article_polish_lm(article_polish_lm)
        lm_configs.set_topic_improver_lm(topic_improver_lm)
        
        return lm_configs
    
    def _setup_google_models(self, config: ReportGenerationConfig, lm_configs: STORMWikiLMConfigs) -> STORMWikiLMConfigs:
        """Setup Google/Gemini language models."""
        gemini_kwargs = {
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        # Check if GOOGLE_API_KEY is loaded
        if not gemini_kwargs["api_key"]:
            raise ValueError("GOOGLE_API_KEY not found. Please set it in secrets.toml or environment variables.")
        
        # Model names for Google/Gemini
        conversation_model_name = "models/gemini-2.0-flash"
        outline_gen_model_name = "models/gemini-1.5-pro"
        generation_model_name = "models/gemini-1.5-pro"
        polish_model_name = "models/gemini-1.5-pro"
        topic_improver_model_name = "models/gemini-1.5-pro"
        
        # Configure Google Gemini-based language models
        conv_simulator_lm = GoogleModel(model=conversation_model_name, max_tokens=500, **gemini_kwargs)
        question_asker_lm = GoogleModel(model=conversation_model_name, max_tokens=500, **gemini_kwargs)
        outline_gen_lm = GoogleModel(model=outline_gen_model_name, max_tokens=3000, **gemini_kwargs)
        article_gen_lm = GoogleModel(model=generation_model_name, max_tokens=3000, **gemini_kwargs)
        article_polish_lm = GoogleModel(model=polish_model_name, max_tokens=30000, **gemini_kwargs)
        topic_improver_lm = GoogleModel(model=topic_improver_model_name, max_tokens=500, **gemini_kwargs)

        
        lm_configs.set_conv_simulator_lm(conv_simulator_lm)
        lm_configs.set_question_asker_lm(question_asker_lm)
        lm_configs.set_outline_gen_lm(outline_gen_lm)
        lm_configs.set_article_gen_lm(article_gen_lm)
        lm_configs.set_article_polish_lm(article_polish_lm)
        lm_configs.set_topic_improver_lm(topic_improver_lm)
        
        return lm_configs
    
    def _setup_retriever(self, config: ReportGenerationConfig, engine_args: STORMWikiRunnerArguments):
        """Setup the retrieval model based on the configured retriever type."""
        time_range = config.time_range.value if config.time_range else None
        
        # Determine domains to include based on configuration
        domains_to_include = None
        if config.whitelist_domains:
            domains_to_include = config.whitelist_domains
        elif config.include_domains:
            # Use predefined whitelisted domains when include_domains is True but no specific domains provided
            domains_to_include = get_whitelisted_domains()
            
        if config.retriever == RetrieverType.TAVILY:
            return TavilySearchRM(
                tavily_search_api_key=os.getenv("TAVILY_API_KEY"),
                k=engine_args.search_top_k,
                include_raw_content=False,
                include_answer=False,
                time_range=time_range,
                search_depth=config.search_depth,
                chunks_per_source=3,
                include_domains=domains_to_include,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.BRAVE:
            return BraveRM(
                brave_search_api_key=os.getenv("BRAVE_API_KEY"),
                k=engine_args.search_top_k,
                time_range=time_range,
                include_domains=domains_to_include,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.SERPER:
            serper_api_key = os.getenv("SERPER_API_KEY")
            if not serper_api_key:
                raise ValueError("SERPER_API_KEY not found. Please set it in secrets.toml or environment variables.")
            
            query_params = {
                "autocorrect": True,
                "num": engine_args.search_top_k,
                "page": 1
            }
            return SerperRM(
                serper_search_api_key=serper_api_key,
                query_params=query_params
            )
        elif config.retriever == RetrieverType.YOU:
            return YouRM(
                ydc_api_key=os.getenv("YDC_API_KEY"),
                k=engine_args.search_top_k,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.BING:
            return BingSearch(
                bing_search_api_key=os.getenv("BING_SEARCH_API_KEY"),
                k=engine_args.search_top_k,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.DUCKDUCKGO:
            return DuckDuckGoSearchRM(
                k=engine_args.search_top_k,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.SEARXNG:
            return SearXNG(
                searxng_api_url=os.getenv("searxng_api_url"),
                k=engine_args.search_top_k,
                time_range=time_range,
                is_valid_source=is_valid_source,
            )
        elif config.retriever == RetrieverType.AZURE_AI_SEARCH:
            return AzureAISearch(
                azure_ai_search_api_key=os.getenv("AZURE_AI_SEARCH_API_KEY"),
                azure_ai_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
                azure_ai_search_index=os.getenv("AZURE_AI_SEARCH_INDEX"),
                k=engine_args.search_top_k,
                is_valid_source=is_valid_source,
            )
        else:
            raise ValueError(
                f"Unsupported retriever: {config.retriever}. "
                f"Supported retrievers: {', '.join([r.value for r in RetrieverType])}"
            )
    
    def _load_content_from_file(self, file_path: str) -> Optional[str]:
        """Load content from a .txt or .md file and clean it."""
        if not os.path.exists(file_path):
            self.logger.warning(f"File not found: {file_path}")
            return None
        if file_path.endswith((".txt", ".md")):
            try:
                raw_content = FileIOHelper.load_str(file_path)
                cleaned_content = clean_paper_content(raw_content)
                return cleaned_content
            except Exception as e:
                self.logger.error(f"Error reading or cleaning text file {file_path}: {e}")
                return None
        else:
            self.logger.warning(f"Unsupported file type: {file_path}. Please use .txt or .md.")
            return None
    
    def _load_structured_data(self, path: str) -> Union[str, List[str], None]:
        """Load structured data from a given path and clean paper content."""
        if os.path.isdir(path):
            all_contents = []
            self.logger.info(f"Loading and cleaning structured data from directory: {path}")
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                if os.path.isfile(file_path) and file_path.endswith((".txt", ".md")):
                    content = self._load_content_from_file(file_path)
                    if content:
                        all_contents.append(content)
            return all_contents if all_contents else None
        elif os.path.isfile(path):
            self.logger.info(f"Loading and cleaning structured data from file: {path}")
            return self._load_content_from_file(path)
        else:
            self.logger.info(
                f"Path '{path}' is not a file or directory. Treating as direct content and cleaning."
            )
            return clean_paper_content(path)
    
    def _process_csv_metadata(self, config: ReportGenerationConfig) -> tuple[str, Optional[str], Optional[Union[str, List[str]]]]:
        """Process CSV metadata and return article title, speakers, and transcript input."""
        article_title = config.article_title
        speakers = None
        transcript_input = None
        
        if not config.csv_path:
            return article_title, speakers, transcript_input
        
        try:
            df_orig = pd.read_csv(config.csv_path)
            df = df_orig.copy()
            df_for_description_extraction = df_orig.copy()
            
            session_code_filter_applied_and_matched = False
            date_filter_applied_and_matched = False
            
            # Session Code Filter (non-interactive for API use)
            if config.csv_session_code:
                df_session_filtered = df[df["Session Code"] == config.csv_session_code]
                if not df_session_filtered.empty:
                    df = df_session_filtered
                    df_for_description_extraction = df.copy()
                    article_title = df["Title"].iloc[0]
                    speakers = df["Speakers"].iloc[0] if "Speakers" in df.columns and pd.notna(df["Speakers"].iloc[0]) else None
                    self.logger.info(f"Filtered by Session Code. Using article title: {article_title}")
                    session_code_filter_applied_and_matched = True
                else:
                    self.logger.info(f"Session Code {config.csv_session_code} not found. Proceeding without session code filter.")
            
            # Date Filter (non-interactive for API use)
            if config.csv_date_filter:
                try:
                    target_date = datetime.strptime(config.csv_date_filter, "%Y-%m-%d").date()
                    current_year = datetime.now().year
                    
                    def convert_date_format(date_str):
                        try:
                            dt_obj = pd.to_datetime(date_str).date()
                            return dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            try:
                                dt_obj = datetime.strptime(str(date_str).split(', ')[1], "%B %d").date()
                                return dt_obj.replace(year=current_year).strftime("%Y-%m-%d")
                            except Exception:
                                return None
                    
                    df["Formatted Date"] = df["Date"].astype(str).apply(convert_date_format)
                    df_date_filtered = df[df["Formatted Date"] == target_date.strftime("%Y-%m-%d")]
                    
                    if not df_date_filtered.empty:
                        df = df_date_filtered
                        df_for_description_extraction = df.copy()
                        
                        if not session_code_filter_applied_and_matched:
                            article_title = df_date_filtered["Title"].iloc[0] if "Title" in df_date_filtered.columns else config.article_title
                            speakers = df_date_filtered["Speakers"].iloc[0] if "Speakers" in df_date_filtered.columns and pd.notna(df_date_filtered["Speakers"].iloc[0]) else None
                            self.logger.info(f"Using article title from date filter: {article_title}")
                        else:
                            self.logger.info("Date filter further refined CSV data. Title/speakers already set by session code filter.")
                        date_filter_applied_and_matched = True
                        
                        # Check if transcript should be sourced from this date-filtered data
                        if (
                            not config.transcript_path
                            and not config.paper_path
                            and transcript_input is None
                        ):
                            descriptions = df_date_filtered["Description"].tolist()
                            cleaned_descriptions = [clean_paper_content(desc) for desc in descriptions if pd.notna(desc)]
                            if cleaned_descriptions:
                                if len(cleaned_descriptions) == 1:
                                    transcript_input = cleaned_descriptions[0]
                                else:
                                    transcript_input = cleaned_descriptions
                                self.logger.info(f"Extracted {len(cleaned_descriptions)} descriptions for date {config.csv_date_filter} to be used as transcript.")
                    else:
                        self.logger.info(f"No entries found for date {config.csv_date_filter}. Previous filters (if any) remain.")
                except ValueError as ve:
                    self.logger.error(f"Invalid date format: {ve}. Please use YYYY-MM-DD. Skipping date filter.")
            
            # Core logic for transcript from Description if not otherwise provided
            if (
                not config.transcript_path
                and not config.paper_path
                and transcript_input is None
            ):
                if "Description" in df_for_description_extraction.columns and not df_for_description_extraction.empty:
                    descriptions_from_csv = df_for_description_extraction["Description"].tolist()
                    cleaned_descriptions_from_csv = [clean_paper_content(desc) for desc in descriptions_from_csv if pd.notna(desc)]
                    if cleaned_descriptions_from_csv:
                        if len(cleaned_descriptions_from_csv) == 1:
                            transcript_input = cleaned_descriptions_from_csv[0]
                        else:
                            transcript_input = cleaned_descriptions_from_csv
                        self.logger.info(f"Used 'Description' column from CSV as transcript_input ({len(cleaned_descriptions_from_csv)} items)")
                        
                        # Set title and speakers from first row
                        if not df_for_description_extraction.empty:
                            if not session_code_filter_applied_and_matched and not date_filter_applied_and_matched:
                                article_title = (
                                    df_for_description_extraction["Title"].iloc[0]
                                    if "Title" in df_for_description_extraction.columns
                                    else config.article_title
                                )
                                speakers = (
                                    df_for_description_extraction["Speakers"].iloc[0]
                                    if "Speakers" in df_for_description_extraction.columns
                                    and pd.notna(df_for_description_extraction["Speakers"].iloc[0])
                                    else None
                                )
                                self.logger.info(f"Using article title/speakers from CSV: {article_title}")
        
        except Exception as e:
            self.logger.error(f"Error processing CSV file: {e}. Using default title: {article_title}")
        
        return article_title, speakers, transcript_input
    
    def _process_transcripts(self, config: ReportGenerationConfig) -> Optional[Union[str, List[str]]]:
        """Process transcript data from provided paths."""
        transcripts_data = []
        
        if not config.transcript_path:
            return None
        
        self.logger.info(f"Processing transcript paths: {config.transcript_path}")
        for path_item in config.transcript_path:
            content = self._load_structured_data(path_item)
            if content:
                if isinstance(content, list):
                    transcripts_data.extend(content)
                elif isinstance(content, str):
                    transcripts_data.append(content)
                self.logger.info(f"Successfully loaded transcript data from: {path_item}")
            else:
                self.logger.warning(f"No transcript data loaded from: {path_item}")
        
        if not transcripts_data:
            self.logger.info("No transcripts were loaded.")
            return None
        elif len(transcripts_data) == 1:
            return transcripts_data[0]
        else:
            return transcripts_data
    
    def _process_papers(self, config: ReportGenerationConfig) -> tuple[Optional[Union[str, List[str]]], List[Dict], List[str]]:
        """Process paper data and extract figures."""
        paper_data = []
        figure_data_for_runner = []
        original_paper_paths_for_images = config.paper_path[:] if config.paper_path else []
        
        if not config.paper_path:
            return None, [], []
        
        self.logger.info(f"Processing paper paths: {config.paper_path}")
        
        for path_item in config.paper_path:
            content = self._load_structured_data(path_item)
            if content:
                if isinstance(content, list):
                    paper_data.extend(content)
                elif isinstance(content, str):
                    paper_data.append(content)
                self.logger.info(f"Successfully loaded paper data from: {path_item}")
            else:
                self.logger.warning(f"No paper data loaded from: {path_item}")
        
        loaded_paper_input = None
        if not paper_data:
            self.logger.info("No papers were loaded.")
        elif len(paper_data) == 1:
            loaded_paper_input = paper_data[0]
            self.logger.info(f"Loaded a single paper string, length {len(loaded_paper_input)} chars.")
        else:
            loaded_paper_input = paper_data
            self.logger.info(f"Loaded {len(loaded_paper_input)} paper segments.")
        
        # Extract figure data
        if loaded_paper_input:
            paper_content_to_process_for_figures = (
                loaded_paper_input if isinstance(loaded_paper_input, str) else paper_data[0]
            )
            
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False, encoding="utf-8"
                ) as tmp_file:
                    tmp_file.write(paper_content_to_process_for_figures)
                    temp_md_file_to_process = tmp_file.name
                
                self.logger.info(f"Extracting figures from temporary file: {temp_md_file_to_process}")
                figure_data_for_runner = extract_figure_data(temp_md_file_to_process)
                if figure_data_for_runner:
                    self.logger.info(f"Successfully extracted {len(figure_data_for_runner)} figures.")
                
            except Exception as e:
                self.logger.error(f"Error during figure extraction: {e}")
            finally:
                if 'temp_md_file_to_process' in locals() and os.path.exists(temp_md_file_to_process):
                    os.remove(temp_md_file_to_process)
                    self.logger.info(f"Removed temporary figure processing file")
        
        return loaded_paper_input, figure_data_for_runner, original_paper_paths_for_images
    
    def _process_video(self, config: ReportGenerationConfig, article_output_dir: str) -> Optional[List[Dict]]:
        """Process caption files to extract figure data."""
        if not config.caption_files:
            return None

        self.logger.info("Processing caption files for figure extraction...")

        all_figure_data = []

        for caption_file in config.caption_files:
            if not os.path.exists(caption_file):
                self.logger.warning(f"Caption file not found: {caption_file}")
                continue

            self.logger.info(f"Processing caption file: {caption_file}")

            # Load and process caption data
            try:
                with open(caption_file, 'r', encoding='utf-8') as f:
                    caption_data = json.load(f)

                if not isinstance(caption_data, list):
                    self.logger.warning(f"Expected list in caption file {caption_file}, got {type(caption_data)}")
                    continue

                # Extract figure data from caption data
                video_figure_data = extract_figure_data(caption_file)
                if not video_figure_data:
                    self.logger.info(f"No figures found in caption file {caption_file}.")
                    continue

                # Update paths in figure data to be relative to article output directory
                base_dir = os.path.dirname(caption_file)  # extractions directory

                for fig_dict in video_figure_data:
                    if 'image_path' in fig_dict:
                        image_path = fig_dict['image_path']

                        # If path is absolute, make it relative to article output directory
                        if os.path.isabs(image_path):
                            try:
                                # Try to make path relative to article output directory
                                rel_path = os.path.relpath(image_path, article_output_dir)
                                fig_dict['image_path'] = rel_path
                            except ValueError:
                                # If paths are on different drives, keep filename only
                                fig_dict['image_path'] = os.path.basename(image_path)
                        elif not image_path.startswith('.'):
                            # If it's a relative path but doesn't start with '.', make it relative to base_dir
                            full_path = os.path.join(base_dir, image_path)
                            try:
                                rel_path = os.path.relpath(full_path, article_output_dir)
                                fig_dict['image_path'] = rel_path
                            except ValueError:
                                fig_dict['image_path'] = os.path.basename(image_path)

                all_figure_data.extend(video_figure_data)
                self.logger.info(f"Successfully extracted {len(video_figure_data)} figures from {caption_file}.")

            except Exception as e:
                self.logger.error(f"Failed to process caption file {caption_file}: {e}")
                continue

        if all_figure_data:
            self.logger.info(f"Total figures extracted from all caption files: {len(all_figure_data)}")
            return all_figure_data
        else:
            self.logger.info("No figures found in any caption files.")
            return None
    
    def generate_report(self, config: ReportGenerationConfig) -> ReportGenerationResult:
        """Generate a research report based on the provided configuration.
        
        Args:
            config: Configuration object containing all generation parameters
            
        Returns:
            ReportGenerationResult with success status and generated files
        """
        processing_logs = []
        generated_files = []
        
        try:
            # Load API keys
            self._load_api_keys()
            processing_logs.append("API keys loaded successfully")
            
            # Configure prompts based on the configuration
            configure_prompts(config.prompt_type)
            processing_logs.append(f"Prompts configured for {config.prompt_type.value} type")
            
            # Validate inputs
            if not config.topic and not config.transcript_path and not config.paper_path and not config.csv_path and not config.caption_files:
                raise ValueError("Either a topic, transcript, paper, CSV file, or caption files must be provided.")
            
            # Setup language models and configurations
            lm_configs = self._setup_language_models(config)
            processing_logs.append(f"Language models configured for {config.model_provider}")
            
            # Set up engine arguments
            engine_args = STORMWikiRunnerArguments(
                output_dir=config.output_dir,
                max_conv_turn=config.max_conv_turn,
                max_perspective=config.max_perspective,
                search_top_k=config.search_top_k,
                initial_retrieval_k=config.initial_retrieval_k,
                final_context_k=config.final_context_k,
                max_thread_num=config.max_thread_num,
                recent_content_only=config.time_range is not None,
                reranker_threshold=config.reranker_threshold,
                time_range=config.time_range.value if config.time_range else None,
            )
            
            # Setup retriever
            rm = self._setup_retriever(config, engine_args)
            processing_logs.append(f"Retriever configured: {config.retriever}")
            
            # Initialize STORM Wiki runner
            runner = STORMWikiRunner(engine_args, lm_configs, rm)
            runner.author_json = config.author_json
            
            # Process CSV metadata
            article_title, speakers, csv_transcript_input = self._process_csv_metadata(config)
            processing_logs.append("CSV metadata processed")
            
            # Process transcripts
            transcript_input = self._process_transcripts(config) or csv_transcript_input
            runner.transcript = transcript_input
            runner.speakers = speakers
            runner.article_title = article_title
            processing_logs.append("Transcript data processed")
            
            # Process papers
            loaded_paper_input, figure_data_for_runner, original_paper_paths_for_images = self._process_papers(config)
            runner.paper = loaded_paper_input
            runner.figure_data = figure_data_for_runner
            processing_logs.append("Paper data processed")
            
            # Parse paper title if single paper provided
            runner.parsed_paper_title = None
            if loaded_paper_input and isinstance(loaded_paper_input, str):
                runner.parsed_paper_title = parse_paper_title(loaded_paper_input)
                if runner.parsed_paper_title and runner.article_title == "StormReport":
                    article_title = runner.parsed_paper_title
                    runner.article_title = article_title
                    self.logger.info(f"Using parsed paper title as article title: {article_title}")
            
            # Validate that we have content to work with
            if not config.topic and not runner.transcript and not runner.paper:
                raise ValueError("Either a topic, transcript, or paper content must be provided for report generation.")
            
            # Set article directory name
            folder_name = truncate_filename(article_title.replace(" ", "_").replace("/", "_"))
            runner.article_dir_name = folder_name
            
            # Update figure data paths
            if not config.caption_files and runner.figure_data and runner.article_dir_name:
                image_output_subfolder_name = f"Images_{runner.article_dir_name}"
                updated_figure_data_list = []
                for fig_dict in runner.figure_data:
                    original_image_path = fig_dict.get("image_path")
                    if original_image_path:
                        base_image_filename = os.path.basename(original_image_path)
                        new_relative_image_path = os.path.join(image_output_subfolder_name, base_image_filename)
                        fig_dict["image_path"] = new_relative_image_path
                    updated_figure_data_list.append(fig_dict)
                runner.figure_data = updated_figure_data_list
            
            # Create output directory and setup query logger
            article_output_dir = os.path.join(config.output_dir, runner.article_dir_name)
            os.makedirs(article_output_dir, exist_ok=True)
            runner.storm_article_generation.query_logger = QueryLogger(article_output_dir)
            
            # Process video if provided
            video_figure_data = self._process_video(config, article_output_dir)
            if video_figure_data:
                if figure_data_for_runner:
                    figure_data_for_runner.extend(video_figure_data)
                else:
                    figure_data_for_runner = video_figure_data
                runner.figure_data = figure_data_for_runner
                processing_logs.append("Video processed and figure data extracted")
            
            # Log processing information
            if config.topic:
                if runner.transcript and runner.paper:
                    self.logger.info(f"Topic, transcript, and paper provided. The topic ('{config.topic}') will be improved using both transcript and paper.")
                elif runner.transcript:
                    self.logger.info(f"Topic and transcript provided. The topic ('{config.topic}') will be improved using the transcript.")
                elif runner.paper:
                    self.logger.info(f"Topic and paper provided. The topic ('{config.topic}') will be improved using the paper.")
                else:
                    self.logger.info(f"Only topic ('{config.topic}') provided. Using the provided topic for improvement/guidance.")
            else:
                if runner.transcript and runner.paper:
                    self.logger.info("Transcript and paper provided (no topic). Key insights will be extracted from both to form a topic.")
                elif runner.transcript:
                    self.logger.info("Only transcript provided (no topic). Key technology or innovations will be extracted from the transcript to form a topic.")
                elif runner.paper:
                    self.logger.info("Only paper provided (no topic). Key insights will be extracted from the paper to form a topic.")
            
            # Execute the pipeline
            runner.run(
                user_input=config.topic,
                do_research=config.do_research,
                do_generate_outline=config.do_generate_outline,
                do_generate_article=config.do_generate_article,
                do_polish_article=config.do_polish_article,
                remove_duplicate=config.remove_duplicate,
                old_outline_path=config.old_outline_path,
                skip_rewrite_outline=config.skip_rewrite_outline,
            )
            
            runner.is_polishing_complete = True
            runner.post_run()
            runner.summary()
            processing_logs.append("Report generation completed")
            
            # Collect generated files
            generated_files.extend([
                os.path.join(article_output_dir, "storm_gen_outline.txt"),
                os.path.join(article_output_dir, "storm_gen_article.md"),
                os.path.join(article_output_dir, "storm_gen_article_polished.md"),
            ])
            
            # Post-process the polished article if requested
            if config.post_processing:
                polished_article_path = os.path.join(article_output_dir, "storm_gen_article_polished.md")
                if os.path.exists(polished_article_path):
                    clean_folder_name = "".join(e for e in folder_name if e.isalnum() or e == "_")
                    output_file = os.path.join(article_output_dir, f"{clean_folder_name}.md")
                    process_file(polished_article_path, output_file, config.post_processing)
                    generated_files.append(output_file)
                    processing_logs.append(f"Post-processed article saved to: {output_file}")
            
            # Copy paper images if applicable
            if original_paper_paths_for_images:
                source_paper_location = original_paper_paths_for_images[0]
                actual_md_or_txt_file_path = None
                
                if os.path.isfile(source_paper_location) and source_paper_location.endswith((".md", ".txt")):
                    actual_md_or_txt_file_path = source_paper_location
                elif os.path.isdir(source_paper_location):
                    found_md_files = glob.glob(os.path.join(source_paper_location, "*.md"))
                    if found_md_files:
                        actual_md_or_txt_file_path = found_md_files[0]
                    else:
                        found_txt_files = glob.glob(os.path.join(source_paper_location, "*.txt"))
                        if found_txt_files:
                            actual_md_or_txt_file_path = found_txt_files[0]
                
                if actual_md_or_txt_file_path:
                    copy_paper_images(
                        paper_md_path=actual_md_or_txt_file_path,
                        report_output_dir=article_output_dir,
                    )
                    processing_logs.append("Paper images copied successfully")
            
            return ReportGenerationResult(
                success=True,
                article_title=article_title,
                output_directory=article_output_dir,
                generated_files=[f for f in generated_files if os.path.exists(f)],
                processing_logs=processing_logs
            )
            
        except Exception as e:
            error_message = f"Report generation failed: {str(e)}"
            self.logger.exception(error_message)
            return ReportGenerationResult(
                success=False,
                article_title=config.article_title,
                output_directory="",
                generated_files=[],
                error_message=error_message,
                processing_logs=processing_logs
            )


# Convenience function for backward compatibility and simple usage
def generate_report_from_config(config: ReportGenerationConfig, secrets_path: str = "secrets.toml") -> ReportGenerationResult:
    """Generate a report using the provided configuration.
    
    Args:
        config: Report generation configuration
        secrets_path: Path to secrets.toml file
        
    Returns:
        ReportGenerationResult with generation status and files
    """
    generator = DeepReportGenerator(secrets_path=secrets_path)
    return generator.generate_report(config)


if __name__ == "__main__":
    # Example usage for general technical reports
    general_config = ReportGenerationConfig(
        topic="Artificial Intelligence in Healthcare",
        output_dir="results/api_test",
        model_provider=ModelProvider.OPENAI,
        retriever=RetrieverType.TAVILY,
        prompt_type=PromptType.GENERAL,  # Use general prompts
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True
    )
    
    # Example usage for financial analysis reports
    financial_config = ReportGenerationConfig(
        topic="Artificial Intelligence in Healthcare",
        output_dir="results/financial_test",
        model_provider=ModelProvider.OPENAI,
        retriever=RetrieverType.TAVILY,
        prompt_type=PromptType.FINANCIAL,  # Use financial prompts
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True
    )
    
    # Choose which config to use
    config = general_config  # Change this to financial_config for financial reports
    
    result = generate_report_from_config(config)
    if result.success:
        print(f"Report generated successfully: {result.article_title}")
        print(f"Output directory: {result.output_directory}")
        print(f"Generated files: {result.generated_files}")
    else:
        print(f"Report generation failed: {result.error_message}") 