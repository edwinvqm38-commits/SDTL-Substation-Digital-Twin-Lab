# SDTL Drawing Analyzer v1.0

## Objetivo

Proveer la infraestructura inicial para leer planos PDF de ingenieria, conservar
la trazabilidad del texto por pagina y convertir resultados basicos a los modelos
`DocumentAnalysis` y `ExtractionResult` de SDTL Core.

## Alcance

- Lectura de archivos PDF con PyMuPDF.
- Conteo de paginas y consulta de sus dimensiones.
- Identificacion de disponibilidad de texto e imagenes.
- Extraccion de texto con numero de pagina basado en uno.
- Extraccion conservadora de titulo, codigo, revision, fecha y disciplina.
- Construccion de resultados validados con Pydantic.

## Limitaciones

- No ejecuta OCR sobre documentos escaneados.
- No interpreta lineas, simbolos, cotas, escalas ni geometria.
- No clasifica elementos electricos o civiles.
- Los metadatos se obtienen mediante etiquetas y patrones simples.
- Un valor no respaldado por el texto se devuelve como `None`.
- Los PDF protegidos con contrasena no se procesan.

## Arquitectura

```text
PDF
 |
 +-- PDFDocumentReader ------> informacion estructural y metadatos PDF
 |
 +-- PDFTextExtractor -------> texto por pagina
              |
              +-- DrawingMetadataExtractor
                              |
                              +-- DrawingAnalysisBuilder
                                      |
                                      +-- DocumentAnalysis
                                      +-- ExtractionResult
```

`document_reader.py` inspecciona el contenedor PDF sin extraer geometria.
`text_extractor.py` mantiene la referencia de pagina de cada texto.
`metadata_extractor.py` aplica reglas conservadoras sobre el texto disponible.
`analysis_builder.py` es el limite entre el analizador y los modelos SDTL Core.

## Dependencias

- Python 3.12.
- PyMuPDF (`fitz`) para lectura y extraccion de texto PDF.
- Pydantic v2 mediante los modelos existentes de SDTL Core.

## Futuras mejoras

- OCR para planos escaneados.
- Preprocesamiento de imagenes con OpenCV.
- Deteccion de lineas y contornos.
- Reconocimiento de simbolos electricos y civiles.
- Extraccion y normalizacion de cotas.
- Identificacion de escalas graficas y textuales.
- Resolucion de referencias cruzadas entre planos.
