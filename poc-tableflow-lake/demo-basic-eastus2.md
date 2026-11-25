# Demo A: Tableflow escribe RDV en Delta

Cluster **Basic** de Confluent Cloud en **Azure eastus2**, con red pública. Tableflow materializa un tópico como tabla Delta en ADLS Gen2. Databricks la consulta. No hay Private Link: un cluster Basic no tiene red privada, y los private endpoints de Tableflow hacia storage existen solo en Enterprise y Dedicated.

Tableflow en Basic y en eastus2 está disponible. Delta no usa el storage gestionado de Confluent: el destino tiene que ser una cuenta tuya.

Los mismos pasos, hechos en el portal de Azure y en la consola de Confluent, están en [manual-consolas.md](manual-consolas.md).

## Ya lo tienes

- Environment y cluster Basic en eastus2.
- Acceso a la consola de Confluent Cloud.

Anota estos dos identificadores, salen en la consola del cluster:

```bash
export CONFLUENT_ENV_ID=env-3r253o
export KAFKA_CLUSTER_ID=lkc-2ryr1m
```

## No aprovisiones

Egress Private Link Gateway, private endpoints `blob` y `dfs`, DNS privado, Polaris, Flink, Kafka Connect y un cluster Dedicated. Si el firewall del storage queda en "solo redes seleccionadas", Tableflow no puede crear esos endpoints desde un Basic y la demo no escribe.

## 1. Cuenta ADLS Gen2 en la suscripción personal

La cuenta va en `sub-denniskano` (`b4f55447-636d-4d6a-bdb8-ed32bbc32d14`), tenant `307f28c3-e152-49cf-9f55-bf842a1aa587`, región eastus2. El script crea el resource group `rg-tableflow-rdv-demo`, la cuenta ADLS Gen2 con acceso público habilitado y el container vacío `rdv-demo`.

```bash
./azure/desplegar.sh
```

Al terminar imprime los tres datos que pide Confluent Cloud: tenant id, storage account y container. También los guarda en `azure/salidas.env`.

## 2. Provider integration

Si la sesión del CLI caducó, el script imprime el enlace de login para abrirlo a mano y espera el código. Schema Registry tiene que estar habilitado en el environment. En Confluent hacen falta `CloudClusterAdmin` sobre el cluster, `DeveloperWrite` sobre los subjects y `Assigner` sobre la provider integration. El script usa el CLI (`provider-integration v2` y `tableflow`).

```bash
./confluent/desplegar.sh
```

Lee el tenant de `azure/salidas.env`, crea la integración `tableflow-rdv-demo` y le asigna ese tenant. Imprime el **Application ID** de la app multi-tenant de Confluent. Con ese id se cierra el acceso en Azure:

```bash
./azure/desplegar.sh --app-id <application-id-que-imprimio-confluent>
```

El script de Azure crea el service principal y asigna **Reader** y **Storage Blob Data Contributor** sobre la cuenta. Los roles tardan unos **3 minutos** en propagarse. El workspace de Databricks se puede crear en esa ventana. No habilites Tableflow antes de que pasen.

## 3. Tópico, Datagen y Tableflow

```bash
./confluent/desplegar.sh --cerrar
```

Eso deja:

- Tópico `rdv-demo-transactions`, 1 partición, `cleanup.policy=delete`. No registres el esquema a mano.
- Conector `datagen-rdv-demo`, quickstart **TRANSACTIONS**, salida **AVRO**, `schema.keyfield=transaction_id`, `tasks.max=1`, `max.interval=5000`. No rellena `schema.string`: las dos opciones se excluyen. El script crea una API key de Kafka para el conector.
- Tableflow en **Delta** contra la cuenta y el container de `azure/salidas.env`, con columnas `PORTABLE` (`cflt_metadata_topic`, `cflt_metadata_partition`, `cflt_metadata_offset`, `cflt_metadata_timestamp`) y errores en modo `LOG` hacia `rdv-demo-tableflow-dlq`. `retention_ms` son 7 días de snapshots, no borra filas.

