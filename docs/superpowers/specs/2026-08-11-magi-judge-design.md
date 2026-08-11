# MAGI Judge — Design Spec

## Purpose
Add a fourth, stronger model that reads all three MAGI node summaries and picks the best one, verdict-style — fitting the deliberation theme (three nodes vote/deliberate, one authority renders the decision).

## Model changes
- Drop `gemma4:26b` (too slow). Replace **MELCHIOR-1**'s model with `gemma2:2b` (already pulled, fast, proven accurate on a real test article).
- New **judge model**: `qwen3:14b` (already being pulled) — stronger than the three node models, used only once per upload (not concurrently with the nodes), so its slower per-call latency is paid once, not three times.
- Final node roster: MELCHIOR-1 → `gemma2:2b`, BALTHASAR-2 → `gemma4:latest`, CASPER-3 → `qwen3:8b`.

## Behavior
1. All three MAGI nodes run concurrently as today (審議中 → 承認/否定 per node, live).
2. Once **all three** have finished (success or failure — see below), the judge step begins automatically, no user action needed.
3. Judge prompt includes only the node name + summary text of nodes that succeeded. If fewer than 2 nodes succeeded, skip the judge entirely and show a note ("Not enough summaries to judge") instead of calling the model — judging one summary against nothing isn't a real comparison.
4. Judge is asked to name the single best summary by node name and give a one-line reason, verbatim pick (not a synthesized rewrite, per earlier decision).
5. Judge output is parsed for the winning node name (simple, forgiving match against the three known names — no strict JSON parsing requirement, since Ollama model output format isn't fully reliable).
   - If the judge's response clearly names one of the candidate nodes, that node wins.
   - If the response doesn't clearly match any candidate node (unparseable), show the judge's raw text in the verdict box without a winner highlight, rather than guessing or erroring.
6. UI: a fourth status area below the diamond, using the same status-badge visual language:
   - **審議中** while nodes are still running (judge hasn't started).
   - **裁定中** (judging) once judge call is in flight.
   - **決定** (decision) + winning node name + judge's reason, once done. The winning node's panel (`.magi-node`) gets a highlighted border (e.g. glowing/bright orange outline) to visually tie the verdict back to the diamond.
   - **否定** (judge call failed) + error text, isolated from the three node results already shown — a judge failure never hides or invalidates the three summaries already rendered.
7. Session caching: judge result cached alongside the per-node cache, keyed on the same text hash + the set of node results it judged, so re-renders (Streamlit reruns) don't re-invoke the judge.

## Non-goals (out of scope)
- Synthesized "best of all three" rewrite (explicitly rejected — verbatim pick only).
- Configurable/swappable judge model via UI (stays a code constant, like the three nodes).
- Judging when 0 or 1 nodes succeeded (shows a note, no judge call).

## Testing
- No new automated tests (same rationale as the rest of the UI/summarization layer — thin wiring around Ollama calls, verified live).
- Verify live: upload a real PDF, confirm judge stage only starts after all three nodes finish, confirm winning panel highlight, confirm a forced judge failure (e.g. temporarily wrong model name) shows an isolated error without affecting the three node panels.
