# SDTL Drawing Analyzer v1.2

## Objetivo

Extraer geometria vectorial nativa desde planos PDF y conservar su documento,
pagina, coordenadas, dimensiones y propiedades graficas. Esta version no aplica
interpretacion semantica ni genera objetos SDTL.

## Arquitectura

```text
PDF
 |
 +-- fitz.Page.get_drawings()
          |
          +-- VectorGeometryExtractor
                  |
                  +-- GeometryEntity (Pydantic)
                          |
                          +-- GeometryAnalysisBuilder
                                  |
                                  +-- resumen por tipo
                                  +-- DrawingAnalysisBuilder metadata
```

`GeometryEntity` pertenece al analizador y mantiene SDTL Core desacoplado de los
detalles de PyMuPDF. Las propiedades de cada path se convierten a estructuras
JSON antes de construir el modelo.

## Metodo usado

La extraccion utiliza `fitz.Page.get_drawings()`. Cada path se recorre por sus
operaciones vectoriales y se registra con numero de pagina basado en uno.

## Entidades soportadas

- Lineas (`l`), con puntos inicial y final y longitud.
- Rectangulos (`re`), con posicion, ancho y alto.
- Paths cerrados de lineas y cuadrilateros (`qu`) como poligonos.
- Curvas Bezier cubicas (`c`), con extremos y puntos de control.
- Operaciones no reconocidas como `unknown`, sin descartarlas.

Se conservan, cuando existen, ancho de linea, color de trazo, color de relleno,
opacidad, estilo de linea, cierre del path, capa y secuencia PDF.

## Limitaciones

- No reconoce equipos.
- No reconoce simbolos.
- No interpreta escalas.
- No genera objetos SDTL.
- No determina unidades reales a partir de coordenadas PDF.
- Un path puede dividirse en varias entidades segun sus operaciones.

## Futuras mejoras

- Asociacion texto-geometria por proximidad espacial.
- Deteccion de cotas y lineas auxiliares.
- Clasificacion de elementos mediante reglas verificables.
- Generacion controlada de candidatos a objetos civiles.
