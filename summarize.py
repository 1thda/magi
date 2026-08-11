from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import ollama

MODELS = ["gemma4:26b", "gemma4:latest"]

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
        return SummaryResult(ok=True, text=response["message"]["content"])
    except Exception as exc:
        return SummaryResult(ok=False, text=str(exc))


def summarize_all(text: str) -> dict[str, SummaryResult]:
    with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
        futures = {model: executor.submit(summarize_one, model, text) for model in MODELS}
        return {model: future.result() for model, future in futures.items()}
