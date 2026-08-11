# Magi

Upload a research article PDF, get it summarized side-by-side by local Ollama models, copy the best one. Named after the three-supercomputer oracle from Neon Genesis Evangelion. The three summarizer nodes are named after the MAGI supercomputers from Neon Genesis Evangelion: MELCHIOR-1 (`gemma4:26b`), BALTHASAR-2 (`gemma4:latest`), CASPER-3 (`qwen3:8b`).

## Setup

1. Install [Ollama](https://ollama.com) and pull the models listed in `summarize.py` (`NODES`):
   ```bash
   ollama pull gemma4:26b
   ollama pull gemma4:latest
   ollama pull qwen3:8b
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

Append a `("NODE-NAME", "ollama-model")` pair to `NODES` in `summarize.py`.
