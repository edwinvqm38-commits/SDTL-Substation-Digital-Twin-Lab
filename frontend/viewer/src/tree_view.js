export class TreeView {
  constructor(container, visualCatalog = {}) {
    this.container = container;
    this.visualCatalog = visualCatalog;
    this.listeners = new Set();
    this.buttons = new Map();
  }

  onObjectSelected(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  setObjects(objects) {
    this.buttons.clear();
    const root = document.createElement("div");
    root.className = "tree-root";
    const rootLabel = document.createElement("div");
    rootLabel.className = "tree-root-label";
    rootLabel.textContent = "SUBESTACION";
    root.append(rootLabel);

    const groups = new Map();
    for (const object of objects) {
      const visual = this.visualCatalog.objectTypes?.[object.type] ?? {};
      const category = visual.category ?? "Sin clasificar";
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push({ ...object, label: visual.label ?? object.type });
    }

    for (const [category, entries] of groups) {
      const group = document.createElement("section");
      group.className = "tree-group";
      const heading = document.createElement("h3");
      heading.textContent = category;
      group.append(heading);
      for (const entry of entries) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tree-item";
        button.dataset.objectId = entry.id;
        button.innerHTML = `<span>${this.#escape(entry.label)}</span><small>${this.#escape(entry.id)}</small>`;
        button.addEventListener("click", () => {
          this.select(entry.id);
          for (const listener of this.listeners) listener(entry.id);
        });
        this.buttons.set(entry.id, button);
        group.append(button);
      }
      root.append(group);
    }
    this.container.replaceChildren(root);
  }

  select(objectId) {
    for (const [id, button] of this.buttons) {
      button.classList.toggle("is-selected", id === objectId);
    }
  }

  #escape(value) {
    const element = document.createElement("span");
    element.textContent = String(value);
    return element.innerHTML;
  }
}