El conector publica el value `datagen.example.transactions`. El key es `transaction_id` (`long`). El value sigue trayendo ese campo, más `card_id` (`long`), `user_id` (`string`), `purchase_id` (`long`) y `store_id` (`int`). No hay timestamp de negocio.

El script espera solo el subject `rdv-demo-transactions-value` antes de habilitar Tableflow (cada 10 segundos, hasta 4 minutos) y después el table location (cada 20 segundos, hasta 2 minutos). Al terminar imprime el **table location**. Tableflow elige la carpeta. En esta corrida quedó así, con dos segmentos delante de la organización:

```text
abfss://rdv-demo@<cuenta>.dfs.core.windows.net/<segmento>/<segmento>/<org>/<env>/<lkc>/v1/<uuid>
```

Esa ruta, completa, es el `LOCATION` de Databricks. La raíz del container no sirve.

## 4. Parar Datagen

`max.interval=5000` es el hueco máximo entre mensajes, no el ritmo. El conector puede publicar más seguido. Cuando el script imprime el table location, Datagen ya lleva un rato publicando: espera **1 minuto** y pausa. Si el subject tardó en aparecer, ya hay decenas de mensajes y puedes pausar enseguida.

```bash
./confluent/desplegar.sh --pausar
```

Si lo dejas en Running, sigue publicando y Tableflow sigue materializando.

## 5. Ver el lake, sin Databricks

El primer commit de un tópico corto es best-effort, del orden de **5 minutos** desde que hay mensajes. Después de pausar, espera esos 5 minutos. Tienen que aparecer `_delta_log/*.json` y archivos `.parquet` bajo el prefijo del table location. En esta corrida fueron cinco commits del log y dos Parquet.

El portal los muestra sin rol de datos: **Containers → rdv-demo → Storage browser**. Este `az` solo funciona si tu usuario tiene **Storage Blob Data Reader**, **Contributor** o **Owner** sobre la cuenta. Sin ese rol responde autorización denegada, aunque los archivos ya estén.

```bash
az storage fs file list -f "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login \
  --recursive --query "[].name" -o tsv
```

Si a los 5 minutos sigue vacío, espera otros 5 y repite. No borres ni edites esos objetos: la tabla se corrompe.

Con eso la mitad de la demo está hecha: el tópico ya es una tabla Delta en la capa RDV.

## 6. Databricks, para consultarla

Hace falta desde el principio de la demo, no al final. Sin esto no hay dónde correr el `SELECT`. El script crea, en el mismo resource group y en eastus2, un workspace **Premium** con acceso público, un Access Connector y el rol **Storage Blob Data Reader** sobre la cuenta. Databricks lee y no escribe encima de Tableflow. La cuenta Free no sirve.

```bash
./azure/databricks.sh
```

