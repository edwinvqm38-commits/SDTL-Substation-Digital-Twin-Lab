# SDTL v1.9 - Parametric 3D Generation Layer

## Objetivo

Transformar exclusivamente objetos SDTL aprobados y con dimensiones confiables
en modelos 3D parametricos serializables. La salida conserva la trazabilidad al
objeto de ingenieria y queda preparada para una exportacion glTF completa futura.

Esta version no implementa BIM, IFC, renderizado ni interpretacion de planos.

## Arquitectura

```text
Modelo de ingenieria             Modelo geometrico             Modelo visual

Approved SDTLObject
  dimensions                          Mesh                       Material3D
  properties          Generator       vertices                  color
  source PDF     ----------------->   faces        ---------->   opacity
  page                                  normals
                         |
                         v
                 Object3D + components
                         |
                         v
              GLTF intermediate manifest
```

Las tres responsabilidades permanecen separadas:

- Ingenieria define dimensiones, propiedades, estado y trazabilidad.
- Geometria define vertices, caras, normales y transformaciones.
- Visualizacion define materiales neutros para futuros renderizadores.

## Flujo

1. El generador valida el tipo del objeto SDTL.
2. Solo acepta estados aprobados o posteriores que conserven aprobacion humana.
3. Resuelve dimensiones nombradas desde entidades v1.8 o `Geometry` de Core.
4. Rechaza dimensiones ausentes, no numericas, infinitas o no positivas.
5. Genera componentes con significado de ingenieria.
6. Construye `Object3D` con transformacion y trazabilidad de origen.
7. `GLTFExporter` prepara un manifiesto glTF 2.0 intermedio.

## Modelos

### Mesh

Contiene `vertices`, `faces`, `normals` y `metadata`. Valida que cada vertice y
normal tenga tres componentes y que las caras solo referencien vertices validos.
No contiene propiedades de materiales ni reglas del activo.

### Transform

Representa posicion, rotacion Euler XYZ en grados y escala. Las escalas deben ser
positivas. `apply()` permite comprobar la transformacion de puntos. El exportador
convierte la rotacion Euler a cuaternion glTF.

### Material3D

Representa propiedades visuales independientes de la malla. La densidad es
opcional para evitar completar propiedades fisicas no verificadas.

### Object3D

Agrupa componentes nombrados, transformacion global, objeto SDTL fuente,
trazabilidad y metadata de generacion. Cada `Object3DComponent` conserva su propia
malla, material y transformacion local.

## Generadores

### RoomGenerator

Convierte `ElectricalRoom` en seis superficies independientes:

- `Floor`
- `Wall_1`
- `Wall_2`
- `Wall_3`
- `Wall_4`
- `Roof`

No agrega puertas o ventanas sin propiedades explicitas que las definan.

### FoundationGenerator

Convierte `Foundation` en una zapata cerrada con ocho vertices y doce caras
triangulares.

### CableTrenchGenerator

Convierte `CableTrench` en una canaleta abierta compuesta por base y dos muros
laterales. Acepta `depth` o `height` como profundidad documentada.

## Materiales

El catalogo incluye `concrete.json`, `steel.json` y `soil.json`. Concreto conserva
la densidad de referencia indicada por la especificacion. Acero y suelo no
declaran densidad porque depende de grado, composicion y condiciones del proyecto.
Los tres definen un color visual y opacidad.

## Exportador glTF

`GLTFExporter` genera una estructura con `asset`, escena, nodos, mallas,
materiales, transformaciones y trazabilidad. Los vertices, caras y normales se
mantienen temporalmente en `primitive.extras`.

Por tanto, el resultado es un manifiesto intermedio orientado a glTF, no un
archivo `.gltf` o `.glb` renderizable. La siguiente fase debe generar buffers,
buffer views y accessors estandar.

## Decisiones

- Sistema cartesiano diestro con eje Z vertical y unidad geometrica en metros.
- Superficies sin espesor cuando el objeto SDTL no documenta espesores.
- Ninguna abertura, espesor o propiedad fisica se inventa.
- Identificadores 3D deterministas derivados del objeto SDTL fuente.
- Se preserva compatibilidad con dimensiones referenciadas de v1.8 y con Core.
- Objetos pendientes de revision no pueden entrar al generador.

## Limitaciones

- No es BIM y no genera IFC.
- No interpreta planos nuevos.
- Solo transforma objetos SDTL aprobados.
- La geometria depende de dimensiones confiables expresadas en metros.
- Los materiales son principalmente visuales.
- No genera puertas, ventanas o entradas de cables sin datos de ingenieria.
- No calcula colisiones, fisica, niveles de detalle ni optimizacion de mallas.
- El manifiesto glTF aun no contiene buffers ni accessors binarios.

## Siguiente fase

SDTL v1.9.5 puede implementar la `GLTF/Babylon.js Visualization Layer`, completar
buffers y accessors glTF, y validar la carga de los modelos en Babylon.js sin
mezclar renderizado con el modelo de ingenieria.
