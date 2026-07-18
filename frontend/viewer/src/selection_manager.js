import { PointerEventTypes } from "@babylonjs/core/Events/pointerEvents.js";
import { HighlightLayer } from "@babylonjs/core/Layers/highlightLayer.js";
import { Color3 } from "@babylonjs/core/Maths/math.color.js";

export class SelectionManager {
  constructor(scene, objectLoader, selectionColor, options = {}) {
    this.scene = scene;
    this.objectLoader = objectLoader;
    this.highlightLayer = options.highlightLayer ?? new HighlightLayer("SDTL_Selection", scene);
    this.selectionColor = Color3.FromHexString(selectionColor);
    this.listeners = new Set();
    this.selectedMeshes = [];
    this.pointerObserver = scene.onPointerObservable?.add((event) => {
      if (event.type !== PointerEventTypes.POINTERPICK) return;
      const mesh = event.pickInfo?.pickedMesh;
      if (mesh) this.selectMesh(mesh);
    });
  }

  onObjectSelected(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  selectMesh(mesh) {
    const relation = this.objectLoader.relationFor(mesh);
    if (!relation) return null;
    return this.selectObject(relation.sdtl_object, relation);
  }

  selectObject(sdtlId, preferredRelation = null) {
    this.clear();
    const meshes = this.objectLoader.meshesForObject(sdtlId);
    for (const mesh of meshes) this.highlightLayer.addMesh(mesh, this.selectionColor);
    this.selectedMeshes = meshes;
    const relation = preferredRelation ?? this.objectLoader.relationFor(meshes[0]);
    if (!relation) return null;
    const selection = { ...relation, meshes };
    for (const listener of this.listeners) listener(selection);
    return selection;
  }

  clear() {
    for (const mesh of this.selectedMeshes) this.highlightLayer.removeMesh(mesh);
    this.selectedMeshes = [];
  }

  dispose() {
    this.clear();
    if (this.pointerObserver) this.scene.onPointerObservable.remove(this.pointerObserver);
    this.highlightLayer.dispose?.();
    this.listeners.clear();
  }
}
