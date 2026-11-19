# Red privada en Dedicated eastus2

Hay tres redes distintas en esta solución. Mezclarlas es lo que hace parecer que "todo Tableflow va por Private Link". Solo el camino de los **archivos** tiene Private Link en Azure.

eastus2 publica Dedicated, Tableflow, Flink y Schema Registry. La matriz de red de Azure admite, para Dedicated, VNet peering y Private Link de entrada. Private Link de salida existe para Connect con clusters Dedicated; el egress de Tableflow hacia storage es otro recurso, el Egress Private Link Gateway, documentado aparte y válido en Enterprise y Dedicated.

## 1. Entrada: clientes hacia el cluster

Los productores y consumidores del banco ya llegan al Dedicated por **Azure Private Link de entrada**. El cluster no expone endpoint público. Ese Private Link no transporta las tablas: transporta el protocolo Kafka (y, con la configuración de red del environment, Flink y Schema Registry).

Schema Registry, el CLI y parte de la consola siguen teniendo matices de plano de control documentados en la guía de Private Link de Dedicated. No cambian el camino de los datos de Tableflow.

Private Link de Azure no cruza de región: el FAQ de networking lo deja explícito. Cluster, gateway de egress y cuenta de storage se quedan en eastus2.

## 2. Salida: Tableflow hacia el data lake

Este es el Private Link que hay que construir para el lake.

Si la cuenta acepta red pública, y no hay private endpoints, Tableflow cae a **Service Endpoints** de Azure. Con `publicNetworkAccess = Disabled` ese atajo no existe: sin los private endpoints, Tableflow no escribe.

La guía de Azure pide, en este orden:

1. **Resource ID** de la cuenta de storage (JSON View del recurso).
2. **Un Egress Private Link Gateway por environment y por región.** En la consola: Network configurations → Add gateway configuration → Private Link → "From Confluent Cloud to your external data systems". Cloud Microsoft Azure, región eastus2. Si el gateway de eastus2 ya existe, se reutiliza.
3. **Dos access points** sobre el mismo Resource ID: subrecurso `blob` y subrecurso `dfs`. Los dos son obligatorios.
4. En la cuenta, Networking → Private endpoints: aprobar las dos conexiones `plap-xxxxxx` que quedan en Pending. La descripción incluye el gateway y el environment.
5. Roles del service principal de la provider integration (`cspi-…`): Reader y Storage Blob Data Contributor.
6. Cuando ambos access points pasan a Ready, crear el registro DNS que muestra la consola para el dominio de cada access point.
7. Recién ahí, habilitar Tableflow con custom storage, la provider integration y esa cuenta.

El resultado: Tableflow escribe Parquet y el log de la tabla dentro de la red de Azure. El dato del tópico no atraviesa internet para llegar al lake.

## 3. Lectura: Databricks hacia el mismo lake

Databricks no lee el cluster de Kafka para este camino. Lee el container por un **Private Endpoint propio** del workspace (subrecurso `dfs`), con una storage credential de Unity Catalog. Ese endpoint lo administra el equipo del lake, no Confluent. Confluent no participa en la consulta.

## Lo que en Azure no tiene Private Link

La página de red privada de Tableflow y la de Azure dicen lo mismo, con distinto alcance:

- El **Iceberg REST Catalog** de Tableflow se alcanza por Private Link **solo en AWS** (ingress PrivateLink Gateway, access point, hosted zone). La página de Azure abre con: Tableflow no soporta acceso privado a su IRC en Azure.
- Las **integraciones de catálogo** — Unity Catalog y Snowflake Open Catalog / Apache Polaris — **no están soportadas vía red privada**.

Eso parte la arquitectura en dos planos:

| Plano | eastus2 privado | Cómo se resuelve |
|---|---|---|
| Bytes de la tabla | Egress Private Link, `blob` + `dfs` | Camino soportado |
| Alta automática en Unity Catalog | Tableflow tendría que llamar al workspace por internet | Registro manual, una vez por tabla |
| Alta automática en Polaris / Open Catalog | Misma limitación de catálogo | No forma parte de este diseño |
| Consulta Iceberg vía el IRC de Tableflow | Sin Private Link en Azure | Haría falta un camino público al catálogo, o esperar soporte |

Un fallo de publicación al catálogo no frena la materialización. La documentación lo separa a propósito: el tópico puede estar en `Syncing` contra el storage y en `Failed` contra el catálogo. En este diseño el estado que importa para el lake es el de materialización; el de catálogo automático se espera apagado.
