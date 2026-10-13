from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OpenAIProvider:
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    name: str = "openai"
    timeout: float | None = None
    max_retries: int = 2
    max_tokens: int | None = None

    def complete(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI provider requires the optional package. "
                "Install with: python -m pip install -r requirements-llm.txt"
            ) from exc
        key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=key, max_retries=self.max_retries, **({"timeout": self.timeout} if self.timeout is not None else {}))
        response = client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            **({"max_tokens": self.max_tokens} if self.max_tokens is not None else {}),
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "{}"


@dataclass(slots=True)
class AnthropicProvider:
    model: str = "claude-3-5-haiku-latest"
    api_key: str | None = None
    name: str = "anthropic"
    timeout: float | None = None
    max_retries: int = 2

    def complete(self, prompt: str) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic provider requires the optional package. "
                "Install with: python -m pip install -r requirements-llm.txt"
            ) from exc
        key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        client = Anthropic(api_key=key, max_retries=self.max_retries, **({"timeout": self.timeout} if self.timeout is not None else {}))
        response = client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "\n".join(parts)


@dataclass(slots=True)
class OllamaProvider:
    model: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434"
    name: str = "ollama"
    timeout: float = 120
    use_env_proxy: bool = True
    max_tokens: int | None = None

    def complete(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, **({"num_predict": self.max_tokens} if self.max_tokens is not None else {})},
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            opener = urllib.request.urlopen if self.use_env_proxy else urllib.request.build_opener(urllib.request.ProxyHandler({})).open
            with opener(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        return str((payload.get("message") or {}).get("content") or "{}")


def make_provider(name: str, model: str | None = None) -> Any:
    name = name.lower()
    if name == "openai":
        return OpenAIProvider(model=model or "gpt-4o-mini")
    if name == "anthropic":
        return AnthropicProvider(model=model or "claude-3-5-haiku-latest")
    if name == "ollama":
        return OllamaProvider(model=model or "llama3.1:8b")
    raise ValueError(f"Unknown LLM provider: {name}")
