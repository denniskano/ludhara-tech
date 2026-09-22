# D05 — importar FinOps Actions / TRU

D01 ya tiene filas de billable y TRU. Este JSON es el tablero de **Finanzas / PEVE**: totales 7d/30d, quién gasta (`action_type` × workflow type), heartbeats/retries, cuota APS y capacidad provisionada.

No sustituye D02 (guardia) ni D03/D04 (ops de la app). No importar `temporal_cloud_action_costs.json` (PromQL v0).

Solo `temporal_cloud_v1_*`. Las series ya son rates o gauges: las queries **no** usan `rate()`.

## Importar el dashboard

1. Grafana → Dashboards → Import → subir `dashboards/d05-finops.json`.
2. Elegir el **mismo Prometheus** que pinta el Temporal overview.
3. Variable Namespace: lista **todos** los namespaces del scrape (`All` = `.*`). Filtra prod o una app en el dropdown. Si no lista nada, Explore → `temporal_cloud_v1_billable_action_count`.
4. Rango por defecto **7d**. Retention prod ≥ 90 días para el stat 30d; si Grafana retiene menos, 30d sale corto o vacío.
5. Refresh 1m.

Paneles vacíos en **TRU** o **ns_capacity**: namespace on-demand. Normal. `provisioned_capacity_tru_count` es 0 fuera de provisioned.

Si Billable sale vacío y D01 sí pinta Actions: el job puede estar droppeando `temporal_cloud_v1_billable_action_count` (cardinalidad). No habilitar `temporal_activity_type` en el scrape 24×7.

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
