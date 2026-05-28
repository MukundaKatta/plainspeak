# plainspeak — submission copy

**Repo:** https://github.com/MukundaKatta/plainspeak

**Target events:** USAII Global AI Hackathon 2026, Global Hack Week: Hacking for Good

**Tagline:** Rewrite dense official and legal letters into language anyone can read.

## Short description

Paste a government notice, a lease clause, or an insurance letter. plainspeak
strips the legalese, shortens the sentences, and reports a reading-grade level.
It redacts personal info before any text reaches an LLM, and works fully offline
with a keyless backend.

## Inspiration

People sign government, legal, and insurance documents they don't fully
understand. Plain language is a fairness and access problem, not a style
preference.

## What it does

Paste a dense official letter and it rewrites the text in plainer language,
reports a reading-grade level so you can see how hard the original was, and
redacts personal info before any text reaches an LLM. It works fully offline
with a keyless backend.

## How we built it

A rules-based legalese simplifier that matches multi-word phrases first, regex
PII redaction, a Flesch-Kincaid grade-level scorer, and a keyless stub plus lazy
LLM backends.

## Challenges we ran into

A phrase-replacement ordering bug turned "the aforementioned policy" into "the
this policy". Fixing it meant matching longer multi-word entries before single
words. The other constraint was making sure PII redaction always runs before any
model call.

## Accomplishments we're proud of

It works with zero keys, never sends raw personal data to a model, and gives a
measurable before-and-after readability number instead of just claiming
"simpler".

## What we learned

Readability you can measure beats readability you assert.

## What's next

More domain dictionaries (medical, tax), multi-language support, and a browser
extension.

## Tech tags

python, plain-language, accessibility, legal-tech, gov-tech, pii-redaction,
flesch-kincaid, readability, offline-first, streamlit, mit
