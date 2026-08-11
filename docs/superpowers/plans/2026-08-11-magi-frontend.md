# MAGI Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the app as the Evangelion MAGI deliberation system: three named model nodes with NERV-style theming, per-node live status (審議中 → 承認/否定), and session caching of summaries.

**Architecture:** `summarize.py` becomes pure config + single-model call (`NODES` pairs, `summarize_one`); `app.py` owns concurrency (`ThreadPoolExecutor` + `as_completed`) so it can update each node's placeholder the moment that model finishes. Theming is injected CSS plus a native `.streamlit/config.toml` dark theme — no framework change, no new dependencies.

**Tech Stack:** Python 3, Streamlit (existing), `ollama` package (existing). No new packages.

## Global Constraints

- Node/model pairs, exactly: MELCHIOR-1 → `gemma4:26b`, BALTHASAR-2 → `gemma4:latest`, CASPER-3 → `qwen3:8b`. Adding a node later must require only appending one `(name, model)` pair to `NODES` in `summarize.py`.
- No new pip dependencies. No frontend rewrite — Streamlit + injected CSS only.
- Copy affordance stays Streamlit's native `st.code()` hover copy icon — no custom clipboard JS.
- One node failing must render 否定 in that node's panel only, never blocking or altering the others.
- Automated tests remain scoped to `extract.py` (`test_extract.py` must stay green, unchanged).
- `NUM_CTX = 65536` and the corrupt-PDF/empty-text error handling from the current app.py must survive the rewrite.
- README keeps the `--server.address=localhost` run command.

---

### Task 1: summarize.py — NODES config + thinking-tag strip

**Files:**
- Modify: `summarize.py`

**Interfaces:**
- Consumes: nothing new.
- Produces (Task 2 imports these): `NODES: list[tuple[str, str]]` — `(node_name, model)` pairs in the order MELCHIOR-1/BALTHASAR-2/CASPER-3; `summarize_one(model: str, text: str) -> SummaryResult` (unchanged signature); `SummaryResult` dataclass with `ok: bool`, `text: str` (unchanged). `MODELS` and `summarize_all` are deleted — nothing may import them after this task.

- [ ] **Step 1: Set up the worktree venv (if not present)**

Run from the worktree root:
```bash
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt
```
Expected: installs cleanly.

- [ ] **Step 2: Rewrite summarize.py**

Replace the entire file with:

```python
import re
from dataclasses import dataclass

import ollama

# (MAGI node name, Ollama model) — append a pair to add a node
NODES = [
    ("MELCHIOR-1", "gemma4:26b"),
    ("BALTHASAR-2", "gemma4:latest"),
    ("CASPER-3", "qwen3:8b"),
]

PROMPT_TEMPLATE = "Summarize this research article in a few paragraphs:\n\n{text}"

# Ollama defaults to a 2048-token context window regardless of what the model
# supports, silently truncating long articles down to their last couple of
# pages. 65536 covers a ~65-page paper and stays under gemma4:latest's 131072 cap.
NUM_CTX = 65536


@dataclass
class SummaryResult:
    ok: bool
    text: str


def summarize_one(model: str, text: str) -> SummaryResult:
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
            options={"num_ctx": NUM_CTX},
        )
        content = response["message"]["content"]
        # thinking models (e.g. qwen3) may inline reasoning; keep only the answer
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return SummaryResult(ok=True, text=content)
    except Exception as exc:
        return SummaryResult(ok=False, text=str(exc))
```

Notes: `ThreadPoolExecutor` import and `summarize_all` are gone on purpose — app.py (Task 2) drives concurrency itself. Do not leave a backward-compat alias.

- [ ] **Step 3: Verify imports and shape**

