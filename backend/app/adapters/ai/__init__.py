"""AI Adapter Factory.

Owned by AI Academic Summary feature.
"""

from __future__ import annotations

from app.adapters.ai.base import AiAdapter
import app.config as config_module


def get_ai_adapter() -> AiAdapter:
    """Return the configured AI adapter instance.

    Reads AI_ENGINE from settings and returns the corresponding adapter.
    Fails fast on unknown engine values — no silent fallbacks.

    Returns:
        An AiAdapter implementation.

    Raises:
        ValueError: If AI_ENGINE is not a recognized value.
    """
    settings = config_module.settings
    engine = settings.AI_ENGINE

    if engine == "fake":
        from app.adapters.ai.fake_adapter import create_fake_adapter
        return create_fake_adapter(mode="success")

    if engine == "ollama":
        from app.adapters.ai.ollama_adapter import OllamaAdapter
        return OllamaAdapter()

    raise ValueError(
        f"Unknown AI_ENGINE: '{engine}'. "
        f"Supported values: 'fake', 'ollama'"
    )