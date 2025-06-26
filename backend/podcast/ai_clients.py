"""
AI client management module for podcast generation.

This module handles OpenAI and DeepSeek client initialization and management.
"""

import os
import logging
from django.conf import settings
import openai

logger = logging.getLogger(__name__)


class AIClientManager:
    """Manages AI clients for OpenAI and DeepSeek providers"""

    def __init__(self):
        # AI clients (lazy initialization to avoid startup errors)
        self._openai_client = None
        self._deepseek_client = None

        # AI provider configuration
        self.ai_provider = getattr(
            settings, "PODCAST_AI_PROVIDER", "openai"
        ).lower()  # 'openai' or 'deepseek'

    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            openai_api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv(
                "OPENAI_API_KEY"
            )
            if not openai_api_key:
                raise ValueError(
                    "OpenAI API key is not configured. Please set OPENAI_API_KEY in settings or environment."
                )

            self._openai_client = openai.OpenAI(
                api_key=openai_api_key,
                organization=getattr(settings, "OPENAI_ORG", None)
                or os.getenv("OPENAI_ORG"),
                project=getattr(settings, "OPENAI_PROJECT", None)
                or os.getenv("OPENAI_PROJECT"),
            )
        return self._openai_client

    @property
    def deepseek_client(self):
        """Lazy initialization of DeepSeek client."""
        if self._deepseek_client is None:
            deepseek_api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or os.getenv(
                "DEEPSEEK_API_KEY"
            )
            if not deepseek_api_key:
                raise ValueError(
                    "DeepSeek API key is not configured. Please set DEEPSEEK_API_KEY in settings or environment."
                )

            # DeepSeek uses OpenAI-compatible API
            self._deepseek_client = openai.OpenAI(
                api_key=deepseek_api_key, base_url="https://api.deepseek.com"
            )
        return self._deepseek_client

    @property
    def ai_client(self):
        """Get the configured AI client based on provider setting."""
        if self.ai_provider == "deepseek":
            return self.deepseek_client
        else:
            return self.openai_client

    def validate_ai_provider(self):
        """Validate that the configured AI provider is available and properly configured."""
        try:
            if self.ai_provider == "deepseek":
                # Test DeepSeek configuration
                _ = self.deepseek_client
                logger.info("DeepSeek provider validated successfully")
            else:
                # Test OpenAI configuration
                _ = self.openai_client
                logger.info("OpenAI provider validated successfully")
            return True
        except Exception as e:
            logger.error(f"AI provider validation failed for {self.ai_provider}: {e}")
            return False

    def get_model_name(self):
        """Get the model name for the current provider"""
        if self.ai_provider == "deepseek":
            return getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
        else:
            return getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")

    def create_chat_completion(self, messages, **kwargs):
        """Create a chat completion using the configured AI provider"""
        model = self.get_model_name()
        logger.info(f"Using {self.ai_provider} provider with model {model}")

        return self.ai_client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )


# Global singleton instance
ai_client_manager = AIClientManager()
