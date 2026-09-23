# Worker / SDK — BCP: Java + OpenTelemetry

Copia local: [dashboards/temporal-sdk-java-otel.json](./dashboards/temporal-sdk-java-otel.json)

**Origen:** https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel.json  
Repo: `tsurdilo/temporal-server-operations` · path `observability/dashboards/sdk/temporal-sdk-java-otel.json` · **v1.4.0** (2026-06-17) · Tihomir Surdilovic (`@temporal.io`)  
Readme: https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel-readme.md

No usar el de Micrometer: los histograms no se llaman igual.

Hay **3 Grafana Cloud** (DESA, CERT, PROD). Las métricas `temporal_*` del SDK llegan al stack del entorno donde está desplegado el worker. No van al Grafana Cloud de PEVE (ese es Temporal Cloud).

## Importar (plataforma)

1. Grafana Cloud **de ese entorno**. Prometheus que scrapea el `/metrics` OTel de los workers (puede haber **más de un AKS**). **No** el datasource de D01 / PEVE.
2. Import → `dashboards/temporal-sdk-java-otel.json`.
3. Namespace lista todos los del scrape.

## Por aplicación

JSON: [dashboards/temporal-sdk-java-otel-aplicacion.json](./dashboards/temporal-sdk-java-otel-aplicacion.json)

1. Importar en **cada** Grafana Cloud donde haya workers (desa, cert y/o prod). Prometheus de workers de **ese** entorno (no D01). Si la app tiene varios AKS ahí, el scrape de todos debe llegar a ese Prometheus.
2. **Código de aplicación:** `apoq`. Filtra `namespace=~apoq*` (varios namespaces de Temporal). No cambia el título.
3. **Name:** Grafana deja `Temporal Java SDK (OTel) — ${APP_CODE}`. Reemplazar a mano (`… — apoq`).
4. **UID:** `temporal-sdk-java-otel-${APP_CODE}` → `temporal-sdk-java-otel-apoq`.
5. Combo **Namespace** solo sus prefijos. All = todos los de ese código, en todos los AKS del entorno.

`temporal_num_pollers` (Active Pollers) requiere Java SDK ≥ 1.30.0. Cache vacío al inicio: esperar WFT o Explore `{__name__=~"temporal_sticky_cache.*"}`.

D01/D02: Cloud (`no_poller`). Este tablero: pollers, slots, cache sticky, schedule-to-start, workflow/activity task del proceso Java.

## Qué no sirve

| Fuente | Por qué no |
|---|---|
| Mixin D01 (`temporal-overview.json`) | Solo Cloud (`temporal_cloud_v1_*`). |
| `temporal-sdk-java-micrometer.json` | Otro reporter. |
| [temporalio/dashboards/sdk](https://github.com/temporalio/dashboards/tree/master/sdk) | Mayo 2025. [Issue #75](https://github.com/temporalio/dashboards/issues/75): nombres viejos. No hay JSON Java OTel ahí. |
