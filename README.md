# Magi

Upload a research article PDF, get it summarized side-by-side by local Ollama models, copy the best one. Named after the three-supercomputer oracle from Neon Genesis Evangelion.

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
streamlit run app.py --server.address=localhost
```

Open the URL Streamlit prints (usually http://localhost:8501), upload a PDF, and read the summaries side by side. Hover a summary to copy it.

## Test

```bash
pytest
```

## Adding a model

Append the Ollama model name to `MODELS` in `summarize.py`.
