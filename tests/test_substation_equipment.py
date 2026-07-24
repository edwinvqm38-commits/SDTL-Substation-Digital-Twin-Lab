from __future__ import annotations

import pytest

from backend.geometry_3d import (
    BusbarGenerator,
    CircuitBreakerGenerator,
    DisconnectorGenerator,
    InsulatorStringGenerator,
    LightningArresterGenerator,
    TransformerGenerator,
)
from backend.object_generation import ObjectMapper
from backend.sdtl_core.entities import (
    Busbar,
    CircuitBreaker,
    Disconnector,
    InsulatorString,
    LightningArrester,
    Transformer,
)

GENERATORS = {
    "Transformer": (Transformer, TransformerGenerator, "Steel"),
    "CircuitBreaker": (CircuitBreaker, CircuitBreakerGenerator, "Steel"),
    "Disconnector": (Disconnector, DisconnectorGenerator, "Steel"),
    "Busbar": (Busbar, BusbarGenerator, "Steel"),
    "InsulatorString": (InsulatorString, InsulatorStringGenerator, "Porcelain"),
    "LightningArrester": (LightningArrester, LightningArresterGenerator, "Porcelain"),
}


def make_equipment(entity_class, *, approved: bool = True, dimensions=None):
    equipment = entity_class(
        id=f"CIV-{entity_class.__name__.upper()}-001",
        source_geometry="GEO-EQUIP-001",
        dimensions=(
            {"length": 3.0, "width": 2.0, "height": 2.5} if dimensions is None else dimensions
        ),
        source_pdf="SE-PI-PL-OC-800.pdf",
        page=1,
    )
    if approved:
        equipment.approve("engineer@sdtl.local")
    return equipment


@pytest.mark.parametrize("object_type", GENERATORS)
def test_generates_a_to_scale_footprint_box(object_type: str) -> None:
    entity_class, generator, material_name = GENERATORS[object_type]
    model = generator.generate(make_equipment(entity_class))

    assert model.type == object_type
    assert model.component_names == ["Body"]
    assert model.components[0].material.name == material_name
    vertices = model.components[0].mesh.vertices
    assert max(point[0] for point in vertices) == pytest.approx(3.0)
    assert max(point[1] for point in vertices) == pytest.approx(2.0)
    assert max(point[2] for point in vertices) == pytest.approx(2.5)


@pytest.mark.parametrize("object_type", GENERATORS)
def test_rejects_unapproved_equipment(object_type: str) -> None:
    entity_class, generator, _ = GENERATORS[object_type]

    with pytest.raises(ValueError, match="approved"):
        generator.generate(make_equipment(entity_class, approved=False))


@pytest.mark.parametrize("object_type", GENERATORS)
def test_rejects_equipment_missing_dimensions(object_type: str) -> None:
    entity_class, generator, _ = GENERATORS[object_type]

    with pytest.raises(ValueError, match="missing dimensions"):
        generator.generate(make_equipment(entity_class, dimensions={}))


@pytest.mark.parametrize(
    ("candidate_type", "object_type"),
    [
        ("transformer", "Transformer"),
        ("circuit_breaker", "CircuitBreaker"),
        ("disconnector", "Disconnector"),
        ("busbar", "Busbar"),
        ("insulator_string", "InsulatorString"),
        ("lightning_arrester", "LightningArrester"),
    ],
)
def test_object_mapper_resolves_substation_equipment_types(
    candidate_type: str, object_type: str
) -> None:
    mapper = ObjectMapper()

    assert mapper.map_type(candidate_type) == object_type
    assert mapper.entity_class(object_type).__name__ == object_type
