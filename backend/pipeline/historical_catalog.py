from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from backend.sdtl_core.entities import CivilObject

_DEFAULT_DB_PATH = Path(__file__).parents[2] / "data" / "historical_catalog.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS historical_dimensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_type TEXT NOT NULL,
    dimension_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    source_pdf TEXT NOT NULL,
    object_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL
)
"""


@dataclass
class HistoricalSuggestion:
    object_type: str
    dimension_name: str
    value: float
    unit: str
    sample_size: int
    minimum: float
    maximum: float


class HistoricalCatalog:
    """Local, no-cost record of previously approved SDTL objects.

    Every time a human approves an object, its named dimensions are recorded
    here. When a later drawing is missing a dimension a 2D view cannot show
    (e.g. a room's height), DimensionResolver consults this catalog before
    falling back to a single fixed default -- so the assumption is grounded
    in "N similar approved constructions averaged X" instead of one made-up
    number, and that provenance is always kept alongside the value.

    Only objects a human has approved are recorded (state != "proposal"),
    since an unapproved proposal's dimensions are not yet confirmed fact.
    """

    MINIMUM_SAMPLES = 3

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(_SCHEMA)

    def record(self, civil_object: CivilObject) -> int:
        """Store every named numeric dimension of an approved object. Returns
        the number of rows recorded (0 if the object is not yet approved or
        has no named dimensions)."""

        if civil_object.state == "proposal":
            return 0

        dimensions = civil_object.dimensions
        if not isinstance(dimensions, list):
            return 0

        rows = [
            (
                civil_object.type,
                item["name"],
                float(item["value"]),
                item.get("unit", "m"),
                civil_object.source_pdf,
                civil_object.id,
                datetime.now(timezone.utc).isoformat(),
            )
            for item in dimensions
            if isinstance(item, dict) and "name" in item and "value" in item
        ]
        if not rows:
            return 0

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO historical_dimensions
                    (object_type, dimension_name, value, unit, source_pdf, object_id, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def suggest(self, object_type: str, dimension_name: str) -> HistoricalSuggestion | None:
        """Return a median-based suggestion if enough historical samples of
        this object type and dimension exist, else None."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT value, unit FROM historical_dimensions
                WHERE object_type = ? AND dimension_name = ?
                """,
                (object_type, dimension_name),
            )
            rows = cursor.fetchall()

        if len(rows) < self.MINIMUM_SAMPLES:
            return None

        values = [row[0] for row in rows]
        units = [row[1] for row in rows]
        most_common_unit = max(set(units), key=units.count)
        return HistoricalSuggestion(
            object_type=object_type,
            dimension_name=dimension_name,
            value=median(values),
            unit=most_common_unit,
            sample_size=len(values),
            minimum=min(values),
            maximum=max(values),
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
