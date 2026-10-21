# Sabores de Azure Databricks y qué puede reemplazar Flink en Confluent Cloud

Parte del paquete [kafka-flink-lakehouse](README.md). El mapa de caminos Kafka → lakehouse está en [02-kafka-hacia-lakehouse.md](02-kafka-hacia-lakehouse.md).

Contexto del Banco: más de 20.000 procesos Databricks, en distintos sabores sobre Azure. Según Data, solo ~5% tiene como origen tópicos Kafka en Confluent Cloud Dedicated.

Este archivo no usa el inventario de esos 20.000 procesos (no está en este repo). Se basa en la documentación pública de Azure Databricks y Confluent Cloud, y en el caso BADI ($6k → $2k, −60%).

Consultado el 14 de octubre de 2026.

---

## 1. Los sabores de Databricks en Azure

No hay un Databricks único. Un “sabor” es la combinación de **qué compute corre** y **para qué se usa**. Microsoft los separa así:

- [Choose compute](https://learn.microsoft.com/en-us/azure/databricks/compute/choose-compute)
- [SQL warehouse types](https://learn.microsoft.com/en-us/azure/databricks/compute/sql-warehouse/warehouse-types)
- [Compute for jobs](https://learn.microsoft.com/en-us/azure/databricks/jobs/compute)
- [Streaming on serverless](https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/streaming)
- [Serverless vs classic pipelines](https://learn.microsoft.com/en-us/azure/databricks/ldp/concepts/serverless-vs-classic-compute)

| Sabor | Qué es | Típico en un banco |
|---|---|---|
| **Jobs Compute (classic)** | Clusters que se levantan para un job y se apagan. El más barato para lotes. | La masa de los 20.000: ETL nocturno, conciliaciones, cargas a lakehouse. |
| **All-purpose Compute** | Clusters interactivos, notebooks, ciencia de datos. Caro si se deja encendido. | Exploración, modelos, desarrollo. |
| **Serverless Jobs / Pipelines** | Databricks opera el compute. Arranque rápido, sin dimensionar VMs. | Jobs modernos, Lakeflow / DLT. |
| **SQL Warehouse** (Serverless, Pro, Classic) | Motor SQL/BI. No es Spark de jobs. | Dashboards, ad-hoc, Power BI, analítica. |
| **Lakeflow / DLT** (classic o serverless) | Pipelines declarativos (batch o streaming). | Ingesta incremental, medallion, CDC. |
| **Structured Streaming en Jobs** | Spark Streaming sobre un job. En serverless solo `Trigger.AvailableNow` (micro-lote programado). Continuo = pipeline Lakeflow en modo continuous. | Consumo de Kafka, archivos, Event Hubs. |
| **Photon** | Motor vectorizado encima de Jobs/SQL. Cobra más DBU; a veces baja el costo total. | SQL y ETL pesado. |

El **tier Standard de Azure Databricks se retira el 1 de octubre de 2026**. Los workspaces nuevos ya van a Premium ([Azure Databricks pricing](https://azure.microsoft.com/en-us/pricing/details/databricks/)). Eso sube DBU, no cambia el sabor.

Un proceso “Databricks” en el inventario casi nunca es “todo Databricks”. Es un job de Spark, un notebook, un SQL warehouse, un pipeline DLT o un stream. Mezclarlos da la cifra de 20.000 y diluye el 5%.

---

## 2. Qué sí puede reemplazar Flink en Confluent Cloud

Flink en Confluent Cloud **no reemplaza Databricks**. Reemplaza el **cómputo de streaming** cuando origen y destino ya son tópicos Kafka del cluster Dedicated.

### Candidatos claros (el ~5%)

1. Jobs Spark Structured Streaming que leen Kafka Dedicated y escriben Kafka Dedicated (el caso BADI).
2. Pipelines Lakeflow/DLT continuos con source y sink Kafka.
3. Jobs batch frecuentes (cada 1–15 min) cuyo único I/O es Kafka: en la práctica son streaming disfrazado de lote, como BADI.

### No son candidatos, aunque el job “toque” Kafka

- SQL Warehouse y BI.
- Notebooks / all-purpose / data science.
- ETL a Delta, ADLS, Synapse, SQL Server, cores del Banco.
- DLT cuyo sink es lakehouse.
- ML, Feature Store, Unity Catalog como producto.
- Streams desde Event Hubs, Event Grid, archivos, JDBC o CDC de bases, no de Confluent Dedicated.

**Regla:** si el dato tiene que vivir en el lakehouse, se queda en Databricks. Si el dato ya vive en Kafka Dedicated y debe seguir ahí, Flink gana.

### Sobre 20.000 procesos

- ~19.000 (95%) no aplican.
- ~1.000 (5%) merecen inventario fino: origen Kafka Dedicated, destino Kafka Dedicated, latencia, estado, ventanas, joins, UDFs.
- De esos 1.000, solo una parte se parece a BADI. El resto puede ser “lee Kafka y escribe Delta”: eso **no** se mueve a Flink.

---

## 3. Diferencia de costos

No se puede extrapolar el 60% de BADI a los 20.000. Ese ahorro sale de **sacar el dato de Kafka, procesarlo fuera y devolverlo**.

### Databricks (Azure, list price Premium, 2026, orientativo)

Fuentes: [Azure Databricks pricing](https://azure.microsoft.com/en-us/pricing/details/databricks/), resúmenes de list price 2026 (Premium / East US). El contrato del Banco puede diferir.

| Compute | List price aproximado | Nota |
|---|---|---|
| Jobs classic | USD 0.30 / DBU-hora | Suma la **VM de Azure** (a menudo otro tanto). |
| Serverless jobs / pipelines | USD 0.45 / DBU-hora | VM incluida. |
| All-purpose | USD 0.55 / DBU-hora | Más VM. |
| SQL Serverless | USD 0.70 / DBU-hora | BI, no jobs. |

Un job que “cuesta $6k” no son 6.000 DBU. Es DBU + VM + (si consume Dedicated) **egress de Kafka** hacia Azure Databricks + ingress de vuelta. En Dedicated el egress es caro; ese ida y vuelta suele ser el costo invisible.

### Flink en Confluent Cloud (list price público)

Fuente: [Billing on Confluent Cloud for Apache Flink](https://docs.confluent.io/cloud/current/flink/concepts/flink-billing.html).

- **USD 0.21 / CFU-hora**, cobrado por minuto (mínimo 1 CFU-minuto por statement).
- El compute pool escala a cero si no hay statements.
- **No hay cargo de red extra de Flink** por leer/escribir Kafka del mismo cloud. Siguen los cargos normales de Kafka (CKU, storage, ingress/egress). Como Flink corre junto al cluster, **no se paga el egress hacia Databricks**.

### Comparación

| Concepto | Databricks job sobre Kafka Dedicated | Flink SQL en el mismo Dedicated |
|---|---|---|
| Compute | DBU + VM, o serverless DBU | CFU por minuto |
| Red | Egress Kafka → Azure + ingress de vuelta | Sin hop extra |
| Idle | Cluster mínimo o serverless mínimo por run | 0 si no hay statement |
| Orquestación | Data Factory / Jobs scheduler | El statement es continuo |
| List price compute | ~0.30–0.45 USD/unidad-hora + VM | 0.21 USD/CFU-hora |

### El caso BADI

- Antes: ~USD 6.000/mes (Databricks + orquestación + tránsito).
- Ahora: ~USD 2.000/mes.
- Ahorro: **−60%**.
- PEVE se lleva el **25%** de esa eficiencia.

Encaja con “apagamos compute Databricks + Data Factory + el peaje de red, y dejamos un statement Flink que cobra solo mientras procesa”. El 25% de PEVE es la porción de esa eficiencia que captura el equipo, no un segundo 60%.

### Sobre el 5% (~1.000 procesos)

- Si 50 se parecen a BADI (Kafka → Kafka, hoy en Jobs + ADF), el techo teórico es del orden de **50 × USD 4.000/mes ≈ USD 200.000/mes**. No es el 60% de toda la factura Databricks.
- Si la mayoría del 5% es “Kafka → Delta”, Flink no baja esa factura; como mucho se gana un Flink intermedio y **se suma** costo, porque Databricks sigue escribiendo el lakehouse.

---

## 4. Shift-left: no migrar el lakehouse, adelantar el procesamiento

La tesis de BADI (Kafka → Kafka) no escala a 20.000 jobs. La tesis que sí escala es **shift-left**: hacer en Flink, sobre el tópico, el trabajo que hoy ocurre *después* de que el dato ya salió de Kafka hacia Databricks u otro destino.

No se “mueve Databricks a Flink”. Se **deja de llevar crudo al lakehouse** cuando el crudo todavía se puede curar, enriquecer o decidir en el stream.

```
Hoy (shift-right)
  productor → tópico crudo → [egress] → Databricks (limpia, join, agrega, decide)
                                    ↘ Delta / SQL / BI
                                    ↘ a veces de vuelta a Kafka

Shift-left
  productor → tópico crudo → Flink en Confluent Cloud
                                ├─ tópico curado / enriquecido / decisión
                                ├─ tópico de excepciones
                                └─ sink al lakehouse (Connect, Tableflow o job Databricks delgado)
                                         ↘ Delta / SQL / BI
```

Databricks no desaparece. Deja de ser el primer motor del evento y pasa a ser el **sistema de registro analítico**: history, ad-hoc, modelos, cumplimiento de retención. Flink se queda con lo que tiene que ocurrir **antes** de persistir.

### Qué se corre a la izquierda (en el tópico)

Solo tiene sentido si el origen ya está (o puede estar) en Kafka Dedicated.

| Trabajo | Por qué a la izquierda | Ejemplo de banco |
|---|---|---|
| Validar contrato y Schema Registry | Un evento inválido no debe entrar al lakehouse ni a un core | Rechazar payload sin `accountId` |
| Deduplicar / idempotencia | Evita inflar Delta y reconciliaciones nocturnas | Mismo `eventId` dos veces |
| Enriquecer con tablas chicas / lookups | El join cabe en estado de Flink; no hace falta un job Spark | Catálogo de producto, sucursal, moneda |
| Filtrar y ruteo | Cada consumidor recibe solo lo suyo | Fraude vs. extracto vs. analítica |
| Agregar ventanas cortas | Segundos o minutos, no el lote de las 02:00 | Totales intradía, alertas, límites |
| Decisión operacional | El resultado debe volver a un tópico, no a un parquet | Aprobar / rechazar / score en caliente |
| PII y clasificación | Enmascarar *antes* de que salga de la plataforma de streaming | Tokenizar documento, cortar PAN |

Criterio: **si el resultado se consume como evento** (otro tópico, API, alerta, core), es shift-left. **Si el resultado se consume como tabla histórica**, se queda a la derecha.

### Qué se queda a la derecha (Databricks / lakehouse)

- Historia larga, reprocesos, “as of” y auditorías de años.
- Joins pesados contra el lakehouse completo (no contra un lookup de Flink).
- SQL Warehouse, dashboards, ciencia de datos, Feature Store.
- Compaction, OPTIMIZE, liquid clustering, gobernanza Unity Catalog.
- Destinos que no son Kafka: ADLS, Synapse, SQL, archivos regulatorios.

Un job “Kafka → Delta” **no se migra**. Se parte:

1. Flink lee el tópico crudo y escribe un tópico **curado** (y otro de excepciones).
2. Un sink único (Connect, Tableflow o un job Databricks delgado) materializa el curado en Delta.
3. Los 20 jobs Spark que hoy limpian el mismo crudo, cada uno a su manera, **dejan de existir** o se vuelven lecturas del curado.

Eso no reduce 20.000 a Flink. Reduce **N limpiezas duplicadas** a **1 contrato de stream**. Databricks sigue, pero más barato y más simple.

### Cómo se aplica, en la práctica

1. **Inventario por tópico, no por job.** De los ~1.000 procesos con origen Kafka, agrupar por tópico de entrada. El candidato no es “el job 4821”; es `payments.posted` y todo lo que lo consume.
2. **Definir el contrato curado.** Schema Registry + tópico `*.curated` + tópico `*.dlq`. Esas reglas salen de Databricks (notebooks, DLT, jobs) y se escriben una vez en Flink SQL.
3. **Un sink al lakehouse.** Tableflow, Kafka Connect o un único Structured Streaming. Deja de haber un cluster Spark por consumidor.
4. **Consumidores operacionales leen Kafka, no Delta.** Si BADI, un autorizador o un motor de alertas necesita el dato en segundos, no espera el job de las 02:00.
5. **Databricks lee el curado.** Los SQL warehouses y los modelos no cambian de producto; cambian de *input*. Siguen siendo Databricks.

BADI fue el caso extremo: origen y destino Kafka, Databricks sobraba. Shift-left cubre el caso común: origen Kafka, destino lakehouse u otro sistema, **Databricks sigue pero más tarde y con menos trabajo**.

### Costo: no es el 60% de los 20.000

Shift-left no apaga Databricks. Cambia *cuánto* Spark hace sobre el mismo evento.

| Palanca | Qué baja | Qué aparece |
|---|---|---|
| Egress Dedicated → Azure | El crudo ya no sale N veces | CFU de Flink (continuo, por minuto) |
| Jobs Spark de limpieza / dedup / filtro | DBU + VM + Data Factory | Un statement (o pocos) por tópico |
| Reprocesos por dato sucio en Delta | Menos OPTIMIZE, menos jobs de calidad | Tópico DLQ + alerta |
| Lakehouse | Sigue | Un sink, no N pipelines |

El 60% de BADI es el techo del patrón Kafka → Kafka. En Kafka → lakehouse el ahorro es **el cómputo Spark que ya no limpia crudo** más **el egress que ya no se paga N veces**, menos el CFU y el sink. Puede ser material en un tópico caliente y casi nulo en un job mensual que lee un snapshot.

El 5% sigue siendo el universo. Shift-left no abre el 95% (archivos, JDBC, cores, BI). Abre, dentro del 5%, los procesos que **hoy no son reemplazables** porque el destino no es Kafka: no se migran; se adelantan.

### Cómo contarlo

1. Databricks en el Banco es **lakehouse, SQL y lotes**. Flink en Confluent es **procesamiento de eventos donde ya viven**.
2. Solo ~**5%** de los 20.000 procesos nace en Kafka Dedicated. Ahí está Flink, no en el resto.
3. Hay dos movimientos, no uno:
   - **Reemplazo** (BADI): Kafka → Kafka. Databricks sale. −60% en ese job.
   - **Shift-left**: Kafka → Flink (contrato curado) → lakehouse / otros. Databricks se queda a la derecha, más flaco.
4. El resto de Databricks **no** se vende como el mismo ahorro. Lo que se vende es: **el dato se cura una vez, en el tópico, antes de salir.**

---

## Fuentes

- Microsoft Learn, Azure Databricks: choose compute, SQL warehouse types, jobs compute, serverless streaming, serverless vs classic pipelines.
- [Azure Databricks pricing](https://azure.microsoft.com/en-us/pricing/details/databricks/)
- [Confluent Cloud Flink billing](https://docs.confluent.io/cloud/current/flink/concepts/flink-billing.html)
- Caso BADI: costos mensuales de producción (mayo–julio) y resultado de la migración a FlinkSQL serverless.
