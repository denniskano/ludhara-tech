# ADLS Gen2 en el portal de Azure

Pasos que faltan cuando la cuenta de almacenamiento ya existe y el conector corre en otro entorno. El portal está en español. La autenticación es la clave de la cuenta. No hace falta Microsoft Entra ID, ni una aplicación, ni un rol.

## No hay un modo ADLS Gen2 adicional

ADLS Gen2 no es otro recurso ni un interruptor que se active después. Es una cuenta de almacenamiento de uso general v2 con el **espacio de nombres jerárquico** habilitado en el momento de crearla.

En la cuenta, abre **Información general** y revisa **Espacio de nombres jerárquico**:

- **Habilitado:** la cuenta ya es ADLS Gen2. No configures nada más para “ponerla en modo ADLS2”.
- **Deshabilitado:** esa cuenta es Blob Storage normal. El espacio de nombres jerárquico no se puede activar después. Crea otra cuenta y, en el asistente, marca **Habilitar espacio de nombres jerárquico**.

No hace falta un recurso aparte llamado Data Lake, ni activar SFTP ni el sitio web estático.

## Campos del conector

| Campo | Dónde sale en el portal |
| --- | --- |
| `azure.datalake.gen2.account.name` | Nombre de la cuenta, el que aparece en el encabezado. Solo letras minúsculas y números. No es el grupo de recursos ni la suscripción. |
| `azure.datalake.gen2.sas.key` | **Seguridad y redes → Claves de acceso → Mostrar** en key1 → **Clave**. Es la clave de la cuenta, no un token SAS. |

```json
"azure.datalake.gen2.account.name": "<nombre-de-la-cuenta>",
"azure.datalake.gen2.sas.key": "<clave-key1>"
```

No configures `azure.datalake.gen2.client.id`, `azure.datalake.gen2.client.key` ni `azure.datalake.gen2.token.endpoint`. Esos campos son de Entra ID. Si van llenos a la vez que la clave, el conector rechaza la configuración.

En el conector de Confluent Cloud la misma clave va en `azure.datalake.gen2.access.key`, no en `sas.key`.

## 1. Contenedor

El conector no crea el contenedor. El primer tramo de `topics.dir` es el nombre del contenedor. Con `transactions/PEVE`, el contenedor se llama `transactions`.

En la cuenta: **Almacenamiento de datos → Contenedores → + Contenedor**.

- Nombre: `transactions`
- Nivel de acceso anónimo: **Privado**

## 2. Clave de acceso

En la cuenta: **Seguridad y redes → Claves de acceso**.

Confirma que **Permitir el acceso con clave de cuenta de almacenamiento** está habilitado. Si está deshabilitado, la clave no autentica aunque la copies. Pulsa **Mostrar** en key1 y copia **Clave**. Ese valor es `azure.datalake.gen2.sas.key`.

La clave da acceso de datos a toda la cuenta. No la subas a git. Si deja de usarse, en **Claves de acceso** rota key1.

## 3. Red

Si el conector está en otra red, en la cuenta abre **Seguridad y redes → Redes** y deja el acceso de red pública habilitado desde todas las redes. El proceso de Connect necesita salida HTTPS hacia `<cuenta>.dfs.core.windows.net`.
