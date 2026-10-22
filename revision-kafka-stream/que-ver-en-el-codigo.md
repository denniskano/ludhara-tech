# Qué deberíamos ver en el código (Quarkus Kafka, Avro → 3 sinks)

No es Kafka Streams. Es **Quarkus + SmallRye Reactive Messaging Kafka** (`quarkus-messaging-kafka`). Consume Avro y escribe a:

1. tópico **encriptado**
2. **DLQ**
3. tópico **unificado**

Si falta alguno de los bloques, o el poison pill de Avro no llega al DLQ, o el unificado se commitea y el encriptado no.

```
incoming Avro (channel source)
    ├─ OK  →  outgoing unificado  +  outgoing encriptado   (mismo Message, ambos ack)
    └─ nack / deserialize fail / encrypt fail  →  DLQ
```

## 1. Channels, no Topology

En `application.properties` (o `application.yaml`), no un `StreamsBuilder`:

```
mp.messaging.incoming.source.connector=smallrye-kafka
mp.messaging.incoming.source.topic=...
mp.messaging.incoming.source.group.id=...          # esto es el consumer group, no application.id

mp.messaging.outgoing.unified.connector=smallrye-kafka
mp.messaging.outgoing.unified.topic=...

mp.messaging.outgoing.encrypted.connector=smallrye-kafka
mp.messaging.outgoing.encrypted.topic=...
```

En Java, **una** de estas formas (no tres `KafkaProducer` a mano):

- `@Incoming("source")` + `@Outgoing("unified")` + `@Outgoing("encrypted")` en el mismo método (SmallRye admite `@Outgoing` repetido), o
- `@Incoming("source")` + dos `@Channel` `Emitter` / `MutinyEmitter`, o
- un `Targeted` / `OutgoingKafkaRecord` por sink

El unificado y el encriptado salen del **mismo** record incoming. Si una segunda app re-lee el unificado para encriptar, hay dos `group.id`, dos offsets y dos ventanas de fallo.

## 2. Avro Confluent, no Apicurio “por default”

En Dedicated / Confluent Cloud el camino oficial de Quarkus es `quarkus-confluent-registry-avro` + `io.confluent:kafka-avro-serializer`, no solo `quarkus-apicurio-registry-avro`.

Ver:

- `src/main/avro/*.avsc` y plugin que genera las clases
- incoming: `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer`
- `specific.avro.reader=true` si el `@Incoming` tipa la clase generada
- outgoing unificado **y** outgoing encriptado: cada uno con `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer` (la autodetect no es fiable si usan `Targeted`)
- `schema.registry.url` + auth (`basic.auth.credentials.source=USER_INFO`, `schema.registry.basic.auth.user.info`) en **cada** channel que serializa/deserializa
- subject strategy alineada con el productor (`TopicNameStrategy` vs `RecordNameStrategy`)

Si el payload del método es `String` / `JsonObject` / `Map`, no están consumiendo Avro: están tirando el schema.

## 3. El DLQ de Quarkus es el `failure-strategy`, y no cubre Avro solo

El DLQ **de negocio** (schema OK, contrato KO) es un `nack` del `Message`. Eso sí entra al strategy:

```
mp.messaging.incoming.source.failure-strategy=dead-letter-queue
mp.messaging.incoming.source.dead-letter-queue.topic=...-dlq
```

Headers que SmallRye escribe solo (tiene que llegar así al tópico, no reinventarlos mal):

- `dead-letter-reason`
- `dead-letter-cause`
- `dead-letter-topic`
- `dead-letter-partition`
- `dead-letter-offset`

Default del strategy es `fail` ( tumba el procesamiento y **no** commitea). Si no está `dead-letter-queue`, no hay DLQ aunque exista el tópico.

**Avro roto no pasa por el `@Incoming`.** Hay que ver **las dos** piezas:

1. `fail-on-deserialization-failure=true` (para que el fallo se reporte y el strategy corra), y/o
2. `value-deserialization-failure-handler=<nombre>` + un `@Identifier("…")` `DeserializationFailureHandler` que preserve los **bytes originales**

Y el serializer del DLQ **explícito**. Con Confluent Avro, a partir de Quarkus 3.5 el default no copia bien el serializer: el value en el DLQ queda `null` si no ponen

```
mp.messaging.incoming.source.dead-letter-queue.value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
```

Si el record ni siquiera es Avro válido, el serializer Avro del DLQ **también falla**. En ese caso el DLQ tiene que ser `byte[]` / envelope JSON con el payload crudo. Un DLQ “Avro del mismo subject” no puede guardar el poison pill.

