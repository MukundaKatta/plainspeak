"""plainspeak demo — runs offline, no API key required.

    python examples/demo.py

Shows the full pipeline on a dense benefits letter: PII redaction, plain
rewrite, the action checklist, the deadlines, and the reading-grade drop.
"""

from __future__ import annotations

from plainspeak import Simplifier

LETTER = """NOTICE OF BENEFITS REDETERMINATION

Pursuant to Section 4.2 of the aforementioned policy, you are hereby notified
that your eligibility for assistance shall be redetermined. In the event that
the requested documentation is not received prior to June 6, 2026, your benefits
will terminate.

You are required to remit the enclosed form and utilize the online portal to
verify your income. Please contact our office at (555) 123-4567 or
benefits@example.gov if you have questions. Your case number is 882-44-1920.
"""


def main() -> None:
    result = Simplifier().simplify(LETTER)

    print("=" * 70)
    print("PLAIN SUMMARY")
    print("=" * 70)
    print(result.plain_summary)

    print()
    print("WHAT YOU NEED TO DO")
    print("-" * 70)
    for item in result.action_items:
        due = f"  (due {item.due})" if item.due else ""
        print(f"  [ ] {item.text}{due}")

    print()
    print("KEY DATES")
    print("-" * 70)
    for date in result.key_dates:
        print(f"  - {date}")

    print()
    print("READING LEVEL")
    print("-" * 70)
    print(f"  before: grade {result.original_grade}")
    print(f"  after:  grade {result.simplified_grade}")
    print(f"  drop:   {result.grade_drop} grade levels easier")

    print()
    print("PRIVACY")
    print("-" * 70)
    print(f"  backend:        {result.backend}")
    print(
        f"  PII redacted:   {result.redactions} item(s) removed before any model call"
    )


if __name__ == "__main__":
    main()