La primera corrida tarda **unos 5 minutos** (registro del provider, Access Connector y workspace). Si el metastore todavía no está asignado, el script lo dice y no crea la credencial. Entra en [https://accounts.azuredatabricks.net](https://accounts.azuredatabricks.net) con el mismo usuario de `az login`. Si sale **Set up your account**, el nombre es solo una etiqueta: en esta corrida fue `tableflow-rdv`. Si caes en el login genérico, **Continue with Microsoft Entra ID** con ese mismo usuario. Abre el workspace. En **Catalog** tienen que verse el catálogo del workspace (`dbw_tableflow_rdv_demo`), `system` y `samples`. Eso es el metastore ya asignado. No crees otro.

Vuelve a correr el mismo script. Esta segunda corrida tarda segundos y deja la credencial `cred_rdv_demo` y el external location `loc_rdv_demo`, de solo lectura, sobre `abfss://rdv-demo@<cuenta>.dfs.core.windows.net/`. La última línea siempre dice que el `SELECT` espera el table location. En este orden todavía no existe: lo imprime `./confluent/desplegar.sh --cerrar`.

```bash
./azure/databricks.sh
```

El `CREATE CATALOG` sin ubicación falla en esta cuenta: el metastore no tiene storage root y Default Storage está activo (`UC_METASTORE_STORAGE_ROOT_URL_NOT_FOUND_WITH_DEFAULT_STORAGE`). Usa el catálogo que ya existe. El nombre es el del workspace, con guiones cambiados por guiones bajos.

En el workspace: **SQL Editor → SQL Query**. **Run all** abre **Attach to an existing compute resource**. Deja **SQL Warehouse** y **Serverless Starter Warehouse**, y pulsa **Start, attach and run**. El arranque del warehouse va en ese botón. La consulta en sí tarda segundos cuando `_delta_log` y los Parquet ya están.

```sql
CREATE SCHEMA IF NOT EXISTS dbw_tableflow_rdv_demo.rdv;

CREATE EXTERNAL TABLE IF NOT EXISTS dbw_tableflow_rdv_demo.rdv.transactions
USING DELTA
LOCATION '<table location, la carpeta completa que imprimió --cerrar>';

SELECT transaction_id, card_id, user_id, purchase_id, store_id,
       cflt_metadata_partition, cflt_metadata_offset, cflt_metadata_timestamp
FROM dbw_tableflow_rdv_demo.rdv.transactions;
```

Tienen que salir filas. `cflt_metadata_partition` en 0 es la partición del tópico. Si el conteo se queda corto, el commit de Tableflow todavía no cerró: espera otros 5 minutos y repite el `SELECT`.

## 7. Publicar la tabla desde Confluent

En esta demo no hace falta repetir `--cerrar`. Tableflow ya está habilitado. Los dos comandos de la integración son estos:

```bash
./azure/databricks.sh
./confluent/desplegar.sh --catalogo
```

`./azure/databricks.sh` activa **External data access**, crea el principal `tableflow-rdv-sp`, guarda el secret en `azure/salidas.env` y concede los permisos sobre `dbw_tableflow_rdv_demo` y `loc_rdv_demo`: Data Editor, **EXTERNAL USE SCHEMA** y, en el external location, `CREATE EXTERNAL TABLE`, `READ FILES`, `WRITE FILES` y **EXTERNAL USE LOCATION**. El secret no se imprime.

`./confluent/desplegar.sh --catalogo` registra la integración `tableflow-rdv-uc`. En unos minutos, en Catalog aparece el schema `lkc-2ryr1m` con la tabla que crea Confluent. `rdv.transactions` sigue siendo la que registraste a mano. `WRITE FILES` solo crea ese objeto en el catálogo. Los Parquet los sigue escribiendo Tableflow.

Al desaprovisionar, `./confluent/desaprovisionar.sh` borra `tableflow-rdv-uc` y `./azure/desaprovisionar.sh` borra `tableflow-rdv-sp`.

## Orden

1. Crea el resource group, la cuenta ADLS Gen2 y el container vacío. El script no vuelve hasta que la cuenta existe. Después no hay espera.

   ```bash
   ./azure/desplegar.sh
   ```

2. Crea la provider integration e imprime el Application ID. Si la sesión caducó, abre el enlace que imprime el CLI y pega el código. Después no hay espera. El aviso de que `provider-integration` v1 está deprecado sale aunque el script llame a v2: no corta el flujo.

   ```bash
   ./confluent/desplegar.sh
   ```

3. Crea el service principal y asigna Reader y Storage Blob Data Contributor. Los roles tardan **3 minutos** en propagarse. Los pasos 4 y 5 cubren esa espera. No lances el paso 6 antes.

   ```bash
   ./azure/desplegar.sh --app-id <application-id>
   ```

4. Crea el workspace Premium, el Access Connector y el permiso de lectura. La primera vez tarda **unos 5 minutos**. Si dice que no hay metastore, termina el alta de la cuenta (sección 6) y comprueba que Catalog muestra `dbw_tableflow_rdv_demo`, `system` y `samples`. Eso no tiene espera extra.

   ```bash
   ./azure/databricks.sh
   ```

5. Con el metastore ya visible en Catalog, crea `cred_rdv_demo`, `loc_rdv_demo` y el service principal `tableflow-rdv-sp`. Activa External data access y concede los permisos del catálogo y del external location. Tarda segundos. El secret queda en `azure/salidas.env` y no se imprime.

   ```bash
   ./azure/databricks.sh
   ```

6. Crea el tópico, arranca Datagen, habilita Tableflow e imprime el table location. El script espera solo: hasta **4 minutos** por el subject y hasta **2 minutos** por la ruta. No lo interrumpas.

   ```bash
   ./confluent/desplegar.sh --cerrar
   ```

7. Publica la tabla en Unity Catalog. No repitas `--cerrar`. El primero deja el principal y los permisos. El segundo registra la integración. En unos minutos aparece el schema `lkc-2ryr1m`. `rdv.transactions` sigue siendo el registro manual.

   ```bash
   ./azure/databricks.sh
   ./confluent/desplegar.sh --catalogo
   ```

8. Pausa Datagen. Espera **1 minuto** después de ver el table location. Si el paso 6 ya se quedó esperando el subject, pausa enseguida.

   ```bash
   ./confluent/desplegar.sh --pausar
   ```

9. Comprueba el container. Espera **5 minutos** desde la pausa. Si sigue vacío, otros 5. El portal muestra los archivos aunque `az` con `--auth-mode login` falle por falta de Storage Blob Data Reader.

   ```bash
   az storage fs file list -f "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login \
     --recursive --query "[].name" -o tsv
   ```

10. Registra la tabla en el catálogo que ya existe y lee las filas. No hay espera si el paso 9 ya mostró `_delta_log` y Parquet. **Run all** pide el warehouse: **Serverless Starter Warehouse → Start, attach and run**.

   ```sql
   CREATE SCHEMA IF NOT EXISTS dbw_tableflow_rdv_demo.rdv;

   CREATE EXTERNAL TABLE IF NOT EXISTS dbw_tableflow_rdv_demo.rdv.transactions
   USING DELTA
   LOCATION '<table location>';

   SELECT transaction_id, card_id, user_id, purchase_id, store_id,
          cflt_metadata_partition, cflt_metadata_offset, cflt_metadata_timestamp
   FROM dbw_tableflow_rdv_demo.rdv.transactions;
   ```

## Al terminar

Primero Confluent, para que deje de escribir. Después Azure: con el workspace todavía en pie quita lo de Unity Catalog y luego borra el resource group. Ese borrado tarda varios minutos y el script no vuelve hasta que termina. Si Azure se detiene con un HTTP distinto de 200 o 404, el resource group sigue; corrige y vuelve a lanzarlo.

No hace falta un `DROP TABLE` a mano.

```bash
./confluent/desaprovisionar.sh
./azure/desaprovisionar.sh
```

`./confluent/desaprovisionar.sh` borra lo que creó la demo en Confluent:

- el conector `datagen-rdv-demo`
- Tableflow en `rdv-demo-transactions`
- los tópicos `rdv-demo-transactions` y `rdv-demo-tableflow-dlq`
- los subjects `rdv-demo-transactions-value` y `rdv-demo-transactions-key`, si existen
- la catalog integration `tableflow-rdv-uc`, si se publicó
- la provider integration `tableflow-rdv-demo`
- la API key de Kafka, y una Cloud API key vieja si `salidas.env` todavía guarda una
- `confluent/salidas.env` y `confluent/datagen.json`

No borra el environment, el cluster, Schema Registry ni el resto de subjects. Si la sesión caducó, imprime el enlace para abrirla a mano.

`./azure/desaprovisionar.sh` borra lo que creó la demo en Azure:

- la tabla `dbw_tableflow_rdv_demo.rdv.transactions`, el schema `rdv`, el external location `loc_rdv_demo`, la credencial `cred_rdv_demo` y el service principal `tableflow-rdv-sp`
- el resource group `rg-tableflow-rdv-demo`: la cuenta, el container, los Parquet, el workspace y el Access Connector
- el resource group gestionado `rg-tableflow-rdv-demo-dbw`, si sigue existiendo después de borrar el workspace
- el service principal de Confluent en el tenant personal
- `azure/salidas.env`

No borra la cuenta de Databricks ni el metastore. La aplicación multi-tenant sigue en el tenant de Confluent: el script solo quita el service principal de tu tenant.
