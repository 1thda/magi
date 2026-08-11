import re
from dataclasses import dataclass

import ollama

# (MAGI node name, Ollama model) — append a pair to add a node
NODES = [
    ("MELCHIOR-1", "gemma4:26b"),
    ("BALTHASAR-2", "gemma4:latest"),
    ("CASPER-3", "qwen3:8b"),
]

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
        content = response["message"]["content"]
        # thinking models (e.g. qwen3) may inline reasoning; keep only the answer
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return SummaryResult(ok=True, text=content)
    except Exception as exc:
        return SummaryResult(ok=False, text=str(exc))
