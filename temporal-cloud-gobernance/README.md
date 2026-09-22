# Temporal Cloud — gobernanza BCP / Yape

| Documento | Uso |
|---|---|
| [session-brief-en.md](./session-brief-en.md) · [HTML](./session-brief-en.html) | Brief de la sesión con Temporal (inglés) |
| [modelo-operativo.md](./modelo-operativo.md) | Cómo operar dos Account bajo un MSA |
| [acta-sesion.md](./acta-sesion.md) | Registrar respuestas del proveedor |

**MSA** = Master Service Agreement (contrato marco: soporte, términos). No es una cuenta Cloud.

---

# Temporal Cloud — dos organizaciones bajo un contrato corporativo

Contexto: MSA / soporte mensual único con Temporal Technologies. Objetivo: **BCP y Yape** (Adam: *“set this up for you and Yape”*) operan de forma independiente: namespaces, métricas y billing, sin que una vea la otra.

Los runbooks que mandó Adam (`github.com/temporalio/runbooks`, `runbooks.tmprl-internal.cloud`, workflows `prod.cp`) **no son documentación de cliente**. Son internos de Temporal. El equivalente público es lo de abajo.

## Veredicto

**Independencia real (namespaces + métricas + factura + IdP) no cabe en una sola cuenta Temporal Cloud.** El contenedor de aislamiento es el **Account**, no el contrato ni el Namespace.

| Necesidad | Una cuenta, namespaces BCP vs Yape | Dos cuentas (BCP y Yape) bajo el mismo MSA |
|---|---|---|
| Crear namespaces sin verse | No. Account Owner / Global Admin ven y administran **todos**. Developer crea los suyos, pero no hay frontera de compañía. | Sí. Cada Account Owner gobierna solo su cuenta. |
| Métricas independientes | No. OpenMetrics es **por cuenta**; el rol Metrics Read-Only es account-level. Un scrape ve todos los namespaces. Filtrar por label no es aislamiento. | Sí. API key y scrape distintos. `temporal_account` distinto. |
| Billing independiente (UI + CSV) | No. Un invoice, Billing Center y Billing API de **esa** cuenta. Tags/Projects sirven para *chargeback interno*, no para dos razones sociales. | Sí, a nivel producto. Cada cuenta: Usage, Invoices, `CreateBillingReport`. |
| Un solo soporte mensual | El contrato no crea cuentas. | **Hay que pedirlo a ventas/soporte.** Adam ya apunta a un ticket para “you and Yape”. No está en la UI. |
| SAML / usuarios | Un IdP, un Account Id. Un email = una cuenta. | Dos SAML (mismo dominio de correo permitido). Un email **no** puede estar en las dos: quien opera ambos usa dos direcciones. |

Lo que el contrato **sí** puede hacer: un MSA, un fee de support, commits/créditos negociados, y **dos Account ID** nombrados. Eso no lo publica la Billing API; lo confirma el AE / support.

Lo que los links de Adam **sí** cubren (dentro de **una** cuenta): atribuir costo **por Namespace** (y tags/Projects) para FinOps. Útil *dentro* de BCP (APOQ vs NREM). No sustituye una cuenta Yape.