Run:
```bash
.venv/bin/python3 -c "from summarize import NODES, summarize_one, SummaryResult; assert len(NODES) == 3 and NODES[0] == ('MELCHIOR-1', 'gemma4:26b') and NODES[2][1] == 'qwen3:8b'; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Confirm extract tests still green**

Run: `.venv/bin/pytest -q`
Expected: 2 passed

- [ ] **Step 5: Live check against whatever models are pulled**

Run `ollama list` first. Then:
```bash
.venv/bin/python3 -c "from summarize import summarize_one; r = summarize_one('gemma4:latest', 'The sky is blue because of Rayleigh scattering.'); print(r.ok, r.text[:80])"
```
Expected: `True` + a non-empty snippet. If `qwen3:8b` appears in `ollama list`, run the same one-liner with `qwen3:8b` and additionally confirm the printed text does not start with `<think>`. If qwen3:8b is still downloading, note that in your report as a concern and continue — the controller will verify it later.

- [ ] **Step 6: Commit**

```bash
git add summarize.py
git commit -m "feat: three MAGI nodes config, strip thinking tags from summaries"
```

---

### Task 2: MAGI-themed app.py, dark theme config, docs

**Files:**
- Modify: `app.py`
- Create: `.streamlit/config.toml`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-11-magi-frontend-design.md` (one line, see Step 4)

**Interfaces:**
- Consumes: `NODES`, `summarize_one`, `SummaryResult` from `summarize.py` (Task 1); `extract_text(pdf_file) -> str` from `extract.py` (raises on corrupt PDF, returns `""` for no text).
- Produces: nothing further consumes this — entry point.

- [ ] **Step 1: Create `.streamlit/config.toml`**

```toml
[theme]
base = "dark"
backgroundColor = "#030000"
secondaryBackgroundColor = "#110800"
primaryColor = "#ff6600"
textColor = "#ff9944"
font = "monospace"
```

- [ ] **Step 2: Rewrite app.py**

Replace the entire file with:

```python
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
```

Design notes (why, for the reviewer): caching lives in `st.session_state` rather than `@st.cache_data` because the summarize calls run in worker threads, where `st.cache_data` lookups emit ScriptRunContext warnings — cache checks here happen on the main thread before submission, sidestepping that entirely. All `st.*` calls stay on the main script thread (`as_completed` loop); worker threads only run `summarize_one`, which touches no Streamlit API.

- [ ] **Step 3: Update README.md**

Three edits:
1. In Setup, the model-pull block becomes:
```bash
ollama pull gemma4:26b
ollama pull gemma4:latest
ollama pull qwen3:8b
```
2. Change the "Adding a model" section body to: "Append a `("NODE-NAME", "ollama-model")` pair to `NODES` in `summarize.py`."
3. After the intro sentence, add: "The three summarizer nodes are named after the MAGI supercomputers from Neon Genesis Evangelion: MELCHIOR-1 (`gemma4:26b`), BALTHASAR-2 (`gemma4:latest`), CASPER-3 (`qwen3:8b`)."

Leave the Run section (with `--server.address=localhost`) untouched.

- [ ] **Step 4: Amend the design spec's caching line**

In `docs/superpowers/specs/2026-08-11-magi-frontend-design.md`, replace the sentence beginning "**Caching**: the per-model summarize call is wrapped with `@st.cache_data`" with: "**Caching**: results are cached in `st.session_state` keyed by (model, text-hash), checked on the main thread before jobs are submitted — `@st.cache_data` was rejected because cache lookups inside worker threads emit ScriptRunContext warnings. Cached results skip the 審議中 state."

- [ ] **Step 5: Verify**

1. `.venv/bin/pytest -q` → 2 passed.
2. `.venv/bin/python3 -c "import ast; ast.parse(open('app.py').read()); print('ok')"` → ok.
3. Start the app: `.venv/bin/streamlit run app.py --server.address localhost --server.port 8503 --server.headless true` in the background; `curl -s http://localhost:8503/_stcore/health` → `ok`; take a browser screenshot if browser tooling is available and confirm the MAGI title lockup and dark/orange theme render; kill the server. Full PDF-upload E2E is the controller's job after this task.

- [ ] **Step 6: Commit**

```bash
git add app.py .streamlit/config.toml README.md docs/superpowers/specs/2026-08-11-magi-frontend-design.md
git commit -m "feat: MAGI-themed UI with per-node live deliberation and session cache"
```
