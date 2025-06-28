"""
Deep Research Agent - AI-powered research report generation.

This package provides comprehensive research report generation capabilities
using state-of-the-art language models and retrieval systems.
"""

import sys
import os
from pathlib import Path

# CRITICAL: Setup path to prioritize local knowledge_storm BEFORE any imports
_PACKAGE_DIR = Path(__file__).parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

# Now import from deep_report_generator (this will now find local knowledge_storm)
from .deep_report_generator import (
    DeepReportGenerator,
    ReportGenerationConfig,
    ReportGenerationResult,
    ModelProvider,
    RetrieverType,
    TimeRange,
    generate_report_from_config,
)

# Version info
__version__ = "1.0.0"
__author__ = "DeepSight Team"

# Public API
__all__ = [
    "DeepReportGenerator",
    "ReportGenerationConfig",
    "ReportGenerationResult",
    "ModelProvider",
    "RetrieverType",
    "TimeRange",
    "generate_report_from_config",
]


# Package-level configuration
def configure_logging(level="INFO"):
    """Configure package-wide logging."""
    import logging

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Initialize package
configure_logging()
