# Overview por aplicación (template)

D01 (mixin) sigue siendo el overview del **account**. D02 y D05 no se recortan por app.

Este JSON es un **template** con las mismas preguntas del overview, limitado a los namespaces de una aplicación:

`{código4}-{dev|desa|cert|prod}` → `apoq-prod`, `nrem-cert`, `cpca-desa`, …

Archivo: [dashboards/d01-aplicacion.json](./dashboards/d01-aplicacion.json)  
uid: `temporal-cloud-overview-app`

No sustituye D03/D04 (types de negocio nominados). Es D01 recortado para que cada equipo vea solo lo suyo.

## Variables

| Variable | Comportamiento |
|---|---|
| `aplicacion` | Prefijo de 4 caracteres (`/^([a-z0-9]{4})-(?:dev\|desa\|cert\|prod)$/`) |
| `temporal_namespace` | Solo `{app}-dev`, `-desa`, `-cert`, `-prod`. All = esos ambientes, no el account |

## Cómo lo usa cada equipo

1. Importar `d01-aplicacion.json` (mismo Prometheus que D01).
2. *Save as* → p.ej. `Temporal Cloud Overview — APOQ` (otro uid).
3. Variables → `aplicacion`: default = `apoq` (o `nrem`, …). *Include All* = off. *Hide* = variable.
4. Queda el dropdown Namespace (`apoq-dev` / `cert` / `prod`).
5. Opcional: folder Grafana + Team del equipo para que no vean la copia de otra app.

PEVE puede dejar el template original con Aplicación visible para cambiar de código.

## Qué no es

| Dashboard | Rol |
|---|---|
| D01 mixin | Plataforma. No se toca. |
| D02 / D05 | Guardia y FinOps de account. Sin variable `aplicacion`. |
| Este template | Overview de **una** app (dev/desa/cert/prod). |
| D03 / D04 | Siguiente corte: types de débito/remesa nominados. |

Si un namespace no lista, no cumple `{4}-{dev\|desa\|cert\|prod}`. Explore → `temporal_cloud_v1_service_request_count`.
