# SDTL Drawing Analyzer v1.5

## Objetivo

Asociar dimensiones detectadas con geometria vectorial cercana mediante reglas
trazables de proximidad y orientacion. La asociacion no interpreta el elemento
medido, no clasifica objetos y no utiliza inteligencia artificial.

## Arquitectura

```text
DimensionEntity -----+
                     |
GeometryEntity ------+-- DimensionGeometryAssociationEngine
                     |              |
SpatialRelation -----+              +-- DimensionAssociation
                                    |
                                    +-- DimensionAssociationBuilder
                                    |       |
                                    |       +-- resumen de asociaciones
                                    |
                                    +-- DrawingAnalysisBuilder metadata
```

`text_source_id` conecta la dimension con `SpatialRelation`. Si la relacion no
incluye distancia, el motor calcula la distancia entre el bounding box del texto
y el centro geometrico. Solo se comparan entidades del mismo documento y pagina.

## Reglas utilizadas

### Proximidad

Una geometria es candidata si su distancia respecto a la dimension es menor o
igual que `distance_threshold`. El valor predeterminado es 100 unidades PDF.

### Orientacion

Para una dimension `linear`, una linea predominantemente horizontal genera
`defines_length`; una linea predominantemente vertical genera `defines_height`.
Proximidad y orientacion compatible producen confianza `0.90`.

### Proximidad sin orientacion

Una geometria cercana que no sea una linea orientable genera `unknown` con
confianza `0.70`. Los tipos `defines_spacing` y `defines_radius` quedan reservados
para reglas futuras.

### Unidades

La unidad original (`m`, `mm`, `cm` u otra) se conserva en los metadatos de la
asociacion. No se convierte ni se infiere ninguna unidad.

## Limitaciones

- No interpreta elementos.
- No genera objetos civiles.
- No convierte escala ni unidades.
- No usa inteligencia artificial.
- No identifica el objeto objetivo de una linea de cota.
- La orientacion usa el eje dominante de una linea PDF.

## Futuras mejoras

- Clasificacion civil basada en evidencia validada.
- Deteccion de simbolos.
- Conversion a unidades reales usando escalas verificadas.
- Generacion supervisada de candidatos a `SDTLObject`.
