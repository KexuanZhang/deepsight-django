"""
Interfaces for report generation components.
"""

from .report_generator_interface import ReportGeneratorInterface
from .input_processor_interface import InputProcessorInterface
from .configuration_interface import ReportConfigurationInterface
from .file_storage_interface import FileStorageInterface

__all__ = [
    'ReportGeneratorInterface',
    'InputProcessorInterface',
    'ReportConfigurationInterface',
    'FileStorageInterface'
]