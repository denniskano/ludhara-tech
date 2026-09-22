# D02 — importar SLO y alertas P1

D01 (overview) se queda como exploración. Este JSON es el tablero de **guardia**: error rate Start/Signal, exhaustion, throttle, no poller, backlog, fail/timeout por type, actions vs límite.

Solo `temporal_cloud_v1_*`. Las series v1 ya son rates o gauges: las queries **no** usan `rate()`.

## Importar el dashboard

1. Grafana → Dashboards → Import → subir `dashboards/d02-slo.json`.
2. Elegir el **mismo Prometheus** que pinta el Temporal overview.
3. Variable Namespace: lista **todos** los `temporal_namespace` del scrape (`All` = `.*`). Recorte por aplicación: template [d01-aplicacion.json](./dashboards/d01-aplicacion.json), no este JSON.
4. Refresh 1m (Cloud agrega a 1 minuto).

Si Error rate y Requests salen vacíos, el label `temporal_namespace` no es el esperado: Explore → `temporal_cloud_v1_service_request_count` y copiar el valor exacto.

`up{job="temporal-cloud"}` de las alertas: el job puede llamarse distinto en Grafana Cloud. En Explore: `up{job=~".*temporal.*"}`.

## Convención de las métricas v1

Todas llevan prefijo `temporal_cloud_v1_`. Temporal las publica ya agregadas a **1 minuto**:

| Tipo | Qué es | Cómo agregar |
|---|---|---|
| Rate | Eventos **por segundo** (media del último minuto) | `sum`, `sum by (...)`. **No** `rate()` / `increase()` |
| Gauge / Value | Valor puntual (abiertos, límite, TRU) | `sum` o `last_over_time` |

Un valor `0.5` en una rate = ~30 eventos en ese minuto, no “medio evento”. Los bursts de 5 s se diluyen en la ventana de 60 s: por eso se alerta **throttle/exhaustion**, no solo el % medio del límite.

Labels que usa D02: `temporal_namespace`, `operation`, `temporal_task_queue`, `temporal_workflow_type`, `is_background`.

## Métricas del tablero (qué miden y cómo leerlas)

### Frontend — ¿Cloud acepta Start y Signal?

**`temporal_cloud_v1_service_request_count`** (rate)  
Requests gRPC por segundo al frontend de Cloud. En D02 se filtra `operation=~"StartWorkflowExecution|SignalWorkflowExecution|SignalWithStartWorkflowExecution"`: es el camino de negocio (abrir o empujar un workflow), no Query/List/Describe.

- Label `operation`: nombre del RPC.
- **Leer:** volumen. Si está en 0, el error rate “verde” no significa que Cloud esté sano: no hay tráfico (cliente parado, outage de red hacia Cloud, o freeze de deploys).
- **Piso de paging:** la alerta P1 exige `> 0.1` requests/s para no disparar en namespaces idle.

**`temporal_cloud_v1_service_error_count`** (rate)  
Errores gRPC por segundo de esas mismas operations. No es “el débito falló en el core”: es que Cloud **no aceptó o no completó** el RPC (deadline, unavailable, invalid, etc.).

**Error rate (panel)** = `errors / clamp_min(requests, 0.001)` sobre Start+Signal+SignalWithStart.

- Amarillo 0.5%, rojo **1%** (P1 a 10 min si además hay volumen).
- `clamp_min` evita división por cero cuando no hay requests.
- **No es** fail-rate de workflow. Un Start exitoso puede terminar luego en `workflow_failed_count`.

### Saturación SaaS — burst vs cuota

**`temporal_cloud_v1_resource_exhausted_error_count`** (rate)  
Cloud rechazó un burst que un recurso no pudo absorber. Los SDK reintentan. **No incluye** el throttle por límite de namespace (eso son las `*_throttled_count`).

- Rojo si > 0. P1 a 2 min.
- El % de Actions vs `action_limit` puede seguir verde: la media de 1 min esconde el pico.

