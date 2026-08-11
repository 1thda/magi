# Magi

Upload a research article PDF, get it summarized side-by-side by local Ollama models, copy the best one. Named after the three-supercomputer oracle from Neon Genesis Evangelion. The three summarizer nodes are named after the MAGI supercomputers from Neon Genesis Evangelion: MELCHIOR-1 (`gemma2:2b`), BALTHASAR-2 (`gemma4:latest`), CASPER-3 (`qwen3:8b`). A fourth model, `qwen3:14b`, acts as judge, picking the best of the three summaries.

## Setup

1. Install [Ollama](https://ollama.com) and pull all four models: the three nodes listed in `summarize.py` (`NODES`), plus the judge model (`qwen3:14b`), which is used separately and deliberately does not appear in `NODES`:
   ```bash
   ollama pull gemma2:2b
   ollama pull gemma4:latest
   ollama pull qwen3:8b
   ollama pull qwen3:14b
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
streamlit run app.py --server.address=localhost
```

Open the URL Streamlit prints (usually http://localhost:8501), upload a PDF, and read the summaries side by side. Hover a summary to copy it.

## Test

```bash
pytest
```

## Adding a model

Append a `("NODE-NAME", "ollama-model")` pair to `NODES` in `summarize.py`. Note: the diamond layout in `app.py` (`TOP_NODE`/`LEFT_NODE`/`RIGHT_NODE`) is hardcoded to exactly the three named nodes, so swapping which models those three nodes use is fine, but adding a fourth node pair requires reworking the layout too, not just editing `NODES`.
