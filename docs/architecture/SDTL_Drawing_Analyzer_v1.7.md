# SDTL Drawing Analyzer v1.7

## Objetivo

Crear la primera capa semantica deterministica de SDTL. La version transforma
geometrias validadas en candidatos de elementos de ingenieria respaldados por
evidencia, sin crear objetos SDTL definitivos ni modelos BIM.

## Arquitectura

```text
Capa geometrica
GeometryEntity + ExtractedText + DimensionEntity + DimensionTopology
       |
       +-- GeometryFeatureExtractor
       +-- TextGeometryRelationEngine
                    |
                    v
Capa semantica
Engineering Catalog + SemanticResolutionEngine
                    |
                    +-- CandidateConfidenceCalculator
                    |
                    v
CandidateBuilder --> EngineeringCandidate
                    |
                    v
Capa SDTL futura: validacion humana, SDTLObject, BIM y simulacion
```

La capa geometrica no conoce tipos de ingenieria. La capa semantica consume
caracteristicas y evidencia, pero solo genera candidatos. SDTL Core no depende de
ninguna regla de catalogo.

## Flujo

1. `GeometryFeatureExtractor` calcula area, perimetro, dimensiones, aspecto,
   orientacion, cierre y proximidad.
2. `TextGeometryRelationEngine` evalua distancia, centroide, contencion y
   alineacion entre texto y geometria.
3. `SemanticResolutionEngine` compara la evidencia con catalogos JSON.
4. `CandidateConfidenceCalculator` calcula contribuciones independientes.
5. `CandidateBuilder` construye `EngineeringCandidate` con evidencia y
   trazabilidad PDF.
6. `DrawingAnalysisBuilder` registra version `1.7` y cantidad de candidatos.

## Modelos

### GeometryFeature

Conserva la geometria fuente y propiedades calculadas. No altera el
`GeometryEntity` original.

### TextGeometryRelation

Registra texto, geometria, distancia, contencion, alineacion y confianza.

### CandidateConfidence

Desglosa `geometry_score`, `text_score`, `dimension_score`, `topology_score` y
`final`.

### EngineeringCandidate

Contiene tipo posible, estado `candidate`, confianza, geometria fuente,
evidencias, scores y trazabilidad. No es un `SDTLObject`.

## Catalogo inicial

`civil_elements.json` contiene reglas iniciales para:

- `ELECTRICAL_ROOM`: rectangulo cerrado y patrones de sala/control/electrica.
- `CABLE_TRENCH`: rectangulo largo, aspecto minimo 5 y ancho 0.3 a 2 m.
- `FOUNDATION`: rectangulo cerrado con dimension obligatoria.
- `FENCE`: linea o polilinea abierta larga.
- `ROAD`: poligono cerrado de area grande.

`electrical_elements.json` y `structural_elements.json` se crean vacios para
extensiones futuras controladas. Los catalogos son datos editables, no codigo.

## Reglas y confianza

La confianza maxima es `0.95`:

- Coincidencia geometrica: hasta `0.35`.
- Coincidencia textual: hasta `0.30`.
- Evidencia dimensional: hasta `0.20`.
- Topologia validada: hasta `0.10`.

Una geometria incompatible se rechaza. Una geometria compatible sin texto puede
generar un candidato de confianza baja para revision. Las reglas con
`dimension_required` no producen candidato sin evidencia dimensional.

Los textos se normalizan en mayusculas y sin acentos para comparar patrones, pero
la evidencia conserva el texto PDF original.

## Decisiones tecnicas

- Pydantic v2 garantiza contratos y serializacion JSON.
- Los catalogos se cargan mediante el parser JSON estandar.
- La trazabilidad se copia al candidato sin perder PDF, pagina o coordenadas.
- Las evidencias permanecen separadas para permitir auditoria y recalculo.
- No se aplican modelos probabilisticos ni inteligencia artificial.

## Limitaciones

- No reemplaza la revision de ingenieria.
- No genera BIM, IFC, modelos 3D ni simulaciones.
- No crea objetos SDTL definitivos.
- Las reglas iniciales son ampliables y requieren validacion con planos reales.
- La confianza representa coincidencia de evidencia, no certeza de ingenieria.
- Las reglas metricas requieren coordenadas y unidades previamente calibradas.
- Los catalogos electrico y estructural aun no contienen reglas.

## Siguiente fase

SDTL Drawing Analyzer v1.8 puede introducir una capa de generacion supervisada de
objetos. Solo candidatos aceptados y con trazabilidad completa deberian convertirse
en propuestas de `SDTLObject`; la confirmacion humana debe permanecer explicita.
