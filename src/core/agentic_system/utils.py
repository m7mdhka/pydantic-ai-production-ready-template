"""Agentic system utilities."""

from pydantic_ai import ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

from src.core.config import settings as app_settings


def get_chat_model(
    model_name: str,
    settings: ModelSettings,
) -> OpenAIChatModel:
    """Get a model from the model registry."""
    return OpenAIChatModel(
        model_name=model_name,
        settings=settings,
        provider=LiteLLMProvider(
            api_base=app_settings.litellm_base_url.unicode_string(),
        ),
    )
