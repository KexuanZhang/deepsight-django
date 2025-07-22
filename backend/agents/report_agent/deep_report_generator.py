import os
import sys

if sys.platform == "darwin":  # macOS
    # Core macOS forking safety
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    # PyTorch/OpenMP/MKL safety
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    # Disable MPS completely due to Metal Performance Shaders kernel compilation issues
    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
    os.environ.setdefault("PYTORCH_DISABLE_MPS", "1")

    # Library-specific safety
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import glob
import json
import logging
import pathlib
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from prompts import PromptType, configure_prompts, create_prompt_module

# Get the directory where the script is located
SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()

# Add parent directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# NOTE: We perform knowledge_storm imports lazily (after prompt configuration)
# to ensure the correct prompt type is loaded before any modules evaluate
# their docstrings. See `_lazy_import_knowledge_storm()` below.

# Placeholder type hints (optional) – will be overwritten after lazy import
STORMWikiLMConfigs = None  # type: ignore
STORMWikiRunner = None  # type: ignore
STORMWikiRunnerArguments = None  # type: ignore
OpenAIModel = GoogleModel = None  # type: ignore
BraveRM = TavilySearchRM = SerperRM = YouRM = BingSearch = DuckDuckGoSearchRM = SearXNG = AzureAISearch = None  # type: ignore
get_whitelisted_domains = is_valid_source = None  # type: ignore
FileIOHelper = QueryLogger = load_api_key = truncate_filename = None  # type: ignore

# ---------------------------------------------------------------------------
# Lazy import helper
# ---------------------------------------------------------------------------

