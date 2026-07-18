from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ExtractedText(BaseModel):
    """Represents text located within an engineering drawing, including its page, bounds, and typography."""

    model_config = ConfigDict(extra="forbid")

    text_id: str
    document_id: str
    page_number: int
    content: str
    x: float
    y: float
    width: float
    height: float
    font_size: float | None = None
    font_name: str | None = None
    confidence: float
