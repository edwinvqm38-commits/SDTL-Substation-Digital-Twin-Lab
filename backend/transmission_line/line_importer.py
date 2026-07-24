from __future__ import annotations

import csv
from pathlib import Path

from pydantic import ValidationError

from .models import ConductorSpan, GeoPoint, Tower


class TransmissionLineImportError(ValueError):
    """Raised when a structured tower/span CSV fails validation."""


class TransmissionLineImporter:
    """Build Tower/ConductorSpan proposals from engineer-authored CSV files.

    Every row becomes a "proposal" asset, exactly like a candidate coming
    out of the PDF pipeline -- structured input still requires an explicit
    human .approve() (see TransmissionAsset) before it can generate 3D
    geometry or count as part of the active digital twin.
    """

    def import_towers(self, path: str | Path) -> list[Tower]:
        source = Path(path)
        towers: list[Tower] = []
        with source.open(encoding="utf-8-sig", newline="") as file:
            for row_number, row in enumerate(csv.DictReader(file), start=2):
                try:
                    towers.append(
                        Tower(
                            id=row["id"],
                            source_dataset=f"{source.name}:row={row_number}",
                            name=row["name"],
                            tower_type=row["tower_type"],
                            location=GeoPoint(
                                latitude=float(row["latitude"]),
                                longitude=float(row["longitude"]),
                                elevation_m=float(row["elevation_m"]) if row.get("elevation_m") else 0.0,
                            ),
                            height_m=float(row["height_m"]),
                            base_width_m=(
                                float(row["base_width_m"]) if row.get("base_width_m") else None
                            ),
                        )
                    )
                except (KeyError, ValueError, ValidationError) as error:
                    raise TransmissionLineImportError(
                        f"{source.name} row {row_number}: {error}"
                    ) from error
        if not towers:
            raise TransmissionLineImportError(f"{source.name} contains no tower rows")
        return towers

    def import_spans(self, path: str | Path, towers: list[Tower]) -> list[ConductorSpan]:
        source = Path(path)
        known_ids = {tower.id for tower in towers}
        spans: list[ConductorSpan] = []
        with source.open(encoding="utf-8-sig", newline="") as file:
            for row_number, row in enumerate(csv.DictReader(file), start=2):
                try:
                    from_tower_id = row["from_tower_id"]
                    to_tower_id = row["to_tower_id"]
                    for tower_id in (from_tower_id, to_tower_id):
                        if tower_id not in known_ids:
                            raise ValueError(f"unknown tower id: {tower_id}")
                    spans.append(
                        ConductorSpan(
                            id=row["id"],
                            source_dataset=f"{source.name}:row={row_number}",
                            from_tower_id=from_tower_id,
                            to_tower_id=to_tower_id,
                            conductor_type=row["conductor_type"],
                            conductors_per_phase=(
                                int(row["conductors_per_phase"])
                                if row.get("conductors_per_phase")
                                else 1
                            ),
                            sag_m=float(row["sag_m"]) if row.get("sag_m") else None,
                        )
                    )
                except (KeyError, ValueError, ValidationError) as error:
                    raise TransmissionLineImportError(
                        f"{source.name} row {row_number}: {error}"
                    ) from error
        return spans
