# MAGI Judge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the three MAGI nodes finish, a fourth stronger model (`qwen3:14b`) reads their summaries and picks the best one verbatim, with a one-line reason, shown in a verdict box with the winning node's panel highlighted.

**Architecture:** `summarize.py` gains a `judge_summaries()` function (same shape as `summarize_one`, run once, not concurrently). `app.py` restructures node panel headers into placeholders (so the winner can be re-rendered with a highlight after the fact), runs the existing node loop unchanged, then runs the judge step once all three nodes are accounted for.

**Tech Stack:** No new dependencies. Reuses `ollama`, `re` (already imported in summarize.py).

## Global Constraints

- Node roster: MELCHIOR-1 → `gemma2:2b` (replacing `gemma4:26b`), BALTHASAR-2 → `gemma4:latest`, CASPER-3 → `qwen3:8b`. `NODES` order and shape (`list[tuple[str, str]]`) stays the same.
- Judge model: `qwen3:14b`, called once per upload, only after all three nodes have finished (success or failure) — never concurrently with the nodes.
- If fewer than 2 nodes succeeded, skip the judge call entirely (no real comparison possible) — show a "not enough summaries" note instead.
- Judge picks one existing summary verbatim by node name + one-line reason — never a synthesized rewrite.
- If the judge's response doesn't clearly name exactly one of the candidate nodes, show its raw text with no winner highlight — never guess.
- A judge failure (exception) must not hide or invalidate the three node summaries already rendered — same isolation pattern as per-node failures.
- Judge result is cached in `st.session_state` alongside the per-node cache, keyed on the text hash + the exact set of node results judged.
- No new automated tests — this layer is thin Ollama wiring, verified live (same rationale as the rest of app.py/summarize.py).

---

### Task 1: summarize.py — swap MELCHIOR-1's model, add judge_summaries()

**Files:**
- Modify: `summarize.py`

**Interfaces:**
- Consumes: nothing new.
- Produces (Task 2 imports these): `NODES` (MELCHIOR-1 now paired with `gemma2:2b`); `JUDGE_MODEL: str = "qwen3:14b"`; `JudgeResult` dataclass with fields `ok: bool`, `winner: str | None`, `text: str`; `judge_summaries(results: dict[str, str]) -> JudgeResult` — `results` maps node name to its summary text (only successful nodes' summaries, caller's responsibility to filter). `summarize_one` and `SummaryResult` are unchanged.

- [ ] **Step 1: Rewrite summarize.py**

Replace the entire file with:

```python
import re
from dataclasses import dataclass

import ollama

# (MAGI node name, Ollama model) — append a pair to add a node
NODES = [
    ("MELCHIOR-1", "gemma2:2b"),
    ("BALTHASAR-2", "gemma4:latest"),
    ("CASPER-3", "qwen3:8b"),
]

JUDGE_MODEL = "qwen3:14b"

PROMPT_TEMPLATE = "Summarize this research article in a few paragraphs:\n\n{text}"

# Ollama defaults to a 2048-token context window regardless of what the model
# supports, silently truncating long articles down to their last couple of
# pages. 65536 covers a ~65-page paper and stays under gemma4:latest's 131072 cap.
NUM_CTX = 65536


@dataclass
class SummaryResult:
    ok: bool
    text: str


@dataclass
class JudgeResult:
    ok: bool
    winner: str | None
    text: str


def _strip_thinking(content: str) -> str:
    # thinking models (e.g. qwen3) may inline reasoning; keep only the answer
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


def summarize_one(model: str, text: str) -> SummaryResult:
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
            options={"num_ctx": NUM_CTX},
        )
        content = _strip_thinking(response["message"]["content"])
        return SummaryResult(ok=True, text=content)
    except Exception as exc:
        return SummaryResult(ok=False, text=str(exc))


def judge_summaries(results: dict[str, str]) -> JudgeResult:
    candidates = list(results.keys())
    listing = "\n\n".join(f"{name}:\n{text}" for name, text in results.items())
    prompt = (
        f"Here are {len(candidates)} summaries of the same research article, "
        f"written by different systems named {', '.join(candidates)}.\n\n"
        f"{listing}\n\n"
        "Which one is the best summary? State the system name of the best one "
        "clearly, then give a one-sentence reason."
    )
    try:
        response = ollama.chat(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX},
        )
        content = _strip_thinking(response["message"]["content"])
        matches = [name for name in candidates if name.lower() in content.lower()]
        winner = matches[0] if len(matches) == 1 else None
        return JudgeResult(ok=True, winner=winner, text=content)
    except Exception as exc:
        return JudgeResult(ok=False, winner=None, text=str(exc))
```

- [ ] **Step 2: Verify imports and shape**

Run:
```bash
.venv/bin/python3 -c "
from summarize import NODES, JUDGE_MODEL, judge_summaries, JudgeResult, summarize_one, SummaryResult
assert dict(NODES)['MELCHIOR-1'] == 'gemma2:2b'
assert JUDGE_MODEL == 'qwen3:14b'
print('ok')
"
```
Expected: `ok`

- [ ] **Step 3: Confirm extract tests still green**

Run: `.venv/bin/pytest -q`
Expected: 2 passed

- [ ] **Step 4: Live check judge_summaries with fake data (no Ollama call needed for this part)**

Run `ollama list` to confirm `qwen3:14b` is pulled. If not present yet, note it as a concern in your report and skip to Step 5 anyway — Task 2's live verification is where this actually gets exercised end-to-end.

