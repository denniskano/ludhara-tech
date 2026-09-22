# Modelo operativo — dos Account, un contrato

Decisión de plataforma (no depende de Temporal): **BCP y Yape no comparten Account.** El MSA cubre soporte; cada empresa tiene su Account ID, SAML, métricas y Billing Center.

Chargeback **dentro** de BCP (APOQ, NREM, resto) sí usa tags y Billing API **de la cuenta BCP**. Eso no se mezcla con Yape.

```text
MSA Temporal (support fee mensual)
 ├── Account BCP     Account Owner PEVE / plataforma BCP
 │    ├── namespaces apoq-* nrem-* …
 │    ├── OpenMetrics (API key BCP) → Grafana job temporal-cloud-bcp
 │    └── Billing API + tags team/env/workload
 └── Account Yape    Account Owner Yape
      ├── namespaces propios
      ├── OpenMetrics (API key Yape) → Grafana job propio (o carpeta Yape)
      └── Billing Center / Billing API Yape
```

## Roles (cuenta BCP)

| Rol Temporal | Quién (BCP) | Qué puede |
|---|---|---|
| Account Owner (mínimo 2 personas, email nominativo) | PEVE + backup | Usuarios, pago, namespaces todos |
| Global Admin | Plataforma / SRE | Usuarios, namespaces, usage. No billing de pago |
| Finance Admin | Finanzas / control de gastos Cloud | Invoices, Billing API. No crea namespaces |
| Developer | Equipo de aplicación (APOQ, NREM) | Crea y opera **sus** namespaces |
| Metrics Read-Only (service account) | Scrape Grafana | Solo métricas; una key por cuenta |

Yape define los mismos roles **en su cuenta**. Un mismo email no puede estar en BCP y Yape: quien opera las dos usa dos direcciones (o IdP-initiated con dos tiles SAML).

## Namespaces (cuenta BCP)

Patrón ya usado: `{app}-{env}` → `apoq-prod`, `nrem-prod`, `apoq-cert`.

Tags al crear (Account Owner / Admin). Billing API los relee incluso en meses pasados:

| Tag | Ejemplo | Uso |
|---|---|---|
| team | apoq, nrem, peve | Chargeback |
| env | prod, cert, dev | Separar factura de no-prod |
| workload | transferencias, remesas | Producto |
| cost-center | (código interno) | Contabilidad |

No tag `org=yape` en la cuenta BCP.

## Métricas

- Un scrape OpenMetrics **por Account** (`metrics.temporal.io`, Bearer Metrics Read-Only).
- Grafana: datasource o job `temporal-cloud-bcp` filtrado a namespaces BCP. Yape no comparte esa key.
- El overview de Grafana Cloud es exploración de **una** cuenta. SLO y alertas van por namespace prod (paquete `grafana-temporal/`).

## Billing

- Invoice de usage: el de **esa** cuenta (Account Owner / Finance Admin).
- Support fee: una línea de contrato; Temporal debe decir si sale en un invoice padre o aparte (acta).
- Finanzas corporativas que necesiten BCP+Yape: dos CSV Billing API (`BillingAccountID` distinto), salvo que Temporal confirme un rollup.

Mes en curso del Billing API es provisional (~24 h de lag). Cierre = invoice del Billing Center.

## Red y seguridad

Private Link / mTLS es **por Account** (connectivity rules). Dos cuentas = dos onboarding de red, no un atajo. Audit logs no cruzan cuentas: control sobre Yape es contractual (evidencias), no un rol en la cuenta BCP.

## Qué no hacer

- Una sola cuenta Temporal “del holding” con namespaces `yape-*`.
- Un scrape de métricas BCP para “ver Yape”.
- Account Owner compartido BCP/Yape con el mismo email.
- Esperar a que tags sustituyan la segunda cuenta.
