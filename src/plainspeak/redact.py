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
_CARD_LIKE = re.compile(r"\b\d{13,19}\b")  # solid card / long account numbers
# Grouped card / account numbers, e.g. "4111 1111 1111 1111" or
# "4111-1111-1111-1111" or the 4-6-5 Amex shape. Anchored on a 4-digit lead
# with 2+ following groups so it cannot swallow a phone or SSN; the 13-19
# total-digit guard below keeps phones (10), SSNs (9), and dates out.
_CARD_GROUPED = re.compile(r"\b\d{4}(?:[ -]\d{2,6}){2,4}\b")
_CARD_DIGITS = re.compile(r"\d")

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

    def _sub_grouped_cards(s: str) -> str:
        # Only treat a grouped run as a card when its total digit count is in
        # the 13-19 card/account range; this excludes phones, SSNs, and dates.
        def _replace(m: re.Match[str]) -> str:
            if 13 <= len(_CARD_DIGITS.findall(m.group(0))) <= 19:
                report.cards += 1
                return _PLACEHOLDER["cards"]
            return m.group(0)

        return _CARD_GROUPED.sub(_replace, s)

    clean = text
    clean = _sub(_EMAIL, "emails", clean)
    clean = _sub(_SSN_LIKE, "ids", clean)
    clean = _sub(_PHONE, "phones", clean)
    clean = _sub_grouped_cards(clean)
    clean = _sub(_CARD_LIKE, "cards", clean)
    return clean, report