El incoming del source **no** se suscribe al tópico DLQ.

## 4. Unificado + encriptado: mismo ack

Camino OK:

- map source Avro → record canónico (clase generada, otro `.avsc`)
- produce al channel `unified`
- produce al channel `encrypted` (otro topic, otro subject, otro serializer/config)
- el incoming se **ack** solo cuando **ambos** outgoing confirmaron

Si usan dos `Emitter.send` sueltos y ackean el incoming al terminar el método, el offset avanza aunque el encriptado haya fallado. Lo correcto en Mutiny es combinar las dos `Uni` (`Uni.combine().all()`) y `nack` si encrypt o unified fallan.

Encriptado, visible en código:

- CSFLE/CSPE en el serde de Confluent, **o** encrypt en el processor (`map` / método) antes del `Emitter`
- allowlist de campos; KEK / key id en config, no hardcoded
- encrypt fail → `nack` (DLQ), **nunca** plaintext al tópico encriptado
- logs sin campos sensibles

Quarkus Kafka **no** es EOS de Kafka Streams. `enable.idempotence=true` + `acks=all` en los outgoing reduce duplicados; no une unificado y encriptado en una transacción. Si prometen “los dos o ninguno”, tiene que estar el combine de acks (o un outbox). Si no, documentar at-least-once e idempotencia por key.

## 5. `application.properties` que no puede faltar

| Clave | Por qué |
| --- | --- |
| `kafka.bootstrap.servers` (o por channel) | Dedicated |
| `security.protocol` / `sasl.jaas.config` | Dedicated |
| `group.id` del incoming | consumer group |
| `auto.offset.reset` | solo primer arranque de ese group |
| `failure-strategy` + `dead-letter-queue.topic` | si no, default `fail` |
| `dead-letter-queue.value.serializer` | bug/hueco Avro Confluent |
| `value-deserialization-failure-handler` o `fail-on-deserialization-failure` | poison Avro |
| SR URL + auth en in y en **cada** out | |
| `acks=all` en outgoing | |

`application.id` de Streams **no aplica**. Si aparece `quarkus-kafka-streams` además de messaging, son dos stacks: hay que decir cuál mueve los 3 tópicos.

## 6. Lo que no debería estar

- `KafkaProducer` / `KafkaConsumer` crudos al lado de los channels “porque el DLQ es especial”
- `catch (Exception e) { log; return; }` sin `nack` → offset se commitea, record perdido, DLQ vacío
- un solo `@Outgoing` y el encriptado “después en otro micro”
- DLQ con el mismo Avro Specific que el source y sin handler de deserialize
- `quarkus-apicurio-registry-avro` apuntando a Confluent Cloud sin el serde Confluent
- tópico encriptado = unificado con un boolean `encrypted`

## 7. Pruebas Quarkus (no TopologyTestDriver)

`@QuarkusTest` + Kafka companion / channels inyectados:

1. Avro válido → 1 en unificado **y** 1 en encriptado; DLQ vacío.
2. Bytes que no son Avro → 1 en DLQ con payload original (`dead-letter-*` o envelope); unificado y encriptado vacíos.
3. Avro válido, validación KO → `nack` → DLQ de negocio.
4. Encrypt down → nack; **no** plaintext en encriptado; unificado no queda huérfano (o queda documentado).
5. Ciphertext ≠ payload del unificado.

## 8. Preguntas al código

1. ¿`failure-strategy` es `dead-letter-queue` o sigue el default `fail`?
2. ¿El serializer del DLQ está puesto a mano? ¿El DLQ acepta `byte[]` cuando Avro no parsea?
3. ¿Hay `DeserializationFailureHandler`?
4. ¿Los dos outgoing se combinan antes del ack del incoming?
5. ¿CSFLE en el serde o encrypt en el bean?
6. ¿`quarkus-confluent-registry-avro` o Apicurio contra Confluent?
7. ¿Quién reprocessa el DLQ?
8. ¿Schema Registry por Internet? (Dedicated Private Link: el cluster es privado; SR suele seguir público salvo SR privado.)

Fuentes: [Quarkus Kafka](https://quarkus.io/guides/kafka) (`failure-strategy`, headers `dead-letter-*`), [Quarkus Avro + Schema Registry](https://quarkus.io/guides/kafka-schema-registry-avro), [SmallRye Avro / Confluent](https://smallrye.io/smallrye-reactive-messaging/latest/kafka/avro-configuration/), [Quarkus #38284](https://github.com/quarkusio/quarkus/issues/38284) (DLQ Avro value `null` si no se fija el serializer).