def _lazy_import_knowledge_storm():
    """Import knowledge_storm modules *after* prompts are configured.

    This avoids loading the default GENERAL prompts when the package-level
    imports evaluate docstrings at import time. We import once and cache the
    objects in ``globals()`` so subsequent calls are no-ops.
    """

    if globals().get("STORMWikiRunner") is not None:
        # Already imported
        return

    global STORMWikiLMConfigs, STORMWikiRunner, STORMWikiRunnerArguments
    global OpenAIModel, GoogleModel
    global BraveRM, TavilySearchRM, SerperRM, YouRM, BingSearch, DuckDuckGoSearchRM, SearXNG, AzureAISearch
    global get_whitelisted_domains, is_valid_source
    global FileIOHelper, QueryLogger, load_api_key, truncate_filename

    from knowledge_storm import (
        STORMWikiLMConfigs as _STORMWikiLMConfigs,
        STORMWikiRunner as _STORMWikiRunner,
        STORMWikiRunnerArguments as _STORMWikiRunnerArguments,
    )

    from knowledge_storm.lm import OpenAIModel as _OpenAIModel, GoogleModel as _GoogleModel

    from knowledge_storm.rm import (
        BraveRM as _BraveRM,
        TavilySearchRM as _TavilySearchRM,
        SerperRM as _SerperRM,
        YouRM as _YouRM,
        BingSearch as _BingSearch,
        DuckDuckGoSearchRM as _DuckDuckGoSearchRM,
        SearXNG as _SearXNG,
        AzureAISearch as _AzureAISearch,
    )

    from knowledge_storm.storm_wiki.modules.retriever import (
        get_whitelisted_domains as _get_whitelisted_domains,
        is_valid_source as _is_valid_source,
    )

    from knowledge_storm.utils import (
        FileIOHelper as _FileIOHelper,
        QueryLogger as _QueryLogger,
        load_api_key as _load_api_key,
        truncate_filename as _truncate_filename,
    )

    # Assign to globals so that other methods/classes can use them
    STORMWikiLMConfigs = _STORMWikiLMConfigs
    STORMWikiRunner = _STORMWikiRunner
    STORMWikiRunnerArguments = _STORMWikiRunnerArguments
    OpenAIModel = _OpenAIModel
    GoogleModel = _GoogleModel
    BraveRM = _BraveRM
    TavilySearchRM = _TavilySearchRM
    SerperRM = _SerperRM
    YouRM = _YouRM
    BingSearch = _BingSearch
    DuckDuckGoSearchRM = _DuckDuckGoSearchRM
    SearXNG = _SearXNG
    AzureAISearch = _AzureAISearch
    get_whitelisted_domains = _get_whitelisted_domains
    is_valid_source = _is_valid_source
    FileIOHelper = _FileIOHelper
    QueryLogger = _QueryLogger
    load_api_key = _load_api_key
    truncate_filename = _truncate_filename


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
    report_id: Optional[int] = None

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
    # Consolidated text input (replaces paper_path, transcript_path, paper_content, transcript_content)
    text_input: Optional[str] = None
    csv_path: Optional[str] = None
    author_json: Optional[str] = None
    caption_files: Optional[List[str]] = None
    selected_files_paths: Optional[List[str]] = None  # For image path fixing
    user_id: Optional[str] = None  # User ID for MinIO access

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
    report_content: Optional[str] = None
    generated_topic: Optional[str] = None


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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def _load_api_keys(self):
        """Load API keys from secrets.toml file."""
        try:
            load_api_key(toml_file_path=self.secrets_path)
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            raise

    def _setup_language_models(
        self, config: ReportGenerationConfig
    ) -> STORMWikiLMConfigs:
        """Setup language model configurations based on provider."""
        lm_configs = STORMWikiLMConfigs()

        if config.model_provider == ModelProvider.GOOGLE:
            return self._setup_google_models(config, lm_configs)
        elif config.model_provider == ModelProvider.OPENAI:
            return self._setup_openai_models(config, lm_configs)
        else:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    def _setup_openai_models(
        self, config: ReportGenerationConfig, lm_configs: STORMWikiLMConfigs
    ) -> STORMWikiLMConfigs:
        """Setup OpenAI language models."""
        openai_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        # Check if OPENAI_API_KEY is loaded
        if not openai_kwargs["api_key"]:
            raise ValueError(
                "OPENAI_API_KEY not found. Please set it in secrets.toml or environment variables."
            )

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

    def _setup_google_models(
        self, config: ReportGenerationConfig, lm_configs: STORMWikiLMConfigs
    ) -> STORMWikiLMConfigs:
        """Setup Google/Gemini language models."""
        gemini_kwargs = {
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        # Check if GOOGLE_API_KEY is loaded
        if not gemini_kwargs["api_key"]:
            raise ValueError(
                "GOOGLE_API_KEY not found. Please set it in secrets.toml or environment variables."
            )

        # Model names for Google/Gemini
        conversation_model_name = "models/gemini-2.5-flash-lite-preview-06-17"
        outline_gen_model_name = "models/gemini-2.5-flash"
        generation_model_name = "models/gemini-2.5-flash"
        polish_model_name = "gemini-2.5-pro"
        topic_improver_model_name = "gemini-2.5-pro"

        # Configure Google Gemini-based language models
        conv_simulator_lm = GoogleModel(
            model=conversation_model_name, max_tokens=500, **gemini_kwargs
        )
        question_asker_lm = GoogleModel(
            model=conversation_model_name, max_tokens=500, **gemini_kwargs
        )
        outline_gen_lm = GoogleModel(
            model=outline_gen_model_name, max_tokens=3000, **gemini_kwargs
        )
        article_gen_lm = GoogleModel(
            model=generation_model_name, max_tokens=3000, **gemini_kwargs
        )
        article_polish_lm = GoogleModel(
            model=polish_model_name, max_tokens=30000, **gemini_kwargs
        )
        topic_improver_lm = GoogleModel(
            model=topic_improver_model_name, max_tokens=500, **gemini_kwargs
        )

        lm_configs.set_conv_simulator_lm(conv_simulator_lm)
        lm_configs.set_question_asker_lm(question_asker_lm)
        lm_configs.set_outline_gen_lm(outline_gen_lm)
        lm_configs.set_article_gen_lm(article_gen_lm)
        lm_configs.set_article_polish_lm(article_polish_lm)
        lm_configs.set_topic_improver_lm(topic_improver_lm)

        return lm_configs

    def _setup_retriever(
        self, config: ReportGenerationConfig, engine_args: STORMWikiRunnerArguments
    ):
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
                raise ValueError(
                    "SERPER_API_KEY not found. Please set it in secrets.toml or environment variables."
                )

            query_params = {
                "autocorrect": True,
                "num": engine_args.search_top_k,
                "page": 1,
            }
            return SerperRM(
                serper_search_api_key=serper_api_key, query_params=query_params
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
                self.logger.error(
                    f"Error reading or cleaning text file {file_path}: {e}"
                )
                return None
        else:
            self.logger.warning(
                f"Unsupported file type: {file_path}. Please use .txt or .md."
            )
            return None

    def _load_structured_data(self, path: str) -> Union[str, List[str], None]:
        """Load structured data from a given path and clean paper content."""
        if os.path.isdir(path):
            all_contents = []
            self.logger.info(
                f"Loading and cleaning structured data from directory: {path}"
            )
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

    def _process_csv_metadata(
        self, config: ReportGenerationConfig
    ) -> tuple[str, Optional[str], Optional[Union[str, List[str]]]]:
        """Process CSV metadata and return article title, speakers, and text input."""
        article_title = config.article_title
        speakers = None
        text_input = None

        if not config.csv_path:
            return article_title, speakers, text_input

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
                    speakers = (
                        df["Speakers"].iloc[0]
                        if "Speakers" in df.columns and pd.notna(df["Speakers"].iloc[0])
                        else None
                    )
                    self.logger.info(
                        f"Filtered by Session Code. Using article title: {article_title}"
                    )
                    session_code_filter_applied_and_matched = True
                else:
                    self.logger.info(
                        f"Session Code {config.csv_session_code} not found. Proceeding without session code filter."
                    )

            # Date Filter (non-interactive for API use)
            if config.csv_date_filter:
                try:
                    target_date = datetime.strptime(
                        config.csv_date_filter, "%Y-%m-%d"
                    ).date()
                    current_year = datetime.now().year

                    def convert_date_format(date_str):
                        try:
                            dt_obj = pd.to_datetime(date_str).date()
                            return dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            try:
                                dt_obj = datetime.strptime(
                                    str(date_str).split(", ")[1], "%B %d"
                                ).date()
                                return dt_obj.replace(year=current_year).strftime(
                                    "%Y-%m-%d"
                                )
                            except Exception:
                                return None

                    df["Formatted Date"] = (
                        df["Date"].astype(str).apply(convert_date_format)
                    )
                    df_date_filtered = df[
                        df["Formatted Date"] == target_date.strftime("%Y-%m-%d")
                    ]

                    if not df_date_filtered.empty:
                        df = df_date_filtered
                        df_for_description_extraction = df.copy()

                        if not session_code_filter_applied_and_matched:
                            article_title = (
                                df_date_filtered["Title"].iloc[0]
                                if "Title" in df_date_filtered.columns
                                else config.article_title
                            )
                            speakers = (
                                df_date_filtered["Speakers"].iloc[0]
                                if "Speakers" in df_date_filtered.columns
                                and pd.notna(df_date_filtered["Speakers"].iloc[0])
                                else None
                            )
                            self.logger.info(
                                f"Using article title from date filter: {article_title}"
                            )
                        else:
                            self.logger.info(
                                "Date filter further refined CSV data. Title/speakers already set by session code filter."
                            )
                        date_filter_applied_and_matched = True

                        # Check if text should be sourced from this date-filtered data
                        if (
                            not config.text_input
                            and not config.csv_path
                            and text_input is None
                        ):
                            descriptions = df_date_filtered["Description"].tolist()
                            cleaned_descriptions = [
                                clean_paper_content(desc)
                                for desc in descriptions
                                if pd.notna(desc)
                            ]
                            if cleaned_descriptions:
                                if len(cleaned_descriptions) == 1:
                                    text_input = cleaned_descriptions[0]
                                else:
                                    text_input = cleaned_descriptions
                                self.logger.info(
                                    f"Extracted {len(cleaned_descriptions)} descriptions for date {config.csv_date_filter} to be used as text input."
                                )
                    else:
                        self.logger.info(
                            f"No entries found for date {config.csv_date_filter}. Previous filters (if any) remain."
                        )
                except ValueError as ve:
                    self.logger.error(
                        f"Invalid date format: {ve}. Please use YYYY-MM-DD. Skipping date filter."
                    )

            # Core logic for text input from Description if not otherwise provided
            if (
                not config.text_input
                and not config.csv_path
                and text_input is None
            ):
                if (
                    "Description" in df_for_description_extraction.columns
                    and not df_for_description_extraction.empty
                ):
                    descriptions_from_csv = df_for_description_extraction[
                        "Description"
                    ].tolist()
                    cleaned_descriptions_from_csv = [
                        clean_paper_content(desc)
                        for desc in descriptions_from_csv
                        if pd.notna(desc)
                    ]
                    if cleaned_descriptions_from_csv:
                        if len(cleaned_descriptions_from_csv) == 1:
                            text_input = cleaned_descriptions_from_csv[0]
                        else:
                            text_input = cleaned_descriptions_from_csv
                        self.logger.info(
                            f"Used 'Description' column from CSV as text_input ({len(cleaned_descriptions_from_csv)} items)"
                        )

                        # Set title and speakers from first row
                        if not df_for_description_extraction.empty:
                            if (
                                not session_code_filter_applied_and_matched
                                and not date_filter_applied_and_matched
                            ):
                                article_title = (
                                    df_for_description_extraction["Title"].iloc[0]
                                    if "Title" in df_for_description_extraction.columns
                                    else config.article_title
                                )
                                speakers = (
                                    df_for_description_extraction["Speakers"].iloc[0]
                                    if "Speakers"
                                    in df_for_description_extraction.columns
                                    and pd.notna(
                                        df_for_description_extraction["Speakers"].iloc[
                                            0
                                        ]
                                    )
                                    else None
                                )
                                self.logger.info(
                                    f"Using article title/speakers from CSV: {article_title}"
                                )

        except Exception as e:
            self.logger.error(
                f"Error processing CSV file: {e}. Using default title: {article_title}"
            )

        return article_title, speakers, text_input


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
            # Store report_id for use in filename generation
            self.report_id = config.report_id
            
            # Configure prompts based on the configuration
            configure_prompts(config.prompt_type)
            processing_logs.append(
                f"Prompts configured for {config.prompt_type.value} type"
            )

            # Perform lazy import of knowledge_storm now that prompts are configured
            _lazy_import_knowledge_storm()

            # Load API keys (requires knowledge_storm.utils.load_api_key)
            self._load_api_keys()
            processing_logs.append("API keys loaded successfully")

            # Validate inputs
            if (
                not config.topic
                and not config.text_input
                and not config.csv_path
                and not config.caption_files
            ):
                raise ValueError(
                    "Either a topic, text input, CSV file, or caption files must be provided."
                )

            # Setup language models and configurations
            lm_configs = self._setup_language_models(config)
            processing_logs.append(
                f"Language models configured for {config.model_provider}"
            )

            # Set up engine arguments
            engine_args = STORMWikiRunnerArguments(
                output_dir=config.output_dir,
                article_title=config.article_title,
                max_conv_turn=config.max_conv_turn,
                max_perspective=config.max_perspective,
                search_top_k=config.search_top_k,
                initial_retrieval_k=config.initial_retrieval_k,
                final_context_k=config.final_context_k,
                max_thread_num=config.max_thread_num,
                recent_content_only=config.time_range is not None,
                reranker_threshold=config.reranker_threshold,
                time_range=config.time_range.value if config.time_range else None,
                text_input=config.text_input,
                report_id=config.report_id,
            )

            # Setup retriever
            rm = self._setup_retriever(config, engine_args)
            processing_logs.append(f"Retriever configured: {config.retriever}")

            # Initialize STORM Wiki runner
            runner = STORMWikiRunner(engine_args, lm_configs, rm)
            runner.author_json = config.author_json

            # Pass selected_files_paths and user_id for image path fixing
            if config.selected_files_paths:
                runner.selected_files_paths = config.selected_files_paths
            if config.user_id:
                runner.user_id = config.user_id

            # Process CSV metadata
            article_title, speakers, csv_text_input = self._process_csv_metadata(
                config
            )
            processing_logs.append("CSV metadata processed")

            # Use text_input directly if provided, otherwise use CSV text input
            if config.text_input:
                # text_input is already consolidated from the input processor
                runner.text_input = config.text_input
                processing_logs.append("Text input loaded")
            elif csv_text_input:
                runner.text_input = csv_text_input
                processing_logs.append("CSV text input loaded as text input")
            
            runner.speakers = speakers
            runner.article_title = article_title

            # Validate that we have content to work with
            if not config.topic and not runner.text_input:
                raise ValueError(
                    "Either a topic or text input must be provided for report generation."
                )

            # Set article directory name (but don't create subfolder - use output_dir directly)
            folder_name = truncate_filename(
                article_title.replace(" ", "_").replace("/", "_")
            )
            runner.article_dir_name = folder_name

            # Use output directory directly without creating subfolder
            article_output_dir = config.output_dir
            os.makedirs(article_output_dir, exist_ok=True)
            runner.storm_article_generation.query_logger = QueryLogger(
                article_output_dir
            )

            # Handle figure data if provided
            if hasattr(config, 'figure_data') and config.figure_data:
                runner.figure_data = config.figure_data
                processing_logs.append(f"Figure data loaded: {len(config.figure_data)} figures")

            # Log processing information
            if config.topic:
                if runner.text_input:
                    self.logger.info(
                        f"Topic and text input provided. The topic ('{config.topic}') will be improved using the text input."
                    )
                else:
                    self.logger.info(
                        f"Only topic ('{config.topic}') provided. Using the provided topic for improvement/guidance."
                    )
            else:
                self.logger.info(
                    "Text input provided (no topic). Key technology or innovations will be extracted from the text input to form a topic."
                )

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

            # Collect all files from the output directory
            import glob
            all_files = glob.glob(os.path.join(article_output_dir, "*"))
            # Filter to only include files (not directories) and common report file types
            generated_files.extend([
                f for f in all_files 
                if os.path.isfile(f) and any(f.endswith(ext) for ext in 
                    ['.md', '.txt', '.json', '.jsonl', '.html', '.pdf', '.csv'])
            ])
            
            self.logger.info(f"Collected {len(generated_files)} files from output directory: {[os.path.basename(f) for f in generated_files]}")
            
            # Also collect the basic storm files specifically (for backwards compatibility)
            basic_storm_files = [
                os.path.join(article_output_dir, "storm_gen_outline.txt"),
                os.path.join(article_output_dir, "storm_gen_article.md"),
                os.path.join(article_output_dir, "storm_gen_article_polished.md"),
            ]
            # Add any basic files that weren't already collected
            for f in basic_storm_files:
                if f not in generated_files and os.path.exists(f):
                    generated_files.append(f)

            # Store the final processed report content for Django FileField storage
            # The actual file will be created by job_service.py using Django FileField
            final_report_content = None
            if config.post_processing:
                polished_article_path = os.path.join(
                    article_output_dir, "storm_gen_article_polished.md"
                )
                if os.path.exists(polished_article_path):
                    # Apply full post-processing (image paths + citations removal + etc.)
                    if config.selected_files_paths:
                        # Storm files already have image path fixing, but we need to apply it again
                        # plus other post-processing for the final Report content
                        with open(polished_article_path, "r", encoding="utf-8") as f:
                            content = f.read()


                        # Apply other post-processing (citations, captions, placeholders)
                        from agents.report_agent.utils.post_processing import (
                            remove_citations,
                            remove_captions,
                            remove_figure_placeholders,
                        )

                        content = remove_citations(content, True)
                        content = remove_captions(content, True)
                        content = remove_figure_placeholders(content, True)

                        final_report_content = content
                        processing_logs.append(
                            "Full post-processing applied to Report content"
                        )
                    else:
                        # No image path fixing needed, just apply traditional post-processing
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as temp_file:
                            process_file(
                                polished_article_path, temp_file.name, config.post_processing
                            )
                            with open(temp_file.name, 'r', encoding='utf-8') as f:
                                final_report_content = f.read()
                            os.unlink(temp_file.name)
                        processing_logs.append(
                            "Traditional post-processing applied to Report content"
                        )

                    processing_logs.append(
                        "Generated final Report content (will be stored via Django FileField)"
                    )
            else:
                processing_logs.append(
                    "Post-processing disabled: Only storm_gen_article.md and storm_gen_article_polished.md generated"
                )

            # Use generated article title if available, otherwise use original
            final_article_title = getattr(runner, 'generated_article_title', None) or article_title
            
            # Create report_{id}.md file with the final content
            if final_report_content and config.report_id:
                report_file_path = os.path.join(article_output_dir, f"report_{config.report_id}.md")
                try:
                    with open(report_file_path, 'w', encoding='utf-8') as f:
                        f.write(final_report_content)
                    generated_files.append(report_file_path)
                    self.logger.info(f"Created report_{config.report_id}.md file")
                except Exception as e:
                    self.logger.warning(f"Failed to create report_{config.report_id}.md file: {e}")
            
            return ReportGenerationResult(
                success=True,
                article_title=final_article_title,
                output_directory=article_output_dir,
                generated_files=[f for f in generated_files if os.path.exists(f)],
                processing_logs=processing_logs,
                report_content=final_report_content,
                generated_topic=getattr(runner, 'generated_topic', None),
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
                processing_logs=processing_logs,
                generated_topic=None,
            )


# Convenience function for backward compatibility and simple usage
def generate_report_from_config(
    config: ReportGenerationConfig, secrets_path: str = "secrets.toml"
) -> ReportGenerationResult:
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
        do_polish_article=True,
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
        do_polish_article=True,
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
