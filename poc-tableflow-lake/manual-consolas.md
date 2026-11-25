# Demo A, desde las consolas

El mismo aprovisionamiento que `azure/desplegar.sh` y `confluent/desplegar.sh`, hecho en [portal.azure.com](https://portal.azure.com) y en [confluent.cloud](https://confluent.cloud). El cluster ya existe: Basic, público, eastus2, environment `env-3r253o`, cluster `lkc-2ryr1m`.

Hay un ida y vuelta. El storage se crea en Azure, la integración se abre en Confluent, el acceso se cierra en Azure y el tópico se materializa de nuevo en Confluent.

| Dato | Valor |
|---|---|
| Suscripción | `sub-denniskano`, `b4f55447-636d-4d6a-bdb8-ed32bbc32d14` |
| Tenant | `307f28c3-e152-49cf-9f55-bf842a1aa587` |
| Resource group | `rg-tableflow-rdv-demo` |
| Región | East US 2 |
| Storage account | `sttfrdvb4f55447` |
| Container | `rdv-demo` |
| Provider integration | `tableflow-rdv-demo` |
| Tópico | `rdv-demo-transactions` |
| Conector | `datagen-rdv-demo` |

No crees private endpoints, un Egress Private Link Gateway ni un firewall de "solo redes seleccionadas". Un Basic no puede usar esos endpoints y Tableflow no escribiría.

## 1. Azure: la cuenta y el container vacío

1. En el portal, abre el menú de la cuenta y **Switch directory**. Entra al directorio cuyo tenant es `307f28c3-e152-49cf-9f55-bf842a1aa587`. Lo confirmas en **Microsoft Entra ID → Overview → Tenant ID**.
2. **Storage accounts → Create**.
3. En **Basics**:
   - Subscription: `sub-denniskano`.
   - Resource group: **Create new**, `rg-tableflow-rdv-demo`.
   - Storage account name: `sttfrdvb4f55447`.
   - Region: **East US 2**.
   - Performance: **Standard**.
   - Redundancy: **Locally-redundant storage (LRS)**.
4. En **Advanced**:
   - **Enable hierarchical namespace**: marcado. Sin eso la cuenta no es ADLS Gen2 y Tableflow no la acepta.
   - Minimum TLS version: **Version 1.2**.
   - Allow anonymous access on individual containers: sin marcar.
5. En **Networking**: **Enable public access from all networks**. Déjalo así. Si más adelante lo pasas a redes seleccionadas, este cluster Basic no llega al storage.
6. **Review + create → Create**.
7. Abre la cuenta. **Containers → + Container**. Nombre `rdv-demo`, anonymous access **Private**. No subas ningún archivo: Tableflow exige el container vacío.
8. Anota el tenant id del paso 1. La cuenta y el container son los otros dos datos que pide Confluent.

## 2. Confluent: abrir la provider integration

Schema Registry tiene que estar habilitado en el environment. Si no lo está, actívalo desde el environment antes de producir en AVRO. Hacen falta `CloudClusterAdmin` sobre el cluster, `DeveloperWrite` sobre los subjects y `Assigner` sobre la provider integration. Para crear el service principal en el paso 3 hace falta **Cloud Application Administrator** o **Application Administrator** en Entra ID.

1. Entra al environment `env-3r253o`.
2. Menú izquierdo: **Integrations → Provider Integrations → Add integration**.
3. Elige **Microsoft Entra ID**. Nombre: `tableflow-rdv-demo`. **Continue**.
4. **Create Entra ID app**. Copia el **application client ID** y guárdalo. Es el id de la app multi-tenant de Confluent, no un id de tu tenant.
5. En **Select Confluent resources** elige Tableflow. En **List of permissions needed** tienen que salir **Reader** y **Storage Blob Data Contributor**. Esos dos roles van sobre la cuenta de storage.
6. No pulses **Continue** todavía. El asistente se puede cerrar: la integración queda en **Draft** y se retoma con **Complete**.

## 3. Azure: el service principal y los dos roles

El portal no crea un service principal para una aplicación multi-tenant de otro tenant. Confluent documenta ese paso con Azure CLI. El resto sí es el portal.

1. Con la sesión puesta en el tenant personal:

```bash
az account set --subscription b4f55447-636d-4d6a-bdb8-ed32bbc32d14
az ad sp create --id <application-client-id>
```

Si el tenant pide consentimiento de administrador, ábrelo con una cuenta que lo tenga y repite el `az ad sp create`:

```text
https://login.microsoftonline.com/307f28c3-e152-49cf-9f55-bf842a1aa587/adminconsent?client_id=<application-client-id>
```

2. En el portal, abre la cuenta `sttfrdvb4f55447` → **Access control (IAM) → Add → Add role assignment**.
3. Rol **Reader**. En **Members**, **User, group, or service principal** y busca el principal que acabas de crear. El nombre se parece a `cspi-…`. Scope: esta storage account. **Review + assign**.
4. Repite el alta con el rol **Storage Blob Data Contributor** y el mismo principal.
5. Espera unos tres minutos a que los roles propaguen.

## 4. Confluent: validar el tenant

1. **Provider Integrations**. Si la integración sigue en **Draft**, pulsa **Complete**.
2. En **Microsoft tenant ID** pega `307f28c3-e152-49cf-9f55-bf842a1aa587`.
3. **Validate**. La validación solo comprueba que el service principal existe en tu tenant. Si falla, revisa el tenant y que el `az ad sp create` haya terminado.
4. **Continue**. El estado pasa a **Created**.

## 5. Confluent: tópico, Datagen y Tableflow

1. En el cluster `lkc-2ryr1m`: **Topics → Create topic**.
   - Nombre: `rdv-demo-transactions`.
   - Particiones: 1.
   - Deja el default. `cleanup.policy` tiene que quedar en `delete`. Si lo pones en `compact`, Tableflow hace UPSERT y la RDV deja de ser un append.
   - No definas un data contract. El esquema lo registra el conector.
2. **Connectors → Add connector → Datagen Source**. Si aparece **Launch sample data**, ciérralo: ese atajo crea otro tópico. Abre la configuración del conector.
   - Nombre: `datagen-rdv-demo`.
   - Topic: `rdv-demo-transactions`.
   - Credenciales: **My account** alcanza para esta demo. La consola genera la API key.
   - **Select a template**: **Transactions**. No rellenes **Schema string**. Las dos opciones se excluyen.
   - **Select output record value format**: **AVRO**.
   - **Show advanced configurations**:
     - **Schema Keyfield**: `transaction_id`.
     - **Max interval between messages (ms)**: `5000`.
   - Tasks: 1.
   - **Launch**.
3. Espera a que el conector pase a **Running** y a que en **Schema Registry** aparezca el subject `rdv-demo-transactions-value`. Sin ese subject, Tableflow no materializa el tópico. El value es `datagen.example.transactions`: `transaction_id` y `card_id` (`long`), `user_id` (`string`), `purchase_id` (`long`), `store_id` (`int`). El key es `transaction_id`. No hay timestamp de negocio.
4. Abre el tópico → **Enable Tableflow**.
   - Formato: **Delta**.
   - **Configure custom storage**.
   - Provider integration: `tableflow-rdv-demo`.
   - Storage account: `sttfrdvb4f55447`. Container: `rdv-demo`.
   - Continúa y lanza.
5. El diálogo no pide el nombre de las columnas de origen ni qué hacer con un registro malo. El default es el esquema `DEFAULT` y el modo `SUSPEND`, que detiene el tópico entero si un registro no entra. Para dejarlo como el script, antes del primer commit:

```bash
confluent tableflow topic update rdv-demo-transactions \
  --cluster lkc-2ryr1m \
  --environment env-3r253o \
  --metadata-column-naming-scheme PORTABLE \
  --error-handling LOG \
  --log-target rdv-demo-tableflow-dlq \
  --retention-ms 604800000
```

`PORTABLE` crea `cflt_metadata_topic`, `cflt_metadata_partition`, `cflt_metadata_offset` y `cflt_metadata_timestamp`. `LOG` manda el registro malo a `rdv-demo-tableflow-dlq` y Tableflow crea esa DLQ si no existe. `retention_ms` son 7 días de snapshots, no borra filas. El primer commit de un tópico corto tarda unos 5 minutos, así que el comando alcanza a aplicarse.

6. En la sección **Monitor** del tópico, copia el **storage location**. Tableflow elige la carpeta. Tiene esta forma:

```text
abfss://rdv-demo@sttfrdvb4f55447.dfs.core.windows.net/<segmento>/<segmento>/<org>/<env>/<lkc>/v1/<uuid>
```

Esa ruta es la que usa Databricks.

## 6. Confluent: parar Datagen

`max.interval` es 5000 ms: es el hueco máximo, no un mensaje cada 5 segundos. Cuando **Topics → rdv-demo-transactions → Messages** muestre unas decenas, o haya pasado **1 minuto** desde que Tableflow ya tiene storage location, abre el conector `datagen-rdv-demo` y pulsa **Pause**. Si lo dejas en **Running**, sigue publicando.

## 7. Azure: ver el lake

Espera **5 minutos** desde la pausa. En la cuenta, abre **Containers → rdv-demo** y entra en el prefijo del storage location. Tienen que aparecer `_delta_log` y archivos `.parquet`. Si sigue vacío, espera otros 5 minutos. No borres ni edites esos objetos: la tabla se corrompe. El portal muestra los archivos aunque tu usuario no tenga Storage Blob Data Reader.

Con eso el tópico ya es una tabla Delta. El `SELECT` desde Databricks está en [demo-basic-eastus2.md](demo-basic-eastus2.md), sección 6. Usa el storage location copiado en el paso 5.

Para que Confluent publique la tabla en Unity Catalog, sin repetir el alta de Tableflow:

```bash
./azure/databricks.sh
./confluent/desplegar.sh --catalogo
```

El primero activa External data access, crea el principal `tableflow-rdv-sp`, guarda el secret en `azure/salidas.env` y concede los permisos sobre `dbw_tableflow_rdv_demo` y `loc_rdv_demo`. El segundo registra la integración `tableflow-rdv-uc`. En unos minutos aparece el schema `lkc-2ryr1m`. `rdv.transactions`, si la registraste a mano, sigue siendo otra tabla. Al desaprovisionar, `./confluent/desaprovisionar.sh` borra `tableflow-rdv-uc` y `./azure/desaprovisionar.sh` borra `tableflow-rdv-sp`.

## Al terminar

Hazlo en este orden. Confluent primero, para que deje de escribir. En Databricks, quita los objetos de Unity Catalog mientras el workspace existe. El resource group al final: al borrarlo se lleva el storage y el workspace, y ese borrado tarda varios minutos.

En Confluent:

1. Borra el conector `datagen-rdv-demo`.
2. En el tópico `rdv-demo-transactions`, **Disable Tableflow**.
3. Borra los tópicos `rdv-demo-transactions` y `rdv-demo-tableflow-dlq`.
4. En Schema Registry, borra los subjects `rdv-demo-transactions-value` y, si existe, `rdv-demo-transactions-key`. No toques el resto.
5. **Provider Integrations →** `tableflow-rdv-demo` **→ Delete**.
6. En **API keys** del cluster, borra la key del conector.

No borres el environment ni el cluster. Si publicaste la catalog integration, bórrala en **Tableflow → External Catalog Integrations** antes de deshabilitar Tableflow. El script `./confluent/desaprovisionar.sh` la incluye.

En el workspace de Databricks, antes de borrar nada en Azure:

```sql
DROP TABLE IF EXISTS dbw_tableflow_rdv_demo.rdv.transactions;
DROP SCHEMA IF EXISTS dbw_tableflow_rdv_demo.rdv;
```

En **Catalog**, borra el external location `loc_rdv_demo` y después la credencial `cred_rdv_demo`. El external location depende de la credencial. No borres la cuenta de Databricks ni el metastore.

En Azure:

1. **Resource groups →** `rg-tableflow-rdv-demo` **→ Delete resource group**. Se lleva la cuenta, el container, los Parquet, el workspace `dbw-tableflow-rdv-demo` y el Access Connector `ac-tableflow-rdv-demo`.
2. Si queda `rg-tableflow-rdv-demo-dbw`, bórralo también. Es el grupo que Databricks crea para el workspace.
3. **Microsoft Entra ID → Enterprise applications**. Busca el application client ID y bórralo. Eso quita el service principal de tu tenant. La aplicación multi-tenant sigue en el tenant de Confluent.

Los scripts que hacen esta misma limpieza son `./confluent/desaprovisionar.sh` y `./azure/desaprovisionar.sh`.
