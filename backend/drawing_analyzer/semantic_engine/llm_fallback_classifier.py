from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
import urllib.error
import urllib.request

_PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "deepseek/deepseek-chat",
        "api_key_env": "OPENROUTER_API_KEY",
    },
}

HttpPost = Callable[[str, dict[str, str], dict], dict]


@dataclass
class LLMSuggestion:
    object_type: str
    provider: str
    model: str
    raw_response: str


def _urllib_post(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class LLMFallbackClassifier:
    """Optional, low-volume fallback that asks a cheap LLM to classify a
    drawing text label the deterministic catalog (civil_elements.json etc.)
    did not recognize.

    This never replaces the deterministic rules -- it only runs after they
    fail to find a match -- and it never creates or approves an SDTL object
    on its own: a suggestion is only ever surfaced as an "ai_suggested_type"
    annotation for a human to confirm (see pipeline/extraction_pipeline.py).

    Talks to DeepSeek's or OpenRouter's OpenAI-compatible chat completion API
    (whichever is configured) with a short prompt and a handful of output
    tokens, so even a drawing with many unmatched labels costs a fraction of
    a cent. Never raises: missing configuration, a network error, or a
    malformed response all just return None so the pipeline degrades to "no
    AI assist" instead of breaking.
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 8.0,
        http_post: HttpPost | None = None,
    ) -> None:
        self.provider = provider or os.environ.get("SDTL_LLM_PROVIDER", "deepseek")
        config = _PROVIDER_CONFIG.get(self.provider)
        if config is None:
            raise ValueError(
                f"Unsupported LLM provider: {self.provider!r}; "
                f"expected one of {sorted(_PROVIDER_CONFIG)}"
            )
        self._config = config
        self.api_key = api_key or os.environ.get(config["api_key_env"])
        self.model = model or os.environ.get("SDTL_LLM_MODEL", config["default_model"])
        self.timeout = timeout
        self._http_post = http_post or (
            lambda url, headers, payload: _urllib_post(url, headers, payload, self.timeout)
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def classify_label(
        self, text: str, candidate_types: list[str]
    ) -> LLMSuggestion | None:
        """Classify a short drawing label as one of candidate_types, or None
        if unconfigured, ambiguous, or the API call fails for any reason."""

        if not self.is_configured or not text.strip() or not candidate_types:
            return None

        system_prompt = (
            "Eres un asistente que clasifica etiquetas cortas de planos de "
            "ingenieria (electricos, civiles, arquitectonicos). Responde "
            "SOLO con una de estas palabras exactas: "
            f"{', '.join(candidate_types)}, unknown. Sin explicaciones."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text.strip()[:200]},
            ],
            "temperature": 0,
            "max_tokens": 8,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            body = self._http_post(self._config["base_url"], headers, payload)
            content = body["choices"][0]["message"]["content"].strip().lower()
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            IndexError,
            AttributeError,
        ):
            return None

        matched = next(
            (candidate for candidate in candidate_types if candidate.lower() in content),
            None,
        )
        if matched is None:
            return None

        return LLMSuggestion(
            object_type=matched,
            provider=self.provider,
            model=self.model,
            raw_response=content,
        )
