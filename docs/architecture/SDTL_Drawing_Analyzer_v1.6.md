# SDTL Drawing Analyzer v1.6

## Objetivo

Resolver de forma trazable la geometria objetivo medida por una dimension grafica.
La version combina linea de cota, lineas auxiliares, orientacion, coincidencia de
extremos y distancia sin interpretar elementos civiles ni usar inteligencia
artificial.

## Arquitectura

```text
DimensionEntity --------+
                        |
DimensionAssociation ---+-- DimensionTargetResolutionEngine
                        |              |
GeometryEntity ---------+              +-- ExtensionLineDetector
                        |              |
SpatialRelation --------+              +-- DimensionGeometryLink
                                       |
                                       +-- DimensionGeometryLinkBuilder
                                       |       |
                                       |       +-- resumen de resolucion
                                       |
                                       +-- DrawingAnalysisBuilder metadata
```

## Reglas geometricas

- Las entidades deben pertenecer al mismo documento y pagina.
- Las lineas auxiliares son cortas, cercanas y perpendiculares a la linea de cota.
- Una dimension horizontal busca lineas horizontales o bordes horizontales.
- Una dimension vertical busca lineas verticales o bordes laterales.
- Los extremos de la linea de cota se comparan con los limites del candidato.
- La distancia se calcula entre bounding boxes en unidades PDF.

## Sistema de puntuacion

- Orientacion compatible: `0.45`.
- Coincidencia de ambos extremos: `0.35`.
- Coincidencia de un extremo: `0.175`.
- Proximidad: hasta `0.20`, decreciendo con la distancia.

Se selecciona el candidato con mayor score. En empate se favorece la menor
distancia y se usa el identificador geometrico para obtener un resultado estable.
El score y todos los candidatos evaluados se conservan en `metadata`.

## Criterios de confianza

- `0.95`: orientacion correcta y ambos extremos coinciden.
- `0.85`: orientacion correcta y proximidad.
- `0.70`: solo proximidad.
- `0.00`: no se encontro una geometria objetivo verificable.

## Limitaciones

- No reconoce elementos civiles.
- No interpreta simbolos.
- No genera objetos 3D.
- No usa inteligencia artificial.
- No convierte escalas ni unidades.
- Usa bounding boxes y orientacion dominante, no topologia CAD completa.

## Futuras mejoras

- Clasificacion civil basada en evidencia revisada.
- Reconocimiento de bloques CAD.
- Generacion supervisada de `SDTLObject`.
- Integracion BIM con parametros y unidades verificadas.
