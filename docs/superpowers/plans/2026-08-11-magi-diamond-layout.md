# MAGI Diamond Layout — Plan

**Goal:** Restyle the app to closely resemble the real MAGI system screen from Evangelion (reference image: black terminal frame, orange double-line border, green double-rule header with Japanese text, top-left system-info block, top-right blue-bordered "情報" box, and the three nodes arranged in a diamond — BALTHASAR-2 on top, CASPER-3 bottom-left, MELCHIOR-1 bottom-right, converging on a small center "MAGI" hub) instead of the current plain left-to-right row of three trapezoid columns.

**Constraint discovered while scoping:** Streamlit's `st.markdown(unsafe_allow_html=True)` calls are each rendered independently — you cannot open a `<div>` in one call and close it in a later call to wrap other Streamlit widgets (columns, file uploader, etc.) inside it. Two consequences for the implementation:
- The outer bordered "frame" must be applied via CSS directly to Streamlit's own top-level content wrapper (its stable class needs confirming live, the same way `.stCode` was found for the earlier wrap-fix — likely `.block-container` or similar), not a hand-rolled wrapper div.
- The three node panels stay as `st.columns()` — each panel's HTML (name/model header) and its `st.empty()` placeholder are self-contained within one column, which already works today and needs no structural change.

## Layout Plan

1. **Outer frame**: CSS on Streamlit's main container — orange double border, black background, max-width, centered.
2. **Header row**: one `st.markdown` block, flex row with two Japanese labels (e.g. 質問 / 解決), bordered top+bottom with a green double rule.
3. **Info row**: one `st.markdown` block, flex row — left side small monospace system-info text (CODE/FILE/EXTENSION/PRIORITY flavor text), right side a blue-bordered "情報" box.
4. **Diamond**:
   - Row A: `st.columns([1,2,1])`, only the center column holds the **BALTHASAR-2** panel (top position) — trapezoid narrowing toward the bottom via `clip-path`.
   - Row B: `st.columns([2,1,2])` — left column holds **CASPER-3** (clip-path beveling its top-right corner toward center), middle column holds a static decorative "MAGI" hub label with short orange tick-mark dividers, right column holds **MELCHIOR-1** (mirrored bevel on its top-left corner).
   - Node→position mapping is hardcoded by name (`BALTHASAR-2` → top, `CASPER-3` → left, `MELCHIOR-1` → right) since the diamond geometry only makes sense for exactly these three; this replaces the current generic `zip(columns, NODES)` loop.
5. **Colors**: light-blue (~`#57c2e6`) panel backgrounds with black bold text (matches reference), black page background, orange (~`#ff8800`) primary accent/border, green (~`#33cc66`) accent for header rules, light blue for the info box border — all existing status-badge colors (審議中/承認/否定) stay as-is, just re-checked for contrast against the new blue panels.
6. **File uploader**: kept functional as today (no fake decorative input bars); optionally re-skinned with the same monospace/terminal styling to fit, but no behavior change.

## Verification steps (do live, not in this plan doc)
1. Start the app locally, inspect the DOM once to confirm the stable class name for Streamlit's main content wrapper (needed for step 1's outer border) and confirm `st.columns` row spacing behaves as expected when two `st.columns()` calls are stacked with tight margins.
2. Screenshot against the reference image; iterate spacing/clip-path values 1-2 rounds.
3. Run `pytest -q` (must stay 2 passed — no backend change).
4. Full E2E: upload a real PDF, confirm all three panels still go 審議中 → 承認/否定 independently, copy button still works, session cache still skips re-summarizing.

## Estimate
Single-file change (`app.py` CSS + the panel-placement loop restructured from generic to named positions). No new dependencies, no backend/summarize.py changes. Realistically 2-3 screenshot-iteration rounds to get spacing/shapes close to the reference.

## Open question for you
Given this needs live visual iteration (screenshots) to get right and that costs a few rounds of tool calls: do you want me to (a) do it now in one focused pass with a capped number of iterations, or (b) hold off until you're ready to spend the credits on it?
