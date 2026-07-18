# SDTL Drawing Analyzer v1.3

## Objetivo

Crear relaciones espaciales verificables entre texto localizado y geometria
vectorial extraida de una misma pagina PDF. El motor describe posicion relativa
sin interpretar ingenieria, clasificar equipos ni reconocer simbolos.

## Arquitectura

```text
ExtractedText --------+
                      |
                      +-- SpatialAssociationEngine
                      |          |
GeometryEntity -------+          +-- SpatialRelation
                                 |
                                 +-- AssociationBuilder
                                 |       |
                                 |       +-- resumen de asociaciones
                                 |
                                 +-- DrawingAnalysisBuilder metadata
```

Las comparaciones se realizan unicamente cuando texto y geometria pertenecen al
mismo documento y pagina. Cada relacion conserva los bounding boxes, el umbral
de distancia y los identificadores de origen.

## Reglas espaciales

Las reglas se aplican con precedencia `inside`, `intersects`, `near`, generando
como maximo una relacion por par texto-geometria.

### inside

Si el centro del bounding box del texto esta dentro del bounding box geometrico,
se genera `inside` con confianza `0.95`.

### near

Si no existe una relacion mas fuerte y la distancia euclidiana entre centros es
menor que `distance_threshold`, se genera `near` con confianza `0.80`. El umbral
predeterminado es 100 unidades PDF y puede configurarse.

### intersects

Si los bounding boxes se cruzan pero el centro del texto no esta dentro de la
geometria, se genera `intersects` con confianza `0.85`.

`overlap_ratio` representa el area intersectada dividida por el area del bounding
box del texto. La distancia siempre se calcula entre centros.

## Limitaciones

- No interpreta ingenieria.
- No clasifica equipos.
- No reconoce simbolos.
- Solo utiliza bounding boxes rectangulares.
- No considera rotacion, topologia ni forma exacta del path.
- El tipo `overlaps` queda reservado para reglas futuras.

## Futuras mejoras

- Asociacion especializada entre texto y cotas.
- Clasificacion de elementos con reglas auditables.
- Modelos de machine learning sobre asociaciones validadas.
- Generacion controlada de candidatos a `SDTLObject`.
