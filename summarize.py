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
