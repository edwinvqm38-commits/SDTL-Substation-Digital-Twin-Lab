from __future__ import annotations

import pytest

from backend.drawing_analyzer.semantic_engine import LLMFallbackClassifier, LLMSuggestion


def _fake_response(content: str):
    def _post(url: str, headers: dict, payload: dict) -> dict:
        return {"choices": [{"message": {"content": content}}]}

    return _post


def test_returns_none_when_no_api_key_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    classifier = LLMFallbackClassifier(provider="deepseek")

    assert classifier.is_configured is False
    assert classifier.classify_label("SALA DE TABLEROS", ["electrical_room"]) is None


def test_classifies_label_using_configured_provider() -> None:
    classifier = LLMFallbackClassifier(
        provider="deepseek",
        api_key="test-key",
        http_post=_fake_response("electrical_room"),
    )

    suggestion = classifier.classify_label(
        "SALA DE TABLEROS", ["electrical_room", "cable_trench"]
    )

    assert isinstance(suggestion, LLMSuggestion)
    assert suggestion.object_type == "electrical_room"
    assert suggestion.provider == "deepseek"


def test_openrouter_provider_uses_its_own_api_key_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    classifier = LLMFallbackClassifier(
        provider="openrouter", http_post=_fake_response("cable_trench")
    )

    suggestion = classifier.classify_label(
        "DUCTO DE CABLES", ["electrical_room", "cable_trench"]
    )

    assert suggestion.object_type == "cable_trench"
    assert suggestion.provider == "openrouter"


def test_unrecognized_response_returns_none() -> None:
    classifier = LLMFallbackClassifier(
        provider="deepseek", api_key="test-key", http_post=_fake_response("unknown")
    )

    assert classifier.classify_label("TEXTO RARO", ["electrical_room"]) is None


def test_transport_failure_returns_none_instead_of_raising() -> None:
    def _broken_post(url: str, headers: dict, payload: dict) -> dict:
        raise ConnectionError("network unavailable")

    classifier = LLMFallbackClassifier(
        provider="deepseek", api_key="test-key", http_post=_broken_post
    )

    assert classifier.classify_label("SALA ELECTRICA", ["electrical_room"]) is None


def test_unsupported_provider_raises_at_construction() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMFallbackClassifier(provider="not-a-real-provider")


def test_empty_text_returns_none_without_calling_transport() -> None:
    calls = []

    def _tracking_post(url: str, headers: dict, payload: dict) -> dict:
        calls.append(payload)
        return {"choices": [{"message": {"content": "electrical_room"}}]}

    classifier = LLMFallbackClassifier(
        provider="deepseek", api_key="test-key", http_post=_tracking_post
    )

    assert classifier.classify_label("   ", ["electrical_room"]) is None
    assert calls == []
