# consumer-cuenta-360

Microservicio Quarkus que consume 10 tópicos de Confluent Cloud, cada uno con su esquema Avro, para alimentar una sola vista de cuenta. Volumetría objetivo: 500 TPS por tópico en hora pico, 5 000 TPS en total.

Un channel de SmallRye por tópico. Cada channel tiene su consumer group, su clase Avro, su dead-letter queue y su pool de hilos. Comparten el proceso, la configuración de conexión y el handler de errores de deserialización.

| Tópico | Consumer group | DLQ |
| --- | --- | --- |
| `cuenta-abierta` | `cuenta-360.cuenta-abierta` | `cuenta-360.cuenta-abierta.dlq` |
| `cuenta-cerrada` | `cuenta-360.cuenta-cerrada` | `cuenta-360.cuenta-cerrada.dlq` |
| `movimiento-registrado` | `cuenta-360.movimiento-registrado` | `cuenta-360.movimiento-registrado.dlq` |
| `transferencia-enviada` | `cuenta-360.transferencia-enviada` | `cuenta-360.transferencia-enviada.dlq` |
| `transferencia-recibida` | `cuenta-360.transferencia-recibida` | `cuenta-360.transferencia-recibida.dlq` |
| `pago-servicio-realizado` | `cuenta-360.pago-servicio-realizado` | `cuenta-360.pago-servicio-realizado.dlq` |
| `tarjeta-emitida` | `cuenta-360.tarjeta-emitida` | `cuenta-360.tarjeta-emitida.dlq` |
| `tarjeta-bloqueada` | `cuenta-360.tarjeta-bloqueada` | `cuenta-360.tarjeta-bloqueada.dlq` |
| `cliente-actualizado` | `cuenta-360.cliente-actualizado` | `cuenta-360.cliente-actualizado.dlq` |
| `limite-actualizado` | `cuenta-360.limite-actualizado` | `cuenta-360.limite-actualizado.dlq` |

## Estructura

```
src/main/avro/                     10 esquemas; quarkus-avro genera las clases
src/main/java/.../consumer/        un @Incoming por tópico
src/main/java/.../kafka/           handler de deserialización: veneno vs. Schema Registry caído
src/main/java/.../proyeccion/      contrato idempotente + implementación en memoria (reemplazar)
src/main/resources/application.properties
k8s/deployment.yaml                probes, rolling update, recursos
k8s/keda-scaledobject.yaml         escalado por lag de los 10 grupos
```

## Ejecutar

```bash
# Tests unitarios
mvn test

# Prueba de punta a punta con Dev Services (Docker): Kafka, Schema Registry,
# 6 particiones por tópico, 5 000 eventos por tópico y un mensaje venenoso
mvn test -Dtest=Cuenta360IT

# Contra Confluent Cloud
export KAFKA_BOOTSTRAP_SERVERS=pkc-xxxx.confluent.cloud:9092
export KAFKA_API_KEY=... KAFKA_API_SECRET=...
export SCHEMA_REGISTRY_URL=https://psrc-xxxx.confluent.cloud
export SCHEMA_REGISTRY_API_KEY=... SCHEMA_REGISTRY_API_SECRET=...
mvn package && java -jar target/quarkus-app/quarkus-run.jar
```

En una laptop, un solo proceso consumió los 50 000 eventos de la prueba en 5 a 6,5 s en tres corridas, entre 7 600 y 9 800 eventos/s. Esa cifra mide Kafka, Avro y SmallRye sin downstream: con la base de datos real el límite pasa a ser su latencia.

## Antes de producción

- **Esquemas:** los `.avsc` de `src/main/avro` deben ser los publicados por cada owner, con el mismo `name` y `namespace`. Descárgalos de Schema Registry; no los reescribas.
- **Proyección:** `ProyeccionEnMemoria` es un reemplazo temporal. La implementación real va contra la base de datos y respeta el contrato de `ProyeccionCuenta360`: idempotente y condicionada por `ocurridoEn`.
- **Tópicos fuente:** son de cada owner y necesitan 6 particiones.
- **DLQ:** son de este servicio. Créalas y registra su subject, porque en prod `auto.register.schemas=false`. Si la escritura en la DLQ falla, el channel muere, el pod se reinicia y vuelve a fallar con el mismo mensaje:

