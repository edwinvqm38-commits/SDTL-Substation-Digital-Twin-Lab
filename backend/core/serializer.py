from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


def serialize_model(model: BaseModel) -> str:
    """Serialize an SDTL Pydantic model to formatted JSON."""

    if not isinstance(model, BaseModel):
        raise TypeError("serialize_model expects a Pydantic BaseModel instance")

    return model.model_dump_json(indent=2)


def save_json(model: BaseModel, path: str | Path) -> None:
    """Serialize an SDTL model and save it as a UTF-8 JSON file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialize_model(model), encoding="utf-8")
