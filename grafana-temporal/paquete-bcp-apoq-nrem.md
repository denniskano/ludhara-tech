# Paquete Temporal Cloud — BCP (APOQ / NREM)

Solo métricas `temporal_cloud_v1_*`. Workers/SDK y Private Link: corte siguiente.

Prácticas: RED en el frontend de Cloud (rate, errors, duration), saturación de cuotas SaaS, SLI/SLO por namespace crítico, FinOps de Actions, cardinalidad controlada (labels opt-in fuera del scrape 24x7).

Namespaces de referencia: `apoq-prod`, `nrem-prod` (ajustar al inventario). APOQ y NREM son independientes; tablero y alertas por aplicación.

## 1. Una fuente: OpenMetrics

```yaml
scrape_configs:
  - job_name: temporal-cloud
    scrape_interval: 60s
    scrape_timeout: 30s
    honor_timestamps: true
    scheme: https
    metrics_path: /v1/metrics
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/temporal-metrics-api-key
    params:
      namespaces:
        - apoq-prod
        - nrem-prod
    static_configs:
      - targets: ["metrics.temporal.io"]
```

Intervalo 60 s: las series ya vienen agregadas a 1 minuto. Intervalos menores suben DPM y no mejoran resolución. Job de cert separado si no se opera 24x7.

Labels opt-in (`temporal_activity_type`, worker deployment) solo en un scrape de diagnóstico.

Las rates de 1 min suavizan bursts: puede haber `resource_exhausted` con la utilización media “por debajo del límite”. Alertar throttle/exhaustion, no solo `% del limit`.

## 2. Dashboards Cloud

| ID | Dashboard | Audiencia | Origen |
|---|---|---|---|
| D01 | Temporal Cloud Overview | PEVE / SRE plataforma | **Instalado** (mixin Grafana). |
| D01-app | Overview por aplicación | Equipo de cada app | **Importar** [d01-aplicacion.json](./dashboards/d01-aplicacion.json): pedir código; solo esos namespaces. Types de esa app salen solos. [Guía](./dashboards-por-aplicacion.md). |
| D02 | SLO — namespaces críticos | Continuidad / PEVE / PO | **Importar** [dashboards/d02-slo.json](./dashboards/d02-slo.json). |
| D03 | FinOps Actions / TRU | Finanzas plataforma / PEVE | **Importar** [dashboards/d03-finops.json](./dashboards/d03-finops.json). |

No importar `temporal_cloud_openmetrics.json` además de D01. Retirar `temporal_cloud.json` (v0) antes del 5 oct 2026. Vista ejecutiva: [monitoreo-bcp.html](./monitoreo-bcp.html).

## 3. D01 — overview (qué mirar en incidente)

Orden de lectura:

1. Failed workflows / failed by type y task queue.
2. Task backlog + `no_poller_tasks_count`.
3. Sync match rate.
4. Resource exhausted + actions/operations/RPS throttled vs `*_limit`.
5. Service errors en `StartWorkflowExecution` / `SignalWorkflowExecution` / `SignalWithStartWorkflowExecution`.
6. Replication lag **solo si** el namespace es HA multi-región.

