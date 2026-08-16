import summarize
from summarize import _strip_thinking, judge_summaries, summarize_one


def test_strip_thinking_removes_think_block():
    raw = "<think>internal reasoning</think>The actual answer."
    assert _strip_thinking(raw) == "The actual answer."


def test_strip_thinking_passes_through_plain_text():
    assert _strip_thinking("Just an answer.") == "Just an answer."


def _fake_chat(content):
    def chat(model, messages, options):
        return {"message": {"content": content}}
    return chat


def test_summarize_one_returns_ok_result(monkeypatch):
    monkeypatch.setattr(summarize.ollama, "chat", _fake_chat("A summary."))
    result = summarize_one("some-model", "article text")
    assert result.ok
    assert result.text == "A summary."


def test_summarize_one_catches_errors(monkeypatch):
    def raising_chat(model, messages, options):
        raise RuntimeError("model not found")
    monkeypatch.setattr(summarize.ollama, "chat", raising_chat)
    result = summarize_one("missing-model", "article text")
    assert not result.ok
    assert "model not found" in result.text


def test_judge_summaries_picks_unambiguous_winner(monkeypatch):
    monkeypatch.setattr(
        summarize.ollama, "chat", _fake_chat("NODE-A is the best summary because it is thorough.")
    )
    result = judge_summaries({"NODE-A": "summary a", "NODE-B": "summary b"})
    assert result.ok
    assert result.winner == "NODE-A"


def test_judge_summaries_winner_none_when_ambiguous(monkeypatch):
    monkeypatch.setattr(
        summarize.ollama, "chat", _fake_chat("Both NODE-A and NODE-B are good.")
    )
    result = judge_summaries({"NODE-A": "summary a", "NODE-B": "summary b"})
    assert result.ok
    assert result.winner is None


def test_judge_summaries_catches_errors(monkeypatch):
    def raising_chat(model, messages, options):
        raise RuntimeError("connection refused")
    monkeypatch.setattr(summarize.ollama, "chat", raising_chat)
    result = judge_summaries({"NODE-A": "summary a", "NODE-B": "summary b"})
    assert not result.ok
    assert result.winner is None
