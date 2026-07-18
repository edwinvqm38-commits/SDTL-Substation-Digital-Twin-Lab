export class ObjectInspector {
  constructor(metadataPanel, typeLabel) {
    this.metadataPanel = metadataPanel;
    this.typeLabel = typeLabel;
  }

  inspect(selection) {
    if (!selection) {
      this.clear();
      return;
    }
    this.typeLabel.textContent = selection.metadata.display_name ?? selection.metadata.object_type;
    this.metadataPanel.render({
      ...selection.metadata,
      component_name: selection.component,
    });
  }

  clear() {
    this.typeLabel.textContent = "Sin seleccion";
    this.metadataPanel.clear();
  }
}