No usar como paging los p95/p99 en namespaces de bajo volumen: un solo Start lento mueve el percentil. Temporal lo documenta en el [catálogo](https://docs.temporal.io/cloud/metrics/openmetrics/metrics-reference): alertas de percentil con piso de `service_request_count`.

`no_poller` y backlog son señales **de Cloud** (el matching no encuentra poller / hay cola). En este corte no se profundiza en slots del worker; basta con paging y el tablero de la app.

## 4. D02 — SLI / SLO (producción)

Umbrales de ejemplo para discutir con PO y Continuidad, no contractuales.

| SLI | Métrica Cloud | SLO inicial (propuesta) |
|---|---|---|
| Disponibilidad de API | 1 − `service_error_count` / `service_request_count` en Start/Signal/SignalWithStart | 99.9% mensual por namespace prod |
| Éxito de workflow | `workflow_success_count` / (success+failed+timeout) por `temporal_workflow_type` crítico | 99.5% (excluir cancel/terminate operativos) |
| Matching | `no_poller_tasks_count` = 0 | 100% con pollers en prod |
| Cola | `approximate_backlog_count` (métrica aproximada) | sin crecimiento 15 min por encima del umbral de TQ |
| Throttle | `total_action_throttled_count` + `operations_throttled_count` + `service_request_throttled_count` | 0 sostenido > 2 min |
| Exhaustion | `resource_exhausted_error_count` | 0 sostenido > 2 min |
| Latencia de aceptación | `service_latency_p95` Start/Signal, **y** requests/min por encima de un piso | p95 < 500 ms (ajustar) |
| HA (si aplica) | `replication_lag_p99` | < objetivo de Continuidad |
| Scrape | `up{job="temporal-cloud"}` | 100% (ceguera de plataforma) |

Error budget: paging por burn-rate 1h/6h. “Open Workflows” no es un SLO.

Paneles mínimos D02:

- Stats: error rate Start+Signal, throttle, no-poller, open workflows, scrape `up`.
- Timeseries RED + cuotas, por namespace (variable; no hardcodear apps).
- Tabla: workflow types con failed+timeout en la ventana.

## 5. D01-app — tablero de aplicación (solo Cloud)

No hay tablero por type nominado (débito, emisión, …). Cada equipo importa [d01-aplicacion.json](./dashboards/d01-aplicacion.json) con su código de 4; el dashboard lista todos los namespaces `codigo*` y todos los `temporal_workflow_type` de esa app.

Guía: [dashboards-por-aplicacion.md](./dashboards-por-aplicacion.md).

`workflow_failed_count` no distingue fallo de negocio (compensación esperada) de fallo de plataforma.

## 6. D03 — FinOps

Importar [dashboards/d03-finops.json](./dashboards/d03-finops.json). Pasos: [d03-importar.md](./d03-importar.md). Independiente del overview por app.

- `temporal_cloud_v1_billable_action_count` por `action_type` y `temporal_workflow_type` (totales rango / 7d / 30d).
- `temporal_cloud_v1_total_action_count{is_background="false"}` vs `temporal_cloud_v1_action_limit` + throttle.
- Heartbeat y `retry_activity` como % del billable (el core que reintenta infla factura).
- TRU: `provisioned_capacity_tru_count` (0 = on-demand) y `action_limit` vs `action_on_demand_envelope_limit`.
- Capacidad no usada: `action_type` `ns_capacity:tru` si el namespace está provisioned.

No hay precio en OpenMetrics: el tablero es volumen para cruzar con la factura. Alertas P3: Actions > 80% del límite y billable > 150% vs media 7d.

## 7. Mapa de métricas Cloud (qué debe existir)

Agrupado como producto SaaS. Prefijo `temporal_cloud_v1_`.

| Grupo | Métricas | Para qué |
|---|---|---|
| Frontend (RED) | `service_request_count`, `service_error_count`, `service_request_throttled_count`, `service_latency_p50/p95/p99`, `service_pending_requests` | ¿Cloud acepta trabajo? |
| Exhaustion | `resource_exhausted_error_count` | Burst que el límite medio no muestra |
| Workflows | `namespace_open_workflows`, `workflow_{success,failed,timeout,cancel,terminate,continued_as_new}_count`, `workflow_schedule_to_close_latency_p*` | Resultado de negocio por type |
| Activities | `activity_{success,fail,timeout,cancel,task_fail,task_timeout}_count`, `activity_*_latency_p*` | Fallos de pasos, no solo del workflow |
| Task queues | `approximate_backlog_count`, `poll_success_count`, `poll_success_sync_count`, `poll_timeout_count`, `no_poller_tasks_count` | Cola y matching |
| Cuotas | `total_action_count`, `total_action_throttled_count`, `operations_count`, `operations_throttled_count`, `action_limit`, `operations_limit`, `service_request_limit`, `poller_limit` | Saturación SaaS |
| Capacidad | `provisioned_capacity_tru_count`, `*_on_demand_envelope_limit` | Provisioned vs on-demand |
| Facturación | `billable_action_count` | Costo por type |
| Schedules | `schedule_action_success_count`, `schedule_buffer_overruns_count`, `schedule_missed_catchup_window_count`, `schedule_overlap_skipped_count` | Jobs diferidos / cut-off |
| HA | `replication_lag_p50/p95/p99` | Solo namespaces high availability |

No re-agregar percentiles entre namespaces. Retention prod ≥ 90 días (SLO y Actions).

## 8. Alertas

Ver [alertas-catalogo.yaml](./alertas-catalogo.yaml). Síntoma + namespace + (si aplica) workflow type. Sin paging de p99 en cert ni sin piso de QPS.

| Severidad | Señal Cloud | Destino |
|---|---|---|
| P1 | scrape down; error rate Start/Signal; resource exhausted; throttle; no poller en TQ prod | Guardia PEVE + app |
| P2 | backlog alto 15 min; fail+timeout por type crítico; schedule missed/overrun; replication lag HA | SRE + PO |
| P3 | Actions > 80% del límite; billable vs baseline | Ticket |

## 9. Orden de este corte

1. Job OpenMetrics + retiro PromQL v0 (límite 5 oct 2026).
2. Importar D01. **Hecho.** Validar: [d01-siguiente.md](./d01-siguiente.md).
3. Alertas P1 y D02 SLO **o** D03 FinOps.
4. Cada app importa D01-app con su código.

Siguiente corte (fuera de aquí): SDK workers y camino Azure.
