# Magi — Design Spec

## Purpose
A locally hosted browser tool: upload a research article PDF, get it summarized by multiple local LLMs (via Ollama) side by side, and pick the best summary by eye.

## Scope (MVP)
- Single-user, local-only (no auth, no deployment).
- Two models for now: `gemma4:26b`, `gemma4:latest`. Adding a third later = append one string to a config list.
- No persistence — summaries live only for the session; "selecting" a summary just means copying it to the clipboard.

## Architecture
Single Streamlit script (`app.py`). No separate frontend/backend split — Streamlit serves the browser UI directly from the Python process.

1. **Upload** — `st.file_uploader` accepts a PDF.
2. **Extract** — `pypdf.PdfReader` pulls raw text from all pages, concatenated.
3. **Summarize** — for each model in `MODELS = ["gemma4:26b", "gemma4:latest"]`, call Ollama's `chat` API with a fixed prompt ("Summarize this research article in a few paragraphs: {text}"). Both calls run concurrently via `concurrent.futures.ThreadPoolExecutor`, since the 26b model is slow and sequential calls would double wait time.
4. **Display** — `st.columns(len(MODELS))`, one column per model, each showing the model name as a header and the summary in `st.code()` (which has a hover copy-to-clipboard icon built in — no custom JS needed).

## Data flow
```
PDF upload → pypdf text extraction → (parallel) Ollama chat per model → st.columns side-by-side display → user reads, clicks copy icon on preferred one
```

## Error handling
- No PDF uploaded: show nothing, wait for upload (Streamlit's natural idle state).
- PDF has no extractable text (e.g. scanned image): show a `st.error` telling the user the PDF has no extractable text — OCR is out of scope for MVP.
- A model call fails (Ollama not running, model not pulled): catch the exception per-model and show `st.error` in that model's column, without blocking the other column's result.

## Config
- `MODELS` list at top of `app.py` — the only place to touch to add/remove a model.
- Prompt template as a constant near `MODELS`.

## Testing
- One `test_extract.py`: asserts `pypdf` extraction returns non-empty text for a sample PDF, and returns empty/handled gracefully for a text-less PDF. This is the only branchy, non-trivial logic (text extraction can fail); the Ollama calls and UI are thin wiring not worth a test at MVP stage.

## Out of scope (explicitly deferred)
- Third model slot (config-only change when ready).
- Saving/logging selected summaries to a file.
- OCR for scanned PDFs.
- Auth, multi-user, remote hosting.
- Custom/editable prompts per model.

## Deliverable
- `app.py`, `requirements.txt` (`streamlit`, `pypdf`, `ollama`), short `README.md` (setup + `streamlit run app.py`), `.gitignore` (Python venv/cache).
- Committed to local git repo at `~/magi`, pushed to GitHub (user creates/authorizes the remote).
