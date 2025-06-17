# import os
# from pathlib import Path
# from typing import List, Optional, Annotated
# from pydantic import BaseModel, Field, ConfigDict
# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     # Use ConfigDict instead of class Config
#     model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
#     # Project configuration
#     PROJECT_NAME: str = "DeepSight Research Platform"
#     VERSION: str = "1.0.0"
#     DESCRIPTION: str = "AI-powered research report generation platform"
#     API_V1_STR: str = "/api/v1"
    
#     # CORS settings - Use Annotated with Field for environment variables
#     BACKEND_CORS_ORIGINS: Annotated[List[str], Field(default=["*"])] = ["*"]
    
#     # File and path settings
#     PROJECT_ROOT: Annotated[str, Field(default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
#     @property
#     def deep_researcher_dir(self) -> Path:
#         return Path(self.PROJECT_ROOT) / "deep_researcher_agent"
    
#     @property
#     def secrets_path(self) -> Path:
#         return self.deep_researcher_dir / "secrets.toml"
    
#     # API settings
#     MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
#     ALLOWED_FILE_TYPES: List[str] = [".txt", ".md", ".pdf", ".csv", ".mp4", ".avi", ".mov"]
    
#     # Background job settings
#     MAX_CONCURRENT_JOBS: Annotated[int, Field(default=3)] = 3
#     JOB_TIMEOUT: Annotated[int, Field(default=3600)] = 3600  # 1 hour in seconds
    
#     # Logging
#     LOG_LEVEL: Annotated[str, Field(default="INFO")] = "INFO"
    
#     # Environment
#     ENVIRONMENT: Annotated[str, Field(default="development")] = "development"
    
#     # Redis configuration for job queues
#     REDIS_HOST: Annotated[str, Field(default="localhost")] = "localhost"
#     REDIS_PORT: Annotated[int, Field(default=6379)] = 6379
#     REDIS_DB: Annotated[int, Field(default=0)] = 0
#     REDIS_PASSWORD: Annotated[Optional[str], Field(default=None)] = None
    
#     @property
#     def redis_url(self) -> str:
#         if self.REDIS_PASSWORD:
#             return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
#         return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
#     # Report generation settings
#     DEEP_REPORT_GENERATOR_PATH: Annotated[str, Field(default="deep_report_generator.py")] = "deep_report_generator.py"
    
#     @property
#     def reports_output_dir(self) -> str:
#         """Get the absolute path to the reports output directory in the root data folder"""
#         return str(Path(self.PROJECT_ROOT) / "data" / "reports")
    
#     # File storage
#     UPLOAD_DIR: Annotated[str, Field(default="data/uploads")] = "data/uploads"
#     PARSED_FILES_DIR: Annotated[str, Field(default="data/parsed_files")] = "data/parsed_files"
    
#     # WebSocket settings
#     WS_HEARTBEAT_INTERVAL: Annotated[int, Field(default=30)] = 30
#     WS_CONNECTION_TIMEOUT: Annotated[int, Field(default=300)] = 300
    
#     # Podcast generation settings
#     OPENAI_API_KEY: Annotated[Optional[str], Field(default=None)] = None
#     OPENAI_ORG: Annotated[Optional[str], Field(default=None)] = None
#     OPENAI_PROJECT: Annotated[Optional[str], Field(default=None)] = None
#     PODCAST_OUTPUT_DIR: Annotated[str, Field(default="data/generated_podcasts")] = "data/generated_podcasts"
#     PODCAST_JOB_TIMEOUT: Annotated[str, Field(default="30m")] = "30m"  # 30 minutes for podcast generation
    
#     # MiniMax TTS settings
#     MINIMAX_API_KEY: Annotated[Optional[str], Field(default=None)] = None
#     MINIMAX_GROUP_ID: Annotated[Optional[str], Field(default=None)] = None
    
#     # Feature extraction settings
#     ENABLE_ADVANCED_EXTRACTION: Annotated[bool, Field(default=True)] = True
#     EXTRACTION_TIMEOUT: Annotated[int, Field(default=7200)] = 7200  # 2 hours
    
