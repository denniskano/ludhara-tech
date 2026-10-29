# Calculadora Temporal Cloud — commitment 3 años

Estima **Actions**, **Active Storage** y **Retained Storage** a partir de varios workflow types, cada uno con caminos (porcentaje) para activities, timers, signals, etc.

Tarifas por defecto del contrato (editables):

| Dimensión | Tarifa |
|---|---|
| Actions | **$23.16** / millón |
| Active Storage | **$0.039** / GB-hora |
| Retained Storage | **$0.00105** / GB-hora |

List price público de Temporal es distinto (Actions desde $50/millón, Active $0.042/GBh). Esta calculadora usa el commitment, no el list.

| Archivo | Uso |
|---|---|
| [calculadora-temporal-cloud.html](./calculadora-temporal-cloud.html) | Calculadora interactiva (varios workflows + pasos) |
| [calculadora-temporal-cloud.xlsx](./calculadora-temporal-cloud.xlsx) | Misma lógica en Excel (celdas amarillas = input). Hoja **Diccionario** = glosario de cada campo |
| [explicacion-excel.md](./explicacion-excel.md) | Cómo leer el Excel: Active vs Retained, Event History, Retention Period |
| [build_excel.py](./build_excel.py) | Regenera el xlsx |

## Abrir en Windows

- **Excel:** doble clic al `.xlsx`. Si sale Vista protegida (archivo de internet/GitHub), **Habilitar edición**. Recalcula solo (fórmulas nativas, Excel 2016 / Microsoft 365). No hace falta Macros. Hoja **Listas** visible: ahí están los desplegables.
- **HTML:** clic derecho → Abrir con **Microsoft Edge** o Chrome. No usar Internet Explorer 11. Si lo bajas de GitHub, Edge puede pedir “Permitir contenido bloqueado”; es solo JavaScript local, no hay servidor.

## Qué cuenta como Action

Fuente: [Temporal Cloud Actions](https://docs.temporal.io/cloud/actions). Replay **no** factura.

| En la calculadora | Actions oficiales |
|---|---|
| Origen Cliente | 1 × `start_workflow` |
| Origen Signal-With-Start | 1 total (start+signal juntos) |
| Origen Schedule | 3 (2 del Schedule + 1 start del workflow) |
| Activity | 1 `schedule_activity` + retries + heartbeats que llegan al server |
| Local Activities (por WFT) | 1 por Workflow Task, no N |
| Timer | 1 `start_timer` (incluye timeouts implícitos del SDK) |
| Signal / Query / Update | 1 cada uno |
| Child (hijo **no** listado) | 2 (intent + start) |
| Continue-As-New | 1 |

Storage: [Temporal Cloud pricing](https://docs.temporal.io/cloud/pricing). GBh = GB × horas.

| Campo oficial | Qué es | Dónde se ingresa |
|---|---|---|
| **Workflow Execution Duration (h)** | Horas que la ejecución está Running | Por workflow type |
| **Payload StartWorkflow (KB)** | Tamaño del input / mensaje de arranque | Por workflow type |
| **Payload del mensaje (KB)** | Tamaño del payload que fluye en ese paso | Por paso |
| **Event History (KB)** | Calculado: start + Σ (veces × % × payload × copias). Activity ×2 (input+result) y ×(1+retries). Query y Timer = 0 | Fórmula, no se escribe |
| **Namespace Retention Period (días)** | **Solo Retained Storage.** Días que el namespace guarda el Event History **después de close**. No es Active. Un solo namespace (máx. 90 en Cloud) | Hoja Tarifas B8 |

- **Active Storage** = ejecuciones × Event History (GB) × Workflow Execution Duration
- **Retained Storage** = ejecuciones × Event History (GB) × Namespace Retention Period × 24 h

El detalle de workflows es **producción**. Certificación y desarrollo se estiman como **% del TOTAL de producción** (`PCT_CERT`, `PCT_DEV` en Tarifas). **TOTAL cuenta** = prod + cert + dev. El atajo asume el mismo mix, Duration, Retention y retries.

Es un **estimado de régimen** (mes calendario), no la factura. Temporal documenta hasta ±5% entre métricas y metering.

Storage: **1 GB = 1.000.000 KB** (decimal). En Excel los nombres de workflow type deben ser **únicos** (Pasos se agrupa con SUMIF).

Regenerar Excel:

```bash
python3 -m venv .venv
.venv/bin/pip install openpyxl
.venv/bin/python build_excel.py
```
