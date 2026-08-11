from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from extract import extract_text
from summarize import NODES, summarize_one

st.set_page_config(page_title="Magi", layout="wide")

MAGI_CSS = """
<style>
.stApp { background-color: #030000; }
.magi-title {
    text-align: center; color: #ff3300; font-size: 3rem; font-weight: bold;
    letter-spacing: 0.4em; font-family: "Courier New", monospace;
    border-top: 3px solid #ff6600; border-bottom: 3px solid #ff6600;
}
.magi-sub {
    text-align: center; color: #33ff66; letter-spacing: 0.3em;
    font-size: 0.8rem; font-family: "Courier New", monospace;
    margin-bottom: 1.5em;
}
.magi-node {
    background: #041104; border: 2px solid #ff6600;
    clip-path: polygon(12% 0, 100% 0, 100% 78%, 88% 100%, 0 100%, 0 22%);
    padding: 0.6em 1em; text-align: center; margin-bottom: 0.4em;
}
.magi-name {
    color: #66ff99; font-size: 1.5rem; font-weight: bold;
    letter-spacing: 0.15em; font-family: "Courier New", monospace;
}
.magi-model { color: #ff9944; font-size: 0.75rem; letter-spacing: 0.1em; }
.magi-status {
    text-align: center; font-size: 1.1rem; font-weight: bold;
    padding: 0.2em; margin-bottom: 0.4em; font-family: "Courier New", monospace;
}
.magi-status.deliberating {
    color: #ffaa00; border: 1px dashed #ffaa00;
    animation: magi-blink 1s step-start infinite;
}
.magi-status.approved { color: #33ff66; border: 1px solid #33ff66; }
.magi-status.rejected { color: #ff3333; border: 1px solid #ff3333; background: #220000; }
@keyframes magi-blink { 50% { opacity: 0.25; } }
@media (prefers-reduced-motion: reduce) {
    .magi-status.deliberating { animation: none; }
}
</style>
"""

st.markdown(MAGI_CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="magi-title">MAGI</div>'
    '<div class="magi-sub">DELIBERATION SYSTEM</div>',
    unsafe_allow_html=True,
)


def status_html(label: str, state: str) -> str:
    return f'<div class="magi-status {state}">{label}</div>'


# Streamlit placeholders keep column position after the `with column:` block exits, so this can render from as_completed().
def show_result(placeholder, result):
    with placeholder.container():
        if result.ok:
            st.markdown(status_html("承認", "approved"), unsafe_allow_html=True)
            st.code(result.text, language=None)
        else:
            st.markdown(status_html("否定", "rejected"), unsafe_allow_html=True)
            st.error(result.text)


if "summary_cache" not in st.session_state:
    st.session_state.summary_cache = {}
cache = st.session_state.summary_cache

uploaded_file = st.file_uploader("Upload a research article PDF", type="pdf")

if uploaded_file is not None:
    try:
        text = extract_text(uploaded_file)
    except Exception:
        st.error("Couldn't read this PDF — it may be corrupt or not a valid PDF file.")
        st.stop()

    if not text:
        st.error(
            "Couldn't extract any text from this PDF. "
            "Scanned/image-only PDFs aren't supported yet."
        )
        st.stop()

    columns = st.columns(len(NODES))
    placeholders = {}
    for column, (name, model) in zip(columns, NODES):
        with column:
            st.markdown(
                f'<div class="magi-node"><div class="magi-name">{name}</div>'
                f'<div class="magi-model">{model}</div></div>',
                unsafe_allow_html=True,
            )
            placeholders[name] = st.empty()

    text_key = hash(text)
    with ThreadPoolExecutor(max_workers=len(NODES)) as executor:
        futures = {}
        for name, model in NODES:
            key = (model, text_key)
            if key in cache:
                show_result(placeholders[name], cache[key])
            else:
                placeholders[name].markdown(
                    status_html("審議中", "deliberating"), unsafe_allow_html=True
                )
                futures[executor.submit(summarize_one, model, text)] = (name, key)
        for future in as_completed(futures):
            name, key = futures[future]
            result = future.result()
            cache[key] = result
            show_result(placeholders[name], result)