**`temporal_cloud_v1_total_action_throttled_count`** (rate)  
Actions por segundo que Cloud frenó por el límite de Actions del namespace.

**`temporal_cloud_v1_operations_throttled_count`** (rate)  
Igual para el límite de operations.

**`temporal_cloud_v1_service_request_throttled_count`** (rate)  
Igual para el RPS del frontend (`service_request_limit`).

El panel **Throttle** suma las tres. Rojo si cualquiera > 0. P1 a 2 min. Distinto de exhausted: throttle = te pasaste de la cuota configurada; exhausted = un recurso no aguantó el pico.

### Matching — ¿hay worker escuchando?

**`temporal_cloud_v1_no_poller_tasks_count`** (rate)  
Tareas por segundo que el matching de Cloud no pudo entregar porque **no había poller** en esa task queue (workflow o activity). Señal de Cloud, no diagnóstico del pod.

- Causas típicas: worker caído, TQ mal escrita, deploy, HPA a 0, mTLS mal, worker apuntando a otro namespace.
- P1 a 3 min. D01 verde + este panel rojo = el fallo típico “Cloud sano, app no procesa”.

**`temporal_cloud_v1_approximate_backlog_count`** (gauge)  
Cola aproximada de tareas pendientes por `temporal_task_queue`. Temporal avisa: puede sobrecontar tasks inválidas y **resetear a 0** en una TQ idle.

- No es un SLO exacto. Sirve para tendencia (¿crece 15 min?).
- P2 de ejemplo: > 100 durante 15 min.

### Resultado de workflow — no es el mismo que el error rate

**`temporal_cloud_v1_namespace_open_workflows`** (gauge)  
Workflows abiertos ahora. **No es SLO.** Subida sostenida = no cierran (bucle, CAN, worker que no avanza). P2 si > 150% vs hace 24 h.

**`temporal_cloud_v1_workflow_failed_count`** (rate)  
Cierres en Failed por segundo, por `temporal_workflow_type`. Incluye fallos de **negocio** (compensación que ApplicationFailure, validación). El PO decide qué type pagina.

**`temporal_cloud_v1_workflow_timeout_count`** (rate)  
Cierres por timeout (start-to-close / execution). Distinto de fail: el workflow no decidió fallar; se venció.

No están en D02 (sí en D01): `workflow_success_count`, `cancel`, `terminate`, `continued_as_new`. Cancel/terminate operativos no deben entrar al fail-rate de paging.

### Cuota de Actions (puente a D05)

**`temporal_cloud_v1_total_action_count`** (rate)  
Actions por segundo. Solo `is_background="false"` cuenta contra el límite. Background no satura la cuota APS.

**`temporal_cloud_v1_action_limit`** (gauge)  
Tope de Actions/s configurado en el namespace. El panel pinta uso vs este tope. Rojo sostenido > 80% es P3 (ticket), no P1; el P1 es throttle > 0.

`billable_action_count` no está en D02: es factura (D05). `total_action_count` es cuota operativa; no son idénticos (Temporal excluye algunos tipos del billable).

## Alertas P1 (mismo datasource)

Alerting → Alert rules. Copiar exprs de [alertas-catalogo.yaml](./alertas-catalogo.yaml). Empezar por estas cinco:

| Alerta | For |
|---|---|
| scrape down (`up == 0`) | 5m |
| error rate Start/Signal > 1% **y** requests/s > 0.1 | 10m |
| resource exhausted > 0 | 2m |
| throttle actions/ops/RPS > 0 | 2m |
| no poller en namespaces de guardia | 3m |

Contact point: guardia PEVE + app. No paging de p95/p99 en este corte.

## PromQL v0

Si en el overview o en Explore aparece `temporal_cloud_v0_*`, el scrape viejo se **apaga el 5 oct 2026**. D02 no funciona contra v0.

## Qué no es este tablero

No sustituye D03/D04 (workflow types de débito/remesa). Open workflows no es SLO. Workers/SDK: corte siguiente.
