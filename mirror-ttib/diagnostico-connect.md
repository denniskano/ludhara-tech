# Diagnóstico — connect.log (Mirror Source TTIB)

**Conector:** `connect-ttib-st-transfer-mr-source` (`MirrorSourceConnector`)  
**Worker:** `clientId=2`, grupo `cc-connect-ttib-st-transfer-mr-source-group`  
**Ventana del log:** 2026-09-16 **15:33:57 → 19:46:20 UTC** (~4 h 12 min). El archivo no incluye el arranque del worker.  
**Tópico origen:** `azc-ttib-operation-online` (`lkc-xzyppq`) → destino `pkc-lgwgm`.

## Conclusión

Nada llega al tópico destino. El worker está UP (tasks RUNNING, generation 36, probes 200, 0 ERROR/WARN), pero **no escribe**. El DEBUG de Connect cubre tres causas a la vez: origen vacío, Filter SMT, o **drop por error de conversión**.

La conversión apunta a un Schema Registry **dado de baja**. En `config.json` el conector pisa el SR del worker:

| Dónde | SR | Estado |
|---|---|---|
| Worker (`dev-vars.yaml`) `CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL` | `https://psrc-q2n1d.westus2.azure.confluent.cloud` (destino, Confluent Cloud) | El que debe usarse |
| Conector `value.converter.schema.registry.url` | `schemaregistry.kafka-desa-eu2/cu1.credito.bcp.com.pe` + mTLS JKS | **Baja.** Solo el destino tiene schema |

El override del conector gana. `AvroConverter` corre **después** de las SMT, al serializar hacia `pkc-lgwgm`. Con `auto.register.schemas=false` y `use.latest.version=true` tiene que leer el subject en ese SR. El interno no responde: el record no sale. El mismo DEBUG lo describe como *dropped due to conversion errors*; a nivel DEBUG puede no haber stack.

`config.json` **no se modifica**. El cambio de SR está en [`config-v2.json`](./config-v2.json): URL `psrc-q2n1d`, basic auth con `confluent-sr.username` / `confluent-sr.password` (credencial Jenkins ya presente), sin mTLS del SR interno.

Tras aplicar v2, si write sigue en 0, el Filter SMT (`process` + `event`) sigue siendo la segunda causa.

## Qué está sano

| Señal | Evidencia |
|---|---|
| Grupo Connect | Heartbeats OK, **generation 36** fija, mismo `member id` todo el archivo. Sin rebalance. |
| Tasks | 0, 1 y 2 viven las 4 h. |
| REST / K8s | `GET /` → 200, `kube-probe/1.34`. |
| Mirror scheduler | `refreshing topics took 9 ms` (26 veces). `RenameReplicationPolicy` source=`azc-ttib-operation-online`, target=`cc-loc-ttib-transfer`. |

## Qué no es un incidente (ruido)

**`Node N disconnected` (975 INFO).** Idle de Confluent Cloud, no caída de red. Se reparte ~72–73 veces por cliente (producers de task, offsets, statuses, configs, admin). Los **consumers de origen** solo aparecen 2 veces (`consumer-null-*`): el poll al source mantiene la conexión; los producers del target **no tienen nada que enviar** y el broker cierra por idle. Los heartbeats al coordinator siguen OK.

**OpenTelemetry JMX** (`Unusable value java.lang.String` en `status`, `leader-name`): el agent no puede mapear atributos String. Cosmético; 2016 líneas.

El nivel **DEBUG** infla el archivo (~35k líneas). Para operación: INFO + métricas JMX.

## Cadena de conversión (por qué el SR del destino importa)

No es MM2 byte-a-byte. El value hace:

1. SMT `jsonToAvroValue` (`TransformationFromJsonToMap$Value`) — no usa SR.
2. Filter `process` include `490000…497000`.
3. Filter `event` include `COMPLETADA` / `RECHAZADA` (`missing.or.null` → exclude).
4. `AvroConverter` serializa al cluster destino con el schema **latest** del SR configurado en el conector.

Origen (`lkc-xzyppq`) no tiene SR. Destino (`pkc-lgwgm`) sí: `psrc-q2n1d`. El conector no puede apuntar al SR interno.

| # | Hipótesis | Tras el arreglo de SR |
|---|---|---|
| 1 | SR interno muerto en el override del conector | **Propuesto en config-v2.json.** Aplicar y mirar write-rate. |
| 2 | Filter SMT tira el resto | Si poll > 0 y write = 0 con SR Cloud, relajar filtros en cert. |
| 3 | Origen idle | Lag ≈ 0 y poll = 0 en `azc-ttib-operation-online`. |
| 4 | Red / coordinator | Descartado: generation fija, probes 200. |

Subject Avro esperado en el SR destino: el del tópico **renombrado** por `RenameReplicationPolicy` (`<topic>-value`). `auto.register.schemas=false`: el schema tiene que existir ahí de antemano.

