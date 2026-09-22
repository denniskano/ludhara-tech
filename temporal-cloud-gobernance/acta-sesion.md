# Acta — sesión Temporal Cloud (BCP / Yape)

Rellenar con lo que confirme el proveedor. Lo no marcado sigue abierto.

**Fecha:**  
**Asistentes BCP:**  
**Asistentes Temporal:**  

## Confirmado en la sesión

| # | Pregunta | Respuesta (texto / n/a) |
|---|---|---|
| 1 | MSA cubre **dos Account ID** con **un** support fee | |
| 2 | Account ID BCP / Account ID Yape | BCP: ________  Yape: ________ |
| 3 | Razón social en cada invoice | BCP: ________  Yape: ________ |
| 4 | SLA y cupo de tickets: ¿compartido? | |
| 5 | Invoices de **usage**: uno o dos | |
| 6 | Commit de Actions y créditos: pool o por cuenta | |
| 7 | Límites (namespaces, RPS, TRU): por cuenta o compartidos | |
| 8 | Cuenta Yape: ¿existe o hay que crearla? Fecha | |
| 9 | SAML: uno por cuenta. Email único por cuenta — ¿excepción para plataforma? | |
| 10 | Finance corporativo: ¿Billing API de las dos cuentas sin ser Owner de Yape? | |
| 11 | Métricas: dos keys Metrics Read-Only. ¿Cross-account scrape? | |
| 12 | Billing API: pasos de **cliente** (no runbook interno). ¿Habilitado en ambas? | |
| 13 | Support fee: ¿aparece en el CSV o solo en invoice? | |
| 14 | PrivateLink / mTLS: por cuenta o por namespace | |
| 15 | Ticket de onboarding (número) | |

## Decisiones BCP (propias)

- [ ] Adoptar dos Account (ver [modelo-operativo.md](./modelo-operativo.md)).
- [ ] Tags obligatorios en alta de namespace (cuenta BCP).
- [ ] Grafana: job OpenMetrics solo cuenta BCP; Yape aparte.
- [ ] Account Owner BCP: dos personas nominativas, no casilla genérica.

## Pendiente del proveedor

- [ ]  
- [ ]  

## Próximo paso

Dueño: ________    Fecha: ________
