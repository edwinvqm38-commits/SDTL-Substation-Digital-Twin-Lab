import { ImportMeshAsync } from "@babylonjs/core/Loading/sceneLoader.js";

export class ObjectLoader {
  constructor(scene, visualCatalog = {}, importer = ImportMeshAsync) {
    this.scene = scene;
    this.visualCatalog = visualCatalog;
    this.importer = importer;
    this.relations = new Map();
    this.loadedMeshes = [];
    this.loaderReady = null;
  }

  async loadUrl(url) {
    await this.#ensureGltfLoader();
    this.disposeLoaded();
    const result = await this.importer(url, this.scene);
    this.registerMeshes(result.meshes ?? []);
    return result;
  }

  async loadFile(file) {
    await this.#ensureGltfLoader();
    const extension = file.name.toLowerCase().endsWith(".glb") ? ".glb" : ".gltf";
    this.disposeLoaded();
    const result = await this.importer(file, this.scene, { pluginExtension: extension });
    this.registerMeshes(result.meshes ?? []);
    return result;
  }

  registerMeshes(meshes) {
    this.loadedMeshes = meshes;
    this.relations.clear();
    for (const mesh of meshes) {
      if (mesh.getTotalVertices?.() <= 0) continue;
      const metadata = this.#resolveMetadata(mesh);
      if (!metadata?.sdtl_id) continue;
      mesh.isPickable = true;
      this.relations.set(mesh.uniqueId, {
        mesh,
        component: metadata.component_name ?? mesh.name,
        sdtl_object: metadata.sdtl_id,
        metadata: this.#withCatalogMetadata(metadata),
      });
    }
    return this.listObjects();
  }

  relationFor(mesh) {
    let current = mesh;
    while (current) {
      const relation = this.relations.get(current.uniqueId);
      if (relation) return relation;
      current = current.parent;
    }
    return null;
  }

  meshesForObject(sdtlId) {
    return [...this.relations.values()]
      .filter((relation) => relation.sdtl_object === sdtlId)
      .map((relation) => relation.mesh);
  }

  listObjects() {
    const objects = new Map();
    for (const relation of this.relations.values()) {
      if (!objects.has(relation.sdtl_object)) {
        objects.set(relation.sdtl_object, {
          id: relation.sdtl_object,
          type: relation.metadata.object_type,
          metadata: relation.metadata,
          meshes: [],
        });
      }
      objects.get(relation.sdtl_object).meshes.push(relation.mesh);
    }
    return [...objects.values()];
  }

  disposeLoaded() {
    for (const mesh of this.loadedMeshes) mesh.dispose?.();
    this.loadedMeshes = [];
    this.relations.clear();
  }

  #resolveMetadata(mesh) {
    let current = mesh;
    while (current) {
      const raw = current.metadata?.gltf?.extras ?? current.metadata?.extras ?? current.metadata;
      const metadata = raw?.metadata ?? raw;
      if (metadata?.sdtl_id) return metadata;
      current = current.parent;
    }
    return null;
  }

  #withCatalogMetadata(metadata) {
    const visual = this.visualCatalog.objectTypes?.[metadata.object_type] ?? {};
    return {
      ...metadata,
      material: metadata.material ?? visual.material ?? null,
      display_name: visual.label ?? metadata.object_type,
      category: visual.category ?? "Sin clasificar",
    };
  }

  async #ensureGltfLoader() {
    this.loaderReady ??= import("@babylonjs/loaders/glTF");
    await this.loaderReady;
  }
}