```bash
for t in cuenta-abierta cuenta-cerrada movimiento-registrado transferencia-enviada transferencia-recibida \
         pago-servicio-realizado tarjeta-emitida tarjeta-bloqueada cliente-actualizado limite-actualizado; do
  confluent kafka topic create "cuenta-360.$t.dlq" --partitions 1 --config retention.ms=1209600000
  confluent schema-registry schema create --subject "cuenta-360.$t.dlq-value" \
    --schema "src/main/avro/$t.avsc" --type avro
done
```

## Criterios de tuning

### Particiones y réplicas

| Valor | Por qué |
| --- | --- |
| 6 particiones por tópico | El tope de paralelismo de un grupo es su número de particiones. 6 deja crecer de 2 a 6 pods sin repartir. |
| 2 pods mínimo | Uno alcanza por caudal; el segundo mantiene el consumo cuando el otro se reinicia o se redespliega. |
| 6 pods máximo | Con 6 particiones, el séptimo pod entraría a los 10 grupos sin recibir ninguna. |
| `partitions=1` por channel (default) | Un `KafkaConsumer` por tópico y pod. A 500 TPS el poll no es el cuello; la concurrencia la da el pool. |

### Concurrencia por tópico

`@Blocking(value = "<tópico>-pool", ordered = false)` con `max-concurrency=16`.

\[
\text{concurrencia por pod} = \frac{500\ \text{TPS}}{\text{pods}} \times \text{latencia del downstream} \times 3
\]

Con 2 pods y 20 ms: \(250 \times 0{,}02 \times 3 = 15\). Si el downstream tarda 50 ms, sube `cuenta360.worker.max-concurrency` a 40 o añade pods. El pool por tópico evita que un downstream lento en un tópico ocupe los hilos de los otros nueve.

`ordered = false` quita el orden dentro de la partición. Por eso la proyección descarta el evento si ya aplicó uno más reciente para la misma entidad. Si un tópico exige orden estricto por clave, ese channel va con `ordered = true` y su paralelismo pasa a depender solo de las particiones.

### Commit y backpressure

| Valor | Por qué |
| --- | --- |
| `enable.auto.commit=false` + `commit-strategy=throttled` | Confirma el offset contiguo más alto ya procesado. Con procesamiento fuera de orden no se salta mensajes. |
| `max.poll.records=200`, `max-queue-size-factor=2` | Como mucho 400 registros en cola por channel. Al llenarse, SmallRye pausa las particiones en vez de acumular heap. |
| `throttled.unprocessed-record-max-age.ms=300000` | Un mensaje 5 min sin procesar marca el channel como no sano. El default de 60 s reiniciaría el pod con un downstream lento pero vivo. |

### Fetch y memoria

| Valor | Por qué |
| --- | --- |
| `fetch.min.bytes=32768`, `fetch.max.wait.ms=100` | Agrupa mensajes por fetch. Menos requests contra Confluent Cloud, a cambio de hasta 100 ms de latencia. |
| `fetch.max.bytes=8 MB`, `max.partition.fetch.bytes=1 MB` | El default de 50 MB por consumer, por 10 consumers, es medio GB de buffers posibles en un pod de 1 GiB. |
| Pod de 1 GiB, `MaxRAMPercentage=75`, `ExitOnOutOfMemoryError` | Heap de unos 768 MB. Ante un OOM el proceso sale de inmediato y Kubernetes lo reinicia, en lugar de seguir degradado. |

### Rebalance

