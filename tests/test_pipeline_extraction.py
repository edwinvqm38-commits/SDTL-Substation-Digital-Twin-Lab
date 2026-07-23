from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from backend.drawing_analyzer.semantic_engine import LLMFallbackClassifier
from backend.pipeline.dimension_resolver import DimensionResolver
from backend.pipeline.extraction_pipeline import DrawingToObjectsPipeline
from backend.pipeline.historical_catalog import HistoricalCatalog


def _isolated_pipeline(
    tmp_path: Path, llm_classifier: LLMFallbackClassifier | None = None
) -> DrawingToObjectsPipeline:
    """Build a pipeline backed by a throwaway historical catalog so tests
    never read or write the repo's real data/historical_catalog.sqlite3."""

    resolver = DimensionResolver(
        historical_catalog=HistoricalCatalog(tmp_path / "history.sqlite3")
    )
    return DrawingToObjectsPipeline(
        dimension_resolver=resolver, llm_classifier=llm_classifier
    )


def _draw_line(page: fitz.Page, start: tuple[float, float], end: tuple[float, float]) -> None:
    shape = page.new_shape()
    shape.draw_line(fitz.Point(*start), fitz.Point(*end))
    shape.finish(width=1, color=(0, 0, 0))
    shape.commit()


def _electrical_room_pdf(path: Path) -> Path:
    """Build a minimal synthetic engineering drawing: one rectangular room with
    a horizontal and a vertical dimension (each with two extension lines) and
    a semantic label. The two dimensions are kept well past the association
    engines' default 100-unit proximity threshold from each other's line so a
    dimension's text is only ever close enough to associate with its own
    dimension line, not the other axis's.
    """

    document = fitz.open()
    page = document.new_page(width=400, height=350)

    room = page.new_shape()
    room.draw_rect(fitz.Rect(100, 100, 300, 220))
    room.finish(width=1, color=(0, 0, 0))
    room.commit()

    # Horizontal dimension (length): line + two extension lines, well above the room.
    _draw_line(page, (100, 40), (300, 40))
    _draw_line(page, (100, 40), (100, 100))
    _draw_line(page, (300, 40), (300, 100))

    # Vertical dimension (width): line + two short extension-line stubs.
    # Extension lines must stay well under half the dimension line's own
    # length (120) for ExtensionLineDetector's default is_short rule.
    _draw_line(page, (20, 100), (20, 220))
    _draw_line(page, (20, 100), (50, 100))
    _draw_line(page, (20, 220), (50, 220))

    page.insert_text(fitz.Point(190, 30), "20 m", fontsize=8)
    page.insert_text(fitz.Point(3, 160), "12 m", fontsize=8)
    page.insert_text(fitz.Point(180, 165), "SALA ELECTRICA", fontsize=8)

    document.save(path)
    document.close()
    return path


@pytest.fixture
def electrical_room_pdf(tmp_path: Path) -> Path:
    return _electrical_room_pdf(tmp_path / "SE-PI-PL-OC-900.pdf")


def test_pipeline_creates_electrical_room_proposal_from_pdf(
    electrical_room_pdf: Path, tmp_path: Path
) -> None:
    result = _isolated_pipeline(tmp_path).run(electrical_room_pdf)

    assert result.statistics["geometries"] > 0
    assert result.statistics["objects_created"] >= 1

    room = next(obj for obj in result.objects if obj.type == "ElectricalRoom")
    assert room.state == "proposal"
    assert room.source_pdf == electrical_room_pdf.name
    assert room.page == 1

    dimensions = {item["name"]: item for item in room.dimensions}
    assert dimensions["length"]["value"] == 20.0
    assert dimensions["length"]["source"] == "drawing"
    assert dimensions["width"]["value"] == 12.0
    assert dimensions["width"]["source"] == "drawing"
    assert dimensions["height"]["source"] == "default"
    assert room.properties["dimension_defaults_applied"] == ["height"]

    assert result.scale.meters_per_pdf_unit == 0.1
    assert result.scale.sample_size == 2
    assert room.properties["position"] == [20.0, 16.0, 0.0]


def test_pipeline_report_lists_skipped_low_confidence_candidates(
    electrical_room_pdf: Path, tmp_path: Path
) -> None:
    result = _isolated_pipeline(tmp_path).run(electrical_room_pdf)

    assert result.statistics["candidates"] >= result.statistics["objects_created"]
    assert result.statistics["candidates"] == (
        result.statistics["objects_created"] + result.statistics["objects_skipped"]
    )


def test_llm_fallback_annotates_semantic_only_skips(
    electrical_room_pdf: Path, tmp_path: Path
) -> None:
    def _fake_post(url: str, headers: dict, payload: dict) -> dict:
        return {"choices": [{"message": {"content": "electrical_room"}}]}

    classifier = LLMFallbackClassifier(
        provider="deepseek", api_key="test-key", http_post=_fake_post
    )

    result = _isolated_pipeline(tmp_path, llm_classifier=classifier).run(
        electrical_room_pdf
    )

    semantic_only_skips = [
        item for item in result.skipped if item.reason == "failed checks: semantic"
    ]
    assert semantic_only_skips
    assert all(item.ai_suggested_type == "electrical_room" for item in semantic_only_skips)
    assert all(item.ai_model == "deepseek:deepseek-chat" for item in semantic_only_skips)


def test_without_llm_configured_skips_have_no_ai_suggestion(
    electrical_room_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    unconfigured = LLMFallbackClassifier(provider="deepseek", api_key=None)

    result = _isolated_pipeline(tmp_path, llm_classifier=unconfigured).run(
        electrical_room_pdf
    )

    assert result.skipped
    assert all(item.ai_suggested_type is None for item in result.skipped)