Fuentes públicas: [cuentas y acceso](https://docs.temporal.io/cloud/manage-access), [roles](https://docs.temporal.io/cloud/manage-access/roles-and-permissions), [Billing Center](https://docs.temporal.io/cloud/billing), [Billing API](https://docs.temporal.io/cloud/billing-api), [cost governance](https://docs.temporal.io/best-practices/cost-governance), [OpenMetrics](https://docs.temporal.io/cloud/metrics/openmetrics).

## Qué implica el producto (hechos)

- **Account** = frontera de usuarios, SAML, SCIM, invoices, plan, métricas, creación de namespaces a escala de cuenta. [docs](https://docs.temporal.io/cloud/manage-access)
- Varias cuentas en el **mismo dominio de email**, cada una con su SAML y Account Id. Un email solo en una cuenta.
- **Finance Admin**: ve billing/usage, **no** crea namespaces. **Developer**: crea namespaces, **no** ve billing. Nadie en una cuenta tiene “solo Yape” si Yape vive en la misma cuenta que BCP, salvo que no existan Account Owner/Global Admin compartidos — y entonces no hay gobierno corporativo unificado sobre esa cuenta.
- Billing API: CSV FOCUS, grano horario/diario/mensual, columnas `BillingAccountID`, `ResourceID` = `namespace.accountId`, `Tags`. Un reporte a la vez **por cuenta**. Mes en curso es provisional (lag ~24 h).
- UI: [Usage](https://cloud.temporal.io/usage) (costo por Namespace), [Invoices](https://cloud.temporal.io/billing/invoices). Account Owner / Finance Admin.
- OpenMetrics: `https://metrics.temporal.io/v1/metrics`, Service Account Metrics Read-Only **de esa cuenta**. Filtro `namespaces=` es recorte de volumen, no multi-tenant de dos empresas.

## Modelo recomendado para la sesión

```text
Contrato (MSA + support fee mensual)
        ├── Account BCP   → namespaces APOQ/NREM/…  → métricas BCP  → invoice BCP
        └── Account Yape  → namespaces Yape         → métricas Yape → invoice Yape
```

Finanzas corporativas, si necesitan el total: dos CSV Billing API (`BillingAccountID` distinto) o un rollup que Temporal **debe confirmar** (no está documentado como “parent account”).

No usar una cuenta con tags `org=bcp|yape`. Eso es chargeback, no independencia.

## Preguntas para Temporal (hoy)

Contrato y cuentas

1. Confirmar por escrito: el MSA cubre **dos Account ID** (BCP y Yape) con **un** fee de support. Pedir los Account ID y el nombre legal de cada billed entity.
2. ¿El support entitlement (SLA, named contacts, ticket portal) queda enganchado a ambos Account ID? ¿Un ticket de Yape consume el mismo cupo?
3. ¿Hay “parent / linked billing account”, o son dos invoices Stripe y el banco suma? ¿Créditos y commit de Actions son **pool** o **por cuenta**?
4. Límites: namespaces, RPS, TRU, retención — ¿por cuenta o compartidos?

Independencia operativa

5. Provisionar (o confirmar) cuenta Yape separada: Account Owner Yape, SAML propio, SCIM propio.
6. Un email no puede estar en las dos. ¿Recomendación para PEVE/plataforma que deba ver ambas? (alias, grupo break-glass)
7. ¿Puede un Finance Admin *corporativo* leer Billing API de **las dos** cuentas sin ser Account Owner de Yape? Si no, el rollup es export CSV, no UI.

Métricas

8. Dos Service Accounts Metrics Read-Only, dos API keys. Confirmar que **no** existe scrape cross-account.
9. Grafana: dos jobs OpenMetrics. ¿Algún producto “org dashboard” que no sea eso?

Billing (lo que cubren sus runbooks internos)

10. Activar Billing API en **cada** cuenta (`CreateBillingReport` / Finance Admin). Pedir que traduzcan `billing-api.md` y `namespace-cost-attribution.md` a pasos de **cliente** (UI + Cloud Ops API), no a runbooks `prod.cp`.
11. Tags obligatorios (`team`, `env`, `workload`, `cost-center`) **dentro** de cada cuenta. ¿Quién puede editar tags? (docs: Account Owner / Admin).
12. Mes en curso no es factura. ¿Fecha de cierre y si el support fee aparece como línea en el CSV o solo en el invoice?

Seguridad / banco

13. Audit logs y retención por cuenta. ¿BCP (control) puede exigir evidencia de Yape sin acceso a su cuenta?
14. PrivateLink / mTLS: ¿por cuenta, por namespace? Impacto en dos cuentas vs una.

Cierre de la sesión (pedir en el acta)

- [ ] Dos Account ID escritos, mapeados a BCP y Yape  
- [ ] Cómo se factura support (una línea vs dos)  
- [ ] Cómo se emiten invoices de usage (una vs dos)  
- [ ] Ticket de onboarding Billing API + OpenMetrics en ambas  
- [ ] Fecha de provisioning de la segunda cuenta si aún no existe  

## Uso de los links de Adam (para no perder tiempo)

| Link | Usar en la sesión |
|---|---|
| [Billing API público](https://docs.temporal.io/cloud/billing-api) | Sí. Es el producto. |
| [Usage](https://cloud.temporal.io/usage) / [Invoices](https://cloud.temporal.io/billing/invoices) | Sí, **dentro de cada cuenta** (Account Owner / Finance Admin). |
| `namespace-cost-attribution` interno | Pedir el doc de cliente o un walkthrough. No abrir `tmprl-internal`. |
| Workflows `create-billing-report` en `prod.cp` | Control plane de Temporal, no del banco. Equivale a `CreateBillingReport` en Cloud Ops. |
| “Open a support ticket … you and Yape” | **Eso** es el enganche del contrato a dos cuentas. Pedir número de ticket y Account IDs. |
