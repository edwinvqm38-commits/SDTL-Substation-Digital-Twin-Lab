import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera.js";
import { Engine } from "@babylonjs/core/Engines/engine.js";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight.js";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight.js";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color.js";
import { Vector3 } from "@babylonjs/core/Maths/math.vector.js";
import { CreateLines, CreateLineSystem } from "@babylonjs/core/Meshes/Builders/linesBuilder.js";
import { Scene } from "@babylonjs/core/scene.js";

export class SceneManager {
  constructor(canvas, palette, options = {}) {
    this.canvas = canvas;
    this.palette = palette;
    const engineFactory = options.engineFactory ?? ((target) => new Engine(target, true, {
      preserveDrawingBuffer: true,
      stencil: true,
      adaptToDeviceRatio: true,
    }));
    this.engine = engineFactory(canvas);
    this.scene = this.#createScene();
    this.camera = this.#createCamera();
    this.#createLights();
    this.#createGrid();
    this.#createAxes();
    this.resizeHandler = () => this.engine.resize();
    globalThis.addEventListener?.("resize", this.resizeHandler);
  }

  start() {
    this.engine.runRenderLoop(() => this.scene.render());
  }

  resetCamera() {
    this.camera.setTarget(Vector3.Zero());
    this.camera.alpha = -Math.PI / 3;
    this.camera.beta = Math.PI / 3;
    this.camera.radius = 24;
  }

  frameMeshes(meshes) {
    const visibleMeshes = meshes.filter((mesh) => mesh.getTotalVertices?.() > 0);
    if (!visibleMeshes.length) return;
    const bounds = visibleMeshes.map((mesh) => mesh.getHierarchyBoundingVectors?.(true)).filter(Boolean);
    if (!bounds.length) return;
    const minimum = bounds.reduce((value, item) => Vector3.Minimize(value, item.min), bounds[0].min);
    const maximum = bounds.reduce((value, item) => Vector3.Maximize(value, item.max), bounds[0].max);
    const center = minimum.add(maximum).scale(0.5);
    const extent = maximum.subtract(minimum).length();
    this.camera.setTarget(center);
    this.camera.radius = Math.max(extent * 1.6, 8);
  }

  dispose() {
    globalThis.removeEventListener?.("resize", this.resizeHandler);
    this.scene.dispose();
    this.engine.dispose();
  }

  #createScene() {
    const scene = new Scene(this.engine);
    scene.clearColor = Color4.FromHexString(this.palette.background);
    return scene;
  }

  #createCamera() {
    const camera = new ArcRotateCamera(
      "SDTL_OrbitCamera",
      -Math.PI / 3,
      Math.PI / 3,
      24,
      Vector3.Zero(),
      this.scene,
    );
    camera.lowerRadiusLimit = 1;
    camera.upperRadiusLimit = 500;
    camera.wheelPrecision = 30;
    camera.panningSensibility = 80;
    if (this.canvas) camera.attachControl(this.canvas, true);
    return camera;
  }

  #createLights() {
    const ambient = new HemisphericLight("Ambient", new Vector3(0, 1, 0), this.scene);
    ambient.intensity = 0.75;
    const directional = new DirectionalLight("Directional", new Vector3(-1, -2, -1), this.scene);
    directional.intensity = 0.65;
  }

  #createGrid() {
    const size = 40;
    const step = 1;
    const lines = [];
    const colors = [];
    const minor = Color4.FromHexString(this.palette.gridMinor);
    const major = Color4.FromHexString(this.palette.gridMajor);
    for (let offset = -size; offset <= size; offset += step) {
      lines.push([new Vector3(-size, 0, offset), new Vector3(size, 0, offset)]);
      lines.push([new Vector3(offset, 0, -size), new Vector3(offset, 0, size)]);
      const color = offset % 5 === 0 ? major : minor;
      colors.push([color, color], [color, color]);
    }
    const grid = CreateLineSystem("EngineeringGrid", { lines, colors }, this.scene);
    grid.isPickable = false;
  }

  #createAxes() {
    const length = 4;
    const axes = [
      ["Axis_X", new Vector3(length, 0, 0), this.palette.axisX],
      ["Axis_Y", new Vector3(0, length, 0), this.palette.axisY],
      ["Axis_Z", new Vector3(0, 0, length), this.palette.axisZ],
    ];
    for (const [name, endpoint, color] of axes) {
      const axis = CreateLines(name, {
        points: [Vector3.Zero(), endpoint],
      }, this.scene);
      axis.color = Color3.FromHexString(color);
      axis.isPickable = false;
    }
  }
}
