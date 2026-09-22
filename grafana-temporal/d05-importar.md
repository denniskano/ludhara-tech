# D05 — importar FinOps Actions / TRU

D01 ya tiene filas de billable y TRU. Este JSON es el tablero de **Finanzas / PEVE**: totales 7d/30d, quién gasta (`action_type` × workflow type), heartbeats/retries, cuota APS y capacidad provisionada.

No sustituye D02 (guardia) ni D03/D04 (ops de la app). No importar `temporal_cloud_action_costs.json` (PromQL v0).

Solo `temporal_cloud_v1_*`. Las series ya son rates o gauges: las queries **no** usan `rate()`.

## Importar el dashboard

1. Grafana → Dashboards → Import → subir `dashboards/d05-finops.json`.
2. Elegir el **mismo Prometheus** que pinta el Temporal overview.
3. Variable Namespace: lista **todos** los namespaces del scrape (`All` = `.*`). Recorte por aplicación: [d01-aplicacion.json](./dashboards/d01-aplicacion.json). Si no lista nada, Explore → `temporal_cloud_v1_billable_action_count`.
4. Rango por defecto **7d**. Retention prod ≥ 90 días para el stat 30d; si Grafana retiene menos, 30d sale corto o vacío.
5. Refresh 1m.

Paneles vacíos en **TRU** o **ns_capacity**: namespace on-demand. Normal. `provisioned_capacity_tru_count` es 0 fuera de provisioned.

Si Billable sale vacío y D01 sí pinta Actions: el job puede estar droppeando `temporal_cloud_v1_billable_action_count` (cardinalidad). No habilitar `temporal_activity_type` en el scrape 24×7.

## Convención de las métricas v1

Igual que D02: series ya son rate/s o gauge. **No** usar `rate()`. Totales 7d/30d se **estiman** con `sum_over_time` (cada sample es la media del minuto × 60 s). No son el número de la factura; sirven para cruzarla.

Labels de D05: `temporal_namespace`, `action_type`, `temporal_workflow_type`, `is_background`. Alta cardinalidad: cada par type × action_type es una serie.

## Métricas del tablero (qué miden y cómo leerlas)

### Facturación — volumen, no dólares

**`temporal_cloud_v1_billable_action_count`** (rate)  
Actions **facturables** por segundo, rotas por `action_type` y `temporal_workflow_type`. Es la métrica de costo. Temporal documenta excepciones: no todos los cargos aparecen (p. ej. algunos de capacidad/export).

- **Stats rango / 7d / 30d:** `sum_over_time(...) * 60` o media × segundos del periodo. Requiere retención (30d vacío = Grafana no guarda tanto).
- **Por action_type:** qué operación come (Start, Signal, heartbeat, retry, `ns_capacity:tru`, …).
- **Por workflow type:** qué proceso de negocio come.
- **Top 20:** `avg_over_time` × `$__range_s` ≈ conteo en la ventana.
- **Baseline 7d × 1.5:** media de la rate a 7 días. Si la rate actual la supera 2 h y hay volumen > 0.1/s → P3.
- Vacío con D01 pintando Actions: relabel droppeó esta métrica, no “no hay gasto”.

**`action_type` que D05 destaca**

| Valor (aprox.) | Significado |
|---|---|
| `record_activity_heartbeat` y variantes `*_by_id` / `standalone` | Heartbeat de activity. Cada ping es una Action. Intervalo agresivo = factura alta sin más transferencias. |
| `retry_activity` | Reintento de activity. Core/worker inestable o timeout corto. |
| `ns_capacity:tru` (o similar) | Cargo por TRU provisionado y **no usado** en la hora. Solo namespaces provisioned. |

### Cuota operativa — no es lo mismo que billable

**`temporal_cloud_v1_total_action_count`** (rate)  
Todas las Actions/s que Cloud cuenta hacia la cuota. Filtro `is_background="false"`: las de background no topan `action_limit`.

- Distinto de billable: una Action puede contar para cuota y no (o sí) para factura, según el catálogo de Temporal.
- Panel **% vs limit:** `total_action{is_background=false} / action_limit`. Amarillo 60%, rojo 80% = P3 a 15 min.

**`temporal_cloud_v1_action_limit`** (gauge)  
Tope APS del namespace (on-demand o el tope elevado si hay TRU).

**`temporal_cloud_v1_total_action_throttled_count`** (rate)  
Actions frenadas por ese tope. En D05 va al lado del %: puedes estar al 50% medio y tener throttle (burst). El paging de throttle es P1 en D02, no se duplica aquí.

En el YAML (no en un panel D05, sí P3): `operations_count` / `operations_limit` y `service_pending_requests` / `poller_limit`.

### Capacidad — on-demand vs TRU

**`temporal_cloud_v1_provisioned_capacity_tru_count`** (gauge)  
TRU contratados en el namespace. **`0` = on-demand. Normal.** No alertar 0. Cada TRU extra implica un mínimo de Actions/hora; si no las usas, Temporal factura `ns_capacity:tru`.

**`temporal_cloud_v1_action_on_demand_envelope_limit`** (gauge)  
Qué `action_limit` tendrías **si** estuvieras on-demand. Si `action_limit` ≠ envelope, el namespace está en capacidad provisionada. Si son iguales, estás on-demand (el panel de TRU en 0 lo confirma).

Existen envelopes análogos para operations y service RPS (`*_on_demand_envelope_limit`); D05 solo pinta el de Actions.

## Qué mirar (15 minutos)

1. Totales 7d / 30d por namespace (desmarcar All y elegir uno).
2. Heartbeat % y retry %: si suben, la factura no es “más transferencias”, son activities ruidosas o el core reintentando.
3. Tabla top 20: el type de negocio que más Actions come.
4. Actions vs `action_limit` (amarillo 60%, rojo 80% = alerta P3). Throttle al lado: el % medio puede verse verde y igual haber burst.
5. `action_limit` ≠ envelope on-demand → el namespace está en TRU. Ahí sí importa el panel de capacidad no usada.

## Alertas P3 (mismo datasource)

No paging. Ticket a FinOps / PEVE. Copiar de [alertas-catalogo.yaml](./alertas-catalogo.yaml):

| Alerta | For |
|---|---|
| Actions > 80% del `action_limit` | 15m |
| Billable > 150% vs media 7d **y** billable/s > 0.1 | 2h |
| Operations / pollers > 80% del límite | 15m |

No alertar TRU=0. No alertar p95. Throttle/exhaustion son P1 en D02, no se duplican aquí.

## Qué no es este tablero

No es forecast de dólares (Temporal no exporta precio en OpenMetrics). Es volumen de Actions para cruzar con la factura del account.

D08 (saturación de cuotas) puede extraer las filas de límite; D05 se queda con gasto y desglose.
