"""plainspeak test suite.

Uses only the Python standard library (``unittest``) so it runs with zero
third-party dependencies. Runs fully offline against the keyless StubBackend.

Run it with::

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

# Make the package importable when the suite is run from a checkout that has
# not been ``pip install``-ed (the source lives under ``src/``).
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from plainspeak import (  # noqa: E402
    ActionItem,
    Backend,
    Simplifier,
    StubBackend,
    extract_actions,
    find_dates,
    grade_level,
    redact_pii,
)

SAMPLE = """NOTICE OF BENEFITS REDETERMINATION

Pursuant to Section 4.2 of the aforementioned policy, you are hereby notified that your eligibility for assistance shall be redetermined. In the event that the requested documentation is not received prior to June 6, 2026, your benefits will terminate.

You are required to remit the enclosed form and utilize the online portal to verify your income. Please contact our office at (555) 123-4567 or benefits@example.gov if you have questions. Your case number is 882-44-1920.
"""


class ReadingGradeTests(unittest.TestCase):
    def test_grade_level_orders_hard_above_easy(self) -> None:
        hard = (
            "Pursuant to the aforementioned regulation, the applicant shall "
            "utilize the prescribed methodology."
        )
        easy = "You must use this form. Call us if you need help."
        self.assertGreater(grade_level(hard), grade_level(easy))

    def test_grade_level_empty_is_zero(self) -> None:
        self.assertEqual(grade_level(""), 0.0)
        self.assertEqual(grade_level("   "), 0.0)

    def test_grade_level_returns_non_negative(self) -> None:
        # A trivially short sentence should never produce a negative grade.
        self.assertGreaterEqual(grade_level("Go now."), 0.0)

    def test_simplify_does_not_raise_grade(self) -> None:
        result = Simplifier().simplify(SAMPLE)
        self.assertGreater(result.original_grade, 8)  # the sample is dense
        self.assertLessEqual(result.simplified_grade, result.original_grade)
        self.assertGreaterEqual(result.grade_drop, 0)


class ActionAndDateTests(unittest.TestCase):
    def test_action_items_extracted(self) -> None:
        result = Simplifier().simplify(SAMPLE)
        self.assertGreaterEqual(len(result.action_items), 2)
        joined = " ".join(item.text.lower() for item in result.action_items)
        self.assertIn("contact", joined)

    def test_extract_actions_attaches_due_date(self) -> None:
        items = extract_actions("You must return the form by June 6, 2026.")
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], ActionItem)
        self.assertEqual(items[0].due, "June 6, 2026")

    def test_extract_actions_ignores_non_action_sentences(self) -> None:
        self.assertEqual(extract_actions("The weather is nice today."), [])

    def test_key_dates_found(self) -> None:
        result = Simplifier().simplify(SAMPLE)
        self.assertIn("June 6, 2026", result.key_dates)

    def test_find_dates_handles_multiple_formats(self) -> None:
        text = "Due 06/15/2026 and again on 2026-07-01 within 30 days."
        dates = find_dates(text)
        self.assertIn("06/15/2026", dates)
        self.assertIn("2026-07-01", dates)
        self.assertTrue(any("within 30 days" in d for d in dates))

    def test_find_dates_deduplicates_in_order(self) -> None:
        text = "June 6, 2026 ... and again June 6, 2026."
        self.assertEqual(find_dates(text), ["June 6, 2026"])


class RedactionTests(unittest.TestCase):
    def test_redaction_counts_each_kind(self) -> None:
        _, report = redact_pii(SAMPLE)
        self.assertEqual(report.emails, 1)
        self.assertEqual(report.phones, 1)
        self.assertEqual(report.ids, 1)
        self.assertEqual(report.total, 3)

    def test_redaction_report_to_dict(self) -> None:
        _, report = redact_pii(SAMPLE)
        d = report.to_dict()
        self.assertEqual(d["total"], 3)
        self.assertEqual(set(d), {"emails", "ids", "phones", "cards", "total"})

    def test_redaction_replaces_with_typed_placeholders(self) -> None:
        clean, _ = redact_pii("Reach me at a@b.com or 555-123-4567.")
        self.assertIn("[EMAIL]", clean)
        self.assertIn("[PHONE]", clean)
        self.assertNotIn("a@b.com", clean)

    def test_redaction_handles_long_card_numbers(self) -> None:
        clean, report = redact_pii("Card 4111111111111111 on file.")
        self.assertEqual(report.cards, 1)
        self.assertIn("[CARD]", clean)

    def test_redaction_no_pii_is_noop(self) -> None:
        text = "You must return the form by June 6, 2026."
        clean, report = redact_pii(text)
        self.assertEqual(clean, text)
        self.assertEqual(report.total, 0)

    def test_simplify_strips_pii_from_output(self) -> None:
        result = Simplifier().simplify(SAMPLE)
        self.assertEqual(result.redactions, 3)
        self.assertNotIn("benefits@example.gov", result.plain_summary)
        self.assertNotIn("(555) 123-4567", result.plain_summary)
        self.assertNotIn("882-44-1920", result.plain_summary)
        self.assertIn("[EMAIL]", result.plain_summary)

    def test_redaction_can_be_disabled(self) -> None:
        result = Simplifier(redact=False).simplify(SAMPLE)
        self.assertEqual(result.redactions, 0)


class BackendTests(unittest.TestCase):
    def test_default_backend_is_stub(self) -> None:
        self.assertEqual(Simplifier().simplify(SAMPLE).backend, "stub")

    def test_stub_backend_satisfies_protocol(self) -> None:
        self.assertIsInstance(StubBackend(), Backend)

    def test_stub_is_deterministic(self) -> None:
        a = Simplifier().simplify(SAMPLE)
        b = Simplifier().simplify(SAMPLE)
        self.assertEqual(a.plain_summary, b.plain_summary)

    def test_stub_replaces_legalese(self) -> None:
        out = StubBackend().rewrite("You shall utilize the form prior to filing.")
        low = out.lower()
        self.assertIn("must", low)
        self.assertIn("use", low)
        self.assertIn("before", low)
        self.assertNotIn("utilize", low)

    def test_custom_backend_is_used(self) -> None:
        class ShoutBackend:
            name = "shout"

            def rewrite(self, text: str, *, reading_level: str, language: str) -> str:
                return text.upper()

        result = Simplifier(backend=ShoutBackend()).simplify("you must pay.")
        self.assertEqual(result.backend, "shout")
        self.assertIn("YOU MUST PAY", result.plain_summary)


class ResultTests(unittest.TestCase):
    def test_to_dict_includes_grade_drop(self) -> None:
        d = Simplifier().simplify(SAMPLE).to_dict()
        self.assertIn("grade_drop", d)
        self.assertEqual(d["backend"], "stub")

    def test_char_counts_are_recorded(self) -> None:
        result = Simplifier().simplify(SAMPLE)
        self.assertEqual(result.original_chars, len(SAMPLE))
        self.assertGreater(result.simplified_chars, 0)


class AuditLogTests(unittest.TestCase):
    def test_audit_log_is_written_and_privacy_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = os.path.join(tmp, "audit.jsonl")
            Simplifier(audit_path=audit).simplify(SAMPLE)

            with open(audit, encoding="utf-8") as fp:
                lines = fp.read().strip().splitlines()

            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])

            self.assertEqual(event["backend"], "stub")
            self.assertEqual(event["redactions"], 3)
            self.assertEqual(event["key_dates"], 1)
            self.assertGreaterEqual(event["action_items"], 2)
            # privacy: the audit log must never carry document text or PII
            self.assertNotIn("plain_summary", event)
            self.assertNotIn("text", event)
            blob = json.dumps(event)
            self.assertNotIn("benefits@example.gov", blob)
            self.assertNotIn("882-44-1920", blob)

    def test_no_audit_path_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Simplifier().simplify(SAMPLE)  # audit_path is None by default
            self.assertEqual(os.listdir(tmp), [])


if __name__ == "__main__":
    unittest.main()
