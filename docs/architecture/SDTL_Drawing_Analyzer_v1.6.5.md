# SDTL Drawing Analyzer v1.6.5

## Objetivo

Agregar una capa intermedia de validacion geometrica avanzada antes de iniciar la
interpretacion semantica. La version valida topologia de cotas, flechas, escala,
unidades, coordenadas y trazabilidad sin clasificar elementos de ingenieria.

## Arquitectura

```text
GeometryEntity + DimensionGeometryLink
                 |
                 +-- ExtensionLineDetector
                 +-- ArrowDetector
                 +-- DimensionTopologyAnalyzer --> DimensionTopology

ExtractedText --> ScaleDetector -----------> DrawingScale
DimensionEntity --> UnitNormalizer --------> NormalizedMeasurement
DrawingScale --> DrawingCoordinateSystemBuilder --> DrawingCoordinateSystem
PDF provenance ----------------------------> TraceabilityMap
```

Los nuevos componentes pertenecen a `drawing_analyzer`. SDTL Core permanece
independiente de reglas PDF, tolerancias geometricas y transformaciones de plano.

## Nuevos modulos

- `dimension_topology_analyzer.py`: valida la estructura completa de una cota.
- `arrow_detector.py`: detecta triangulos pequenos y lineas convergentes.
- `scale_detector.py`: conserva `ScaleInformation` y agrega `DrawingScale`.
- `unit_normalizer.py`: convierte de forma explicita entre `mm`, `cm` y `m`.
- `drawing_coordinate_system.py`: crea una matriz afin PDF a mundo.
- `traceability_map.py`: conserva el origen PDF de datos derivados.

## Modelos creados

- `DimensionTopology`.
- `ArrowDetection`.
- `DrawingScale`.
- `NormalizedMeasurement`.
- `DrawingCoordinateSystem`.
- `TraceabilityMap`.

Todos son modelos Pydantic v2, serializables a JSON y configurados con
`extra="forbid"`.

## Flujo de datos

1. El PDF produce texto y geometria vectorial con identificadores de pagina.
2. Las dimensiones y enlaces resueltos alimentan el analizador de topologia.
3. Las lineas auxiliares y flechas agregan evidencia geometrica verificable.
4. La escala detectada alimenta el sistema de coordenadas del plano.
5. Las medidas se normalizan sin modificar sus valores originales.
6. `TraceabilityMap` conserva PDF, pagina, IDs y coordenadas de origen.
7. `DrawingAnalysisBuilder` publica indicadores de completitud v1.6.5.

## Decisiones tecnicas

- Una topologia puede ser valida sin flechas, pero recibe menor confianza.
- Las flechas triangulares requieren tres vertices, tamano pequeno y proximidad.
- Las lineas convergentes se tratan como candidatos, no como simbolos semanticos.
- La escala no asigna unidades si estas no son proporcionadas por el llamador.
- La matriz invierte el eje Y de PDF para obtener un eje de mundo ascendente.
- La razon de escala opera sobre unidades de dibujo; no convierte puntos PDF
  fisicos a metros sin una calibracion adicional.

## Limitaciones

- No clasifica elementos civiles.
- No interpreta simbolos de ingenieria.
- No genera BIM, modelos 3D ni `SDTLObject`.
- No usa inteligencia artificial.
- No calibra automaticamente puntos PDF contra unidades fisicas de papel.
- No resuelve rotaciones locales o sistemas GIS reales.

## Compatibilidad futura

Los IDs y mapas de trazabilidad preparan integraciones BIM, GIS, SCADA e IEC
61850 sin acoplar esas capas al analizador PDF. La siguiente fase puede consumir
evidencia validada sin alterar los extractores de bajo nivel.
