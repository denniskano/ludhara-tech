# Manual: Azure Private Link hacia Temporal Cloud (por namespace)

Diagrama: [temporal-cloud-azure-private-link.drawio](temporal-cloud-azure-private-link.drawio)
Libreto: [libreto-diagrama-private-link.md](libreto-diagrama-private-link.md)
Fuente: Temporal Cloud on Azure Pre-Release Guide (6 de octubre de 2026) y [Quarkus Temporal](https://docs.quarkiverse.io/quarkus-temporal/dev/index.html).

Temporal Cloud en Azure está en **pre-release** (invite-only): desarrollo y evaluación, **sin SLA ni producción**. Public Preview objetivo: noviembre 2026. GA objetivo: Q1 2027. Regiones: `centralus`, `australiaeast`.

La guía muestra **dos alias distintos** para `centralus`. Confirmar con Temporal el vigente antes de crear el Private Endpoint.

---

## Qué se configura (y qué no)

| Capa | Qué se hace | Quién |
|---|---|---|
| Azure (VNet / AKS) | Private Endpoint, NSG, DNS privado, peering | Plataforma / PEVE / redes |
| Temporal Cloud | Connectivity Rule + attach al namespace | PEVE (cuenta Temporal) |
| Quarkus (worker / starter) | Casi nada: el hostname estándar y TLS. Sin DNS privado, override de SNI | Equipo de la aplicación |

Private Link **no cambia** workflows, activities ni task queues. Cambia **por dónde sale el gRPC :7233**.

---

## Prerrequisitos

- Namespace Temporal Cloud en Azure (`azure-centralus` o `azure-australiaeast`) o réplica en esa región.
- Suscripción Azure y VNet donde corre AKS (o una VNet hub alcanzada por peering / VPN / ExpressRoute).
- Permiso para crear Private Endpoints, Private DNS zones y NSG.
- API key de Temporal Cloud con permiso para crear Connectivity Rules (solo se usa al crear; deshabilitarla después no tumba la regla).
- CLI: `az`, `temporal cloud` (extensión pre-release). `tcld` **no** está soportado en Azure.
- Del namespace: ID (`apoq.<account-id>`), endpoint gRPC (`<ns>.<account-id>.tmprl.cloud:7233` o el que muestre la consola, p. ej. `azure-centralus-prod.a7ux8.tmprl.cloud:7233`).

Alias de Private Link Service (confirmar vigentes):

| Región Temporal | `--region` | Alias (revisar con Temporal) |
|---|---|---|
| centralus | `azure-centralus` | Guía regiones: `pl-lp9jl-pls.…centralus.azure.privatelinkservice` · Paso de creación: `pl-ez4ef-pls.…centralus.azure.privatelinkservice` |
| australiaeast | `azure-australiaeast` | `pl-259e9-pls.8c379ece-f7d6-4bb8-ba46-0e14bb8c84ea.australiaeast.azure.privatelinkservice` |

El alias debe ser de la **región del namespace**. El Private Endpoint puede estar en otra región; se recomienda la misma.

---

## Parte 1 — Azure (red y AKS)

Los workers en AKS no “hablan Private Link”. Hablan un hostname. Azure debe resolverlo a la **IP privada** del Private Endpoint y enrutar TCP 7233.

### 1.1 Elegir la VNet del Private Endpoint

- Misma VNet de AKS (más simple), o
- VNet hub + peering / VPN / ExpressRoute hacia la VNet de AKS.

Crear una subnet dedicada, por ejemplo `snet-privatelink`. El NSG debe **permitir TCP 7233** desde las VNets de workers y clients.

### 1.2 Crear el Private Endpoint

Portal: Private Endpoint → Resource **by alias** → pegar el alias de la región del namespace → VNet/subnet del paso 1.1.

O CLI (nombre y RG de ejemplo):

```bash
az network private-endpoint create \
  --name pe-temporal-centralus \
  --resource-group <rg-red> \
  --vnet-name <vnet-hub> \
  --subnet snet-privatelink \
  --private-connection-resource-id "" \
  --manual-request true \
  --connection-name pe-temporal-centralus-conn \
  --group-ids "" \
  --request-message "Temporal Cloud azure-centralus"
```

En la práctica el portal con **resource alias** es el camino que documenta Temporal. Tras crearlo:

| Campo | Valor esperado |
|---|---|
| Provisioning State | Succeeded |
| Connection status | **Pending** |
| Request/Response | Awaiting Approval |

Si queda Rejected: pasó el plazo de 24 h sin Connectivity Rule, o el alias/región no coinciden. Hay que **recrear** el PE.

### 1.3 Copiar el resource ID y la IP

```bash
az network private-endpoint show \
  --name pe-temporal-centralus \
  --resource-group <rg-red> \
  --query id -o tsv
# /subscriptions/.../resourceGroups/.../providers/Microsoft.Network/privateEndpoints/pe-temporal-centralus

az network private-endpoint show \
  --name pe-temporal-centralus \
  --resource-group <rg-red> \
  --query 'customDnsConfigs[0].ipAddresses[0]' -o tsv
# 10.1.2.3
```

Guardar ambos. La IP entra en DNS; el ID entra en la Connectivity Rule.

### 1.4 Private DNS (recomendado)

Zona: `<account-id>.tmprl.cloud` (el account id de Temporal, no el de Azure).

```bash
az network private-dns zone create \
  --resource-group <rg-dns> \
  --name <account-id>.tmprl.cloud

az network private-dns record-set a add-record \
  --resource-group <rg-dns> \
  --zone-name <account-id>.tmprl.cloud \
  --record-set-name apoq \
  --ipv4-address 10.1.2.3

az network private-dns link vnet create \
  --resource-group <rg-dns> \
  --zone-name <account-id>.tmprl.cloud \
  --name link-aks \
  --virtual-network <vnet-aks-id> \
  --registration-enabled false
```

Un registro A **por namespace**. Vincular la zona a **toda** VNet con workers o starters (AKS spoke y, si aplica, hub). `registration-enabled=false`.

Desde un pod en AKS:

```bash
kubectl run netcheck --rm -it --restart=Never --image=busybox -- \
  nslookup apoq.<account-id>.tmprl.cloud
# Debe devolver 10.1.2.3, no una IP pública
```

Sin esta zona, el hostname resuelve por DNS público y el tráfico **sale a internet**, aunque el PE exista.

HA multi-región (aún no en Azure): Temporal recomienda sobreescribir `azure-<region>.region.tmprl.cloud`, no `<account-id>.tmprl.cloud`.

### 1.5 AKS: qué no hace falta

- No hay annotation de Service ni Ingress para Temporal.
- No hay NetworkPolicy específica más allá de permitir e<gress TCP 7233 hacia la IP del PE (y DNS 53 hacia Azure).
- CoreDNS usa los VNet links de Azure; no hace falta un rewrite a mano si el link está en la VNet del cluster.
- Si AKS está en otra VNet: peering + que esa VNet esté en el Private DNS link.

---

## Parte 2 — Temporal Cloud

Crear el PE **no** abre el namespace. Temporal tiene que **aprobar** el PE (Connectivity Rule) y **adjuntar** esa regla al namespace.

### 2.1 Crear la Connectivity Rule (≤ 24 h)

```bash
temporal cloud connectivity private create \
  --azure-pe-resource-id "/subscriptions/.../privateEndpoints/pe-temporal-centralus" \
  --region azure-centralus
```

Guardar el `connectivityRuleId`. Listar:

```bash
temporal cloud connectivity list
```

Cloud Ops API (mismo efecto):

```bash
curl -X POST "https://saas-api.tmprl.cloud/cloud/connectivity-rules" \
  -H "Authorization: Bearer $TEMPORAL_CLOUD_OPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"spec\": {
      \"privateRule\": {
        \"azurePeResourceId\": \"$AZURE_PE_ID\",
        \"region\": \"azure-centralus\"
      }
    }
  }"
```

`$REGION` es la del **namespace / alias**, no necesariamente la del PE.

Tras crear la regla, el PE pasa a **Approved**. Si sigue Pending: no hay regla con ese resource ID, el ID está mal, o el alias es de otra región (`private endpoint connection not found`).

### 2.2 Adjuntar la regla al namespace

Sin attach, el namespace **sigue aceptando internet** (default).

```bash
temporal cloud namespace connectivity attach \
  --namespace apoq.<account-id> \
  --connectivity-rule-id <azure-rule-id>
```

El namespace en la API **va sin** `.tmprl.cloud`.

| Reglas adjuntas | Quién entra |
|---|---|
| Ninguna | Cualquier cliente autenticado (internet u otro PE) |
| Solo privadas | Solo esos Private Link. Internet: `Request unauthorized` aunque el API key / mTLS sea válido |
| Privadas + pública | Private Link e internet (estado de **migración**) |

**Corte de tráfico:** si hoy los workers salen por internet, adjuntar **también** la regla pública, migrar DNS/pods, **después** `detach` de la pública.

```bash
temporal cloud namespace connectivity attach \
  --namespace apoq.<account-id> \
  --connectivity-rule-id <azure-rule-id> \
  --connectivity-rule-id <public-rule-id>

temporal cloud namespace connectivity list --namespace apoq.<account-id>

temporal cloud namespace connectivity detach \
  --namespace apoq.<account-id> \
  --connectivity-rule-id <public-rule-id>
```

`UpdateNamespace` (Cloud Ops API) es **declarativo**: hay que reenviar el spec completo con `resourceVersion`. Un campo omitido se borra. Partir de `GetNamespace`.

`tcld namespace set-connectivity-rules` también es declarativo (el set completo). En Azure usar `temporal cloud`.

Un PE sirve a **todos** los namespaces de la región. Un namespace acepta **varios** PE.

### 2.3 Probar

Desde un pod en la VNet (debe responder; si no hay workflows, lista vacía = éxito):

```bash
temporal workflow list \
  --address apoq.<account-id>.tmprl.cloud:7233 \
  --namespace apoq.<account-id> \
  --api-key "$API_KEY"
```

Desde fuera de la red, con solo regla privada: `Request unauthorized`.

Sin DNS privado (solo para diagnóstico):

```bash
temporal workflow list \
  --address 10.1.2.3:7233 \
  --namespace apoq.<account-id> \
  --api-key "$API_KEY" \
  --tls --tls-server-name apoq.<account-id>.tmprl.cloud
```

---

## Parte 3 — Microservicio Quarkus (`quarkus-temporal`)

Con **DNS privado**, el pod resuelve `<ns>.<account-id>.tmprl.cloud` a `10.1.2.3`. El client no necesita saber que existe Private Link.

### 3.1 Lo que ya debe existir (Cloud)

API key ([documentación Quarkus](https://docs.quarkiverse.io/quarkus-temporal/dev/index.html)):

```properties
quarkus.temporal.namespace=apoq.<account-id>
quarkus.temporal.connection.target=apoq.<account-id>.tmprl.cloud:7233
quarkus.temporal.connection.api-key=${TEMPORAL_API_KEY}
quarkus.temporal.connection.enable-https=true
```

Si Temporal Cloud Azure publica el endpoint regional (`azure-centralus-prod.xxxx.tmprl.cloud:7233`), usar **ese** hostname en `target` y el registro A de DNS debe coincidir (o un CNAME/A al mismo PE).

mTLS:

```properties
quarkus.temporal.namespace=apoq.<account-id>
quarkus.temporal.connection.target=apoq.<account-id>.tmprl.cloud:7233
quarkus.temporal.connection.enable-https=true
quarkus.temporal.connection.mtls.client-cert-path=/mnt/certs/temporal.pem
quarkus.temporal.connection.mtls.client-key-path=/mnt/certs/temporal.key
quarkus.temporal.connection.mtls.password=${TEMPORAL_MTLS_PASSWORD}
```

Certificados y API key: Secret de AKS / Key Vault, no en la imagen.

### 3.2 Qué cambia por Private Link

| Situación | Cambio en Quarkus |
|---|---|
| Private DNS zone linkeada a la VNet de AKS | **Ninguno.** Mismo `target`, mismo TLS, mismo namespace. |
| Sin DNS privado | El `target` no puede ser solo la IP: el certificado es del hostname. Hay que enviar SNI = hostname del namespace. |

La extensión Quarkus **no documenta** `tls-server-name` / SNI. El SDK / CLI de Temporal sí (`--tls-server-name`, `TEMPORAL_TLS_SERVER_NAME`). Opciones si no hay DNS privado:

1. **Preferible:** crear la Private DNS zone (parte 1.4) y no tocar el microservicio.
2. Channel gRPC gestionado por Quarkus (`quarkus.grpc.clients` / mTLS) con override de autoridad, si el equipo ya lo usa.
3. No apuntar `connection.target` a `10.1.2.3:7233` sin SNI: el handshake TLS falla o Temporal rechaza.

No hace falta, por Private Link:

- Cambiar `@WorkflowInterface` / `@ActivityInterface`
- Task queues
- `fail-on-startup-error` (sí conviene en rollout: si DNS aún no resolvió, el pod no arranca)
- Abrir puertos en el Deployment (el worker es cliente egress)

Sí revisar:

```properties
# Evitar que un rollout tumbe el pod si el PE aún está Pending
quarkus.temporal.worker-factory.fail-on-startup-error=false
quarkus.temporal.worker-factory.startup-max-attempts=5
quarkus.temporal.worker-factory.startup-retry-delay=5s
```

Solo durante la ventana de cutover; en régimen normal el default (`fail-on-startup-error=true`) detecta mal DNS o regla mal adjuntada.

### 3.3 Checklist del pod AKS

1. `nslookup` del hostname → IP del PE.
2. `nc -vz <ip-pe> 7233` o `temporal workflow list` desde un debug container.
3. Arrancar el Deployment; logs del worker: conexión gRPC OK, pollers activos.
4. Desde fuera de la VNet, el mismo API key contra el namespace **privado** debe fallar.

---

## Orden recomendado (sin cortar producción)

1. PE + DNS + link a la VNet de AKS (el tráfico **aún** puede ir por internet).
2. Connectivity Rule (aprueba el PE).
3. Verificar `nslookup` en un pod; opcional: un namespace de prueba con solo regla privada.
4. En el namespace productivo: attach **privada + pública**.
5. Reciclar pods Quarkus (sin cambiar properties si hay DNS).
6. Confirmar pollers y un workflow de prueba.
7. Detach de la regla pública.
8. Probar desde internet: `Request unauthorized`.

---

## Troubleshooting

| Síntoma | Causa habitual |
|---|---|
| PE Pending > 24 h | Sin Connectivity Rule, o resource ID / alias / región incorrectos |
| `nslookup` → IP pública | Falta Private DNS zone o VNet link en la VNet de AKS |
| TLS / certificado no coincide | `target` es la IP y no hay SNI; o el A record apunta a otro hostname |
| `Request unauthorized` desde el pod | Se adjuntó solo la regla privada de **otro** PE; o el pod no sale por el PE |
| Workers caen al attach | Se adjuntó solo privada con workers aún en internet |
| UpdateNamespace borra config | Spec incompleto; faltó `resourceVersion` o se omitieron campos |

---

## Relación con el plan de retiro

Private Link resuelve **conectividad privada**. No reduce la dependencia de Temporal Technologies. El [plan de retiro](../docs/plan-retiro-temporal-cloud-insolvencia.md) sigue aplicando.
