from __future__ import annotations

from dataclasses import dataclass, field
import unicodedata

from backend.sdtl_core.entities import CivilObject

_DIMENSION_SOURCE_FROM_DRAWING = "drawing"


def _normalize_label(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.upper())
    return "".join(character for character in normalized if not unicodedata.combining(character)).strip()


@dataclass
class DimensionConflict:
    """Two or more plans of the same project disagree on a measured value."""

    object_type: str
    label: str
    dimension_name: str
    values: dict[str, float]  # source_pdf -> value (all normalized to the same unit)
    unit: str
    relative_difference: float


@dataclass
class DimensionEnrichment:
    """An object's assumed dimension was replaced with one read directly off
    a sibling plan of the same project, instead of a historical/static guess."""

    object_id: str
    object_type: str
    label: str
    dimension_name: str
    value: float
    unit: str
    borrowed_from_pdf: str


@dataclass
class CrossReferenceReport:
    groups_matched: int = 0
    conflicts: list[DimensionConflict] = field(default_factory=list)
    enrichments: list[DimensionEnrichment] = field(default_factory=list)


class ProjectCrossReferenceEngine:
    """Compare SDTL objects extracted independently from multiple plans of
    the same project (e.g. a civil, an electrical, and an architectural PDF
    for the same substation) to catch disagreements and fill gaps.

    Objects are matched across plans by (object type, drawing text label) --
    e.g. an "ElectricalRoom" labelled "SALA ELECTRICA" in the civil plan and
    again in the architectural plan -- since independently extracted sheets
    generally do not share a coordinate system to match on geometry alone.
    Matching therefore depends on plans using consistent labels/tags (a
    normal drafting convention); objects that only exist on one sheet are
    left untouched and are not a conflict.

    Within a matched group:
      - if two or more plans give a "drawing"-sourced value for the same
        named dimension and they disagree by more than `tolerance`, that is
        reported as a DimensionConflict for a human to resolve -- never
        silently averaged or overwritten.
      - if one plan is missing a dimension (it only has a "default" or
        "historical_estimate" value) and a sibling plan measured it directly,
        the missing one is overwritten with the sibling's value, labelled
        source="cross_reference" with the originating PDF, and reported as a
        DimensionEnrichment.
    """

    def __init__(self, tolerance: float = 0.10) -> None:
        if tolerance < 0:
            raise ValueError("tolerance must be greater than or equal to zero")
        self.tolerance = tolerance

    def run(self, objects: list[CivilObject]) -> CrossReferenceReport:
        report = CrossReferenceReport()

        for (object_type, label), group in self._group(objects).items():
            source_pdfs = {obj.source_pdf for obj in group}
            if len(source_pdfs) < 2:
                continue
            report.groups_matched += 1

            for dimension_name in self._dimension_names(group):
                measured = self._measured_values(group, dimension_name)
                if len(measured) >= 2:
                    self._check_conflict(
                        object_type, label, dimension_name, measured, report
                    )
                if measured:
                    self._enrich_missing(
                        group, dimension_name, measured, object_type, label, report
                    )

        return report

    def _group(
        self, objects: list[CivilObject]
    ) -> dict[tuple[str, str], list[CivilObject]]:
        groups: dict[tuple[str, str], list[CivilObject]] = {}
        for obj in objects:
            for label in self._labels(obj):
                key = (obj.type, label)
                groups.setdefault(key, []).append(obj)
        return groups

    @staticmethod
    def _labels(obj: CivilObject) -> list[str]:
        raw_labels = obj.properties.get("matched_labels") if isinstance(obj.properties, dict) else None
        if not raw_labels:
            return []
        return sorted({_normalize_label(str(label)) for label in raw_labels if str(label).strip()})

    @staticmethod
    def _dimension_names(group: list[CivilObject]) -> set[str]:
        names: set[str] = set()
        for obj in group:
            if isinstance(obj.dimensions, list):
                names.update(
                    item["name"] for item in obj.dimensions if isinstance(item, dict) and "name" in item
                )
        return names

    @staticmethod
    def _measured_values(
        group: list[CivilObject], dimension_name: str
    ) -> dict[str, tuple[float, str]]:
        """source_pdf -> (value, unit) for every object that measured this
        dimension directly off its own drawing (source == "drawing")."""

        measured: dict[str, tuple[float, str]] = {}
        for obj in group:
            if not isinstance(obj.dimensions, list):
                continue
            for item in obj.dimensions:
                if (
                    isinstance(item, dict)
                    and item.get("name") == dimension_name
                    and item.get("source") == _DIMENSION_SOURCE_FROM_DRAWING
                ):
                    measured[obj.source_pdf] = (item["value"], item.get("unit", "m"))
        return measured

    def _check_conflict(
        self,
        object_type: str,
        label: str,
        dimension_name: str,
        measured: dict[str, tuple[float, str]],
        report: CrossReferenceReport,
    ) -> None:
        values = {pdf: value for pdf, (value, _unit) in measured.items()}
        unit = next(iter(measured.values()))[1]
        smallest, largest = min(values.values()), max(values.values())
        if smallest <= 0:
            return
        relative_difference = (largest - smallest) / smallest
        if relative_difference > self.tolerance:
            report.conflicts.append(
                DimensionConflict(
                    object_type=object_type,
                    label=label,
                    dimension_name=dimension_name,
                    values=values,
                    unit=unit,
                    relative_difference=round(relative_difference, 4),
                )
            )

    @staticmethod
    def _enrich_missing(
        group: list[CivilObject],
        dimension_name: str,
        measured: dict[str, tuple[float, str]],
        object_type: str,
        label: str,
        report: CrossReferenceReport,
    ) -> None:
        source_pdf, (value, unit) = next(iter(measured.items()))

        for obj in group:
            if obj.source_pdf in measured or not isinstance(obj.dimensions, list):
                continue
            dimensions = [dict(item) for item in obj.dimensions]
            existing = next(
                (item for item in dimensions if item.get("name") == dimension_name), None
            )
            if existing is not None and existing.get("source") == _DIMENSION_SOURCE_FROM_DRAWING:
                continue

            entry = {
                "name": dimension_name,
                "value": value,
                "unit": unit,
                "source": "cross_reference",
                "borrowed_from_pdf": source_pdf,
            }
            if existing is None:
                dimensions.append(entry)
            else:
                dimensions[dimensions.index(existing)] = entry
            obj.dimensions = dimensions

            defaults_applied = obj.properties.get("dimension_defaults_applied", [])
            obj.properties = {
                **obj.properties,
                "dimension_defaults_applied": [
                    name for name in defaults_applied if name != dimension_name
                ],
            }
            report.enrichments.append(
                DimensionEnrichment(
                    object_id=obj.id,
                    object_type=object_type,
                    label=label,
                    dimension_name=dimension_name,
                    value=value,
                    unit=unit,
                    borrowed_from_pdf=source_pdf,
                )
            )
