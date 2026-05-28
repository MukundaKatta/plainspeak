"""plainspeak — turn dense official letters into plain language, a checklist
of actions, and the deadlines that matter. PII is stripped before any LLM
call. Ships a keyless deterministic backend so it runs anywhere."""

from __future__ import annotations

from .backends import (
    AnthropicBackend,
    Backend,
    GeminiBackend,
    OllamaBackend,
    StubBackend,
)
from .core import (
    ActionItem,
    Simplifier,
    SimplifyResult,
    extract_actions,
    find_dates,
    grade_level,
)
from .redact import RedactionReport, redact_pii

__version__ = "0.1.0"

__all__ = [
    "Simplifier",
    "SimplifyResult",
    "ActionItem",
    "grade_level",
    "extract_actions",
    "find_dates",
    "redact_pii",
    "RedactionReport",
    "Backend",
    "StubBackend",
    "GeminiBackend",
    "AnthropicBackend",
    "OllamaBackend",
    "__version__",
]
