from app.config import settings
from app.providers.base import BaseProvider
from app.providers.claude import ClaudeProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.groq_provider import GroqProvider
from app.providers.ollama import OllamaProvider
from app.providers.mock_provider import MockProvider


def get_provider() -> BaseProvider:
    """Factory: returns the configured AI provider instance."""
    providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "ollama": OllamaProvider,
        "mock": MockProvider,
    }
    provider_cls = providers.get(settings.ai_provider)
    if not provider_cls:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}. Use: {list(providers.keys())}")
    return provider_cls()
