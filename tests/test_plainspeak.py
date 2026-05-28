"""plainspeak test suite. Runs fully offline against the StubBackend."""

from __future__ import annotations

import json

import pytest

from plainspeak import Simplifier, grade_level, redact_pii

SAMPLE = """NOTICE OF BENEFITS REDETERMINATION

Pursuant to Section 4.2 of the aforementioned policy, you are hereby notified that your eligibility for assistance shall be redetermined. In the event that the requested documentation is not received prior to June 6, 2026, your benefits will terminate.

You are required to remit the enclosed form and utilize the online portal to verify your income. Please contact our office at (555) 123-4567 or benefits@example.gov if you have questions. Your case number is 882-44-1920.
"""


# ---- reading grade ---------------------------------------------------------


def test_grade_level_orders_hard_above_easy():
    hard = "Pursuant to the aforementioned regulation, the applicant shall utilize the prescribed methodology."
    easy = "You must use this form. Call us if you need help."
    assert grade_level(hard) > grade_level(easy)


def test_grade_level_empty_is_zero():
    assert grade_level("") == 0.0
    assert grade_level("   ") == 0.0


def test_simplify_does_not_raise_grade():
    result = Simplifier().simplify(SAMPLE)
    assert result.original_grade > 8  # the sample is genuinely dense
    assert result.simplified_grade <= result.original_grade
    assert result.grade_drop >= 0


# ---- actions + dates -------------------------------------------------------


def test_action_items_extracted():
    result = Simplifier().simplify(SAMPLE)
    assert len(result.action_items) >= 2
    joined = " ".join(item.text.lower() for item in result.action_items)
    assert "contact" in joined


def test_key_dates_found():
    result = Simplifier().simplify(SAMPLE)
    assert "June 6, 2026" in result.key_dates


# ---- redaction -------------------------------------------------------------


def test_redaction_counts_each_kind():
    _, report = redact_pii(SAMPLE)
    assert report.emails == 1
    assert report.phones == 1
    assert report.ids == 1
    assert report.total == 3


def test_simplify_strips_pii_from_output():
    result = Simplifier().simplify(SAMPLE)
    assert result.redactions == 3
    assert "benefits@example.gov" not in result.plain_summary
    assert "(555) 123-4567" not in result.plain_summary
    assert "882-44-1920" not in result.plain_summary
    assert "[EMAIL]" in result.plain_summary


def test_redaction_can_be_disabled():
    result = Simplifier(redact=False).simplify(SAMPLE)
    assert result.redactions == 0


# ---- backend + determinism -------------------------------------------------


def test_default_backend_is_stub():
    assert Simplifier().simplify(SAMPLE).backend == "stub"


def test_stub_is_deterministic():
    a = Simplifier().simplify(SAMPLE)
    b = Simplifier().simplify(SAMPLE)
    assert a.plain_summary == b.plain_summary


def test_to_dict_includes_grade_drop():
    d = Simplifier().simplify(SAMPLE).to_dict()
    assert "grade_drop" in d
    assert d["backend"] == "stub"


# ---- audit log -------------------------------------------------------------


def test_audit_log_is_written_and_privacy_safe(tmp_path):
    audit = tmp_path / "audit.jsonl"
    Simplifier(audit_path=str(audit)).simplify(SAMPLE)

    lines = audit.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])

    assert event["backend"] == "stub"
    assert event["redactions"] == 3
    assert event["key_dates"] == 1
    assert event["action_items"] >= 2
    # privacy: the audit log must never carry document text
    assert "plain_summary" not in event
    assert "text" not in event
    blob = json.dumps(event)
    assert "benefits@example.gov" not in blob
    assert "882-44-1920" not in blob
