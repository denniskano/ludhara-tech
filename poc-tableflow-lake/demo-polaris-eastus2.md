# POC 2: Tableflow escribe Iceberg y Polaris es el catálogo

Segunda POC, separada de [demo-basic-eastus2.md](demo-basic-eastus2.md). El cluster es el mismo Basic público de eastus2. Cambia el formato y el catálogo: Tableflow materializa **Iceberg**, y quien publica la tabla es **Apache Polaris**, no Unity Catalog.

No reutilices los scripts de la primera. Esos fuerzan Delta, escriben `azure/salidas.env` y `confluent/salidas.env`, y el alta de catálogo es `--catalogo` contra Databricks. Un tópico de Tableflow admite un solo formato. Esta POC usa otros nombres para poder convivir con la primera si las dos vuelven a desplegarse.

Polaris no entra en el Dedicated privado. La catalog integration no está soportada por red privada, y en Azure el Iceberg REST Catalog de Tableflow no tiene Private Link. El porqué está en [04-polaris.md](04-polaris.md). Esta POC es pública a propósito.

## Qué reemplaza a Databricks

| Primera POC | Esta POC |
|---|---|
| `--table-formats DELTA` | `--table-formats ICEBERG` |
| Unity Catalog, workspace Premium, Access Connector | Apache Polaris, endpoint alcanzable desde Confluent |
| `CREATE EXTERNAL TABLE` y un SQL warehouse | Un motor Iceberg (Spark o Trino) que lea Polaris |
| `cred_rdv_demo` y `loc_rdv_demo` | El motor lleva sus propias credenciales al ADLS. Con BYOS, ni el IRC de Tableflow ni Polaris hacen credential vending |
| Tabla `dbw_tableflow_rdv_demo.rdv.transactions` | Tabla de solo lectura en el warehouse de Polaris. El schema por defecto es el id del cluster, `lkc-2ryr1m` |

Los Parquet los sigue escribiendo Tableflow. Polaris guarda el snapshot vigente, no una segunda copia de los archivos.

## Nombres

Mismo cluster, otros recursos.

| Pieza | Valor |
|---|---|
| Environment | `env-3r253o` |
| Cluster | `lkc-2ryr1m`, Basic, público, eastus2 |
| Suscripción | `sub-denniskano` |
| Resource group | `rg-tableflow-polaris-demo` |
| Storage account | una cuenta ADLS Gen2 nueva, HNS, acceso público habilitado, eastus2 |
| Container | `rdv-polaris`, vacío y exclusivo |
| Provider integration | `tableflow-polaris-demo` |
| Tópico | `rdv-polaris-transactions` |
| DLQ | `rdv-polaris-tableflow-dlq` |
| Conector | `datagen-polaris-demo`, quickstart TRANSACTIONS, AVRO |
| Catalog integration | `tableflow-polaris`, tipo `snowflake` en el CLI |

El container tiene que estar vacío cuando se habilita Tableflow. No uses `rdv-demo`.

## Polaris, antes de Confluent

Hace falta un Apache Polaris ya alcanzable por internet. El CLI lo habla con el mismo contrato que Snowflake Open Catalog. La guía paso a paso de Confluent está escrita para **Amazon S3** y para Open Catalog, y Snowflake ya no da de alta Open Catalog a cuentas nuevas. Esta POC no usa esa cuenta: usa Polaris, y el storage de las tablas sigue siendo ADLS, que es el storage que Tableflow documenta en Azure.

Polaris tiene que conocer el container como almacenamiento externo del warehouse, con un principal que pueda actualizar el catálogo. De esa configuración salen los cinco datos que pide Confluent:

- URL del catálogo, el endpoint REST de Polaris.
- Warehouse, el nombre del catálogo externo dentro de Polaris.
- Client ID y client secret de la conexión de servicio creada para Tableflow.
- Allowed scope con forma `PRINCIPAL_ROLE:<rol>`.

Sin un tópico Iceberg ya materializado, el sync de catálogo se queda en `pending`.

## Orden

1. Crea el resource group, la cuenta ADLS Gen2 y el container vacío `rdv-polaris` en la suscripción personal. Misma región y las mismas reglas de red que la primera demo: hierarchical namespace y acceso público habilitado. Un Basic no puede usar private endpoints.

2. Crea la provider integration `tableflow-polaris-demo` con el tenant de Azure. El Application ID recibe **Reader** y **Storage Blob Data Contributor** sobre la cuenta nueva. Espera **3 minutos**.

3. Crea el tópico `rdv-polaris-transactions`, una partición, `cleanup.policy=delete`. Arranca Datagen TRANSACTIONS en AVRO, sin registrar el esquema a mano. Habilita Tableflow en **Iceberg**, no en Delta:

```bash
confluent tableflow topic enable rdv-polaris-transactions \
  --cluster lkc-2ryr1m --environment env-3r253o \
  --storage-type AzureDataLakeStorageGen2 \
  --provider-integration <cspi-de-esta-poc> \
  --storage-account-name <cuenta-nueva> \
  --container-name rdv-polaris \
  --table-formats ICEBERG \
  --metadata-column-naming-scheme PORTABLE \
  --error-handling LOG \
  --log-target rdv-polaris-tableflow-dlq \
  --retention-ms 604800000
```

El script espera solo el subject (hasta 4 minutos) y el table location (hasta 2 minutos) en la primera POC. Aquí el comando no espera: cuando imprima la ruta, espera **1 minuto** y pausa el conector. El primer commit de un tópico corto es del orden de **5 minutos**.

4. Con el tópico ya en Syncing, publica el catálogo. No es `--catalogo`: ese flag es Unity Catalog.

```bash
confluent tableflow catalog-integration create tableflow-polaris \
  --type snowflake \
  --endpoint '<url-del-catalogo-polaris>' \
  --warehouse '<warehouse>' \
  --allowed-scope 'PRINCIPAL_ROLE:<rol>' \
  --client-id '<client-id>' \
  --client-secret '<client-secret>' \
  --cluster lkc-2ryr1m \
  --environment env-3r253o
```

Un cluster admite una integration por tipo de catálogo. Esta no choca con una de Unity Catalog, si algún día vuelven a convivir: son tipos distintos y tópicos distintos.

5. En Polaris, el warehouse debe mostrar la tabla bajo el schema `lkc-2ryr1m`, salvo que la integration fije otro namespace. La comprobación es esa tabla, de solo lectura, y un `SELECT` desde Spark o Trino con credenciales propias al container. No hay SQL warehouse de Databricks en esta POC.

## Qué no hace esta POC

- No registra la tabla en Unity Catalog ni crea el workspace `dbw-tableflow-rdv-demo`.
- No lee el Delta de `rdv-demo`. Ese camino es la primera POC.
- No abre Private Link ni el Dedicated.
- No despliega el servidor de Polaris. El endpoint, el warehouse y el principal tienen que existir antes del paso 4.

## Al terminar

1. `confluent tableflow catalog-integration delete <id> --force --cluster lkc-2ryr1m --environment env-3r253o`.
2. Deshabilita Tableflow en `rdv-polaris-transactions`, borra el conector, los tópicos, los subjects de esta POC y la provider integration `tableflow-polaris-demo`.
3. Borra `rg-tableflow-polaris-demo` y el service principal de esta POC en el tenant. No borres el de la primera si las dos están vivas.
4. Polaris, su principal y su almacén se apagan aparte. Confluent no los crea.
