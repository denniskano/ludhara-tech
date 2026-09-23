# Inventario de dashboards Temporal Cloud

SDK Java+OTel: [dashboards-sdk.md](./dashboards-sdk.md). Private Link / scrape AKS: operación del worker, no este inventario Cloud.

## 1. Grafana mixin — Temporal overview (OpenMetrics)

Fuente: [grafana/jsonnet-libs/temporal-mixin](https://github.com/grafana/jsonnet-libs/blob/master/temporal-mixin/dashboards/temporal-overview.json). Es el JSON que Grafana Cloud instala con la integración Temporal.

El mixin **solo publica este dashboard**. No hay un pack aparte de costs o SLO.

| Sección | Qué muestra | Métricas |
|---|---|---|
| Request intensity / operations by namespace | Tráfico gRPC | `temporal_cloud_v1_service_request_count` |
| Task backlog / backlog levels / sync match | Cola y matching | `approximate_backlog_count`, `poll_success*`, `poll_timeout_count` |
| Workflows | Abiertos, éxito/falla/timeout/cancel/CAN por tipo y task queue | `namespace_open_workflows`, `workflow_*_count` |
| Workflow latency p50/p95/p99 | Schedule-to-close | `workflow_schedule_to_close_latency_p*` |
| Activities | Éxito, fail, timeout, retries, latencia | `activity_*_count`, `activity_*_latency_p*` |
| Pollers | No poller, success, timeout, sync/async | `no_poller_tasks_count`, `poll_*` |
| Usage & quotas | Actions, requests, operations vs límites | `total_action_count`, `*_limit`, `*_throttled_count` |
| Schedules | Éxito, buffer overrun, catchup missed | `schedule_*_count` |
| Service | Requests/errors, resource exhausted, replication lag | `service_*`, `resource_exhausted_error_count`, `replication_lag_p*` |
| Service operations latency | Start / Signal / SignalWithStart | `service_latency_p*` |
| Billable actions | Por `action_type` y workflow type, 1d/7d/30d | `billable_action_count` |
| Provisioned capacity (TRU) | Utilización vs envelope on-demand | `provisioned_capacity_tru_count`, `*_on_demand_envelope_limit` |
| Heartbeat / retry ratio | Activities caras o inestables | derivados de activity metrics |

El overview es **exploración del account** (variables: datasource, account, namespace, region). No es SLO, no es tablero de APOQ, no trae alertas.

Lo que hay que construir encima, todavía con métricas Cloud:

- Salud del scrape (`up` del job contra `metrics.temporal.io`).
- SLO: [d02-slo.json](./dashboards/d02-slo.json). FinOps: [d03-finops.json](./dashboards/d03-finops.json).
- Vista por aplicación: [d01-aplicacion.json](./dashboards/d01-aplicacion.json) (código al importar).
- Alertas: [alertas-catalogo.yaml](./alertas-catalogo.yaml).

## 2. temporalio — Temporal Cloud External Metrics

Fuente: [temporal_cloud_openmetrics.json](https://github.com/temporalio/dashboards/blob/master/cloud/temporal_cloud_openmetrics.json).

Mismo endpoint v1. Más corto que el mixin: summary, workflows, pollers, usage, schedules, service, replication lag, latencias Start/Signal.

**No incluye** (el mixin sí): activities, latencia schedule-to-close de workflows, billable actions desglosadas, TRU, heartbeat/retry ratio.

Si ya está el mixin, no duplicar este JSON como segunda fuente de verdad.

## 3. temporal_cloud.json (PromQL v0)

Histórico contra `temporal_cloud_v0_*` (contadores acumulados). Deprecado 2 abr 2026; **apagado 5 oct 2026**. Ver [reference v0](https://docs.temporal.io/production-deployment/cloud/metrics/reference) y [migration guide](https://docs.temporal.io/cloud/metrics/openmetrics/migration-guide).

v1 expone gauges que ya son rates por segundo en ventanas de 1 minuto. Las queries `rate()` / `increase()` de v0 no se copian. Los percentiles v1 no se re-agregan entre namespaces ni a ventanas más largas.

## 4. Action costs (JSON + YAML)

[temporal_cloud_action_costs.json](https://github.com/temporalio/dashboards/blob/master/cloud/temporal_cloud_action_costs.json) y [alerts YAML](https://github.com/temporalio/dashboards/blob/master/cloud/temporal_cloud_action_costs_alerts.yaml) son FinOps sobre PromQL v0.

El mixin OpenMetrics ya cubre `temporal_cloud_v1_billable_action_count` y TRU. Costos y alertas de gasto: **D03** ([dashboards/d03-finops.json](./dashboards/d03-finops.json)), no el JSON v0.

## 5. Comparación (solo Cloud)

| Pregunta | Mixin overview | OpenMetrics Temporal | v0 Cloud JSON |
|---|---|---|---|
| ¿Cloud acepta Start/Signal? | Sí | Sí | Legado |
| ¿Hay pollers? (visto desde Cloud) | `no_poller`, pending pollers | Igual | Legado |
| ¿Hay backlog? | Backlog + sync match | Igual | Legado |
| ¿Falló un workflow type de APOQ? | Por type y task queue | Igual | Legado |
| ¿Falló una activity? | Sí | No | Legado |
| ¿Nos throttlean / exhausted? | Usage & quotas | Usage & quotas | Legado |
| ¿Cuánto estamos gastando? | Billable + TRU | Actions agregadas | Action costs v0 |
| ¿HA cross-region? | Replication lag p* | Replication lag p* | Histograma |
| ¿SLO / error budget? | No | No | No |
| ¿Alertas? | No | No | Costs YAML (v0) |

Importar overview y el JSON OpenMetrics de Temporal responde las mismas preguntas de exploración. No duplicar. Encima: D02, D03, D01-app y alertas v1.
