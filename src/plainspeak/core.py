"""plainspeak core: turn a dense official document into plain language,
a checklist of actions, and the deadlines that matter — with PII stripped
before the model ever sees the text.

    from plainspeak import Simplifier
    result = Simplifier().simplify(letter_text)
    print(result.plain_summary)
    for item in result.action_items:
        print("-", item.text, item.due or "")
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field

from .backends import Backend, StubBackend, _split_sentences
from .redact import redact_pii

# ---- reading grade ---------------------------------------------------------

_WORD = re.compile(r"[A-Za-z']+")


def _count_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def grade_level(text: str) -> float:
    """Flesch-Kincaid grade level. Higher = harder to read.

    A benefits letter often lands around grade 14-18; plain language for a
    general audience targets grade 6-8.
    """
    sentences = _split_sentences(text)
    words = _WORD.findall(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    return round(max(0.0, grade), 1)


# ---- action + date extraction ---------------------------------------------

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
_DATE_PATTERNS = [
    re.compile(rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:,?\s+\d{{4}})?", re.IGNORECASE),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(
        r"\bwithin\s+\d+\s+(?:days|weeks|months|business days)\b", re.IGNORECASE
    ),
]

_ACTION_CUES = (
    "must",
    "please",
    "you need to",
    "you should",
    "submit",
    "pay",
    "return the",
    "complete",
    "verify",
    "contact",
    "call",
    "provide",
    "sign",
    "send",
    "reply",
    "respond",
    "apply",
    "bring",
    "upload",
)


def find_dates(text: str) -> list[str]:
    """All date-like strings in document order, de-duplicated."""
    seen: dict[str, None] = {}
    spans: list[tuple[int, str]] = []
    for pat in _DATE_PATTERNS:
        for m in pat.finditer(text):
            spans.append((m.start(), m.group(0).strip()))
    for _, value in sorted(spans, key=lambda x: x[0]):
        norm = re.sub(r"\s+", " ", value)
        if norm not in seen:
            seen[norm] = None
    return list(seen)


@dataclass
class ActionItem:
    text: str
    due: str | None = None


def extract_actions(text: str) -> list[ActionItem]:
    items: list[ActionItem] = []
    for sentence in _split_sentences(text):
        low = sentence.lower()
        if any(cue in low for cue in _ACTION_CUES):
            dates = find_dates(sentence)
            items.append(
                ActionItem(text=sentence.strip(), due=dates[0] if dates else None)
            )
    return items


# ---- result ----------------------------------------------------------------


@dataclass
class SimplifyResult:
    plain_summary: str
    action_items: list[ActionItem]
    key_dates: list[str]
    reading_level: str
    backend: str
    original_chars: int
    simplified_chars: int
    original_grade: float
    simplified_grade: float
    redactions: int

    @property
    def grade_drop(self) -> float:
        return round(self.original_grade - self.simplified_grade, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["grade_drop"] = self.grade_drop
        return d


# ---- simplifier ------------------------------------------------------------


@dataclass
class Simplifier:
    """Configure once, reuse. Defaults to the keyless StubBackend so the
    whole pipeline runs offline."""

    backend: Backend = field(default_factory=StubBackend)
    reading_level: str = "grade-6"
    language: str = "en"
    redact: bool = True
    audit_path: str | None = None

    def simplify(
        self,
        text: str,
        *,
        reading_level: str | None = None,
        language: str | None = None,
    ) -> SimplifyResult:
        level = reading_level or self.reading_level
        lang = language or self.language

        original_grade = grade_level(text)

        work = text
        redactions = 0
        if self.redact:
            work, report = redact_pii(text)
            redactions = report.total

        simplified = self.backend.rewrite(work, reading_level=level, language=lang)

        result = SimplifyResult(
            plain_summary=simplified,
            action_items=extract_actions(simplified),
            key_dates=find_dates(work),
            reading_level=level,
            backend=getattr(self.backend, "name", type(self.backend).__name__),
            original_chars=len(text),
            simplified_chars=len(simplified),
            original_grade=original_grade,
            simplified_grade=grade_level(simplified),
            redactions=redactions,
        )
        self._audit(result)
        return result

    def _audit(self, result: SimplifyResult) -> None:
        """Append one privacy-safe JSONL line. Never logs document text."""
        if not self.audit_path:
            return
        os.makedirs(
            os.path.dirname(os.path.abspath(self.audit_path)) or ".", exist_ok=True
        )
        event = {
            "ts": round(time.time(), 3),
            "backend": result.backend,
            "reading_level": result.reading_level,
            "original_chars": result.original_chars,
            "simplified_chars": result.simplified_chars,
            "original_grade": result.original_grade,
            "simplified_grade": result.simplified_grade,
            "grade_drop": result.grade_drop,
            "redactions": result.redactions,
            "action_items": len(result.action_items),
            "key_dates": len(result.key_dates),
        }
        with open(self.audit_path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, separators=(",", ":")) + "\n")
