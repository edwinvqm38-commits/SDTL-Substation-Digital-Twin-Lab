from __future__ import annotations

from backend.pipeline.cross_reference import ProjectCrossReferenceEngine
from backend.sdtl_core.entities import ElectricalRoom, Foundation


def make_room(
    object_id: str,
    source_pdf: str,
    *,
    length: float | None = 20.0,
    width: float | None = 12.0,
    height_source: str = "drawing",
    height: float = 3.0,
    label: str = "SALA ELECTRICA",
) -> ElectricalRoom:
    dimensions = []
    if length is not None:
        dimensions.append({"name": "length", "value": length, "unit": "m", "source": "drawing"})
    if width is not None:
        dimensions.append({"name": "width", "value": width, "unit": "m", "source": "drawing"})
    dimensions.append({"name": "height", "value": height, "unit": "m", "source": height_source})

    return ElectricalRoom(
        id=object_id,
        source_geometry=f"GEO-{object_id}",
        dimensions=dimensions,
        properties={
            "matched_labels": [label],
            "dimension_defaults_applied": ["height"] if height_source != "drawing" else [],
        },
        source_pdf=source_pdf,
        page=1,
    )


class TestGroupingAndScope:
    def test_objects_from_a_single_pdf_are_not_cross_referenced(self) -> None:
        objects = [
            make_room("OBJ-1", "civil.pdf", height_source="default"),
            make_room("OBJ-2", "civil.pdf", height_source="default"),
        ]

        report = ProjectCrossReferenceEngine().run(objects)

        assert report.groups_matched == 0
        assert report.enrichments == []

    def test_objects_without_matched_labels_do_not_crash(self) -> None:
        room = make_room("OBJ-1", "civil.pdf")
        room.properties = {}

        report = ProjectCrossReferenceEngine().run([room])

        assert report.groups_matched == 0

    def test_different_labels_are_not_grouped_together(self) -> None:
        objects = [
            make_room("OBJ-1", "civil.pdf", label="SALA ELECTRICA"),
            make_room("OBJ-2", "electrico.pdf", label="SALA DE TABLEROS"),
        ]

        report = ProjectCrossReferenceEngine().run(objects)

        assert report.groups_matched == 0


class TestConsistencyChecks:
    def test_agreeing_measurements_produce_no_conflict(self) -> None:
        objects = [
            make_room("OBJ-1", "civil.pdf", length=20.0),
            make_room("OBJ-2", "arquitectonico.pdf", length=20.3),
        ]

        report = ProjectCrossReferenceEngine().run(objects)

        assert report.groups_matched == 1
        assert report.conflicts == []

    def test_disagreeing_measurements_are_reported_not_silently_averaged(self) -> None:
        objects = [
            make_room("OBJ-1", "civil.pdf", length=20.0),
            make_room("OBJ-2", "arquitectonico.pdf", length=24.0),
        ]

        report = ProjectCrossReferenceEngine().run(objects)

        assert len(report.conflicts) == 1
        conflict = report.conflicts[0]
        assert conflict.dimension_name == "length"
        assert conflict.values == {"civil.pdf": 20.0, "arquitectonico.pdf": 24.0}
        assert conflict.relative_difference == 0.2

    def test_tolerance_is_configurable(self) -> None:
        objects = [
            make_room("OBJ-1", "civil.pdf", length=20.0),
            make_room("OBJ-2", "arquitectonico.pdf", length=21.0),
        ]

        loose = ProjectCrossReferenceEngine(tolerance=0.10).run(objects)
        strict = ProjectCrossReferenceEngine(tolerance=0.01).run(
            [make_room("OBJ-1", "civil.pdf", length=20.0), make_room("OBJ-2", "arquitectonico.pdf", length=21.0)]
        )

        assert loose.conflicts == []
        assert len(strict.conflicts) == 1


class TestEnrichment:
    def test_missing_dimension_is_borrowed_from_sibling_plan(self) -> None:
        civil_room = make_room("OBJ-CIVIL", "civil.pdf", height_source="drawing", height=3.2)
        architectural_room = make_room(
            "OBJ-ARQ", "arquitectonico.pdf", height_source="default", height=3.0
        )

        report = ProjectCrossReferenceEngine().run([civil_room, architectural_room])

        assert len(report.enrichments) == 1
        enrichment = report.enrichments[0]
        assert enrichment.object_id == "OBJ-ARQ"
        assert enrichment.dimension_name == "height"
        assert enrichment.value == 3.2
        assert enrichment.borrowed_from_pdf == "civil.pdf"

        dimensions = {item["name"]: item for item in architectural_room.dimensions}
        assert dimensions["height"]["value"] == 3.2
        assert dimensions["height"]["source"] == "cross_reference"
        assert dimensions["height"]["borrowed_from_pdf"] == "civil.pdf"
        assert "height" not in architectural_room.properties["dimension_defaults_applied"]

    def test_does_not_overwrite_a_sibling_that_also_measured_it(self) -> None:
        civil_room = make_room("OBJ-CIVIL", "civil.pdf", height_source="drawing", height=3.2)
        electrical_room = make_room(
            "OBJ-ELEC", "electrico.pdf", height_source="drawing", height=3.3
        )

        report = ProjectCrossReferenceEngine().run([civil_room, electrical_room])

        assert report.enrichments == []
        dimensions = {item["name"]: item for item in electrical_room.dimensions}
        assert dimensions["height"]["value"] == 3.3
        assert dimensions["height"]["source"] == "drawing"


class TestScopingByType:
    def test_same_label_different_object_types_are_not_grouped(self) -> None:
        room = make_room("OBJ-ROOM", "civil.pdf", label="E-01")
        foundation = Foundation(
            id="OBJ-FOUND",
            source_geometry="GEO-FOUND",
            dimensions=[{"name": "height", "value": 1.0, "unit": "m", "source": "drawing"}],
            properties={"matched_labels": ["E-01"]},
            source_pdf="electrico.pdf",
            page=1,
        )

        report = ProjectCrossReferenceEngine().run([room, foundation])

        assert report.groups_matched == 0
