# SDTL Drawing Analyzer v1.1

## Objetivo

Extender la extraccion de texto nativo de planos PDF para conservar la pagina,
la posicion y la informacion tipografica de cada fragmento. Esta informacion
prepara la asociacion futura entre texto y geometria sin interpretar todavia el
contenido del plano.

## Arquitectura

```text
PDF
 |
 +-- PDFTextExtractor.extract_text() ----------------> texto por pagina (v1.0)
 |
 +-- PDFTextExtractor.extract_text_with_coordinates()
          |
          +-- CoordinateTextExtractor
                  |
                  +-- ExtractedText (Pydantic)
                          |
                          +-- DrawingAnalysisBuilder metadata
```

`ExtractedText` pertenece al analizador documental y no modifica los modelos de
SDTL Core. `CoordinateTextExtractor` concentra el acceso a las coordenadas PDF,
mientras `PDFTextExtractor` conserva la interfaz anterior y expone el nuevo flujo.

## Metodo usado

La extraccion utiliza `fitz.Page.get_text("dict")`. El resultado se recorre por
bloques, lineas y `spans`. Cada `span` con texto produce un `ExtractedText` con:

- Numero de pagina basado en uno.
- Coordenadas `x` e `y` del extremo superior izquierdo.
- Ancho y alto calculados desde el bounding box.
- Tamano y nombre de fuente cuando PyMuPDF los proporciona.
- Confianza `1.0` para texto nativo recuperado directamente del PDF.

## Limitaciones

- No ejecuta OCR; un PDF escaneado sin capa de texto devuelve una lista vacia.
- No interpreta geometricamente las coordenadas ni las relaciona con objetos.
- No reconoce simbolos electricos o civiles.
- Un `span` puede ser solo una parte visual de una frase o etiqueta.
- Las coordenadas usan el sistema de pagina de PyMuPDF.

## Futuras mejoras

- Asociacion texto-geometria mediante proximidad y regiones de pagina.
- Extraccion de cotas a partir de texto, unidades y lineas auxiliares.
- Reconocimiento y normalizacion de etiquetas de equipos.
