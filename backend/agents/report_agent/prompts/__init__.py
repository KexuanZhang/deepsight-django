"""
Prompts module for configurable prompt management.
Supports both financial and general prompts.
"""

from pathlib import Path
from typing import Union
from enum import Enum

import yaml

class PromptType(str, Enum):
    FINANCIAL = "financial"
    GENERAL = "general"
    PAPER = "paper"


class PromptModule:
    """A wrapper class for accessing prompt docstrings."""

    def __init__(self, prompt_type: PromptType = PromptType.GENERAL):
        self.prompt_type = prompt_type
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts from the corresponding YAML file and expose them as attributes."""
        filename_map = {
            PromptType.FINANCIAL: "financial_prompts.yaml",
            PromptType.GENERAL: "general_prompts.yaml",
            PromptType.PAPER: "paper_prompts.yaml",
        }

        yaml_file = filename_map.get(self.prompt_type)
        base_dir = Path(__file__).parent
        file_path = base_dir / yaml_file

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Accept both {prompts: {...}} or direct mapping
        prompts_dict = data.get("prompts", data)

        for key, value in prompts_dict.items():
            # Create attributes for each prompt key
            setattr(self, key, value)
            # Preserve original constant naming convention used throughout the codebase
            setattr(self, f"{key}_docstring", value)

# Global variable to store the current prompt configuration (deprecated)
_current_prompt_type = PromptType.GENERAL
_prompt_module_instance = None


def configure_prompts(prompt_type: Union[PromptType, str] = PromptType.GENERAL):
    """Configure the global prompt type. (Thread-safe version)"""
    global _current_prompt_type, _prompt_module_instance

    if isinstance(prompt_type, str):
        prompt_type = PromptType(prompt_type.lower())

    _current_prompt_type = prompt_type
    # Force immediate reload to ensure thread-safe operation
    _prompt_module_instance = PromptModule(prompt_type)


def create_prompt_module(prompt_type: Union[PromptType, str] = PromptType.GENERAL) -> PromptModule:
    """Create and return a prompt module instance for the specified prompt type."""
    if isinstance(prompt_type, str):
        prompt_type = PromptType(prompt_type.lower())
    
    return PromptModule(prompt_type)


def import_prompts() -> PromptModule:
    """Import and return the configured prompts module."""
    global _prompt_module_instance

    if _prompt_module_instance is None:
        _prompt_module_instance = PromptModule(_current_prompt_type)

    return _prompt_module_instance


def get_current_prompt_type() -> PromptType:
    """Get the currently configured prompt type."""
    return _current_prompt_type
