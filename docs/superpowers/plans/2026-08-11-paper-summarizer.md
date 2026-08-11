# Paper Summarizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local Streamlit app that summarizes an uploaded research-article PDF with two Ollama models side by side, letting the user copy the better summary.

**Architecture:** Three thin Python modules — `extract.py` (PDF → text), `summarize.py` (text → per-model summaries, called concurrently), `app.py` (Streamlit UI wiring the two together). Split from the spec's "single script" wording only so `extract.py`'s logic can be unit-tested without booting the Streamlit runtime; `app.py` still contains 100% of the UI code, matching the spec's intent.

**Tech Stack:** Python 3, Streamlit, pypdf, `ollama` Python package, pytest + reportlab (test-only, for generating fixture PDFs).

## Global Constraints

- Exactly two models for now: `gemma4:26b`, `gemma4:latest` — a third model must be addable by appending one string to `MODELS` in `summarize.py`, no other code changes.
- No persistence, no auth, no remote hosting — local-only single-user tool.
- "Copy the best summary" is satisfied by Streamlit's native `st.code()` hover copy icon — no custom JS/clipboard code.
- Only `extract.py` gets automated tests (per spec: it's the only branchy logic). `summarize.py` and `app.py` are verified manually with Ollama running.
- Prompt is fixed (not user-editable) for MVP.

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Produces: nothing code-level — later tasks assume these files exist and `pip install -r requirements.txt -r requirements-dev.txt` succeeds in a fresh venv.

- [ ] **Step 1: Create `requirements.txt`**

```
streamlit
pypdf
ollama
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
pytest
reportlab
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.DS_Store
```

- [ ] **Step 4: Create `README.md`**

```markdown
# Paper Summarizer

Upload a research article PDF, get it summarized side-by-side by local Ollama models, copy the best one.

## Setup

1. Install [Ollama](https://ollama.com) and pull the models listed in `summarize.py` (`MODELS`):
   ```bash
   ollama pull gemma4:26b
   ollama pull gemma4:latest
   ```
2. Create a virtualenv and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

## Run

```bash
ollama serve &
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501), upload a PDF, and read the summaries side by side. Hover a summary to copy it.

## Test

```bash
pytest
```

## Adding a model

Append the Ollama model name to `MODELS` in `summarize.py`.
```

- [ ] **Step 5: Verify install works**

Run:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt
```
Expected: no errors, all packages install.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore README.md
git commit -m "chore: project scaffolding"
```

---

### Task 2: PDF text extraction

**Files:**
- Create: `extract.py`
- Test: `test_extract.py`

**Interfaces:**
- Consumes: nothing (pure function on a file-like object).
- Produces: `extract_text(pdf_file) -> str` in `extract.py` — `pdf_file` is any file-like/path object `pypdf.PdfReader` accepts (Streamlit's `UploadedFile` qualifies). Returns concatenated page text, stripped; returns `""` if the PDF has no extractable text. Task 4 imports this.

- [ ] **Step 1: Write the failing tests**

```python
# test_extract.py
import io

from reportlab.pdfgen import canvas

from extract import extract_text


def _make_pdf_with_text(text: str) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, text)
    c.save()
    buf.seek(0)
    return buf


def _make_blank_pdf() -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def test_extract_text_returns_text_content():
    pdf = _make_pdf_with_text("Hello Research World")
    result = extract_text(pdf)
    assert "Hello Research World" in result


def test_extract_text_returns_empty_for_blank_pdf():
    pdf = _make_blank_pdf()
    result = extract_text(pdf)
    assert result == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_extract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'extract'`

- [ ] **Step 3: Write minimal implementation**

```python
# extract.py
from pypdf import PdfReader


def extract_text(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_extract.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add extract.py test_extract.py
git commit -m "feat: add PDF text extraction"
```

---

### Task 3: Ollama summarization

**Files:**
- Create: `summarize.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent module).
- Produces (used by Task 4):
  - `MODELS: list[str]` = `["gemma4:26b", "gemma4:latest"]`
  - `SummaryResult` dataclass with fields `ok: bool`, `text: str`
  - `summarize_all(text: str) -> dict[str, SummaryResult]` — keys are the entries of `MODELS`, calls run concurrently.

- [ ] **Step 1: Write the implementation**

```python
# summarize.py
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import ollama

MODELS = ["gemma4:26b", "gemma4:latest"]

PROMPT_TEMPLATE = "Summarize this research article in a few paragraphs:\n\n{text}"


@dataclass
class SummaryResult:
    ok: bool
    text: str


def summarize_one(model: str, text: str) -> SummaryResult:
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
        )
        return SummaryResult(ok=True, text=response["message"]["content"])
    except Exception as exc:
        return SummaryResult(ok=False, text=str(exc))


def summarize_all(text: str) -> dict[str, SummaryResult]:
    with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
        futures = {model: executor.submit(summarize_one, model, text) for model in MODELS}
        return {model: future.result() for model, future in futures.items()}
```

- [ ] **Step 2: Manual verification (requires `ollama serve` running and both models pulled)**

Run:
```bash
python3 -c "from summarize import summarize_all; r = summarize_all('The sky is blue because of Rayleigh scattering.'); [print(m, res.ok, res.text[:80]) for m, res in r.items()]"
```
Expected: two lines printed, one per model in `MODELS`, each with `ok=True` and a non-empty summary snippet. If `ok=False`, the printed text will show the Ollama error (e.g. model not found, server not running) — fix that before continuing.

- [ ] **Step 3: Commit**

```bash
git add summarize.py
git commit -m "feat: add concurrent Ollama summarization"
```

---

### Task 4: Streamlit app

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `extract_text` from `extract.py` (Task 2); `MODELS`, `summarize_all` from `summarize.py` (Task 3).
- Produces: nothing further consumes this — it's the entry point (`streamlit run app.py`).

- [ ] **Step 1: Write the implementation**

```python
# app.py
import streamlit as st

from extract import extract_text
from summarize import MODELS, summarize_all

st.title("Paper Summarizer")

uploaded_file = st.file_uploader("Upload a research article PDF", type="pdf")

if uploaded_file is not None:
    text = extract_text(uploaded_file)

    if not text:
        st.error(
            "Couldn't extract any text from this PDF. "
            "Scanned/image-only PDFs aren't supported yet."
        )
    else:
        with st.spinner("Summarizing with all models..."):
            results = summarize_all(text)

        columns = st.columns(len(MODELS))
        for column, model in zip(columns, MODELS):
            with column:
                st.subheader(model)
                result = results[model]
                if result.ok:
                    st.code(result.text, language=None)
                else:
                    st.error(f"{model} failed: {result.text}")
```

- [ ] **Step 2: Manual end-to-end verification (requires `ollama serve` running and both models pulled)**

Run: `streamlit run app.py`
Then in the browser it opens: upload a real PDF (a short research paper or any text PDF works). Expected: two columns appear, each titled with a model name, each showing a summary in a code block with a copy icon on hover. Upload a scanned/image-only PDF (or a PDF with no text layer) if you have one: expected a red error about no extractable text, no columns shown.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit UI"
```

---

### Task 5: Push to GitHub

**Files:** none (repo operations only)

- [ ] **Step 1: Create a new GitHub repo (via GitHub UI or `gh repo create`) and add it as the `origin` remote**

```bash
git remote add origin <your-repo-url>
```

- [ ] **Step 2: Push**

```bash
git push -u origin main
```

(This step is the user's own action/confirmation — do not push automatically on their behalf.)
