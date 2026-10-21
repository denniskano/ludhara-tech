# Calculadora Private Link — Confluent Cloud Dedicated

Calculadora de costos y consideraciones para **Dedicated** clusters con **Private Link** (AWS PrivateLink, Azure Private Link, Google Cloud Private Service Connect), incluyendo **Cluster Linking** intra-cloud y cross-cloud.

- Excel (fórmulas nativas, desplegables): [`calculadora-privatelink.xlsx`](calculadora-privatelink.xlsx)
- HTML: [`calculadora-privatelink.html`](calculadora-privatelink.html)

En Excel: celdas amarillas = input. Cloud filtra Region. Tarifas Dedicated se editan en la hoja **Tarifas**. Regenerar el xlsx: `python3 build_excel.py`.

## Qué estima

| Bloque | Origen del precio |
| --- | --- |
| Cluster Linking hourly | Documentado: $0.25 público / $0.50 private intra-cloud; $2.50 / $5.00 (premium) cross-cloud private |
| Cluster Linking egress | Documentado: $0.25/GB (incluye metadata). Confluent paga el egress del cloud provider |
| Cluster Linking ingress | = `KafkaNetworkWrite` del destination (no se cobra Kafka ingress extra) |
| CKU, Kafka ingress/egress, storage | **No son list price públicos de Dedicated.** Editable. Sacar de `confluent billing price list` |
| Endpoints del cloud provider | Estimado list US (Azure PE / AWS VPC endpoint / GCP PSC). Editable |

## Fuentes oficiales

- [Billing Dimensions — Cluster Linking](https://docs.confluent.io/cloud/current/billing/billing-dimensions.html)
- [Private networking para Cluster Linking](https://docs.confluent.io/cloud/current/multi-cloud/cluster-linking/private-networking.html)
- [Regiones y Premium region (cross-cloud private)](https://docs.confluent.io/cloud/current/get-started/regions.html)
- [Azure Private Link Dedicated](https://docs.confluent.io/cloud/current/networking/private-links/azure-privatelink.html)
- [AWS PrivateLink Dedicated](https://docs.confluent.io/cloud/current/networking/private-links/aws-privatelink.html)
- [GCP Private Service Connect Dedicated](https://docs.confluent.io/cloud/current/networking/private-links/gcp-private-service-connect.html)
- [Tipos de cluster / CKU](https://docs.confluent.io/cloud/current/clusters/cluster-types.html)
- [confluent billing price list](https://docs.confluent.io/confluent-cli/current/command-reference/billing/price/confluent_billing_price_list.html)

```bash
confluent billing price list \
  --cloud azure --region eastus2 \
  --cluster-type dedicated --network-type private-link
```

## Alcance

Solo **Dedicated**. Cluster Linking private-to-private exige la **misma Confluent Cloud Organization**. Un cluster existente **no se convierte** a Private Link: hay que crear red + cluster nuevos.
