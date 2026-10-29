# Explicación del Excel Temporal Cloud

Archivo: [calculadora-temporal-cloud.xlsx](./calculadora-temporal-cloud.xlsx).  
Hojas: **Tarifas → Resumen → Listas → Workflows → Pasos → Catalogo → Diccionario**.  
Amarillo = input. Verde = fórmula (no editar). En Windows: **Habilitar edición** si aparece Vista protegida.

Este texto responde tres cosas que se confunden: **Namespace Retention Period**, **Active vs Retained** y **Event History**.

## Active Storage y Retained Storage son dos cobros distintos

Temporal Cloud factura el **mismo Event History** en dos momentos, con dos tarifas:

| | Active Storage | Retained Storage |
|---|---|---|
| ¿Cuándo? | Mientras la Workflow Execution está **Running** (open) | **Después de close** (Completed / Failed / Terminated / Canceled) |
| ¿Qué tiempo usa esta calculadora? | **Workflow Execution Duration (h)** — por workflow type | **Namespace Retention Period (días)** × 24 h — un valor del namespace |
| ¿Dónde se ingresa el tiempo? | `Workflows` columna E | `Tarifas` celda B8 (`RETENTION_DIAS`) |
| Tarifa del contrato | $0.039 / GB-h | $0.00105 / GB-h |
| Fórmula (régimen mensual) | `exec × Event History (GB) × Duration` | `exec × Event History (GB) × Retention × 24` |

**Namespace Retention Period no es de Active.** No hay un “retention del activo”. Active dura lo que dure el run. Retention Period es un setting del **namespace**: cuántos días Temporal Cloud guarda el Event History ya cerrado (máx. 90 días).

En este Excel **todos los workflow types corren en un solo namespace**, por eso Retention es un único número, no una columna por fila.

```
run start ──────── Running ──────── close ──────────────────────── drop
                 Active Storage              Retained Storage
                 (Duration horas)            (Retention días × 24 h)
                 Event History GB            el mismo Event History GB
```

## Qué es Event History (KB)

**Event History** es el log persistido de **una** Workflow Execution. Temporal lo escribe como eventos:

- `WorkflowExecutionStarted` — lleva el **Payload** de StartWorkflow (input)
- `ActivityTaskScheduled` / `ActivityTaskCompleted` — input y result de la Activity
- `WorkflowExecutionSignaled` — Payload del Signal
- timers, child, Continue-As-New, etc.

Temporal Cloud cobra storage por el **tamaño** de ese log (GB × horas), no por “un mensaje suelto”. Por eso la calculadora **no pide History a mano**: lo arma desde los Payloads.

```
Event History (KB) =
    Payload StartWorkflow
  + Σ  veces × (% camino / 100) × Payload del mensaje × copias
```

Copias (hoja `Listas` columna D):

| Tipo de paso | Copias en Event History | Por qué |
|---|---|---|
| Activity | 2 × (1 + retries) | Se persiste input y result; cada retry vuelve a persistir |
| Signal, Update, Child, Continue-As-New, Local Activity, Nexus, Upsert SA | 1 | Un Payload en el log |
| Query | 0 | Query **no** se escribe en el Event History |
| Timer / WFT Heartbeat | 0 | Evento chico; no se modela Payload |

`GB = KB / 1.000.000` (decimal, alineado al GB-hora del contrato).

Heartbeats sí suman **Actions** si llegan al server; **no** se suman al Event History en este modelo.

## Cómo usar cada hoja

### Tarifas

| Celda | Nombre | Qué editar |
|---|---|---|
| B4 | `RATE_ACTIONS` | $ / millón de Actions (commitment) |
| B5 | `RATE_ACTIVE` | $ / GB-h Active Storage |
| B6 | `RATE_RETAINED` | $ / GB-h Retained Storage |
| B7 | `HORAS_MES` | Solo para pasar GBh a GB equivalente. No entra en el USD |
| B8 | `RETENTION_DIAS` | Retention Period del namespace. **Solo Retained** |
| B9 | `PCT_CERT` | % de certificación sobre el TOTAL de producción (default 15) |
| B10 | `PCT_DEV` | % de desarrollo sobre el TOTAL de producción (default 5) |

El detalle de `Workflows` / `Pasos` es **producción**. Cert y dev no tienen filas propias:  
`USD cert = TOTAL prod × PCT_CERT / 100`  
`USD dev = TOTAL prod × PCT_DEV / 100`  
`TOTAL cuenta = prod + cert + dev`

Eso asume el mismo mix de types, Duration, Retention, retries y heartbeats. Si un ambiente tiene Retention distinta, el % no alcanza.

### Workflows (un type por fila)

Escribes: nombre (único), ejecuciones/mes, origen, **Duration**, **Payload StartWorkflow**.  
El resto es fórmula: Event History, Actions, Active GBh, Retained GBh, USD.

Origen:

- Cliente = 1 Action (`start_workflow`)
- Signal-With-Start = 1 Action total
- Schedule = 3 (incluye el start)
- Ninguno = 0 (solo los pasos)

### Pasos (detalle de cada type)

Columna A = el **mismo nombre** que en Workflows.  
Por paso: tipo, veces, % del camino, retries/heartbeats (Activity), **Payload del mensaje (KB)**.

Actions del paso ≠ Event History del paso. Un Query cobra Action y **0 KB** de history.

### Resumen

- `C12` TOTAL producción = Actions + Active + Retained del detalle.
- `C13` certificación = `C12 × PCT_CERT / 100`
- `C14` desarrollo = `C12 × PCT_DEV / 100`
- `C15` **TOTAL cuenta** = C12 + C13 + C14
- `B16` debe ser **0** (nombres duplicados rompen el SUMIF).

### Listas / Catalogo / Diccionario

- **Listas:** orígenes y tipos (desplegables). No es input de negocio.
- **Catalogo:** usage names oficiales de Actions.
- **Diccionario:** el mismo glosario, celda por celda, dentro del xlsx.

## Ejemplo del archivo (Pago + Alta)

Namespace Retention = 30 días. Pago Duration 0.4 h, start 8 KB. Alta Duration 2.5 h, start 16 KB.

| Type | Event History / exec | Active GBh | Retained GBh |
|---|---|---|---|
| Pago interbancario (50k) | ~61.7 KB | exec × 61.7e-6 × 0.4 | exec × 61.7e-6 × 30 × 24 |
| Alta de cliente (8k) | ~122.5 KB | exec × 122.5e-6 × 2.5 | exec × 122.5e-6 × 30 × 24 |

Actions se calculan aparte (caminos, retries, heartbeats). Storage no usa esas Actions.

## Límites del estimado

- Régimen de un mes calendario, no la factura hora a hora.
- Temporal documenta hasta ±5% entre métricas OpenMetrics y metering.
- No incluye Support, Export, Fairness ni TRU ociosos.
- Replay no factura Actions.
- Fuentes: [Actions](https://docs.temporal.io/cloud/actions), [Pricing / storage](https://docs.temporal.io/cloud/pricing).

Regenerar el xlsx: `.venv/bin/python build_excel.py`
