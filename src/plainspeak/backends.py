"""Rewrite backends. A backend turns dense text into plain language.

`StubBackend` is a deterministic, dependency-free rewriter so the demo and
test suite run with no API key. The LLM backends (`GeminiBackend`,
`AnthropicBackend`, `OllamaBackend`) are thin and import their SDK lazily,
so installing plainspeak core never pulls a vendor dependency.

Every backend implements one method:

    rewrite(text, *, reading_level, language) -> str
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

# Multi-word phrases first so they match before their single-word parts.
_LEGALESE: dict[str, str] = {
    "in accordance with": "following",
    "in the event that": "if",
    "with respect to": "about",
    "for the purpose of": "to",
    "pursuant to": "under",
    "prior to": "before",
    "subsequent to": "after",
    "in order to": "to",
    "at this time": "now",
    "the aforementioned": "this",
    "is required to": "must",
    "are required to": "must",
    "aforementioned": "this",
    "notwithstanding": "despite",
    "hereby": "",
    "herein": "here",
    "thereof": "of it",
    "utilize": "use",
    "commence": "start",
    "terminate": "end",
    "remit": "pay",
    "furnish": "give",
    "indicate": "show",
    "endeavor": "try",
    "ascertain": "find out",
    "shall": "must",
    "shall not": "must not",
}


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _simplify_sentence(sentence: str) -> str:
    out = sentence
    for phrase, repl in _LEGALESE.items():
        out = re.sub(rf"\b{re.escape(phrase)}\b", repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+([.,;:])", r"\1", out)  # tidy space before punctuation
    out = re.sub(r"\s+", " ", out).strip()
    return out


@runtime_checkable
class Backend(Protocol):
    name: str

    def rewrite(self, text: str, *, reading_level: str, language: str) -> str: ...


class StubBackend:
    """Deterministic plain-language rewriter. No network, no key.

    Swaps common legalese for plain words and breaks run-on sentences at
    semicolons and ", and " joins. Good enough to show a real reading-grade
    drop in the demo; swap in an LLM backend for production quality.
    """

    name = "stub"

    def rewrite(self, text: str, *, reading_level: str = "grade-6", language: str = "en") -> str:
        rewritten: list[str] = []
        for sentence in _split_sentences(text):
            simple = _simplify_sentence(sentence)
            if len(simple.split()) > 18:
                clauses = re.split(r";\s*|,\s+and\s+", simple)
                for clause in clauses:
                    clause = clause.strip()
                    if clause:
                        rewritten.append(clause[0].upper() + clause[1:])
            else:
                rewritten.append(simple)
        return " ".join(s if s.endswith((".", "!", "?")) else s + "." for s in rewritten)


_PROMPT = (
    "Rewrite the following official document in plain {language} at a "
    "{reading_level} reading level. Keep every date, amount, and deadline "
    "exact. Use short sentences. Do not invent facts. Return only the "
    "rewritten text.\n\n---\n{text}\n---"
)


class GeminiBackend:
    """Google Gemini backend. Requires `google-genai` and GEMINI_API_KEY."""

    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None):
        from google import genai  # lazy import

        import os

        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self._model = model

    def rewrite(self, text: str, *, reading_level: str = "grade-6", language: str = "en") -> str:
        prompt = _PROMPT.format(language=language, reading_level=reading_level, text=text)
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        return (resp.text or "").strip()


class AnthropicBackend:
    """Anthropic Claude backend. Requires `anthropic` and ANTHROPIC_API_KEY."""

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        import anthropic  # lazy import

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def rewrite(self, text: str, *, reading_level: str = "grade-6", language: str = "en") -> str:
        prompt = _PROMPT.format(language=language, reading_level=reading_level, text=text)
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()


class OllamaBackend:
    """Local Ollama backend. Requires a running ollama server. No key."""

    name = "ollama"

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self._model = model
        self._host = host.rstrip("/")

    def rewrite(self, text: str, *, reading_level: str = "grade-6", language: str = "en") -> str:
        import httpx  # lazy import

        prompt = _PROMPT.format(language=language, reading_level=reading_level, text=text)
        resp = httpx.post(
            f"{self._host}/api/generate",
            json={"model": self._model, "prompt": prompt, "stream": False},
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