## Cómo imprimir el error en el log

Hoy el worker está en DEBUG de `WorkerSourceTask` y solo dice que el record no se produjo. **No imprime la excepción** de Avro/SR ni de las SMT. El Filter que descarta por `process`/`event` tampoco deja traza: es un drop silencioso.

Hay dos palancas. La del conector es la que saca el stack a INFO/ERROR. La de log4j es para el cliente HTTP del Schema Registry.

### 1. Dead letter / error reporter del conector (recomendado)

Añadir al JSON del conector (v2 o un PUT puntual en cert). No hace falta tocar `config.json` de producción:

```json
"errors.tolerance": "all",
"errors.log.enable": "true",
"errors.log.include.messages": "true"
```

| Propiedad | Efecto |
|---|---|
| `errors.log.enable=true` | Connect escribe **ERROR** con la excepción (timeout al SR interno, 401 al `psrc`, schema no encontrado, fallo de `jsonToAvroValue`). Sin esto, `errors.tolerance=all` traga el fallo y solo queda el DEBUG de “no records produced”. |
| `errors.log.include.messages=true` | Incluye key/value del record en ese ERROR. Útil en cert; en prod puede llevar PII. |
| `errors.tolerance=all` | La task **sigue RUNNING** y se ve el ERROR por record. Con el default `none`, la task debería pasar a FAILED con stack; en este log no pasó (o no llegó ningún record al converter). |

Buscar en el log: `Error encountered in task`, `Tolerance exceeded`, `RestClientException`, `UnknownHostException`, `Connection refused`, `Subject not found`.

El Filter SMT **no** pasa por este reporter: un exclude no es un error. Si tras habilitar lo anterior **siguen sin aparecer ERROR** y write=0, no es el SR: los records no sobreviven a `filterProcess` / `filterEvent`.

### 2. Loggers del worker (`dev-vars.yaml`) — prod vs desarrollo

`CONNECT_LOG4J_LOGGERS` solo **pisa** paquetes. No define el nivel raíz. El `connect.log` actual está en DEBUG de `WorkerSourceTask` / `WorkerCoordinator` (heartbeats y commit vacío): eso sale del template `connect-log4j.properties` o de `CONNECT_LOG4J_ROOT_LOGLEVEL`, no de las líneas de ZooKeeper.

ZooKeeper no va ni en prod ni en desarrollo (Cloud → Cloud).

**Producción** (estable, poco ruido):

```yaml
CONNECT_LOG4J_LOGGERS: org.reflections=ERROR
```

Raíz en INFO (`CONNECT_LOG4J_ROOT_LOGLEVEL: INFO` si el template lo deja en DEBUG). Sin `WorkerSourceTask=DEBUG`. En el conector, no hace falta `errors.tolerance=all`. Default `none`: si Avro/SR falla, la task pasa a FAILED y el stack sale solo. Opcional: `errors.log.enable=true` y **sin** `errors.log.include.messages` (payload).

**Desarrollo ahora** (ver el error de SR/Avro). Dos cosas; la del conector no requiere reinicio:

1. PUT del conector:

```json
"errors.tolerance": "all",
"errors.log.enable": "true",
"errors.log.include.messages": "true"
```

2. Worker (reinicio de pod). Raíz INFO + DEBUG solo del cliente SR:

```yaml
CONNECT_LOG4J_ROOT_LOGLEVEL: INFO
CONNECT_LOG4J_LOGGERS: org.reflections=ERROR,org.apache.kafka.connect.runtime.errors=ERROR,io.confluent.kafka.serializers=DEBUG,io.confluent.kafka.schemaregistry.client=DEBUG,io.confluent.connect.avro=DEBUG
```

Buscar `RestClientException`, `Error encountered in task`, HTTP al SR. Cuando terminen, volver al valor de producción.

El Filter SMT no deja ERROR aunque esté esto: un exclude no es un fallo. Si no hay ERROR y write=0, el record no llegó al converter.

### 3. Qué no esperes ver

`kube-probe` 200 y `Node disconnected` no son el error de conversión. Bajar el resto del worker a INFO cuando termine el diagnóstico.

## Qué hacer ahora

1. En cert: PUT con las tres keys `errors.*` sobre el conector **actual** (SR interno) y generar un evento que pase los filtros. El ERROR del log confirma o descarta el SR muerto.
2. Aplicar [`config-v2.json`](./config-v2.json) (mismo PUT/pipeline). REST: `schema.registry.url` = `psrc-q2n1d` y sin `ssl.keystore` / `ssl.truststore` de SR.
3. JMX: `source-record-poll-rate` vs `source-record-write-rate`.
4. Si write sigue 0 **sin** ERROR de `errors.log`: muestra de `process`/`event` en origen vs los Filter.
