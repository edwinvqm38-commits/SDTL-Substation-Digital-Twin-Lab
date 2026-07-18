import { NullEngine, Scene } from "@babylonjs/core";
import { describe, expect, it, vi } from "vitest";

import { MetadataPanel } from "../metadata_panel.js";
import { ObjectLoader } from "../object_loader.js";
import { SceneManager } from "../scene_manager.js";
import { SelectionManager } from "../selection_manager.js";
import demoGltf from "../../demo/electrical_room_demo.gltf?raw";

const palette = {
  background: "#E8EDF1FF",
  gridMinor: "#C9D2D8A6",
  gridMajor: "#93A4AFFF",
  axisX: "#C43C3C",
  axisY: "#2E8B57",
  axisZ: "#3973B8",
  selection: "#E0B82E",
};

function fakeMesh() {
  return {
    uniqueId: 17,
    name: "Wall_1",
    parent: null,
    isPickable: false,
    metadata: {
      gltf: {
        extras: {
          metadata: {
            sdtl_id: "CIV-ROOM-001",
            object_type: "ElectricalRoom",
            component_name: "Wall_1",
            source_pdf: "SE-PI-PL-OC-700.pdf",
            page: 2,
          },
        },
      },
    },
    getTotalVertices: () => 4,
    dispose: vi.fn(),
  };
}

describe("SDTL viewer", () => {
  it("creates a Babylon scene with an orbital camera", () => {
    const canvas = document.createElement("canvas");
    const manager = new SceneManager(canvas, palette, {
      engineFactory: () => new NullEngine({ renderWidth: 800, renderHeight: 600 }),
    });

    expect(manager.scene).toBeDefined();
    expect(manager.camera.name).toBe("SDTL_OrbitCamera");
    expect(manager.scene.lights).toHaveLength(2);
    manager.dispose();
  });

  it("loads a model and registers its SDTL relationship", async () => {
    const mesh = fakeMesh();
    const importer = vi.fn().mockResolvedValue({ meshes: [mesh] });
    const loader = new ObjectLoader({}, {}, importer);

    const result = await loader.loadUrl("./demo/room.gltf");

    expect(importer).toHaveBeenCalledWith("./demo/room.gltf", {});
    expect(result.meshes).toEqual([mesh]);
    expect(loader.relationFor(mesh).sdtl_object).toBe("CIV-ROOM-001");
    expect(mesh.isPickable).toBe(true);
  });

  it("imports the generated demo through the Babylon glTF loader", async () => {
    const engine = new NullEngine({ renderWidth: 800, renderHeight: 600 });
    const scene = new Scene(engine);
    const loader = new ObjectLoader(scene);

    const result = await loader.loadUrl(`data:${demoGltf}`);
    const objects = loader.listObjects();

    expect(result.meshes.length).toBeGreaterThan(1);
    expect(objects).toHaveLength(1);
    expect(objects[0].id).toBe("CIV-ROOM-001");
    expect(objects[0].metadata.source_pdf).toBe("SE-PI-PL-OC-700.pdf");
    scene.dispose();
    engine.dispose();
  });

  it("selects every mesh related to one SDTL object", () => {
    const mesh = fakeMesh();
    const relation = {
      mesh,
      component: "Wall_1",
      sdtl_object: "CIV-ROOM-001",
      metadata: { sdtl_id: "CIV-ROOM-001", object_type: "ElectricalRoom" },
    };
    const loader = {
      relationFor: () => relation,
      meshesForObject: () => [mesh],
    };
    const highlightLayer = {
      addMesh: vi.fn(),
      removeMesh: vi.fn(),
      dispose: vi.fn(),
    };
    const scene = { onPointerObservable: { add: vi.fn(), remove: vi.fn() } };
    const selection = new SelectionManager(scene, loader, palette.selection, { highlightLayer });
    const listener = vi.fn();
    selection.onObjectSelected(listener);

    const selected = selection.selectMesh(mesh);

    expect(selected.sdtl_object).toBe("CIV-ROOM-001");
    expect(highlightLayer.addMesh).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledOnce();
    selection.dispose();
  });

  it("renders engineering and traceability metadata", () => {
    const container = document.createElement("div");
    const panel = new MetadataPanel(container);

    panel.render({
      sdtl_id: "CIV-ROOM-001",
      object_type: "ElectricalRoom",
      state: "approved",
      confidence: 0.93,
      dimensions: { length: 12, width: 8, height: 4 },
      unit: "m",
      material: "Concrete",
      source_pdf: "SE-PI-PL-OC-700.pdf",
      page: 2,
      source_geometry: "GEO-ROOM-001",
    });

    expect(container.textContent).toContain("CIV-ROOM-001");
    expect(container.textContent).toContain("93 %");
    expect(container.textContent).toContain("SE-PI-PL-OC-700.pdf");
    expect(container.textContent).toContain("length: 12 m");
  });
});
