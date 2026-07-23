import { describe, expect, it, vi } from "vitest";

import { LayerFilter } from "../layer_filter.js";

const catalog = {
  objectTypes: {
    ElectricalRoom: { label: "Sala electrica", category: "Obras civiles" },
    CableTrench: { label: "Canaleta de cables", category: "Canaletas" },
    Foundation: { label: "Fundacion", category: "Fundaciones" },
  },
};

function fakeMesh() {
  return { setEnabled: vi.fn() };
}

function objectsFixture() {
  const roomMesh = fakeMesh();
  const trenchMesh = fakeMesh();
  return [
    { id: "OBJ-ROOM-1", type: "ElectricalRoom", meshes: [roomMesh] },
    { id: "OBJ-TRENCH-1", type: "CableTrench", meshes: [trenchMesh] },
  ];
}

describe("LayerFilter", () => {
  it("renders one row per object type grouped by catalog category", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);

    filter.setObjects(objectsFixture());

    expect(container.textContent).toContain("Obras civiles");
    expect(container.textContent).toContain("Sala electrica");
    expect(container.textContent).toContain("Canaletas");
    expect(container.textContent).toContain("Canaleta de cables");
    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(2);
  });

  it("hides every mesh of a type when its checkbox is unchecked", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    const objects = objectsFixture();
    filter.setObjects(objects);

    filter.setVisible("ElectricalRoom", false);

    expect(objects[0].meshes[0].setEnabled).toHaveBeenCalledWith(false);
    expect(objects[1].meshes[0].setEnabled).not.toHaveBeenCalledWith(false);
  });

  it("re-shows a type's meshes when toggled back on", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    const objects = objectsFixture();
    filter.setObjects(objects);

    filter.setVisible("ElectricalRoom", false);
    filter.setVisible("ElectricalRoom", true);

    expect(objects[0].meshes[0].setEnabled).toHaveBeenLastCalledWith(true);
  });

  it("checkbox change events toggle visibility through the DOM", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    const objects = objectsFixture();
    filter.setObjects(objects);

    const checkbox = container.querySelector('input[type="checkbox"]');
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change"));

    expect(filter.isVisible("ElectricalRoom")).toBe(false);
  });

  it("hideAll and showAll affect every known type", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    const objects = objectsFixture();
    filter.setObjects(objects);

    filter.hideAll();
    expect(objects[0].meshes[0].setEnabled).toHaveBeenLastCalledWith(false);
    expect(objects[1].meshes[0].setEnabled).toHaveBeenLastCalledWith(false);

    filter.showAll();
    expect(objects[0].meshes[0].setEnabled).toHaveBeenLastCalledWith(true);
    expect(objects[1].meshes[0].setEnabled).toHaveBeenLastCalledWith(true);
  });

  it("falls back to an ungrouped category for unknown object types", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, {});

    filter.setObjects([{ id: "OBJ-X", type: "Fence", meshes: [fakeMesh()] }]);

    expect(container.textContent).toContain("Sin clasificar");
    expect(container.textContent).toContain("Fence");
  });

  it("clears the panel when there are no objects", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    filter.setObjects(objectsFixture());

    filter.setObjects([]);

    expect(container.children).toHaveLength(0);
  });

  it("shows the count of objects sharing a type", () => {
    const container = document.createElement("div");
    const filter = new LayerFilter(container, catalog);
    const secondRoomMesh = fakeMesh();

    filter.setObjects([
      ...objectsFixture(),
      { id: "OBJ-ROOM-2", type: "ElectricalRoom", meshes: [secondRoomMesh] },
    ]);

    const rows = [...container.querySelectorAll(".layer-filter-item")];
    const roomRow = rows.find((row) => row.textContent.includes("Sala electrica"));
    expect(roomRow.querySelector("small").textContent).toBe("2");
  });
});
