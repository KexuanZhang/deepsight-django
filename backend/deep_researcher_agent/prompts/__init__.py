"""
Prompts module for configurable prompt management.
Supports both financial and general prompts.
"""

import os
from typing import Union, Optional
from enum import Enum


class PromptType(str, Enum):
    FINANCIAL = "financial"
    GENERAL = "general"


class PromptModule:
    """A wrapper class for accessing prompt docstrings."""

    def __init__(self, prompt_type: PromptType = PromptType.GENERAL):
        self.prompt_type = prompt_type
        self._load_prompts()

    def _load_prompts(self):
        """Load the appropriate prompt module based on prompt_type."""
        if self.prompt_type == PromptType.FINANCIAL:
            from . import financial_prompts as prompts_module
        else:
            from . import general_prompts as prompts_module

        # Copy all attributes from the selected prompts module
        for attr_name in dir(prompts_module):
            if not attr_name.startswith("_"):
                setattr(self, attr_name, getattr(prompts_module, attr_name))


# Global variable to store the current prompt configuration
_current_prompt_type = PromptType.GENERAL
_prompt_module_instance = None


def configure_prompts(prompt_type: Union[PromptType, str] = PromptType.GENERAL):
    """Configure the global prompt type."""
    global _current_prompt_type, _prompt_module_instance

    if isinstance(prompt_type, str):
        prompt_type = PromptType(prompt_type.lower())

    _current_prompt_type = prompt_type
    _prompt_module_instance = None  # Reset to force reload


def import_prompts() -> PromptModule:
    """Import and return the configured prompts module."""
    global _prompt_module_instance

    if _prompt_module_instance is None:
        _prompt_module_instance = PromptModule(_current_prompt_type)

    return _prompt_module_instance


def get_current_prompt_type() -> PromptType:
    """Get the currently configured prompt type."""
    return _current_prompt_type
