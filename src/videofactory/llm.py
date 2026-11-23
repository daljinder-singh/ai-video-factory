"""Minimal Ollama client with schema-constrained JSON output."""
from __future__ import annotations

import json
import time

import requests


class LLMError(RuntimeError):
    pass


class Ollama:
    def __init__(self, model: str, url: str = "http://localhost:11434", num_ctx: int = 8192):
        self.model, self.url, self.num_ctx = model, url.rstrip("/"), num_ctx
        self.total_seconds = 0.0

    def check(self) -> None:
        try:
            tags = requests.get(f"{self.url}/api/tags", timeout=5).json()
        except requests.RequestException as e:
            raise LLMError(f"Ollama not reachable at {self.url}: {e}. Start it with: ollama serve") from e
        names = [m["name"] for m in tags.get("models", [])]
        if self.model not in names and f"{self.model}:latest" not in names:
            raise LLMError(f"Model {self.model!r} not pulled. Available: {names}. Run: ollama pull {self.model}")

    def chat_json(self, messages: list[dict], schema: dict, *, max_tokens: int = 800,
                  temperature: float = 0.4) -> dict:
        body = {
            "model": self.model, "messages": messages, "stream": False, "think": False,
            "format": schema, "keep_alive": "30m",
            "options": {"num_ctx": self.num_ctx, "num_predict": max_tokens, "temperature": temperature},
        }
        t0 = time.time()
        try:
            r = requests.post(f"{self.url}/api/chat", json=body, timeout=1800)
            r.raise_for_status()
        except requests.RequestException as e:
            raise LLMError(f"Ollama request failed: {e}") from e
        self.total_seconds += time.time() - t0
        content = r.json()["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"Model returned invalid JSON (likely hit max_tokens): {content[:200]}...") from e
