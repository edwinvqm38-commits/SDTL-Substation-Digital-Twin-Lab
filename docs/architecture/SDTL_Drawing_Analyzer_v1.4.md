# SDTL Drawing Analyzer v1.4

## Objetivo

Extraer mediciones trazables desde texto nativo de planos PDF mediante reglas y
expresiones regulares. La version detecta valores dimensionales y escalas sin
interpretar el elemento de ingenieria al que pertenecen.

## Arquitectura

```text
ExtractedText
 |
 +-- DimensionDetector ------> DimensionEntity
 |
 +-- ScaleDetector ----------> ScaleInformation
             |
             +-- MeasurementBuilder
                     |
                     +-- resumen de mediciones
                     +-- DrawingAnalysisBuilder metadata
```

Cada resultado conserva documento, pagina e identificador del texto fuente. Los
metadatos registran la regla aplicada, el texto coincidente y el contenido de
origen para permitir auditoria.

## Patrones soportados

- Medidas lineales con unidad explicita: `12.50 m`, `8 m`, `2500 mm`.
- Diametros con simbolo: `Ø600`, con unidad solo cuando aparece en el texto.
- Niveles con prefijo: `NPT +0.50`.
- Niveles numericos con signo: `+3.20`, `-0.15`.
- Angulos con simbolo de grados: `45°`.
- Valores numericos aislados como tipo `unknown` y confianza reducida.
- Escalas etiquetadas: `ESCALA 1:100`, `E=1/50`, `S=1:200`.
- Escalas aisladas como `1:100` con confianza reducida.

## Limitaciones

- No conoce el significado del elemento medido.
- No convierte unidades.
- No genera geometria 3D.
- No relaciona automaticamente una medida con lineas o cotas.
- No interpreta la escala para obtener dimensiones reales.
- Los patrones dependen de que exista texto nativo en el PDF.

## Futuras mejoras

- Asociacion cota-geometria mediante proximidad y lineas auxiliares.
- Conversion de coordenadas PDF usando la escala detectada.
- Generacion controlada de parametros BIM.
- Creacion supervisada de candidatos a `SDTLObject`.
