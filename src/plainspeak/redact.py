"""PII redaction applied before any text leaves the machine for an LLM.

The whole point of plainspeak is to hand confusing official letters to a
model. Those letters are exactly where sensitive identifiers live: case
numbers, SSNs, phone numbers, emails. We strip them first so the model
(and the audit log) never see them. Redaction is deterministic and runs
with zero dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Order matters: emails first (they contain no digit-only runs), then the
# fixed-shape identifiers (SSN-style), then phones, then long card/account
# digit runs. Running long-digit-run last avoids it eating an SSN or phone.
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SSN_LIKE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")  # 882-44-1920, case/SSN ids
_PHONE = re.compile(r"\(?\b\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b")
_CARD_LIKE = re.compile(r"\b\d{13,19}\b")  # card / long account numbers

_PLACEHOLDER = {
    "emails": "[EMAIL]",
    "ids": "[ID]",
    "phones": "[PHONE]",
    "cards": "[CARD]",
}


@dataclass
class RedactionReport:
    """How many of each kind were removed. No raw values are kept."""

    emails: int = 0
    ids: int = 0
    phones: int = 0
    cards: int = 0

    @property
    def total(self) -> int:
        return self.emails + self.ids + self.phones + self.cards

    def to_dict(self) -> dict[str, int]:
        return {
            "emails": self.emails,
            "ids": self.ids,
            "phones": self.phones,
            "cards": self.cards,
            "total": self.total,
        }


def redact_pii(text: str) -> tuple[str, RedactionReport]:
    """Return (clean_text, report). Replaces PII with typed placeholders."""
    report = RedactionReport()

    def _sub(pattern: re.Pattern[str], field: str, s: str) -> str:
        count = len(pattern.findall(s))
        if count:
            setattr(report, field, getattr(report, field) + count)
            s = pattern.sub(_PLACEHOLDER[field], s)
        return s

    clean = text
    clean = _sub(_EMAIL, "emails", clean)
    clean = _sub(_SSN_LIKE, "ids", clean)
    clean = _sub(_PHONE, "phones", clean)
    clean = _sub(_CARD_LIKE, "cards", clean)
    return clean, report
