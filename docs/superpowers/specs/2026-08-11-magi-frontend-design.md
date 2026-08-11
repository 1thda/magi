# Magi Frontend (MAGI Theme) — Design Spec

## Purpose
Restyle the app to resemble the MAGI supercomputer UI from Neon Genesis Evangelion, expand to three model nodes, and make results appear per-node as each model finishes instead of blocking on the slowest.

## Scope
- Keep the Streamlit stack; achieve the look with injected custom CSS (`st.markdown` + `unsafe_allow_html`). No frontend rewrite.
- Three nodes, each a (MAGI name, Ollama model) pair:
  - MELCHIOR-1 → `gemma4:26b`
  - BALTHASAR-2 → `gemma4:latest`
  - CASPER-3 → `qwen3:8b`
- Adding a node later remains a one-line config change.

## Architecture

### summarize.py changes
- Replace `MODELS: list[str]` with `NODES: list[tuple[str, str]]` of `(node_name, model)` pairs in the order above.
- `summarize_one(model, text)` unchanged.
- Drop `summarize_all` (app.py now drives concurrency itself so it can update the UI incrementally). `NUM_CTX`, `PROMPT_TEMPLATE`, `SummaryResult` unchanged.

### app.py changes
- **Theme CSS injected once at the top**: black page background; orange (#f60) borders/chrome; monospace font; green-tinted (#9f9-on-dark) panels; panel corners cut with `clip-path` polygons to evoke the MAGI trapezoids; a central "MAGI" title lockup instead of `st.title`; blinking animation for the deliberating state.
- **Panel layout**: `st.columns(len(NODES))`; each column holds a styled header block (MAGI name large, model name small underneath), a status badge, and a result area.
- **Live deliberation flow**:
  1. On upload + successful extraction, create one `st.empty()` placeholder per node and render all as **審議中** (deliberating, blinking orange).
  2. Submit all node jobs to a `ThreadPoolExecutor`; iterate `concurrent.futures.as_completed`; as each future lands, rewrite that node's placeholder: **承認** (green badge) + summary in `st.code` (native copy button) on success, **否定** (red badge) + error text on failure.
  3. One node failing never blocks or alters the others.
- **Caching**: results are cached in `st.session_state` keyed by (model, text-hash), checked on the main thread before jobs are submitted — `@st.cache_data` was rejected because cache lookups inside worker threads emit ScriptRunContext warnings. Cached results skip the 審議中 state.
- Existing behavior kept: PDF-only uploader, corrupt-PDF try/except with friendly error, empty-text error, localhost binding docs.

## Error handling
- Unchanged from current app for upload/extraction errors.
- Per-node failure renders 否定 + error in that node's panel only (same isolation as today, new styling).

## Testing
- `test_extract.py` untouched and must stay green.
- summarize.py restructure + app UI verified by the same live manual pattern as the MVP: run app, upload a real PDF, confirm three panels go 審議中 → 承認 independently (fast nodes first), confirm copy button works, confirm a bad model name renders 否定 without affecting others.

## Out of scope (deferred)
- Chunked/map-reduce summarization for very long papers.
- Hex-grid background flourishes, sound, scanline effects beyond simple CSS.
- Any backend/framework change.

## Deliverable
- Modified `summarize.py`, `app.py`, README note for the third model (`ollama pull qwen3:8b`), committed and pushed to GitHub.
