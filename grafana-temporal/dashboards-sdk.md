# Worker / SDK — BCP: Java + OpenTelemetry

Copia local: [dashboards/temporal-sdk-java-otel.json](./dashboards/temporal-sdk-java-otel.json)

**Origen:** https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel.json  
Repo: `tsurdilo/temporal-server-operations` · path `observability/dashboards/sdk/temporal-sdk-java-otel.json` · **v1.4.0** (2026-06-17) · Tihomir Surdilovic (`@temporal.io`)  
Readme: https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel-readme.md

No usar el de Micrometer: los histograms no se llaman igual.

## Importar (plataforma)

1. Prometheus que scrapea el `/metrics` OTel de los pods (AKS). **No** el datasource de D01.
2. Grafana → Import → `dashboards/temporal-sdk-java-otel.json`.
3. Namespace lista todos los del scrape.

## Por aplicación

JSON: [dashboards/temporal-sdk-java-otel-aplicacion.json](./dashboards/temporal-sdk-java-otel-aplicacion.json)

1. Mismo Prometheus de AKS (no D01).
2. **Código de aplicación:** `apoq`. Filtra `namespace=~apoq*`. No cambia el título.
3. **Name:** Grafana deja `Temporal Java SDK (OTel) — ${APP_CODE}`. Reemplazar a mano (`… — apoq`).
4. **UID:** `temporal-sdk-java-otel-${APP_CODE}` → `temporal-sdk-java-otel-apoq`.
5. Combo **Namespace** solo sus prefijos. All = todos los de ese código.

`temporal_num_pollers` (Active Pollers) requiere Java SDK ≥ 1.30.0. Cache vacío al inicio: esperar WFT o Explore `{__name__=~"temporal_sticky_cache.*"}`.

D01/D02: Cloud (`no_poller`). Este tablero: pollers, slots, cache sticky, schedule-to-start, workflow/activity task del proceso Java.

## Qué no sirve

| Fuente | Por qué no |
|---|---|
| Mixin D01 (`temporal-overview.json`) | Solo Cloud (`temporal_cloud_v1_*`). |
| `temporal-sdk-java-micrometer.json` | Otro reporter. |
| [temporalio/dashboards/sdk](https://github.com/temporalio/dashboards/tree/master/sdk) | Mayo 2025. [Issue #75](https://github.com/temporalio/dashboards/issues/75): nombres viejos. No hay JSON Java OTel ahí. |
