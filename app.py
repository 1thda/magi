from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from extract import extract_text
from summarize import NODES, judge_summaries, summarize_one

st.set_page_config(page_title="Magi", layout="wide")

# Diamond layout is hardcoded to these three names — the geometry only makes
# sense for exactly this arrangement (top / bottom-left / bottom-right).
TOP_NODE = "BALTHASAR-2"
LEFT_NODE = "CASPER-3"
RIGHT_NODE = "MELCHIOR-1"

MAGI_CSS = """
<style>
.stApp { background-color: #000000; }
[data-testid="stMainBlockContainer"] {
    border: 4px double #ff8800;
    max-width: 920px;
    padding: 1em 1.6em 1.6em;
    margin: 1em auto;
}
.magi-header {
    display: flex; justify-content: space-between; align-items: center;
    border-top: 4px double #33cc66; border-bottom: 4px double #33cc66;
    padding: 0.35em 0.1em; margin-bottom: 0.7em;
}
.magi-header span {
    color: #ff8800; font-size: 2rem; font-weight: bold;
    letter-spacing: 0.4em; font-family: "Courier New", monospace;
}
.magi-info-row {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 1em;
}
.magi-info-left {
    color: #ff9944; font-size: 0.7rem; line-height: 1.5;
    font-family: "Courier New", monospace; white-space: pre;
}
.magi-info-right {
    border: 2px solid #4fc3e8; color: #4fc3e8; padding: 0.15em 0.7em;
    font-family: "Courier New", monospace; font-weight: bold; font-size: 1.1rem;
}
.magi-node {
    background: #57c2e6; color: #000; text-align: center;
    padding: 0.9em 0.7em 1.6em;
}
.magi-node-top { clip-path: polygon(0 0, 100% 0, 76% 100%, 24% 100%); margin-bottom: -2px; }
.magi-node-left { clip-path: polygon(0 0, 74% 0, 100% 32%, 100% 100%, 0 100%); }
.magi-node-right { clip-path: polygon(26% 0, 100% 0, 100% 100%, 0 100%, 0 32%); }
.magi-name {
    font-size: 1.25rem; font-weight: bold; letter-spacing: 0.08em;
    font-family: "Courier New", monospace;
}
.magi-model { font-size: 0.7rem; font-family: "Courier New", monospace; opacity: 0.7; }
.magi-hub { text-align: center; padding-top: 1.6em; }
.magi-hub-line { border-top: 2px solid #ff8800; width: 55%; margin: 0.35em auto; }
.magi-hub-label {
    color: #ff8800; font-weight: bold; letter-spacing: 0.2em;
    font-family: "Courier New", monospace; font-size: 1.3rem;
}
.magi-status {
    text-align: center; font-size: 1.1rem; font-weight: bold;
    padding: 0.2em; margin: 0.5em 0 0.4em; font-family: "Courier New", monospace;
}
.magi-status.deliberating {
    color: #ffaa00; border: 1px dashed #ffaa00;
    animation: magi-blink 1s step-start infinite;
}
.magi-status.approved { color: #33ff66; border: 1px solid #33ff66; }
.magi-status.rejected { color: #ff3333; border: 1px solid #ff3333; background: #220000; }
.magi-status.skipped { color: #888899; border: 1px solid #555566; }
.magi-node-winner { filter: drop-shadow(0 0 10px #ffdd00) drop-shadow(0 0 4px #ffdd00); }
@keyframes magi-blink { 50% { opacity: 0.25; } }
@media (prefers-reduced-motion: reduce) {
    .magi-status.deliberating { animation: none; }
}
.stCode pre, .stCode code {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}
</style>
"""

st.markdown(MAGI_CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="magi-header"><span>質問</span><span>解決</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="magi-info-row">'
    '<div class="magi-info-left">CODE:127\nFILE:MAGI_SYS\nEXTENTION:0256'
    '\nEX_MODE:ON\nPRIORITY:AAA</div>'
    '<div class="magi-info-right">情報</div>'
    "</div>",
    unsafe_allow_html=True,
)


def node_header_html(name: str, model: str, position_class: str) -> str:
    return (
        f'<div class="magi-node {position_class}">'
        f'<div class="magi-name">{name}</div>'
        f'<div class="magi-model">{model}</div>'
        "</div>"
    )


def status_html(label: str, state: str) -> str:
    return f'<div class="magi-status {state}">{label}</div>'


# Streamlit placeholders keep their position after the `with column:` block
# exits, so this can render from as_completed() regardless of finish order.
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

    node_by_name = dict(NODES)
    placeholders = {}
    header_placeholders = {}
    position_class = {TOP_NODE: "magi-node-top", LEFT_NODE: "magi-node-left", RIGHT_NODE: "magi-node-right"}

    def render_header(name, extra_class=""):
        cls = f"{position_class[name]} {extra_class}".strip()
        header_placeholders[name].markdown(
            node_header_html(name, node_by_name[name], cls), unsafe_allow_html=True
        )

    top_row = st.columns([1, 2, 1])
    with top_row[1]:
        header_placeholders[TOP_NODE] = st.empty()
        render_header(TOP_NODE)
        placeholders[TOP_NODE] = st.empty()

    bottom_row = st.columns([2, 1, 2])
    with bottom_row[0]:
        header_placeholders[LEFT_NODE] = st.empty()
        render_header(LEFT_NODE)
        placeholders[LEFT_NODE] = st.empty()
    with bottom_row[1]:
        st.markdown(
            '<div class="magi-hub">'
            '<div class="magi-hub-line"></div>'
            '<div class="magi-hub-label">MAGI</div>'
            '<div class="magi-hub-line"></div>'
            "</div>",
            unsafe_allow_html=True,
        )
    with bottom_row[2]:
        header_placeholders[RIGHT_NODE] = st.empty()
        render_header(RIGHT_NODE)
        placeholders[RIGHT_NODE] = st.empty()

    verdict_placeholder = st.empty()
    verdict_placeholder.markdown(status_html("審議中", "deliberating"), unsafe_allow_html=True)

    text_key = hash(text)
    node_results = {}
    with ThreadPoolExecutor(max_workers=len(NODES)) as executor:
        futures = {}
        for name, model in NODES:
            key = (model, text_key)
            if key in cache:
                node_results[name] = cache[key]
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
            node_results[name] = result
            show_result(placeholders[name], result)

    successes = {name: result.text for name, result in node_results.items() if result.ok}

    if len(successes) < 2:
        with verdict_placeholder.container():
            st.markdown(status_html("対象外", "skipped"), unsafe_allow_html=True)
            st.info("Not enough summaries to judge (need at least 2 successful nodes).")
    else:
        verdict_placeholder.markdown(status_html("裁定中", "deliberating"), unsafe_allow_html=True)
        judge_key = (text_key, frozenset(successes.items()))
        if judge_key in cache:
            judge_result = cache[judge_key]
        else:
            judge_result = judge_summaries(successes)
            cache[judge_key] = judge_result

        if judge_result.winner:
            render_header(judge_result.winner, "magi-node-winner")

        with verdict_placeholder.container():
            if not judge_result.ok:
                st.markdown(status_html("否定", "rejected"), unsafe_allow_html=True)
                st.error(judge_result.text)
            else:
                st.markdown(status_html("決定", "approved"), unsafe_allow_html=True)
                if judge_result.winner:
                    st.markdown(f"**Winner: {judge_result.winner}**")
                st.write(judge_result.text)
