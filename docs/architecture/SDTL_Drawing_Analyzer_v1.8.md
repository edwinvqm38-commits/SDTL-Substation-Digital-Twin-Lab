# SDTL Drawing Analyzer v1.8

## Objetivo

Crear la primera capa supervisada de generacion de objetos digitales SDTL. La
version transforma un `EngineeringCandidate` completo en un `ObjectProposal`
auditable y permite materializar una entidad civil persistente sin activarla.

No genera modelos 3D, BIM, IFC ni simulaciones electricas.

## Arquitectura

```text
Drawing Analyzer                 Object Generation              SDTL Core

EngineeringCandidate
        |
        v
 ObjectValidator --+--> ObjectMapper --> ObjectProposal
        |           |                         |
        +-- rechazo |                         v
                    |                  revision humana
                    |                         |
                    +-------------------------v
                                      CivilObject
```

- Drawing Analyzer descubre candidatos y conserva evidencia.
- Object Generation valida, mapea y construye propuestas.
- SDTL Core representa entidades persistentes y sus estados.
- El catalogo JSON desacopla los nombres del analizador de las clases SDTL.

## Flujo

1. `ObjectValidator` exige confianza minima `0.85`.
2. La geometria debe incluir origen, coordenadas y evidencia dimensional con
   unidad.
3. La evidencia semantica debe contener texto asociado.
4. La trazabilidad debe conservar PDF, pagina y origen geometrico.
5. `ObjectMapper` obtiene el tipo SDTL desde `civil_objects.json`.
6. `SDTLObjectFactory` crea una propuesta en `pending_review`.
7. La propuesta se materializa como objeto con estado `proposal`.
8. Un revisor humano aprueba el objeto antes de que pueda activarse.

## Modelos

### ObjectProposal

Contiene identificador, candidato fuente, tipo SDTL, propiedades, referencia
geometrica, trazabilidad, confianza, estado de revision y registro de revision
humana. Pydantic v2 garantiza validacion y serializacion JSON.

Los nombres canonicos son `candidate_source` y `review_status`. Al validar JSON
tambien se aceptan `source_candidate` y `status` para compatibilidad con ejemplos
tempranos de v1.8.

### Entidades civiles

La primera familia incluye:

- `ElectricalRoom`
- `CableTrench`
- `Foundation`
- `Fence`
- `Road`

Cada entidad conserva geometria fuente, coordenadas, dimensiones, propiedades,
PDF y pagina. No contiene geometria 3D ni interpretacion BIM.

## Estados

```text
candidate -> proposal -> approved -> active -> modified -> retired
```

`EngineeringCandidate` representa el estado `candidate`. Los objetos generados
comienzan en `proposal`. `approve(reviewer)` registra una decision humana y
produce `approved`; solo entonces `activate()` permite llegar a `active`.

Un objeto activo puede pasar a `modified` o `retired`. Un objeto modificado puede
volver a `active` o retirarse. Las transiciones fuera de este flujo se rechazan.

## Decisiones

- La validacion devuelve comprobaciones independientes para geometria, semantica
  y trazabilidad.
- La confianza no sustituye las comprobaciones de evidencia.
- Las unidades se leen de la evidencia dimensional existente en v1.7.
- No se modifica `EngineeringCandidate` ni los modelos historicos de SDTL Core.
- La fabrica depende de interfaces pequenas: validador y mapper sustituibles.
- La activacion nunca ocurre durante la generacion.

## Limitaciones

- La revision humana se modela, pero aun no existe flujo de usuario ni firma.
- Las dimensiones conservan sus referencias y unidades; v1.7 no incorpora el
  valor numerico directamente en la evidencia del candidato.
- El catalogo inicial solo contiene cinco tipos civiles.
- No hay persistencia en base de datos ni control de concurrencia.
- No se generan objetos electricos, BIM, IFC, GIS ni SCADA.

## Siguiente fase

SDTL v1.9 puede introducir una `3D/BIM Generation Layer` para objetos aprobados,
manteniendo la geometria derivada separada de la evidencia PDF original.
