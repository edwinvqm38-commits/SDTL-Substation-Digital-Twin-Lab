import { LayerFilter } from "./layer_filter.js";
import { MetadataPanel } from "./metadata_panel.js";
import { ObjectInspector } from "./object_inspector.js";
import { ObjectLoader } from "./object_loader.js";
import { SceneManager } from "./scene_manager.js";
import { SelectionManager } from "./selection_manager.js";
import { TreeView } from "./tree_view.js";
import "./styles.css";

const canvas = document.querySelector("#render-canvas");
const loadingState = document.querySelector("#loading-state");
const status = document.querySelector("#viewer-status");
const objectCount = document.querySelector("#object-count");
const fileInput = document.querySelector("#model-file");
const catalogUrl = new URL("../catalog/visual_materials.json", import.meta.url);
const demoUrl = new URL("../demo/electrical_room_demo.gltf", import.meta.url);

async function bootstrap() {
  const catalog = await fetch(catalogUrl).then((response) => {
    if (!response.ok) throw new Error("No se pudo cargar el catalogo visual");
    return response.json();
  });
  const sceneManager = new SceneManager(canvas, catalog.scene);
  const loader = new ObjectLoader(sceneManager.scene, catalog);
  const selection = new SelectionManager(sceneManager.scene, loader, catalog.scene.selection);
  const metadataPanel = new MetadataPanel(document.querySelector("#metadata-panel"));
  const inspector = new ObjectInspector(metadataPanel, document.querySelector("#selection-type"));
  const tree = new TreeView(document.querySelector("#tree-view"), catalog);
  const layerFilter = new LayerFilter(document.querySelector("#layer-filter"), catalog);

  const refreshHierarchy = (result) => {
    const objects = loader.listObjects();
    tree.setObjects(objects);
    layerFilter.setObjects(objects);
    objectCount.textContent = `${objects.length} ${objects.length === 1 ? "objeto" : "objetos"}`;
    sceneManager.frameMeshes(result.meshes ?? []);
    if (objects.length) selection.selectObject(objects[0].id);
  };

  selection.onObjectSelected((selected) => {
    inspector.inspect(selected);
    tree.select(selected.sdtl_object);
  });
  tree.onObjectSelected((objectId) => selection.selectObject(objectId));
  document.querySelector("#reset-camera").addEventListener("click", () => sceneManager.resetCamera());
  fileInput.addEventListener("change", async () => {
    const [file] = fileInput.files;
    if (!file) return;
    await loadModel(() => loader.loadFile(file), file.name, refreshHierarchy);
  });

  sceneManager.start();
  await loadModel(
    () => loader.loadUrl(demoUrl.href),
    "ElectricalRoom demo",
    refreshHierarchy,
  );
}

async function loadModel(load, label, onLoaded) {
  loadingState.hidden = false;
  status.textContent = "Cargando";
  try {
    const result = await load();
    onLoaded(result);
    status.textContent = label;
  } catch (error) {
    console.error(error);
    status.textContent = "Error de carga";
  } finally {
    loadingState.hidden = true;
  }
}

bootstrap().catch((error) => {
  console.error(error);
  status.textContent = "Error de inicializacion";
  loadingState.hidden = true;
});
