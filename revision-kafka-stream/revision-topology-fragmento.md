# Revisión: `TopologyApplicationService.buildTopology()` (fragmento)

Es **Kafka Streams** (`StreamsBuilder` / `split` / `to`), no SmallRye `@Incoming`. En Quarkus eso es `quarkus-kafka-streams`.

```
APSY_PROCESSED_TOPIC (Avro VirtualAccountMovement)
    → process(EventWithHeaders)
    → mapValues(ProcessEntityHash)          // encrypt/hash
    → selectKey(account del encrypted)
    → split(flag)
         success  → APSY_PROCESSED_ENCRYPTED_TOPIC
         rejected → (no se ve en el fragmento)
    → tópico unificado: no aparece
```

## Bug: el camino DLQ se cae antes del `split`

En el `catch` devuelven `WrapperMessageHash(encrypted=null, original, flag=false)`.

Inmediatamente después:

```java
.selectKey((key, value) -> value.virtualAccountMovementEncrypted().getAccountNumber())
```

Si `encrypted` es `null`, esto es **NPE**. El record no llega a `rejected`, no llega a ningún `.to(DLQ)`, el stream thread falla. El log dice “enviando a DLQ” pero el código no envía: solo arma un wrapper y después lo rompe.

El `.peek(Util.logEncryptedAccountMovement(...))` está **antes** del `split`: también corre en el camino `flag=false`.

**Orden correcto:** `split` primero (o `selectKey` solo en la rama `success`). En `rejected`, key original + payload original.

## Lo que sí está

- Consume Avro tipado: `Consumed.with(Serdes.String(), virtualAccountMovementSerde)`.
- Serde de encrypted y de source configurados (`configure(..., false)`).
- Encrypt/hash en processor (`ProcessEntityHash(hashService, hashKey)`).
- `split` por `flag`: intentan separar OK vs KO.
- Sink del encriptado: `to(APSY_PROCESSED_ENCRYPTED_TOPIC)`.

## Lo que no está (en este recorte)

| Esperado | En el fragmento |
| --- | --- |
| `.to(DLQ)` en `split_virtualAccountMovements-rejected` | No se ve |
| Produce al tópico **unificado** | No se ve |
| `Produced.with(...)` en el `to` | Cortado; hay que ver el serde del sink |
| `DeserializationExceptionHandler` / consume `byte[]` | No. Avro roto no entra al `mapValues` |
| Headers de fallo en el DLQ (`exception`, offset, topic) | El wrapper solo lleva `flag=false` + original |
| Tests de NPE en encrypt fail | — |

## Otros riesgos

1. **Log del catch** imprime el `value` completo (`VirtualAccountMovement` en claro). PII en logs.
2. **`selectKey` a account number** re-particiona. El DLQ y el encriptado ya no alinean partition/offset con el source. Si el unificado usa otra key, los tres sinks no correlacionan.
3. **`EventWithHeaders`** si lanza, no hay `catch` (el try solo cubre el `mapValues`).
4. **Hash vs encrypt:** el log dice “with hashing”. Confirmar que el tópico `*_ENCRYPTED_*` no es solo hash irreversible si el consumidor necesita descifrar.
5. Quarkus Messaging (`failure-strategy=dead-letter-queue`) **no aplica** a esta topology.

## Qué pedir del resto del archivo

1. `branches.get("split_virtualAccountMovements-rejected").to(...)`
2. El `to` del tópico unificado (mismo record OK, no un segundo consume).
3. `application.properties` de `quarkus.kafka-streams.*` (EOS, exception handlers, SR).
4. `WrapperMessageHash`, `ProcessEntityHash`, `EventWithHeaders`.
5. Qué pasa si `getAccountNumber()` es null en un OK.
