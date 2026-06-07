# plainspeak

Turn dense official letters — benefits notices, medical bills, legal mail — into
plain language, a checklist of what you actually have to **do**, and the
**dates** that matter. PII is stripped *before* any model sees the text, and the
whole thing runs offline with a keyless deterministic backend, so you can try it
in seconds with no API key.

[![CI](https://github.com/MukundaKatta/plainspeak/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/plainspeak/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-unittest-blueviolet.svg)](tests/)

---

## Why

A benefits redetermination letter reads at a US grade 14–18 level. The person who
needs to act on it may read at grade 6. That gap is where people miss deadlines,
lose coverage, and give up. `plainspeak` closes it:

- **Rewrites** the letter into short, plain sentences.
- **Extracts the actions** ("return the form", "verify your income") and attaches
  the deadline to each one.
- **Pulls every date** so nothing time-sensitive gets buried.
- **Redacts PII first.** Emails, phone numbers, SSN-like and card-like numbers
  are replaced with placeholders *before* the text is sent to any backend, and
  the audit log never stores document text.

## Quickstart (no API key)

```bash
pip install -e .
python examples/demo.py
```

```python
from plainspeak import Simplifier

result = Simplifier().simplify(letter_text)

print(result.plain_summary)
print(f"reading grade: {result.original_grade} -> {result.simplified_grade}")

for item in result.action_items:
    print("-", item.text, f"(due {item.due})" if item.due else "")

print("deadlines:", result.key_dates)
```

The default `StubBackend` is a deterministic, dependency-free rewriter. It swaps
common legalese for plain words and breaks run-on sentences — enough to show a
real reading-grade drop with zero setup. Swap in an LLM backend for production
quality.

## Dashboard

```bash
pip install -e ".[dashboard]"
streamlit run app.py
```

Paste a letter, see the plain rewrite, the action checklist, the deadlines, and
a live before/after reading-grade number — plus a count of how much PII was
stripped before anything left your machine.

## LLM backends

All optional and lazily imported, so the core install pulls **zero** vendor
dependencies.

| Backend            | Install              | Needs                          |
| ------------------ | -------------------- | ------------------------------ |
| `StubBackend`      | (built in)           | nothing — runs offline         |
| `GeminiBackend`    | `.[gemini]`          | `GEMINI_API_KEY`               |
| `AnthropicBackend` | `.[anthropic]`       | `ANTHROPIC_API_KEY`            |
| `OllamaBackend`    | `.[ollama]`          | a local Ollama server          |

```python
from plainspeak import Simplifier, GeminiBackend

result = Simplifier(backend=GeminiBackend()).simplify(letter_text)
```

Every backend gets the **redacted** text — the PII never reaches the model.

## How it works

```
raw letter
   │
   ▼
redact PII  ──►  [EMAIL] [PHONE] [ID] [CARD]     (before any model call)
   │
   ▼
rewrite (Stub / Gemini / Anthropic / Ollama)
   │
   ├─►  plain summary
   ├─►  action checklist  (cue verbs + attached deadline)
   └─►  key dates         (ordered, de-duplicated)
   │
   ▼
reading grade: original vs. simplified  (Flesch–Kincaid)
```

## Privacy & audit

`plainspeak` is built for sensitive mail, so privacy is a first-class feature:

- **Redaction runs first.** The model only ever sees placeholder tokens, never
  the real email, phone, SSN, or card number.
- **The audit log is text-free.** Pass `audit_path=` and you get one JSONL line
  per run with counts and reading grades — backend, redaction count, grade drop,
  number of actions and dates — and *never* the document or its PII.

```python
Simplifier(audit_path="audit.jsonl").simplify(letter_text)
# {"ts":..., "backend":"stub", "redactions":3, "grade_drop":7.4, "action_items":3, ...}
```

## API

`from plainspeak import ...`

| Object | Kind | What it does |
| ------ | ---- | ------------ |
| `Simplifier(backend=StubBackend(), reading_level="grade-6", redact=True, audit_path=None)` | class | Configure once, reuse. Call `.simplify(text)` for a `SimplifyResult`. |
| `Simplifier.simplify(text, *, reading_level=None, language=None)` | method | Redact PII, rewrite, extract actions and dates, score reading grade. |
| `SimplifyResult` | dataclass | `plain_summary`, `action_items`, `key_dates`, `original_grade`, `simplified_grade`, `grade_drop`, `redactions`, … plus `.to_dict()`. |
| `ActionItem(text, due=None)` | dataclass | One thing to do, with an optional attached deadline. |
| `grade_level(text) -> float` | function | Flesch–Kincaid grade level (higher = harder). |
| `extract_actions(text) -> list[ActionItem]` | function | Pull action sentences and attach their deadlines. |
| `find_dates(text) -> list[str]` | function | Every date-like string, in order, de-duplicated. |
| `redact_pii(text) -> tuple[str, RedactionReport]` | function | Replace emails / phones / IDs / cards with typed placeholders. |
| `StubBackend`, `GeminiBackend`, `AnthropicBackend`, `OllamaBackend` | classes | Rewrite backends. Stub is keyless and offline; the rest import their SDK lazily. |

Any object with a `name` attribute and a `rewrite(text, *, reading_level, language) -> str`
method satisfies the `Backend` protocol, so you can plug in your own.

## Tests

The suite uses only the Python standard library (`unittest`) — no third-party
test dependency and no API key. From a checkout:

```bash
python3 -m unittest discover -s tests
```

It runs fully offline against the stub backend. CI runs the same command on
Python 3.10–3.13 (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## License

MIT — see [LICENSE](LICENSE).
