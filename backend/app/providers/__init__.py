from app.config import settings
from app.providers.base import BaseProvider
from app.providers.claude import ClaudeProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.ollama import OllamaProvider


def get_provider() -> BaseProvider:
    """Factory: returns the configured AI provider instance."""
    providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    provider_cls = providers.get(settings.ai_provider)
    if not provider_cls:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}. Use: {list(providers.keys())}")
    return provider_cls()