#     # Storage settings
#     PROCESSED_FILES_DIR: Annotated[str, Field(default="data/processed_files")] = "data/processed_files"
#     EXTRACTIONS_DIR: Annotated[str, Field(default="data/extractions")] = "data/extractions"
    
#     # Advanced extraction settings
#     MAX_EXTRACTION_JOBS: Annotated[int, Field(default=5)] = 5
#     EXTRACTION_RESULTS_RETENTION_DAYS: Annotated[int, Field(default=7)] = 7
    
#     # Extraction job timeout settings
#     EXTRACTION_JOB_TIMEOUT: Annotated[str, Field(default="15m")] = "15m"  # 15 minutes for individual extraction
#     BATCH_EXTRACTION_JOB_TIMEOUT: Annotated[str, Field(default="30m")] = "30m"  # 30 minutes for batch extraction
    
#     # PDF extraction settings
#     DEFAULT_WHISPER_MODEL: Annotated[str, Field(default="base")] = "base"
#     MAX_PDF_PAGES: Annotated[Optional[int], Field(default=None)] = None
    
#     # Media extraction settings
#     DEFAULT_FRAME_INTERVAL: Annotated[int, Field(default=30)] = 30
#     MAX_FRAMES_PER_VIDEO: Annotated[int, Field(default=20)] = 20
    
#     # URL extraction settings
#     DEFAULT_URL_TIMEOUT: Annotated[int, Field(default=30)] = 30
#     ENABLE_JS_RENDERING: Annotated[bool, Field(default=True)] = True
    
#     @property
#     def all_cors_origins(self) -> List[str]:
#         return self.BACKEND_CORS_ORIGINS


# settings = Settings()


# def get_settings() -> Settings:
#     """Get the settings instance."""
#     return settings 

