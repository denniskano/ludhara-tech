# Revisión: config del MS (Quarkus Kafka Streams)

`processing.guarantee: exactly_once_v2` confirma el ERROR. El fencing es de esta garantía. La config **no** define los tiempos que evitan que el coordinator aborte la transacción.

## application-id ≠ el del log

| Dónde | Valor |
| --- | --- |
| Config | `cloud-apsy-virtual-account-movements-encrypted-cg` |
| ERROR 18-oct | `cloud-apsy-account-movements-cg-group` |

O son **dos** apps, o el log es de otro deploy/nombre. El group que hay que mirar en Dedicated es el que salga en el thread del ERROR, no solo el del yaml actual.

`quarkus.kafka-streams.topics: azc-apsy-virtual-account-movements` — Quarkus solo espera el **source** al arrancar. No lista encrypted, unified, DLQ ni el repartition que crea el `selectKey`. No causa el epoch; sí deja el health incompleto.

## Lo que está y empuja el fencing

```yaml
kafka-streams:
  consumer.max.poll.records: 500
  producer.linger.ms: 0
  producer.batch.size: 10240
  processing.guarantee: exactly_once_v2
# no hay transaction.timeout.ms
# no hay max.poll.interval.ms
# no hay commit.interval.ms
```

Más, en el mismo MS:

```yaml
singlecrypto.hash:
  master-key-name: ${azure.keyvault.hash.master.key.name}
  wrapped-key-name: ${azure.keyvault.hash.wrapped.key.name}
```

El `mapValues(ProcessEntityHash)` llama **Azure Key Vault por record** (y Schema Registry en el serde). Eso es I/O síncrono en el StreamThread.

Con EOS, Streams deja `commit.interval.ms = 100` (no lo pongan a 30s). `transaction.timeout.ms` si no se setea queda en el default de Streams (~**10 s**, no los 60 s del producer suelto).

500 records × RTT a Key Vault. Si KV está a 30–80 ms, un poll son 15–40 s de CPU bloqueada **sin poll/heartbeat útil**. Eso supera 10 s de transacción → el coordinator hace rollback → epoch nuevo → el produce al tópico encriptado sale exactamente:

`InvalidProducerEpochException: Producer attempted to produce with an old epoch`

Si además hay corte Private Link (el caso de octubre), el mismo hilo no heartbeatea → rebalance → tres pods se pelean `0_0` / `0_5` / `0_7`.

`linger.ms: 0` + `batch.size: 10 KB` + EOS = muchos produce chicos dentro de la transacción (source → repartition del `selectKey` → encrypted → unified). Más RPCs al Dedicated, más superficie para coger un epoch viejo a mitad de batch.

## Lo que no está (y debería)

| Clave | Por qué |
| --- | --- |
| `transaction.timeout.ms` | Tiene que ser **>** peor ventana hash+SR+produce. Empezar 120000; `max.poll.interval.ms` ≥ ese valor |
| `consumer.max.poll.interval.ms` | Default 300000. Bajar records o subir esto si KV se pone lento |
| `consumer.max.poll.records` | 500 es alto con KV síncrono. 25–50 |
| `num.standby.replicas` | 1 reduce restore después de cada fence (en client Streams clásico) |
| `replication.factor: 3` | changelog / repartition en Dedicated |
| Exception handlers | deserialize / production; StreamsUncaught → `REPLACE_THREAD` |
| `request.timeout.ms` / reconnect backoff | Dedicated + Private Link |

No setear `commit.interval.ms` a 30000 con EOS: Streams lo pone en 100 ms a propósito.

No apagar `exactly_once_v2` para “quitar el ERROR” si unificado y encriptado deben nacer juntos.

## Health + probes

`quarkus.kafka-streams.health.enabled: true`. Si el probe de K8s pega durante restore/rebalance y mata el pod, **fabrican** el siguiente fence. El readiness no puede exigir RUNNING en medio de un rebalance.

## Ajuste mínimo (mismo EOS)

```yaml
kafka-streams:
  processing:
    guarantee: exactly_once_v2
  transaction:
    timeout:
      ms: 120000
  consumer:
    max:
      poll:
        records: 50
        interval:
          ms: 180000
  producer:
    linger:
      ms: 10
    batch:
      size: 32768
  # opcional, changelog / repartition
  replication:
    factor: 3
  num:
    standby:
      replicas: 1
```

Bajar `max.poll.records` suele valer más que solo subir el timeout: cada transacción termina antes.

Cachear/envolver la key de Key Vault **fuera** del record (el yaml ya tiene master + wrapped: si `ProcessEntityHash` pide unwrap **por mensaje**, eso es el cuello). Unwrap una vez al arrancar; en el `mapValues` solo HMAC/encrypt local.

## Cómo cruzar con el ERROR del 18-oct

1. ¿El `application-id` del pod que logueó es este yaml o `…-cg-group`?
2. En brokers, misma ventana: `rollback of ongoing transaction … due to timeout` → timeout de TX, no solo rebalance.
3. Latencia p99 de Key Vault y de produce 9092 (Private Link) vs 10 s.
4. Members del consumer group: si hay 3 pods y N particiones, cada fence mueve tasks como en el log.

El yaml no está “mal” por usar EOS. Está incompleto para un processor que sale a Key Vault y a Dedicated por Private Link.
