from app.ai.triage import MockTriageProvider, TriageProvider
from app.config import get_settings


def get_triage_provider() -> TriageProvider:
    """Claude si AI_PROVIDER=claude et une clé est fournie ; sinon le mode démonstration (NFR-04)."""
    settings = get_settings()
    if settings.ai_provider == "claude" and settings.anthropic_api_key:
        from app.ai.claude import ClaudeTriageProvider

        return ClaudeTriageProvider(settings.ai_model, settings.anthropic_api_key)
    return MockTriageProvider()
