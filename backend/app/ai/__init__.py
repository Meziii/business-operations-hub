from typing import TYPE_CHECKING

from app.ai.triage import MockTriageProvider, TriageProvider
from app.config import get_settings

if TYPE_CHECKING:
    from app.modules.documents.extract import DocumentExtractor


def get_document_extractor() -> "DocumentExtractor":
    """Même règle que le tri : Claude si configuré, sinon le mode démonstration (NFR-04)."""
    from app.modules.documents.extract import MockDocumentExtractor

    settings = get_settings()
    if settings.ai_provider == "claude" and settings.anthropic_api_key:
        from app.modules.documents.claude_extract import ClaudeDocumentExtractor

        return ClaudeDocumentExtractor(settings.ai_model, settings.anthropic_api_key)
    return MockDocumentExtractor()


def get_triage_provider() -> TriageProvider:
    """Claude si AI_PROVIDER=claude et une clé est fournie ; sinon le mode démonstration (NFR-04)."""
    settings = get_settings()
    if settings.ai_provider == "claude" and settings.anthropic_api_key:
        from app.ai.claude import ClaudeTriageProvider

        return ClaudeTriageProvider(settings.ai_model, settings.anthropic_api_key)
    return MockTriageProvider()
