# D02 — importar SLO y alertas P1

D01 (overview) se queda como exploración. Este JSON es el tablero de **guardia**: error rate Start/Signal, exhaustion, throttle, no poller, backlog, fail/timeout por type, actions vs límite.

Solo `temporal_cloud_v1_*`. Las series v1 ya son rates o gauges: las queries **no** usan `rate()`.

## Importar el dashboard

1. Grafana → Dashboards → Import → subir `dashboards/d02-slo.json`.
2. Elegir el **mismo Prometheus** que pinta el Temporal overview.
3. Variable Namespace: lista **todos** los `temporal_namespace` del scrape (`All` = `.*`). En el dropdown elige prod, cert o una app. Si quieres acotar el dashboard (solo prod), pon regex en la variable, p.ej. `.*-prod$` — no hace falta otro JSON.
4. Refresh 1m (Cloud agrega a 1 minuto).

Si Error rate y Requests salen vacíos, el label `temporal_namespace` no es el esperado: Explore → `temporal_cloud_v1_service_request_count` y copiar el valor exacto.

`up{job="temporal-cloud"}` de las alertas: el job puede llamarse distinto en Grafana Cloud. En Explore: `up{job=~".*temporal.*"}`.

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
