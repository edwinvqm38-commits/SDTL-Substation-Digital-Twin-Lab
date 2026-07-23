export class LayerFilter {
  constructor(container, visualCatalog = {}) {
    this.container = container;
    this.visualCatalog = visualCatalog;
    this.checkboxes = new Map();
    this.objectsByType = new Map();
    this.hiddenTypes = new Set();
  }

  setObjects(objects) {
    this.objectsByType.clear();
    for (const object of objects) {
      if (!this.objectsByType.has(object.type)) this.objectsByType.set(object.type, []);
      this.objectsByType.get(object.type).push(object);
    }
    this.hiddenTypes.clear();
    this.#render();
    this.#applyVisibility();
  }

  isVisible(type) {
    return !this.hiddenTypes.has(type);
  }

  setVisible(type, visible) {
    if (visible) this.hiddenTypes.delete(type);
    else this.hiddenTypes.add(type);
    const checkbox = this.checkboxes.get(type);
    if (checkbox) checkbox.checked = visible;
    this.#applyMeshVisibility(type, visible);
  }

  showAll() {
    for (const type of this.objectsByType.keys()) this.setVisible(type, true);
  }

  hideAll() {
    for (const type of this.objectsByType.keys()) this.setVisible(type, false);
  }

  #render() {
    this.checkboxes.clear();

    if (!this.objectsByType.size) {
      this.container.replaceChildren();
      return;
    }

    const root = document.createElement("div");
    root.className = "layer-filter";

    const actions = document.createElement("div");
    actions.className = "layer-filter-actions";
    const showAllButton = document.createElement("button");
    showAllButton.type = "button";
    showAllButton.textContent = "Todas";
    showAllButton.addEventListener("click", () => this.showAll());
    const hideAllButton = document.createElement("button");
    hideAllButton.type = "button";
    hideAllButton.textContent = "Ninguna";
    hideAllButton.addEventListener("click", () => this.hideAll());
    actions.append(showAllButton, hideAllButton);
    root.append(actions);

    for (const [category, entries] of this.#groupedByCategory()) {
      const section = document.createElement("section");
      section.className = "layer-filter-group";
      const heading = document.createElement("h3");
      heading.textContent = category;
      section.append(heading);

      for (const { type, label } of entries) {
        section.append(this.#buildRow(type, label));
      }
      root.append(section);
    }

    this.container.replaceChildren(root);
  }

  #buildRow(type, label) {
    const row = document.createElement("label");
    row.className = "layer-filter-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = this.isVisible(type);
    checkbox.addEventListener("change", () => this.setVisible(type, checkbox.checked));
    this.checkboxes.set(type, checkbox);

    const text = document.createElement("span");
    text.textContent = label;

    const count = document.createElement("small");
    count.textContent = String(this.objectsByType.get(type).length);

    row.append(checkbox, text, count);
    return row;
  }

  #groupedByCategory() {
    const groups = new Map();
    for (const type of this.objectsByType.keys()) {
      const visual = this.visualCatalog.objectTypes?.[type] ?? {};
      const category = visual.category ?? "Sin clasificar";
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push({ type, label: visual.label ?? type });
    }
    return groups;
  }

  #applyVisibility() {
    for (const type of this.objectsByType.keys()) {
      this.#applyMeshVisibility(type, this.isVisible(type));
    }
  }

  #applyMeshVisibility(type, visible) {
    const objects = this.objectsByType.get(type) ?? [];
    for (const object of objects) {
      for (const mesh of object.meshes ?? []) {
        mesh.setEnabled?.(visible);
      }
    }
  }
}
