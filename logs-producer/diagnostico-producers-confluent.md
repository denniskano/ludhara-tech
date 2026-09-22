# Diagnóstico: WARN de producers Kafka Streams hacia Confluent Cloud Dedicated

**APSY · 9 de septiembre de 2026 · Uso interno**  
Fuentes: `log-01.log`, `log-02.log`. Nivel observado: WARN.  
Clúster: Confluent Cloud Dedicated `lkc-8p0ror`, Azure eastus2 (Private Link).  
Durante el incidente **no se observaron rebalances** en el Dedicated.

---

## Conclusión

No es un fallo de tópico, partición, ACL, tamaño de mensaje ni serialización. En una ventana de aproximadamente un minuto, varios producers internos de **Kafka Streams (transaccionales)** perdieron la conexión con **varios brokers a la vez** (`NETWORK_EXCEPTION` / `Disconnected from node`). El cliente **reintentó** el produce.

La ausencia de rebalances indica que no hubo reorganización de membresía ni, en lo observado, cambio generalizado de líderes. Los StreamThread siguieron vivos. El incidente es de **conectividad en el produce**, no de reorganización del clúster.

En estos extractos **no hay ERROR** ni agotamiento de reintentos. **No queda demostrada la pérdida de mensajes.**

---

## Origen de los logs

| | log-01 | log-02 |
|---|---|---|
| Servicio | `cloud-virtual-account-movements-encrypted-v1` | `cloud-account-movements-v1` |
| Namespace | apsy | apsy |
| Runtime | Quarkus, Java 17 | Quarkus, Java 17 |
| ClientId | `cloud-apsy-virtual-account-movements-encrypted-cg-{uuid}-StreamThread-1-producer` | `cloud-apsy-account-movements-cg-group-{uuid}-StreamThread-1-producer` |
| Instancias distintas (uuid) | 10 | ~17 |
| Líneas de incidente | 42 | 92 |

Son producers **internos de Kafka Streams** (`StreamThread-1-producer` y `transactionalId`). No un `KafkaProducer` suelto de aplicación.

**Tópicos sink afectados**

- `azc-apsy-virtual-account-movements-encrypted`
- `azc-apsy-unified-account-movements-encrypted`
- `azc-apsy-account-movements`
- `azc-apsy-account-movements-encrypted`

Las particiones van de 0 a ~31. El corte no se concentra en una partición.

**Broker citado en el fallo de autenticación (log-02):**  
`lkc-8p0ror-g003.az1.domjg56my4p.eastus2.azure.confluent.cloud` → `10.175.103.228:9092` (node 3).

---

## Cronología (UTC)

| Hora | Qué se ve |
|---|---|
| 16:38:05–06 | Solo log-02. `AdminClient` de Streams: conexión al node 3 **terminada durante autenticación TLS**. El propio cliente lista credenciales inválidas, firewall que no permite Kafka/TLS, o red transitoria. |
| 16:38–16:52 | Sin líneas en el extracto. |
| 16:52:36–16:52:46 | Primera ráfaga de `Disconnected` (pico en log-02 a las 16:52:36). |
| 16:53:21–16:53:30 | Segunda ráfaga, unos 35 segundos después (reconexión, refresh de metadata y nuevo produce, o segundo corte). |

**Brokers en el disconnect:** 0, 3, 6 y 9.  
Dos aplicaciones, muchas particiones, cuatro brokers, mismos segundos: evento de **ruta de red o del Dedicated**, no de un tópico.

**Conteos**

- log-01: 21 `NETWORK_EXCEPTION` (pares produce-retry + invalid metadata). Nodos: 9 (18), 6 (10), 0 (8), 3 (6).
- log-02: 45 `NETWORK_EXCEPTION` y 2 cortes de autenticación en AdminClient. Nodos: 6 (42), 3 (24), 0 (16), 9 (8).

---

## Interpretación de los WARN

Cada incidente de produce aparece en par:

1. `Got error produce response … Error: NETWORK_EXCEPTION … retrying (2147483646 attempts left). Error Message: Disconnected from node N`
2. `Received invalid metadata error in produce request … Going to request metadata update now`

El socket con el broker se cortó con un Produce in-flight. El cliente invalida metadata, la vuelve a pedir y **reintenta el batch**.