import os
from pathlib import Path
from typing import List, Optional, Annotated
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Tell Pydantic where to load env vars from
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # -------------------------------------------------------------------------
    # Database & Security (now with defaults)
    # -------------------------------------------------------------------------
    DATABASE_URL: Annotated[
        str,
        Field(
            default="sqlite:///./dev.db",
            description="SQLAlchemy database URL",
        )
    ] = "sqlite:///./dev.db"
    SECRET_KEY: Annotated[
        str,
        Field(
            default="CHANGE_ME_IN_PROD",
            description="JWT secret key",
        )
    ] = "CHANGE_ME_IN_PROD"

    # -------------------------------------------------------------------------
    # Project metadata
    # -------------------------------------------------------------------------
    PROJECT_NAME:  str = "DeepSight Research Platform"
    VERSION:       str = "1.0.0"
    DESCRIPTION:   str = "AI-powered research report generation platform"
    API_V1_STR:    str = "/api/v1"

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: Annotated[List[str], Field(default=["*"])] = ["*"]

    @property
    def all_cors_origins(self) -> List[str]:
        return self.BACKEND_CORS_ORIGINS

    # -------------------------------------------------------------------------
    # Paths & file storage
    # -------------------------------------------------------------------------
    PROJECT_ROOT: Annotated[
        str,
        Field(
            default=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
        ),
    ] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    @property
    def deep_researcher_dir(self) -> Path:
        return Path(self.PROJECT_ROOT) / "deep_researcher_agent"

    @property
    def secrets_path(self) -> Path:
        return self.deep_researcher_dir / "secrets.toml"

    UPLOAD_DIR:         Annotated[str, Field(default="data/uploads")]            = "data/uploads"
    PARSED_FILES_DIR:   Annotated[str, Field(default="data/parsed_files")]      = "data/parsed_files"
    PROCESSED_FILES_DIR:Annotated[str, Field(default="data/processed_files")]    = "data/processed_files"
    EXTRACTIONS_DIR:    Annotated[str, Field(default="data/extractions")]        = "data/extractions"

    LOG_LEVEL: Annotated[str, Field(default="INFO", description="Root logger level")] = "INFO"

    # -------------------------------------------------------------------------
    # Upload constraints
    # -------------------------------------------------------------------------
    MAX_UPLOAD_SIZE:    int     = 100 * 1024 * 1024  # 100 MB
    ALLOWED_FILE_TYPES: List[str] = [".txt", ".md", ".pdf", ".csv", ".mp4", ".avi", ".mov"]

    # -------------------------------------------------------------------------
    # Background jobs & Redis
    # -------------------------------------------------------------------------
    MAX_CONCURRENT_JOBS:               Annotated[int, Field(default=3)] = 3
    JOB_TIMEOUT:                      Annotated[int, Field(default=3600)] = 3600

    REDIS_HOST:   Annotated[str, Field(default="localhost")] = "localhost"
    REDIS_PORT:   Annotated[int, Field(default=6379)]       = 6379
    REDIS_DB:     Annotated[int, Field(default=0)]          = 0
    REDIS_PASSWORD: Annotated[Optional[str], Field(default=None)] = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # -------------------------------------------------------------------------
    # Report generation & output
    # -------------------------------------------------------------------------
    DEEP_REPORT_GENERATOR_PATH: Annotated[str, Field(default="deep_report_generator.py")] = "deep_report_generator.py"

    @property
    def reports_output_dir(self) -> str:
        return str(Path(self.PROJECT_ROOT) / "data" / "reports")

    # -------------------------------------------------------------------------
    # WebSocket
    # -------------------------------------------------------------------------
    WS_HEARTBEAT_INTERVAL: Annotated[int, Field(default=30)]  = 30
    WS_CONNECTION_TIMEOUT: Annotated[int, Field(default=300)] = 300

    # -------------------------------------------------------------------------
    # Podcast generation
    # -------------------------------------------------------------------------
    OPENAI_API_KEY:    Annotated[Optional[str], Field(default=None)] = None
    OPENAI_ORG:        Annotated[Optional[str], Field(default=None)] = None
    OPENAI_PROJECT:    Annotated[Optional[str], Field(default=None)] = None
    PODCAST_OUTPUT_DIR:Annotated[str,  Field(default="data/generated_podcasts")] = "data/generated_podcasts"
    PODCAST_JOB_TIMEOUT:Annotated[str,  Field(default="30m")] = "30m"

    # -------------------------------------------------------------------------
    # TTS / MiniMax
    # -------------------------------------------------------------------------
    MINIMAX_API_KEY:  Annotated[Optional[str], Field(default=None)] = None
    MINIMAX_GROUP_ID: Annotated[Optional[str], Field(default=None)] = None

    # -------------------------------------------------------------------------
    # Feature extraction
    # -------------------------------------------------------------------------
    ENABLE_ADVANCED_EXTRACTION:              Annotated[bool,  Field(default=True)] = True
    EXTRACTION_TIMEOUT:                      Annotated[int,   Field(default=7200)] = 7200
    MAX_EXTRACTION_JOBS:                     Annotated[int,   Field(default=5)]    = 5
    EXTRACTION_RESULTS_RETENTION_DAYS:       Annotated[int,   Field(default=7)]    = 7
    EXTRACTION_JOB_TIMEOUT:                  Annotated[str,   Field(default="15m")] = "15m"
    BATCH_EXTRACTION_JOB_TIMEOUT:            Annotated[str,   Field(default="30m")] = "30m"

    DEFAULT_WHISPER_MODEL:                   Annotated[str,   Field(default="base")]  = "base"
    MAX_PDF_PAGES:                           Annotated[Optional[int], Field(default=None)] = None
    DEFAULT_FRAME_INTERVAL:                  Annotated[int, Field(default=30)] = 30
    MAX_FRAMES_PER_VIDEO:                    Annotated[int, Field(default=20)] = 20
    DEFAULT_URL_TIMEOUT:                     Annotated[int, Field(default=30)] = 30
    ENABLE_JS_RENDERING:                     Annotated[bool, Field(default=True)] = True

# create a single shared Settings instance
settings = Settings()

def get_settings() -> Settings:
    """Dependency to retrieve settings instance."""
    return settings
