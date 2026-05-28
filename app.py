"""plainspeak dashboard — paste a dense letter, get plain language back.

    pip install -e ".[dashboard]"
    streamlit run app.py

Runs offline against the keyless stub backend by default. PII is stripped
before the text reaches any backend.
"""

from __future__ import annotations

import streamlit as st

from plainspeak import Simplifier

SAMPLE = """NOTICE OF BENEFITS REDETERMINATION

Pursuant to Section 4.2 of the aforementioned policy, you are hereby notified that your eligibility for assistance shall be redetermined. In the event that the requested documentation is not received prior to June 6, 2026, your benefits will terminate.

You are required to remit the enclosed form and utilize the online portal to verify your income. Please contact our office at (555) 123-4567 or benefits@example.gov if you have questions. Your case number is 882-44-1920.
"""

st.set_page_config(page_title="plainspeak", page_icon="📄", layout="wide")

st.title("📄 plainspeak")
st.caption(
    "Turn dense official letters into plain language, a checklist, and the dates "
    "that matter. PII is stripped before any model sees the text."
)

with st.sidebar:
    st.header("Settings")
    reading_level = st.selectbox(
        "Target reading level",
        ["grade-6", "grade-8", "grade-10"],
        index=0,
    )
    redact = st.toggle("Redact PII before processing", value=True)
    st.markdown("---")
    st.markdown(
        "Default backend is a **keyless, offline** rewriter so this runs with no "
        "API key. Swap in Gemini / Anthropic / Ollama for production quality."
    )

text = st.text_area(
    "Paste a letter",
    value=SAMPLE,
    height=240,
    help="Try a benefits notice, a medical bill, or any dense official mail.",
)

if st.button("Simplify", type="primary"):
    if not text.strip():
        st.warning("Paste some text first.")
        st.stop()

    result = Simplifier(reading_level=reading_level, redact=redact).simplify(text)

    c1, c2, c3 = st.columns(3)
    c1.metric("Reading grade", result.simplified_grade, f"-{result.grade_drop}")
    c2.metric("Actions found", len(result.action_items))
    c3.metric("PII redacted", result.redactions)

    st.subheader("Plain summary")
    st.write(result.plain_summary)

    left, right = st.columns(2)

    with left:
        st.subheader("What you need to do")
        if result.action_items:
            for item in result.action_items:
                due = f"  \n  ⏰ due **{item.due}**" if item.due else ""
                st.checkbox(f"{item.text}{due}", key=item.text)
        else:
            st.write("_No clear action items found._")

    with right:
        st.subheader("Key dates")
        if result.key_dates:
            for date in result.key_dates:
                st.write(f"- {date}")
        else:
            st.write("_No dates found._")

    with st.expander("Before / after reading level"):
        st.write(f"**Original:** grade {result.original_grade}")
        st.write(f"**Simplified:** grade {result.simplified_grade}")
        st.write(f"**Drop:** {result.grade_drop} grade levels easier to read")
        st.caption(f"Backend: {result.backend}")
