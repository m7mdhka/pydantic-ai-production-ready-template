"""Agentic system utilities."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

from src.core.config import settings


def get_chat_model(model_name: str) -> OpenAIChatModel:
    """Get a model from the model registry."""
    return OpenAIChatModel(
        model_name=model_name,
        provider=LiteLLMProvider(
            api_base=settings.litellm_base_url.unicode_string(),
        ),
    )