`2147483646` es `Integer.MAX_VALUE - 1`: `retries` efectivo ilimitado, habitual en Streams. El WARN documenta el **intento fallido**, no el abandono del registro.

**No aparece en el extracto**

- `EXPIRED` / `TimeoutException` / vencimiento de `delivery.timeout.ms`
- `OutOfOrderSequence` / `InvalidProducerEpoch` / `TransactionalIdAuthorization`
- `NOT_LEADER_OR_FOLLOWER` / `UNKNOWN_TOPIC_OR_PARTITION`
- `MESSAGE_TOO_LARGE` / `RECORD_LIST_TOO_LARGE`

No hay evidencia aquí de ACL, tópico inexistente, payload excesivo ni de que se agotara el reintento.

---

## Ausencia de rebalances

Confirmado por operación: **durante el incidente no hubo rebalances** en el Dedicated.

Implicación:

- Un `NETWORK_EXCEPTION` en el producer **no exige** rebalance. El rebalance es de membresía de consumer group o de tareas de Streams.
- Si los StreamThread no mueren y el heartbeat del consumer sigue, el group no se reorganiza.
- Encaja con logs solo WARN de `Sender`, sin ERROR de `StreamThread` / `task died`.
- Debilita la hipótesis de rolling de brokers con elección de líder generalizada o tormenta de consumer groups.
- No descarta un microcorte de Private Link, NLB o proxy: los líderes pueden no cambiar y el producer reconecta al **mismo** broker.

Lectura operativa: incidente de **conectividad en el produce**, recuperado antes de `session.timeout.ms`, no de reorganización del clúster.

---

## Causa más probable

Corte breve en la ruta hacia el Dedicated (Private Link, balanceador, idle/reset en 9092, blip TLS) que afectó sockets de produce contra varios brokers.

Candidatos a contrastar en la misma ventana (16:38 y 16:52–16:53 UTC):

- Evento de red o proxy del Dedicated / Private Link (sin reasignación de particiones).
- Idle timeout o reset en NLB / firewall (Kafka en 9092, no HTTPS).
- Rotación o rechazo de credenciales (el mensaje de 16:38 menciona autenticación).
- Saturación o cierre de conexiones (muchos Streams y un `transactionalId` por tarea).

**Descartable como causa primera con estos datos:** partición concreta, un solo producer mal configurado, rebalance del clúster, o un problema aislado de un tópico.

---

## Riesgo de negocio (Streams + transacciones)

Si el produce forma parte del commit transaccional de Streams:

- Sin ack del broker la transacción no confirma.
- Streams reprocesa el input. Con EOS correcto no debería duplicar el sink; sí puede haber latencia.
- Si algún sink se escribe **fuera** de la transacción, el reintento sí puede duplicar.

Hay que confirmar en código si esos tópicos están en la topología transaccional o hay un producer aparte.

---

## Límites de este extracto

Solo hay WARN de `Sender` y un `AdminClient`. No se ve si el retry **terminó bien**.

Para cerrar pérdida frente a ruido, en la misma ventana hace falta:

- ERROR de `Sender`, `TransactionManager` o `StreamThread`
- `Failed to send`, `Aborting transaction`, `task died`
- Métricas Confluent: produce failed, conexiones, Private Link
- En la app: `record-retry-rate`, `record-error-rate`, `commit-latency` de esos `clientId`

No corresponde “purgar” tópicos por este incidente: el cliente ya reintenta. Un avance de offset sería de **consumo**, no de este produce.

---

## Acciones

1. Contrastar con Confluent y Azure (Private Link / NSG / 9092) las ventanas 16:38 y 16:52–16:53 UTC en `lkc-8p0ror`.
2. Completar la evidencia con ERROR de Streams y `record-error-rate`.
3. Confirmar si los sinks van dentro de la transacción de Streams.
4. No tratarlo como incidente de rebalance ni como fallo de un tópico.

---

## Frase para reporte

Corte de conectividad en el produce hacia brokers del Dedicated (Private Link, eastus2) entre las 16:52 y 16:53 UTC; Kafka Streams reintentó; no hubo rebalances; con este extracto no se demuestra mensaje perdido ni reorganización del clúster.
