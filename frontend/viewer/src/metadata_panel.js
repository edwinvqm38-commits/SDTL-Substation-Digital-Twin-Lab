const EMPTY_VALUE = "No disponible";

export class MetadataPanel {
  constructor(container) {
    this.container = container;
    this.clear();
  }

  render(metadata) {
    this.container.replaceChildren(
      this.#section("Identificacion", [
        ["ID", metadata.sdtl_id],
        ["Tipo", metadata.display_name ?? metadata.object_type],
        ["Estado", this.#capitalize(metadata.state)],
        ["Componente", metadata.component_name],
        ["Confianza", this.#confidence(metadata.confidence)],
      ]),
      this.#section("Ingenieria", [
        ["Dimensiones", this.#dimensions(metadata.dimensions, metadata.unit)],
        ["Material", metadata.material],
      ]),
      this.#section("Trazabilidad", [
        ["PDF", metadata.source_pdf],
        ["Pagina", metadata.page],
        ["Geometria origen", metadata.source_geometry],
      ]),
    );
  }

  clear() {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "Sin objeto seleccionado";
    this.container.replaceChildren(empty);
  }

  #section(title, rows) {
    const section = document.createElement("section");
    section.className = "metadata-section";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const list = document.createElement("dl");
    for (const [label, value] of rows) {
      const term = document.createElement("dt");
      term.textContent = label;
      const detail = document.createElement("dd");
      detail.textContent = value ?? EMPTY_VALUE;
      list.append(term, detail);
    }
    section.append(heading, list);
    return section;
  }

  #dimensions(dimensions = {}, unit = "m") {
    const values = Object.entries(dimensions ?? {});
    if (!values.length) return EMPTY_VALUE;
    return values.map(([name, value]) => `${name}: ${value} ${unit ?? ""}`.trim()).join(" · ");
  }

  #confidence(value) {
    return typeof value === "number" ? `${Math.round(value * 100)} %` : EMPTY_VALUE;
  }

  #capitalize(value) {
    if (!value) return EMPTY_VALUE;
    return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
  }
}