| Valor | Por qué |
| --- | --- |
| Un `group.id` por channel | Sin `group.id` explícito, Quarkus usa el nombre de la aplicación en los 10 channels y queda un solo grupo. |
| `CooperativeStickyAssignor` | Al entrar o salir un pod solo se mueven las particiones necesarias; el resto sigue consumiendo. |
| `session.timeout.ms=45000` | Tolera pausas de red cortas hacia Confluent Cloud sin sacar al pod del grupo. Un pod caído se detecta en 45 s. |
| `maxUnavailable: 0`, `maxSurge: 1` | El rolling update cambia un pod a la vez: un rebalance por paso, no diez pods entrando juntos. |
| KEDA baja como mucho 1 pod cada 2 min, con 10 min de estabilización | Cada bajada rebalancea los 10 grupos; no hay que seguir cada valle. |
| Sin membresía estática | Con un Deployment, el pod nuevo tiene otro nombre; un `group.instance.id` dejaría las particiones del pod viejo sin dueño hasta el `session.timeout`. |

### Esquemas distintos y Schema Registry

| Valor | Por qué |
| --- | --- |
| `specific.avro.value.type` por channel | Fija la clase lectora del tópico. El esquema con que escribió el productor se resuelve contra ella, así que un campo nuevo con default no rompe al consumer. |
| Compatibilidad `FORWARD` o `FULL_TRANSITIVE` en cada subject | El owner puede publicar un esquema nuevo antes de que este servicio se actualice. Con `BACKWARD`, el default de Confluent, hay que desplegar primero el consumer. |
| `AvroDeserializationFailureHandler` | Bytes corruptos, esquema incompatible o id de esquema inexistente: van a la DLQ con los bytes originales, sin pasar por el `@Incoming`. |
| Reintento de Schema Registry: 0,5 s a 10 s de backoff, hasta 2 min | Una caída del registry o una credencial inválida no es veneno: nunca manda mensajes válidos a la DLQ. Pasados 2 min se cierra el consumer de ese channel, el liveness baja y Kubernetes reinicia el pod. |
| `max.poll.interval.ms=300000` | El reintento bloquea el hilo de poll; tiene que terminar antes que este intervalo. |

### Health

| Probe | Qué mira |
| --- | --- |
| Startup `/q/health/started` | Hasta 2 min para conectar los 10 consumers. |
| Readiness `/q/health/ready` | Los 10 channels conectados. Frena el rolling update si el pod nuevo no consume. |
| Liveness `/q/health/live` | Baja cuando un channel reporta una falla: Schema Registry caído más de 2 min, un mensaje más de 5 min sin procesarse, o una escritura fallida en la DLQ. SmallRye no la limpia hasta reiniciar, y ese reinicio es el que recupera el channel. El veneno y los errores de negocio que llegan a la DLQ no lo tocan. |

### Apagado

| Valor | Por qué |
| --- | --- |
| `shutdown-timeout=20000` y `shutdown-check-interval=500` por pool | Con los valores por defecto, Quarkus 3.31 fuerza el cierre de los pools y aparecen errores de timeout negativo en el log. |
| `quarkus.shutdown.timeout=30s`, `terminationGracePeriodSeconds: 45` | Deja terminar lo que está en proceso y confirmar offsets. Lo que no termine se vuelve a entregar al siguiente pod; la proyección idempotente lo absorbe. |

## Qué falla en cascada

| Evento | Efecto |
| --- | --- |
| Mensaje venenoso en un tópico | Va a su DLQ. Los 10 tópicos siguen. |
| Downstream lento para un tópico | Crece el lag de ese grupo; su pool se satura, los otros nueve no. KEDA sube pods para todos. |
| Cambio de esquema compatible | Nadie se entera hasta que actualices la clase. |
| Cambio de esquema incompatible | Los mensajes de ese tópico van a su DLQ hasta que despliegues la clase nueva. Alerta por tasa de DLQ. |
| Schema Registry caído menos de 2 min | Pausa en los tópicos que reciban un id de esquema nuevo; los que ya están en caché siguen. |
| Schema Registry caído más de 2 min | Se cierran los channels afectados y el pod se reinicia. Sin pérdida y sin DLQ. |
| OOM o despliegue | Los 10 consumers paran a la vez en ese pod; el otro pod toma sus particiones tras el rebalance. |
