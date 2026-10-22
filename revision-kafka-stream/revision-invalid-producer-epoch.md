# El ERROR: `InvalidProducerEpochException`

2026-10-18 ~08:47 UTC. Tres instancias del mismo Kafka Streams:

| StreamThread (processId) | Task | Tópico sink |
| --- | --- | --- |
| `…-abe745bf-…` | `0_5` | `azcc-apsy-unified-account-movement-encrypted` |
| `…-acaa451f-…` | `0_7` | `azcc-apsy-account-movements-encrypted` |
| `…-82d6cf2b-…` | `0_0` | (mismo patrón, recorte) |

`application.id` = `cloud-apsy-account-movements-cg-group`. Los UUID no son el group: son el **processId** de cada pod.

El texto *“Producer attempted to produce with an old epoch … producer is fenced, indicating the task may be migrated out”* lo arma Kafka Streams (`RecordCollectorImpl`): traduce `InvalidProducerEpochException` a `TaskMigratedException`. Es el fencing de **exactly-once**, no un fallo de Avro ni del `catch` del hash.

## Qué significa

Con `processing.guarantee=exactly_once` / `exactly_once_v2` cada thread tiene un producer transaccional. El broker guarda un **epoch**. Si la task se va a otro pod (rebalance, timeout, restart), el coordinator **sube el epoch**. El pod viejo intenta un produce con el epoch anterior → fenced. El offset **no** se commitea. Eso evita que el zombie escriba duplicado al sink.

Un ERROR suelto después de un rebalance es el mecanismo funcionando.

Un ERROR que se **repite** (aquí hay 15 en el recorte) es otra cosa: las tasks no se estabilizan. Se diagnostica como **rebalance**, no como “el serializer está mal”.

## Por qué encaja con esta app

1. **Varias réplicas** del mismo `application.id` (tres processId a la vez). Cualquier blip de membresía mueve `0_0` / `0_5` / `0_7`.
2. **Dedicated + Private Link.** Ya hubo `NETWORK_EXCEPTION` / TLS drop hacia brokers del mismo cluster. Un corte de 1 s basta para que expire `session.timeout` o la transacción y otro pod tome la task.
3. **`selectKey(accountNumber)`** en la topology. Eso crea un tópico de **repartition** y otro produce transaccional por record. Más trabajo en la transacción → más chance de `transaction.timeout.ms` si el hash/encrypt o el Schema Registry se atrasan.
4. El sink del ERROR es el tópico **encriptado** (y el unificado-encriptado). El produce que pierde el fencing es el `to(...)`, no el `mapValues`. El record puede reprocesarse después del restore; con EOS no debería duplicar el sink. Sí hay **hueco de latencia** y ERROR ruidoso.

## Qué no es

- No es “no llegó al DLQ”. El fencing ocurre al **enviar** al sink, después del processor.
- No se arregla poniendo otro `catch` en `ProcessEntityHash`.
- No es schema Avro inválido (sería `SerializationException` / deserialize handler).

## Cómo confirmar (logs / metrics)

En la misma ventana 08:47:

- `Revoking`, `Assignment`, `rebalance`, `TaskMigrated`
- `session timed out`, `max.poll.interval`, `Failed to heartbeat`
- En brokers / Dedicated: `Completed rollback of ongoing transaction … due to timeout`
- Cuántas instancias: `group members` de `cloud-apsy-account-movements-cg-group`
- Si después del ERROR el thread queda `RUNNING` y las tasks vuelven: transitorio. Si el thread muere y no hay `StreamsUncaughtExceptionHandler` que lo reemplace: el pod queda cojo.

Métricas: `rebalance-total`, `rebalance-latency-avg`, `commit-latency-max`, `alive-stream-threads`.

## Qué tocar (en este orden)

1. **Por qué se van las tasks.** Red (Private Link, idle 9092), deploy/rollout, probes que matan el pod, `num.stream.threads` × réplicas vs particiones del source.
2. **Tiempos.** `transaction.timeout.ms` (broker y client) **mayor** que el peor `mapValues` (hash + SR). En Streams suele alinearse con `max.poll.interval.ms` (si poll interval > transaction timeout, el coordinator aborta y fenced).
3. **No bajar `retries`.** No desactivar EOS “para que pare el ERROR” sin aceptar at-least-once en los dos tópicos encriptados.
4. **`selectKey`.** Si la key nueva no es obligatoria para el sink, quitarla evita el repartition y acorta la transacción.
5. Handler: `StreamsUncaughtExceptionHandler` → `REPLACE_THREAD` ante `TaskMigratedException` (Streams ya lo trata como migrable; verificar que el thread no quede muerto).

EOS sigue siendo lo correcto para unificado + encriptado en el **mismo** cluster. El ERROR dice que un pod intentó escribir **después** de perder la task. La pregunta operativa es por qué esa task se fue a las 08:47.
