# Guía de Formato Lineal para DFD Lógico

Para cualquier proceso del sistema, debes estructurar la respuesta de manera estrictamente lineal respetando la siguiente sintaxis y reglas de componentes:

## Sintaxis Obligatoria
(ENTIDAD) -> (CONCEPTO_ENTRADA) <- (CONCEPTO_SALIDA) --- (NOMBRE_PROCESO) -> (TABLA_1 -- ATRIBUTO_ESCRITO_1 - ATRIBUTO_ESCRITO_2) -> (TABLA_2 -- ATRIBUTO_ESCRITO_1) <- (TABLA_1 -- ATRIBUTO_LEIDO_1)

---

## Reglas de Rellenado por Componente

1. **(ENTIDAD):**
   * Utiliza exclusivamente alguna de las entidades válidas del sistema: `DUEÑO`, `RECEPCIONISTA`, `SOCIO`, `PROFESOR`, `ENTRENADOR`, `NUTRIGONISTA` (o `NUTRICIONISTA`).

2. **(CONCEPTO_ENTRADA):**
   * Si los datos de entrada son múltiples, agúpalos bajo un concepto o nombre de grupo arbitrario (ej. `Datos de registro`, `Credenciales`). 
   * Si el flujo de entrada requiere un único atributo específico, puedes pasar directamente el nombre de ese atributo en lugar de un concepto abstracto.

3. **(CONCEPTO_SALIDA):**
   * Define el concepto global o respuesta que el sistema devuelve al finalizar el proceso (ej. `Registro ingresado`, `Acceso denegado y cuenta bloqueada`, `Login exitoso`).

4. **--- (NOMBRE_PROCESO):**
   * El nombre del evento lógico del programa (ej. `1. Registrar socio`, `2. Iniciar sesión`). Debe abarcar de manera integral **todos los casos posibles del proceso** (caminos felices, errores, bloqueos, actualizaciones de estado por fallos, etc.).

5. **-> (TABLA -- ATRIBUTOS DE ESCRITURA):**
   * Por cada tabla modificada o insertada, añade un bloque con la flecha `->`, el nombre exacto de la tabla, un doble guion (`--`) y **todos los atributos específicos** que intervienen en cualquiera de los subcasos del proceso (éxito o error), separados estrictamente por un guion (`-`). No dejes fuera atributos de control si el proceso los altera (por ejemplo, `intentos_fallidos` o `bloqueado` si el flujo contempla el bloqueo por errores).

6. **<- (TABLA -- ATRIBUTOS DE LECTURA):**
   * Al final, si el proceso requiere consultar datos de las tablas para validar o tomar decisiones en cualquiera de sus subcasos, añade los bloques con la flecha `<-`, indicando la tabla y los atributos leídos separados por un guion (`-`). Si no hay lectura, déjalo vacío como `<- ()`.