If `qwen3:14b` is present:
```bash
.venv/bin/python3 -c "
from summarize import judge_summaries
r = judge_summaries({'MELCHIOR-1': 'A short summary about cats.', 'BALTHASAR-2': 'A detailed, accurate three-paragraph summary about the history of Rome, covering the Republic, the Empire, and its fall.'})
print(r.ok, r.winner, r.text[:200])
"
```
Expected: `ok=True`, `winner` is either `'MELCHIOR-1'`, `'BALTHASAR-2'`, or `None` (all are valid outcomes — the point is confirming the call succeeds and returns a well-formed `JudgeResult`, not that it necessarily picks one specific side of this obviously-different pair, though in practice it typically should recognize the more detailed one).

- [ ] **Step 5: Commit**

```bash
git add summarize.py
git commit -m "feat: replace gemma4:26b with gemma2:2b, add judge_summaries for verdict step"
```

---

### Task 2: app.py — judge stage, verdict box, winner highlight

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `NODES`, `JUDGE_MODEL` (unused directly, informational), `summarize_one`, `judge_summaries`, `JudgeResult`, `SummaryResult` from `summarize.py` (Task 1). `TOP_NODE`, `LEFT_NODE`, `RIGHT_NODE`, `extract_text`, `MAGI_CSS`, `node_header_html`, `status_html`, `show_result` all already exist in the current `app.py` from the diamond-layout work — keep them, extend as described below.
- Produces: nothing further consumes this — entry point.

- [ ] **Step 1: Add one CSS rule and the winner-highlight rule to `MAGI_CSS`**

In the existing `MAGI_CSS` string in `app.py`, add these two rules (anywhere inside the `<style>` block, e.g. right after the existing `.magi-status.rejected` rule):

```css
.magi-status.skipped { color: #888899; border: 1px solid #555566; }
.magi-node-winner { filter: drop-shadow(0 0 10px #ffdd00) drop-shadow(0 0 4px #ffdd00); }
```

- [ ] **Step 2: Change node header rendering to use placeholders**

Currently each node's header (name/model box) is rendered directly via `st.markdown(node_header_html(...), unsafe_allow_html=True)` inside the column, with no way to re-render it later. Change each of the three header renders (top, left, right) to go through an `st.empty()` placeholder instead, stored in a new `header_placeholders` dict, so Step 5 can redraw the winner's header with the highlight class added.

Replace this block (the `top_row` / `bottom_row` construction, currently the last ~25 lines of the file inside `if uploaded_file is not None:`):

```python
    node_by_name = dict(NODES)
    placeholders = {}

    top_row = st.columns([1, 2, 1])
    with top_row[1]:
        st.markdown(
            node_header_html(TOP_NODE, node_by_name[TOP_NODE], "magi-node-top"),
            unsafe_allow_html=True,
        )
        placeholders[TOP_NODE] = st.empty()

    bottom_row = st.columns([2, 1, 2])
    with bottom_row[0]:
        st.markdown(
            node_header_html(LEFT_NODE, node_by_name[LEFT_NODE], "magi-node-left"),
            unsafe_allow_html=True,
        )
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
        st.markdown(
            node_header_html(RIGHT_NODE, node_by_name[RIGHT_NODE], "magi-node-right"),
            unsafe_allow_html=True,
        )
        placeholders[RIGHT_NODE] = st.empty()
```

with:

```python
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
```

- [ ] **Step 3: Track node results and run the judge step after the node loop**

Find the existing node-running block (the `text_key = hash(text)` line through the end of the `with ThreadPoolExecutor(...) as executor:` block — this is the last block in the current file). Replace it with:

```python
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
        verdict_placeholder.markdown(status_html("対象外", "skipped"), unsafe_allow_html=True)
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
```

Note: `verdict_placeholder.markdown(...)` followed immediately by `with verdict_placeholder.container(): st.markdown(...)` in the `< 2 successes` branch is intentionally redundant-looking but harmless — the first call is overwritten by the container block; simplify by deleting the first `verdict_placeholder.markdown(status_html("対象外", "skipped"), ...)` line in that branch if you prefer (it's dead code). Either way, the final rendered state must be the skipped status + info message.

- [ ] **Step 4: Verify syntax and existing tests**

Run:
```bash
.venv/bin/pytest -q
.venv/bin/python3 -c "import ast; ast.parse(open('app.py').read()); print('syntax ok')"
```
Expected: 2 passed, syntax ok.

- [ ] **Step 5: Live end-to-end verification (requires `ollama serve` running, all 4 models pulled: `gemma2:2b`, `gemma4:latest`, `qwen3:8b`, `qwen3:14b`)**

Run `ollama list` first to confirm all four are present. Then:
```bash
.venv/bin/streamlit run app.py --server.address localhost --server.port 8507 --server.headless true &
```
Use whatever browser tooling is available to upload a real PDF (or generate a tiny test PDF with `reportlab` the same way earlier tasks did) and confirm:
1. All three node panels go 審議中 → 承認/否定 independently, as before.
2. The verdict box shows 審議中 while nodes are running, then either 裁定中 → 決定 (with a winner name + reason, or raw judge text if unparseable) once the judge runs, or 対象外 if fewer than 2 nodes succeeded.
3. If a winner was named, that node's trapezoid panel visibly has the highlight (glow) applied.
4. Re-upload the same PDF (or trigger a rerun) and confirm the judge does not re-run — verdict appears instantly from cache.

Report exactly what you observed (screenshot description or explicit confirmation of each point) — this is the main acceptance bar for the task, since there are no automated tests for this layer. Kill the background server when done.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: add MAGI judge verdict stage with winner highlight"
```
