from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from backend.pipeline.extraction_pipeline import DrawingToObjectsPipeline


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
    electrical_room_pdf: Path,
) -> None:
    result = DrawingToObjectsPipeline().run(electrical_room_pdf)

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


def test_pipeline_report_lists_skipped_low_confidence_candidates(
    electrical_room_pdf: Path,
) -> None:
    result = DrawingToObjectsPipeline().run(electrical_room_pdf)

    assert result.statistics["candidates"] >= result.statistics["objects_created"]
    assert result.statistics["candidates"] == (
        result.statistics["objects_created"] + result.statistics["objects_skipped"]
    )
