# Plan de retiro preventivo de Temporal Cloud ante insolvencia del proveedor

**BCP / PEVE / Versión 1.4**  
Datos elaborados por BCP para uso interno.  
Documento de decisión asociado: resumen para la instancia aprobadora.

| Control | Valor |
|---|---|
| Código | PEVE-PR-2026-001 |
| Versión | 1.4 |
| Estado | Final para aprobación. La fase 0 queda pendiente de ejecución. Destino de la primera versión: Self-Hosted. Tres opciones adicionales en 04.6. |
| Clasificación | Uso interno BCP |
| Dueño | PEVE |
| Revisores | Arquitectura, Seguridad, Continuidad, RNF, Legal / Compras, PO APOQ, PO NREM |
| Aprobador | Instancia aprobadora |
| Vigencia | Hasta la siguiente revisión anual o un cambio material |
| Relacionado | Planes de continuidad y recuperación de Temporal Cloud; receta de despliegue de cada aplicación |

Los campos en cursiva de los anexos A, C, F y G se completan durante la fase 0, con la información de cada dueño.

---

## Ficha del documento

| Campo | Contenido |
|---|---|
| Servicio | Temporal Cloud (orquestación y persistencia del estado de workflows) |
| Proveedor | Temporal Technologies Inc. |
| Función | Crítica / servicio significativo de procesamiento de datos |
| Destino | Temporal Self-Hosted en Azure AKS del Banco (primera versión / vigente). Tres opciones adicionales: sección 04.6 |
| Riesgo cubierto | Insolvencia, liquidación, cese de operaciones o pérdida material de capacidad del proveedor para operar Temporal Cloud |
| Fuera de alcance | Terminación comercial o renegociación de precio. Un destino distinto a Self-Hosted (Durable Functions, Dapr Workflows o Restate) requiere aprobación formal de Arquitectura, Compras y la instancia |
| Gobierno | PEVE gobierna el plan y entrega la receta técnica. Los equipos de aplicación ejecutan y validan su migración. |
| Naturaleza | Preventivo y activable. La alternativa se prepara con anticipación y se ejecuta cuando se declara la pérdida de continuidad del proveedor o el cese del servicio. |

Temporal Cloud es operado por Temporal Technologies Inc. El servidor Temporal, con licencia MIT, puede instalarse y operarse en la infraestructura del Banco. En la primera versión del plan la orquestación se mantiene en el mismo motor. Si el paso 0.0 elige una opción de la sección 04.6, el motor cambia y hay reescritura. Los historiales y el estado de negocio quedan bajo control del BCP en todos los destinos.

Los workers ya se ejecutan en AKS del Banco. En Self-Hosted el cambio es de plano de control y conexión. En Durable Functions, Dapr Workflows o Restate el cambio incluye el modelo de programación; el cómputo puede permanecer en AKS (Dapr, Restate, Durable Task SDK) o pasar a Azure Functions.

---

## Principios

1. **Continuidad y ausencia de duplicidad.** No se admite la doble ejecución de efectos de negocio (débito, crédito, remesa o liquidación). Las activities deben ser idempotentes. Un schedule o un workflow no puede estar activo a la vez en Cloud y en el destino aprobado.
2. **Destino aprobado.** La primera versión del plan migra hacia Temporal Self-Hosted en Azure AKS. Las tres opciones adicionales de la sección 04.6 (Durable Functions, Dapr Workflows y Restate) se documentan para decisión; no se adoptan en la activación sin aprobación formal. Donde el resto del documento dice Self-Hosted como destino de la migración, léase el destino aprobado (Self-Hosted salvo acta del paso 0.0). La conexión dual, los namespaces Temporal y el Anexo B aplican solo si el destino es Self-Hosted.
3. **Preparación previa.** La plataforma objetivo, la receta, el inventario y la exportación de historiales deben existir antes de la notificación del proveedor.
4. **Dos modos de actuación.** En reorganización o venta puede existir una ventana para concluir workflows en Cloud. En liquidación o interrupción definitiva no se espera cooperación del proveedor: se conmuta al destino aprobado y se reconstruye desde el estado de negocio.
5. **Migración por ambientes.** El orden es desarrollo, certificación y producción. No hay pase productivo sin conformidad técnica, funcional y de seguridad.
6. **Responsabilidad distribuida.** PEVE estandariza y consolida. Cada aplicación inventaría, migra, concilia y conserva evidencias.
7. **Retiro de Cloud.** No se retiran configuraciones ni accesos de Cloud mientras exista estado por tratar, salvo que el servicio ya no responda. En ese caso rige el modo estresado.
8. **Evidencia.** Se conserva evidencia técnica, funcional, de continuidad, de datos, de seguridad, contractual y de riesgo.

---

## 01. Identificación y criticidad

Temporal Cloud soporta la orquestación y la persistencia del estado de workflows de aplicaciones del BCP. Al ser un servicio gestionado, su continuidad depende de la estabilidad operativa, financiera y contractual de Temporal Technologies Inc.

El retiro cubre las aplicaciones del BCP que usan o tienen previsto usar Temporal Cloud, en ambientes productivos y no productivos, hasta que no quede ninguna dependencia activa del Banco en el servicio.

**Incluye:** aplicaciones, workflows (activos, históricos, fallidos, compensados o en reproceso), namespaces, workers en AKS, endpoints, red, certificados, secretos, pipelines, observabilidad, pruebas, aprobaciones y evidencias de cierre.

**No incluye:** aplicaciones de empresas distintas a BCP; cambios funcionales que no sean necesarios para el retiro; la adopción de un destino de la sección 04.6 sin aprobación formal; la ejecución detallada de los cambios de cada aplicación, que se documenta en sus procedimientos de despliegue aplicando la receta de PEVE.

### Inventario

| Aplicación | Proceso | Ambiente | Prioridad | Tratamiento |
|---|---|---|---|---|
| APOQ | Transferencias entre cuentas: débito, crédito, compensación y recuperación ante fallos | Producción | Alta | Migración controlada al destino aprobado |
| NREM | Gestión de remesas, emisión y recepción | Producción | Alta | Migración controlada al destino aprobado |
| CPCA | Capa Producto Cuenta Ahorros del Nuevo Autorizador | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| CPCC | Capa Producto Cuenta Corriente del Nuevo Autorizador | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| APTI / TUPI | Pagos y transferencias digitales de alto volumen | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| CDPT | Capa de negocio para pagos y transferencias | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| SRCR | Tracking de pagos y renovación tecnológica | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| LBCL | Transferencias interbancarias BCR y liquidación en LBTR | Desarrollo / certificación | Antes de producción | Migrar o retirar |
| CPCR | Nuevo Core de Cuentas | Desarrollo / certificación | Antes de producción | Migrar o retirar |

APOQ y NREM pueden avanzar como frentes paralelos. No se ha identificado dependencia técnica o funcional entre ambas. Cada aplicación cumple de forma independiente la preparación, las pruebas, la aprobación y el cierre.

Las aplicaciones no productivas deben migrarse al destino aprobado antes de un eventual pase a producción. Si el dueño decide no continuar, se congelan o retiran con evidencia. No se habilitará producción nueva sobre Temporal Cloud.

**Patrón de namespaces.** Si el destino es Self-Hosted: código de aplicación en minúsculas seguido del ambiente, por ejemplo apoq-dev, apoq-cert y apoq-prod. Si el destino es 04.6 no hay namespaces Temporal; el inventario registra task hubs, aplicaciones Dapr o deployments Restate equivalentes.

**Clasificación.** APOQ y NREM son funciones críticas en producción. El resto es material por el tipo de proceso (autorizador, pagos, LBTR, core de cuentas), aunque aún no esté en producción, y no debe pasar a producción sobre Temporal Cloud mientras el proveedor esté en vigilancia.

---

## 02. Objetivos

**General.** Definir el marco técnico, operativo, contractual, de continuidad y de seguridad para retirar Temporal Cloud del BCP y migrar los casos de uso al destino vigente (Temporal Self-Hosted en Azure AKS), o a un destino de la sección 04.6 si la instancia lo aprueba, sin comprometer la continuidad de las aplicaciones productivas ni la trazabilidad de los workflows.

**Específicos**

- Mantener el inventario de aplicaciones, workflows, namespaces, workers y dependencias.
- Tener la plataforma objetivo y la receta listas antes de la activación.
- Establecer el criterio de activación y las acciones inmediatas.
- Preservar continuidad, integridad, trazabilidad y evidencia de los workflows.
- Impedir la ejecución simultánea de un mismo workflow o schedule en ambos ambientes.
- Definir controles de seguridad, accesos y cierre de credenciales.
- Establecer criterios de entrada a producción y de cierre del retiro.

---

## 03. Escenarios y supuestos

El riesgo cubierto es la pérdida de continuidad operativa del proveedor, no un incidente técnico transitorio de Temporal Cloud. Los incidentes de corta duración se tratan en los planes de continuidad y recuperación. Este plan modela tres desenlaces de insolvencia. El resultado financiero negativo del proveedor es un elemento de vigilancia, no el disparador del retiro.

| Desenlace | Situación de Temporal Cloud | Actuación del Banco | Cooperación del proveedor | Horizonte |
|---|---|---|---|---|
| Reorganización concursal | El servicio suele continuar. El contrato puede asumirse o rechazarse | Activar el plan, congelar usos nuevos en Cloud y migrar por ambientes | Limitada. No se depende de servicios profesionales del proveedor | Semanas |
| Venta o cambio de control | El servicio continúa y cambia el dueño | Misma ruta técnica. Se evalúa si el comprador es aceptable para el Banco | Media o alta | Semanas a meses |
| Liquidación o cese abrupto | El plano de control puede interrumpirse. No hay exportación ni soporte | Conmutar al destino aprobado y reabrir los casos críticos desde el estado de negocio | Nula | Horas a pocos días |

### Supuestos

- Si el destino es Self-Hosted: el servidor Temporal y los SDK permanecen disponibles como código abierto. El Banco opera el mismo motor.
- Si el destino es una opción de la sección 04.6: no hay reutilización del SDK Temporal. La fase 0 incluye reescritura y no hay conexión dual. El supuesto de “mismo motor” no aplica.
- No existe una migración oficial de Temporal Cloud hacia ningún destino de este plan. La salida se realiza en la aplicación (cambio de endpoint, o dos implementaciones del proceso), no mediante copia de la base de datos del proveedor.
- La exportación de historiales de Cloud requiere que el servicio esté disponible y se ejecuta de forma periódica. Si no se ha copiado a almacenamiento del Banco antes de la activación, el historial vivo no será recuperable.
- Temporal orquesta la ejecución. El registro de negocio reside en el core, outbox, colas y conciliaciones de APOQ y NREM. En modo estresado, la pérdida máxima de información aceptable se mide contra ese estado, no contra el historial de Cloud.
- Los workers ya se ejecutan en AKS del Banco. El payload enviado a Temporal se encuentra cifrado.
- En liquidación no hay un periodo de transición contractual efectivo.

### Exclusiones de escenario

Una caída transitoria de región, una degradación de corta duración o un incidente de seguridad del servicio se atienden con los planes de continuidad y recuperación. Si el incidente se convierte en cese material, se declara el escenario de este plan.

---

## 04. Solución alternativa y arquitectura objetivo

El destino aprobado es Temporal Self-Hosted en Azure AKS, operado por el Banco. PEVE opera el plano de control. Las aplicaciones siguen operando sus workers. No se adoptará otra plataforma en el momento de la activación, salvo acta previa del paso 0.0 sobre una opción de la sección 04.6.

Arquitectura emite conformidad del patrón. Seguridad valida autenticación, autorización, certificados, cifrado, red, registro de eventos y segregación.

### 04.1 Diagrama de la propuesta

![Arquitectura Temporal Self-Hosted en Azure AKS, BCP / PEVE](assets/arquitectura-temporal-self-hosted-aks.png)

La arquitectura se organiza en tres planos. El Frontend no se expone a internet público.

1. **Aplicación.** APOQ, NREM y las demás aplicaciones del inventario. Los workers permanecen en el AKS del Banco. El core, el outbox y las colas constituyen el registro de negocio.
2. **Plano de control Temporal (AKS PEVE).** Frontend, History, Matching y Worker Service, detrás de un balanceador interno. La consola web se usa solo para administración.
3. **Plataforma Azure privada.** Persistencia, visibilidad, archivo de historiales, secretos y monitoreo, con Private Link o red virtual privada.

```mermaid
flowchart LR
  subgraph apps["Plano de aplicación - BCP"]
    APOQ["APOQ, NREM y demás"]
    W["Workers AKS aplicación"]
    CORE["Core, outbox y colas"]
    APOQ --> W
    W --- CORE
  end

  subgraph cp["Plano de control Temporal - AKS PEVE"]
    ILB["Balanceador interno privado"]
    FE["Frontend"]
    HS["History"]
    MT["Matching"]
    WS["Worker Service"]
    UI["Consola de administración"]
    ILB --> FE
    FE --- HS
    FE --- MT
    FE --- WS
    UI -.-> FE
  end

  subgraph az["Azure privada"]
    PG["PostgreSQL persistencia"]
    VIS["Elasticsearch u OpenSearch"]
    BLOB["Blob: archivo y exportación"]
    KV["Key Vault"]
    MON["Monitor y alertas"]
  end

  W -->|"gRPC mTLS"| ILB
  HS --> PG
  MT --> PG
  FE --> VIS
  WS --> BLOB
  FE --> KV
  cp --> MON
```

### 04.2 Decisiones de diseño

| Decisión | Propuesta | Motivo |
|---|---|---|
| Ubicación del servidor Temporal | AKS dedicado de PEVE, fuera del namespace de la aplicación | Separar la operación de plataforma y la de negocio |
| Instalaciones | Dos: no productiva (desarrollo y certificación) y productiva | Aislar producción y ensayar la receta sin afectar críticos |
| Persistencia | Azure Database for PostgreSQL Flexible Server, con alta disponibilidad y respaldo | Almacén soportado por Temporal y operado en Azure |
| Visibilidad | Elasticsearch u OpenSearch en Azure | Búsqueda de workflows para operación y auditoría |
| Archivo de historiales | Azure Blob (workflows cerrados) | Conservación más allá de la retención del clúster |
| Exportación desde Cloud | Proceso periódico hacia Blob del Banco, mientras Cloud esté disponible | En la activación solo existirá lo ya copiado |
| Acceso al Frontend | Balanceador interno y Private Link, sin dirección pública | Reducir superficie de exposición y controlar residencia |
| Autenticación | mTLS o equivalente aprobado, con identidades en Key Vault | No reutilizar las credenciales de Cloud |
| Workers de aplicación | Permanecen en el AKS actual | El cambio es de conexión |
| Payload | Cifrado en tránsito y en el contenido de negocio | Control ya aplicado por el Banco |
| Namespaces | Código de aplicación y ambiente en cada instalación | Segregación apoq-prod, nrem-prod y equivalentes |
| Recuperación del plano de control | Respaldo y restauración ensayados; segunda zona de disponibilidad en producción | Corresponde a la continuidad de Self-Hosted, no al retiro de Cloud |
| Alcance técnico excluido | Réplica oficial Cloud hacia Self-Hosted y copia de la base de datos de Cloud | El producto no lo ofrece |

La versión del servidor Temporal, el número de particiones de historial y el dimensionamiento de nodos los define PEVE en el Anexo B.

### 04.3 Tratamiento por componente

| Componente | Tratamiento |
|---|---|
| Plano de control | Clúster Self-Hosted en AKS, con alta disponibilidad, respaldo, restauración, observabilidad y control de accesos |
| Workers | Permanecen en AKS del Banco. Se actualizan endpoint, credenciales, certificados y parámetros |
| Namespaces | Equivalentes por aplicación y ambiente |
| Identidad y secretos | Accesos nuevos en Self-Hosted. Revocación de Cloud al cierre |
| Red | Resolución, rutas, puertos, balanceador interno y Private Link |
| Pipelines | Variables por ambiente y trazabilidad del cambio |
| Observabilidad | Registros, métricas, trazas, alertas y tableros sobre Self-Hosted |
| Historiales cerrados | Archivo en Blob y exportación desde Cloud hacia Blob |
| Operación | Procedimiento de incidente, restauración, actualización y escalamiento a cargo de PEVE |

### 04.4 Arquitectura de transición (conexión dual)

Mientras Temporal Cloud responda, el worker utiliza un solo clúster activo por workflow. El indicador de configuración decide el destino de los nuevos inicios. La reversa solo aplica en este modo.

```mermaid
flowchart TB
  APP["Aplicación APOQ / NREM"]
  FLAG["Indicador de destino"]
  CLOUD["Temporal Cloud"]
  SH["Temporal Self-Hosted AKS"]
  CORE["Core / outbox"]

  APP --> FLAG
  FLAG -->|"nuevos inicios"| SH
  FLAG -->|"conclusión de ejecuciones abiertas"| CLOUD
  APP --> CORE
  SH --> CORE
  CLOUD -.->|"exportación periódica"| BLOB["Blob del Banco"]
```

Un identificador de workflow o un schedule no debe estar activo en Cloud y en Self-Hosted al mismo tiempo. Si Self-Hosted no cumple los criterios de aceptación, los nuevos inicios pueden volver a Cloud únicamente mientras ese servicio siga operable.

### 04.5 Arquitectura de conmutación en modo estresado

Si Temporal Cloud no responde, no hay conexión dual ni exportación. Los workers apuntan solo a Self-Hosted. Las ejecuciones abiertas en Cloud se consideran no recuperables como historial y se reconstruyen desde el core.

```mermaid
flowchart LR
  APP["APOQ / NREM"] --> W["Workers"]
  W --> SH["Self-Hosted AKS"]
  W --> CORE["Core / outbox / NREM"]
  CLOUD["Temporal Cloud no disponible"] -.->|sin API| X["sin conclusión ni exportación"]
```

### 04.6 Opciones adicionales de destino

La primera versión del plan tiene un solo destino: Temporal Self-Hosted en Azure AKS. Conserva el motor, los SDK y la receta de conexión dual. El Banco opera el plano de control y **no recibe soporte de Temporal Technologies Inc.** sobre el binario de código abierto. Ese es el intercambio: se elimina la dependencia de continuidad del proveedor y se asume la operación.

A esa primera versión se agregan **tres opciones adicionales**, todas de la misma categoría que Temporal (ejecución durable en código). Ninguna es un cambio de endpoint: exigen reescritura de workflows y no admiten conexión dual con Temporal Cloud.

| # | Opción | Soporte de proveedor | Dónde corre el plano de control |
|---|---|---|---|
| — | Temporal Self-Hosted (primera versión) | No. PEVE opera el OSS | AKS PEVE |
| 1 | Azure Durable Functions | Microsoft / contrato Azure | Durable Task Scheduler (Microsoft) |
| 2 | Dapr Workflows | Microsoft sobre AKS / extensión Dapr | Sidecars y state store en AKS |
| 3 | Restate | Restate Enterprise (SLA negociado) o PEVE si se autoaloja | Restate Cloud o binario en AKS |

#### Criterio de selección

| Criterio | Peso para el Banco | Qué se exige |
|---|---|---|
| Soporte del proveedor | Determinante para críticos | Contrato, SLA, canal 24×7 o equivalente al plan de soporte Azure / enterprise, y contraparte que el Banco pueda contratar |
| Continuidad del proveedor | Alto | Se pondera. Self-Hosted y Dapr/Durable Functions evitan un SaaS de orquestación joven. Restate Cloud lo incrementa; Restate Self-Managed lo reduce si hay contrato Enterprise |
| Contratos y nube ya existentes | Alto | Preferir Azure y proveedores ya aceptados por Compras y Seguridad |
| Reescritura y tiempo de salida | Alto | APOQ y NREM ya están en producción sobre Temporal. Un cambio de motor alarga la fase 0 |
| Residencia y operación en Azure | Alto | AKS, red privada, Key Vault, residencia aceptada |
| Modelo de programación | Medio | Workflows de débito, crédito, remesa, compensación, schedules e idempotencia |

No se evalúan como destino de críticos: Camunda 8 (BPMN / Zeebe; otra categoría, no ejecución durable en código); AWS Step Functions (el Banco está en Azure); Logic Apps (iPaaS); Cadence u Orkes Conductor (grafo de tareas, no replay Temporal; Orkes además concentra soporte en un proveedor de menor escala); un segundo Temporal Cloud en otra cuenta (sigue siendo Temporal Technologies Inc.).

#### Opción adicional 1 — Azure Durable Functions y Durable Task Scheduler

Microsoft opera el plano de control. El Banco ya tiene contratos Azure. El soporte es el plan de soporte Microsoft (Unified o el que Compras tenga vigente), no un proveedor de orquestación distinto.

| Elemento | Propuesta |
|---|---|
| Producto | Azure Durable Functions, con **Durable Task Scheduler** como backend gestionado (recomendado por Microsoft para producción). Alternativa de menor lock-in: Durable Task SDK con persistencia MSSQL en Azure, operada por el Banco |
| Proveedor de soporte | Microsoft. Mismo canal que el resto de Azure del BCP |
| Fortaleza | Contratos existentes, residencia en Azure, identidad (Entra / managed identity), Private Link, tablero nativo del Scheduler, SLA de Azure sobre el servicio gestionado |
| Debilidad | Reescritura completa de workflows Temporal (signals, queries, search attributes, schedules, namespaces). El modelo de hosting habitual es Azure Functions, no los workers actuales en AKS; el Durable Task SDK permite otro host, pero no es el camino más documentado |
| Migración desde Cloud | No hay importación de historial. Igual que Self-Hosted: nuevos inicios en el destino; conclusión o reapertura desde el core |
| Conexión dual | No aplica. No hay dos clústeres Temporal. El indicador de destino pasa a ser “Temporal Cloud / Durable Functions” y exige dos implementaciones del mismo proceso |
| Riesgo de proveedor | Microsoft. Aceptable para el Banco. El residual es lock-in Azure, ya asumido |
| Cuándo elegirla | El Banco no quiere operar un motor de orquestación y exige soporte sobre un contrato ya firmado |

```mermaid
flowchart LR
  subgraph apps["Plano de aplicación - BCP"]
    APOQ["APOQ / NREM"]
    ACT["Activities / functions"]
    CORE["Core, outbox y colas"]
    APOQ --> ACT
    ACT --- CORE
  end

  subgraph azdf["Azure Durable Task"]
    DF["Durable Functions o Durable Task SDK"]
    DTS["Durable Task Scheduler"]
    DF --> DTS
  end

  ACT -->|"orquestación"| DF
  DTS --> MON["Azure Monitor"]
  DTS --> KV["Key Vault / Entra"]
```

#### Opción adicional 2 — Dapr Workflows en AKS

Misma categoría que Temporal: el workflow se escribe en código, se persiste el historial y se reconstruye por replay. Activities, temporizadores y eventos externos equivalen a activities, timers y signals. El runtime de Dapr Workflow se apoya en el Durable Task Framework de Microsoft. Los workers y las aplicaciones permanecen en AKS.

| Elemento | Propuesta |
|---|---|
| Producto | Dapr Workflows (sidecar en AKS), con almacén de estado que soporte workflows. En Azure: PostgreSQL. No usar Cosmos DB para este caso (límite de 2 MB y 100 operaciones por transacción; no hay migración posterior) |
| Proveedor de soporte | Microsoft, sobre AKS y la extensión Dapr de Azure, más el plan de soporte ya contratado. Dapr es CNCF; el canal útil para el Banco es Azure, no el foro de la comunidad |
| Fortaleza | Modelo comparable a Temporal (código, replay, activities). Los procesos siguen en AKS, no hay que pasarlos a Azure Functions. Identidad, red privada y residencia ya aceptadas. Misma familia que la opción 1, otro hosting |
| Debilidad | Reescritura de SDK Temporal. Versionado, search attributes y visibilidad son más débiles que en Temporal. El building block de workflows es más joven que el servidor Temporal; hay que fijar versión soportada (N y N-2) y ensayar restauración del state store |
| Migración desde Cloud | No hay importación de historial. Nuevos inicios en Dapr; conclusión o reapertura desde el core |
| Conexión dual | No aplica. Dos implementaciones del proceso hasta el corte |
| Riesgo de proveedor | Microsoft / Azure. Aceptable para el Banco. El residual es la madurez de Dapr Workflows para volumen y duración de APOQ y NREM, y que PEVE opera sidecars y el state store |
| Cuándo elegirla | El Banco exige soporte Microsoft y quiere conservar el cómputo en AKS, con un modelo de programación del mismo tipo que Temporal |

```mermaid
flowchart LR
  subgraph apps2["Plano de aplicación - BCP"]
    APOQ2["APOQ / NREM"]
    APP["App + activities en AKS"]
    CORE2["Core, outbox y colas"]
    APOQ2 --> APP
    APP --- CORE2
  end

  subgraph dapr["Dapr en AKS"]
    SID["Sidecar daprd"]
    WF["Workflow engine / scheduler"]
    SID --- WF
  end

  APP -->|"SDK workflow"| SID
  WF --> PG2["PostgreSQL estado"]
  WF --> MON2["Monitor y alertas"]
```

Durable Functions (opción 1) y Dapr Workflows (opción 2) no son dos motores distintos: son dos formas de hospedar el Durable Task Framework. La 1 deja el plano de control en Microsoft (Durable Task Scheduler). La 2 lo deja en AKS junto a las aplicaciones. Se elige una de las dos, o ninguna.

#### Opción adicional 3 — Restate

Restate es el destino más cercano a Temporal en modelo mental: ejecución durable en código, SDKs (Java, TypeScript, Go, Python, Kotlin), invocaciones idempotentes, timers y comunicación durable. Se puede autoalojar en AKS o contratar Restate Cloud con plan Enterprise (SLA negociado, soporte P0).

| Elemento | Propuesta |
|---|---|
| Producto | Restate Server (binario en AKS, operador Kubernetes) o Restate Cloud Enterprise. Preferible Self-Managed en AKS si el criterio es no repetir un SaaS único |
| Proveedor de soporte | Restate (plan Enterprise) si se contrata Cloud o soporte sobre el binario. Si solo se autoaloja el OSS, el soporte vuelve a PEVE |
| Fortaleza | Misma categoría que Temporal, con menos piezas que un clúster Temporal (servidor + log). SDKs cercanos al estilo actual. Autoalojable en Azure. Enterprise ofrece SLA y canal de soporte |
| Debilidad | Reescritura de SDK Temporal. Compañía más joven que Temporal Technologies Inc. y que Microsoft. Restate Cloud **repite concentración** de plano de control en un proveedor de orquestación. El OSS sin contrato Enterprise deja al Banco otra vez sin soporte de proveedor |
| Migración desde Cloud | No hay importación de historial. Nuevos inicios en Restate; conclusión o reapertura desde el core |
| Conexión dual | No aplica. Dos implementaciones del proceso hasta el corte |
| Riesgo de proveedor | Restate Cloud: continuidad de un proveedor más pequeño que Temporal. Self-Managed + Enterprise: el residual es la vigencia del contrato de soporte. Self-Managed sin Enterprise: mismo residual que Temporal OSS |
| Cuándo elegirla | El Banco quiere un motor de ejecución durable en código, distinto de Temporal y de Durable Task, y acepta contratar Restate Enterprise o autoalojarlo en AKS |

```mermaid
flowchart LR
  subgraph apps3["Plano de aplicación - BCP"]
    APOQ3["APOQ / NREM"]
    SVC["Servicios / handlers AKS"]
    CORE3["Core, outbox y colas"]
    APOQ3 --> SVC
    SVC --- CORE3
  end

  subgraph rst["Restate"]
    RS["Restate Server"]
    LOG["Log durable"]
    RS --- LOG
  end

  SVC -->|"SDK Restate"| RS
  RS --> MON3["Monitor y alertas"]
  RS --> KV3["Key Vault"]
```

#### Comparación

| | Temporal Self-Hosted (1.ª versión) | Adic. 1 Durable Functions | Adic. 2 Dapr Workflows | Adic. 3 Restate |
|---|---|---|---|---|
| Categoría | Ejecución durable en código | Ejecución durable en código (Durable Task) | Ejecución durable en código (Durable Task) | Ejecución durable en código |
| Soporte de proveedor para críticos | No. PEVE opera el OSS | Sí. Microsoft / contrato Azure | Sí. Microsoft sobre AKS / extensión Dapr | Sí, si hay contrato Enterprise. No, si solo OSS |
| Reescritura de APOQ / NREM | Mínima (endpoint, identidad, receta) | Completa | Completa (SDK Dapr; workers en AKS) | Completa (SDK Restate; handlers en AKS) |
| Conexión dual con Cloud | Sí | No | No | No |
| Tiempo hasta fase 0 operativa | El de la sección 14 | Mayor: nuevo modelo + Functions o DTS | Mayor: sidecar, state store y pruebas de dominio | Mayor: nuevo SDK + servidor o Cloud |
| Residencia / Azure | AKS y PostgreSQL del Banco | Nativo Azure | AKS y PostgreSQL (no Cosmos DB) | AKS (Self-Managed) o Restate Cloud |
| Riesgo que se trata | Cese de Temporal Cloud, sin cambiar de motor | Cese de Temporal Cloud y ausencia de soporte OSS | Igual, conservando cómputo en AKS | Cese de Temporal Cloud, con otro motor durable |
| Quién opera el plano de control | PEVE | Microsoft (Scheduler) o PEVE (MSSQL) | PEVE (sidecars + state store), con soporte Azure | PEVE (AKS) o Restate (Cloud) |

#### Decisión que se pide sobre alternativas

La instancia no está obligada a cambiar el destino. Si no hay acta en contrario, la fase 0 sigue el Anexo B (Self-Hosted).

| Pedido | Efecto |
|---|---|
| Mantener Self-Hosted (primera versión) | Se ejecuta la sección 14. El residual es operar el motor sin soporte de Temporal Technologies Inc. |
| Elegir Durable Functions | Se detiene el Anexo B. Arquitectura emite un patrón Azure. APOQ y NREM reescriben. No hay conexión dual. Compras usa el contrato Microsoft |
| Elegir Dapr Workflows | Se detiene el Anexo B. Arquitectura emite el patrón Dapr en AKS. State store PostgreSQL. APOQ y NREM reescriben al SDK Dapr. No hay conexión dual |
| Elegir Restate | Se detiene el Anexo B. Arquitectura emite el patrón Restate (AKS o Cloud). Compras el contrato Enterprise si se exige soporte de proveedor. APOQ y NREM reescriben al SDK Restate |

Un cambio de destino se aprueba **antes** del paso 0.2. Después de instalar Self-Hosted, cambiar de motor no anula el trabajo de red y de inventario, pero sí anula la receta de conexión dual.

---

## 05. Análisis de impacto

El impacto de cliente se concentra en APOQ y NREM. El resto de aplicaciones no debe entrar a producción sobre Temporal Cloud.

| Aplicación | Proceso | Impacto si Cloud cesa sin plataforma alternativa | Control |
|---|---|---|---|
| APOQ | Transferencias entre cuentas | Workflows de débito, crédito o compensación a medias; riesgo de duplicar o perder un lado de la operación | Indicador de destino (conexión dual solo si Self-Hosted), idempotencia, conciliación, reversa y, en modo estresado, reapertura desde el estado de negocio |
| NREM | Remesas, emisión y recepción | Remesas en curso sin orquestación; riesgo de doble emisión o pérdida de seguimiento | Los mismos controles, con conciliación de remesas |
| No productivas | Autorizador, pagos, LBTR, core | Sin impacto de cliente. Riesgo de nacer atadas a Cloud | Migrar o congelar antes de producción |

Cada aplicación debe mantener actualizados, con el PO, Continuidad y el equipo técnico, el tiempo máximo de recuperación aceptable, la pérdida máxima de información aceptable, la ventana operativa, el volumen típico de workflows, la duración (cortos o largos), los schedules, los efectos de negocio no reversibles y el dueño.

En el seguimiento se estimarán la capacidad de la plataforma destino (no productiva y productiva), el esfuerzo de conexión dual o de reescritura por aplicación, la retención de historiales, la prueba anual de conmutación y el personal de PEVE, aplicación y seguridad. El calendario de una salida con cooperación del proveedor debe ser compatible con el plazo de preaviso contractual. El de liquidación no lo será; por ello la plataforma alternativa se prepara antes.

APOQ y NREM no se bloquean entre sí. El avance a la fase siguiente es por aplicación, con evidencias propias.

---

## 06. Disparadores

La notificación formal del proveedor es un disparador, no el único. En un escenario de insolvencia, esperar únicamente el aviso puede reducir la ventana de actuación.

| Señal | Umbral | Acción | Quién declara |
|---|---|---|---|
| Notificación formal de Temporal Technologies Inc. | Insolvencia, liquidación, disolución, cese, terminación o imposibilidad material de seguir prestando Temporal Cloud | Activación inmediata del plan | Instancia aprobadora, con evidencia custodiada por Legal |
| Comunicación contractual que anticipe la pérdida definitiva de capacidad | Preaviso de cese, rechazo del contrato en concurso o impago de la infraestructura del proveedor | Activación inmediata | Legal / Compras e instancia aprobadora |
| Duda sobre la continuidad del proveedor | Duda sustancial de auditor, incumplimiento de obligaciones financieras o imposibilidad acreditada de operar Cloud | Activación. Congelar nuevos usos de Cloud | RNF, Legal e instancia aprobadora |
| Liquidez | Horizonte de caja reducido sin financiamiento comprometido, o ronda abortada con recorte operativo material | Vigilancia formal. Piloto en un caso no crítico (conexión dual si Self-Hosted; flujo reescrito si 04.6). Acelerar la plataforma destino | RNF y PEVE |
| Degradación persistente de Cloud | Incidentes de prioridad alta reiterados o incumplimiento mensual del nivel de servicio atribuible al proveedor | Tratar como cese material. Migrar las aplicaciones críticas | PEVE, Continuidad e instancia aprobadora |
| Cambio de control | Fusión, venta o cambio de jurisdicción del proveedor o de sus datos | Vigilancia. Misma ruta técnica si el comprador no es aceptable | Legal, Arquitectura e instancia aprobadora |

La **vigilancia** no es la activación: consiste en congelar nuevos usos productivos de Cloud, completar el inventario, ejercitar la receta en no productivo y tener el clúster listo. La **activación** abre el calendario de migración y el seguimiento ejecutivo.

### Acciones inmediatas al activar

1. Registrar y custodiar la comunicación o el expediente de continuidad del proveedor.
2. Convocar a PEVE, aplicaciones, Arquitectura, Continuidad, RNF, Seguridad, Legal y Compras/Contratos.
3. Confirmar si Temporal Cloud sigue disponible y cuál es la ventana residual. Puede ser nula.
4. Congelar despliegues productivos nuevos sobre Temporal Cloud, salvo excepción aprobada.
5. Actualizar el inventario de aplicaciones, workflows, namespaces, workers, datos de estado y accesos.
6. Priorizar APOQ y NREM, y calendarizar el resto (migrar o congelar).
7. Abrir el seguimiento ejecutivo, el control de riesgos y el paquete de evidencias.
8. No eliminar configuraciones ni accesos de Cloud mientras exista estado por tratar y el servicio responda.

---

## 07. Gobierno y roles

| Rol | Responsabilidad | Resultado |
|---|---|---|
| Instancia aprobadora | Autorizar destino (paso 0.0), vigilancia, activación, excepciones, producción y cierre | Decisiones formalizadas |
| PEVE | Gobernar, priorizar, entregar la receta técnica, consolidar evidencias y mantener el plan | Seguimiento único y cierre controlado |
| Coordinación técnica | Articular aplicaciones y frentes técnicos; gestionar bloqueos y avance | Ejecución coordinada |
| Equipos de aplicación | Inventariar, configurar, migrar, probar, conciliar y evidenciar | Aplicación estable en el destino aprobado |
| PO / responsable funcional | Validar impacto, continuidad, conciliación y aceptación | Conformidad funcional |
| Arquitectura | Validar arquitectura objetivo y patrones técnicos | Conformidad arquitectónica |
| Seguridad / Ciberseguridad | Validar accesos, red, certificados, cifrado, registro y cierre seguro | Conformidad de seguridad |
| Continuidad | Validar tiempos de recuperación, pérdida de información y contingencia del modo estresado | Criterios de continuidad aprobados |
| RNF | Validar tratamiento del riesgo y evidencias | Riesgo tratado y trazable |
| Legal / Compras | Gestionar notificaciones, derechos de salida y terminación | Cierre contractual sustentado |

PEVE mantendrá un seguimiento único con avance por aplicación, ambiente, fase, riesgo, bloqueo, responsable y evidencia. Los bloqueos que comprometan continuidad, seguridad o la ventana de salida se elevan a la instancia aprobadora.

El PO valida el impacto funcional y la continuidad del proceso. El equipo técnico identifica workflows, workers, dependencias y datos de estado, ejecuta la migración y conserva las evidencias. PEVE acompaña, estandariza la receta y consolida el seguimiento.

---

## 08. Contrato y periodo de transición

Legal y Compras gestionan las notificaciones, los derechos de salida y la terminación. Conservan las comunicaciones y la constancia de cierre.

El contrato aporta valor en reorganización y venta (preaviso, asistencia, exportación y periodo de transición). En liquidación puede no haber asistencia ni mantenimiento del plano de control. El control principal del plan es la plataforma alternativa, no la cláusula contractual.

Mientras Temporal Cloud exista como contraparte:

- Custodiar el aviso y la ventana residual, si la hay.
- Exigir asistencia de salida y acceso a historiales solo si el proveedor aún opera.
- No pactar un calendario de salida más largo que la capacidad real del destino aprobado.
- Al cierre: terminación, evidencia de que no quedan dependencias y, si hay entidad subsistente, constancia de destrucción o indisponibilidad de datos del Banco en Cloud.

La destrucción certificada de datos en Cloud se solicita cuando existe contraparte. Si no la hay, se documenta la pérdida de control sobre el residual y se retiene lo ya exportado al Banco.

---

## 09. Procedimiento técnico de transición

PEVE define la receta. Cada aplicación la ejecuta. Temporal no ofrece migración automatizada de Cloud hacia ningún destino: si el destino es Self-Hosted se actualiza la conexión; si es 04.6 se reescribe el proceso y se corta el tráfico nuevo.

La receta de conexión, el tratamiento por namespace y la conexión dual de esta sección aplican **solo** si el paso 0.0 confirma Self-Hosted. Si confirma Durable Functions, Dapr Workflows o Restate, rige el Anexo B.4.

### Fases

| Fase | Actividades principales | Responsable líder | Resultado |
|---|---|---|---|
| 0. Preparación preventiva | Confirmación del destino (Self-Hosted vigente, o 04.6 si hay acta). Arquitectura, capacidad, receta, inventario, exportación de historiales a almacenamiento del Banco, conexión dual si el destino es Temporal, observabilidad y pruebas iniciales | PEVE / Arquitectura | Plataforma preparada antes de la activación |
| 1. Activación | Registro del aviso o del expediente, convocatoria, definición del modo (ordenado o estresado) y calendario | PEVE / instancia aprobadora | Plan activado |
| 2. Migración no productiva | Cambios en desarrollo y certificación; pruebas técnicas, funcionales, de seguridad y de observabilidad | Equipos de aplicación | Ambientes no productivos validados |
| 3. Migración productiva | Cambio controlado o conmutación, conciliación, validación, estabilización y reversa si Cloud sigue disponible | Equipos de APOQ y NREM | Aplicaciones operando en el destino aprobado |
| 4. Retiro definitivo | Eliminación de endpoints, accesos, secretos, certificados, pipelines y dependencias de Cloud | Equipos de aplicación / PEVE | Sin dependencias activas |
| 5. Cierre | Consolidación de evidencias, conformidades y cierre contractual y de riesgo | PEVE / áreas de control | Cierre aprobado |

Cada aplicación avanzará a la fase siguiente únicamente cuando cuente con evidencias satisfactorias de la fase anterior. Las excepciones se registrarán con riesgo, control compensatorio, responsable y aprobación.

### Receta de conexión

1. Crear el namespace equivalente en Self-Hosted y validar la segregación por ambiente.
2. Emitir identidad, secretos y certificados del destino. No reutilizar credenciales de Cloud.
3. Actualizar workers y clientes: endpoint, namespace y autenticación.
4. Actualizar pipelines y variables por ambiente.
5. Validar red: resolución, rutas, puertos, balanceadores y conectividad privada.
6. Asegurar registros, métricas, trazas, alertas y tableros en la plataforma objetivo.
7. Habilitar la conexión dual o el indicador de destino, con mecanismo de reversa, mientras Cloud responda.
8. Al cierre, revocar las credenciales de Cloud.

### Tratamiento de workflows

| Estado | Modo ordenado (Cloud disponible) | Modo estresado (liquidación o interrupción) |
|---|---|---|
| Nuevos inicios | Solo Self-Hosted | Solo Self-Hosted |
| Activos cortos | Concluir en Cloud. Sin ejecución simultánea | Reconstruir o cerrar desde el estado de negocio |
| Activos largos | Trasladar el estado a una nueva ejecución en Self-Hosted, o concluir en Cloud si cabe en la ventana | Reabrir desde el estado de negocio. No reejecutar efectos ya confirmados |
| Schedules | Alta en ambos ambientes; pausar en Cloud y reanudar en Self-Hosted con control que impida el disparo doble | Reanudar solo en Self-Hosted |
| Cerrados | Conservar el histórico exigido (exportación a almacenamiento del Banco y retención) | Conservar únicamente lo ya exportado o la evidencia externa |
| Fallidos | Analizar causa, conciliar y decidir reproceso o cierre | Igual, con prioridad en cuentas y remesas |
| Compensados | Mantener evidencia del resultado y de la consistencia | Igual |
| En reproceso | Controlar duplicidad, idempotencia y conciliación antes de reejecutar | Igual. Cloud pudo haber ejecutado un lado no visible |
| No productivos | Migrar si continuarán, o retirar o congelar con evidencia | Congelar pases a producción sobre Cloud |

Cada equipo documenta el mecanismo aplicado: migración, exportación, reconstrucción o evidencia externa. No se eliminan namespaces ni accesos de Cloud mientras quede estado por tratar y el servicio responda.

### Secuencia por ambiente

1. **Desarrollo.** Validar receta, conectividad, workers, autenticación y configuración.
2. **Certificación.** Validar flujos funcionales, integración, rendimiento, observabilidad y reversa.
3. **Producción.** Migrar la dependencia productiva con cambio o conmutación, conciliación y autorización.
4. **Cierre.** Retirar dependencias de Cloud y consolidar evidencias.

### Uso de la reversa

La reversa se ejecutará solo si Temporal Cloud sigue disponible y cuando la validación técnica o funcional no alcance los criterios de aceptación, existan transacciones sin conciliación, se detecte degradación relevante o no se disponga de observabilidad suficiente. La decisión y su evidencia se registrarán. En liquidación no hay reversa hacia Cloud: se estabiliza el destino aprobado y se concilia contra el core.

---

## 10. Continuidad durante la salida

Los planes de continuidad cubren la indisponibilidad de corta duración. Este plan cubre la sustitución del proveedor. Durante el retiro, Continuidad valida que APOQ y NREM no superen el tiempo máximo de recuperación ni la pérdida máxima de información aceptables.

### Controles mínimos (APOQ y NREM)

- Identificar los procesos y transacciones afectados.
- Mantener actualizados el tiempo máximo de recuperación, la pérdida máxima de información y la ventana operativa.
- Definir el tratamiento de solicitudes y workflows en curso (conclusión en Cloud, traslado de estado o reapertura).
- Aplicar monitoreo, alertas, reproceso y conciliación durante la transición.
- Disponer de reversa únicamente si Cloud está disponible.
- Obtener conformidad del PO antes de cerrar la ventana.

| Aplicación | Proceso | Control de continuidad | Validación |
|---|---|---|---|
| APOQ | Transferencias entre cuentas | Plan de cambio o conmutación, tratamiento de transacciones, conciliación, monitoreo y reversa si aplica | PO y equipo técnico |
| NREM | Remesas | Plan de cambio o conmutación, tratamiento de remesas en curso, conciliación, monitoreo y reversa si aplica | PO y equipo técnico |
| No productivas | Casos en desarrollo o certificación | Migración antes de producción o retiro controlado | Dueño y equipo técnico |

La continuidad se considera restablecida cuando los flujos críticos operan en el destino aprobado, las transacciones en curso han sido conciliadas o tratadas, la observabilidad se encuentra activa y el PO emite conformidad funcional.

Si Temporal Cloud ya no está disponible, no se espera el historial vivo. Se reabren solo los casos que el core, el outbox o las colas muestran como pendientes. Se bloquea cualquier activity cuyo efecto de negocio ya esté confirmado en el registro de la aplicación.

---

## 11. Criterios de éxito y cierre

### Criterios de éxito

- Todas las aplicaciones incluidas operan en el destino aprobado o fueron retiradas o congeladas antes de producción.
- No existen workflows productivos ni datos de estado sin tratamiento.
- Los históricos requeridos se conservan para auditoría y trazabilidad, en control del Banco.
- Se retiraron o deshabilitaron endpoints, accesos, secretos, certificados y credenciales de Temporal Cloud.
- No existe ejecución simultánea en ambos ambientes.
- Las evidencias técnicas, funcionales, de continuidad, de datos, de seguridad, contractuales y de riesgo están consolidadas.
- PEVE y las áreas de control aprueban el cierre. La instancia aprobadora lo formaliza.

### Paquete mínimo de evidencias

| Dimensión | Evidencia |
|---|---|
| Técnica | Configuración aplicada, pruebas, conectividad, pipelines y validación de estabilidad |
| Funcional | Conformidad del PO y evidencia de flujos críticos |
| Continuidad | Conciliación, tratamiento de transacciones y cumplimiento de la ventana operativa |
| Datos | Tratamiento de workflows activos e históricos, integridad y ubicación de la exportación |
| Seguridad | Accesos, secretos, certificados, registro de eventos y cierre seguro |
| Contractual | Comunicaciones, terminación o constancia de inexistencia de contraparte |
| Riesgo | Tratamiento del riesgo residual y aprobación de cierre |

### Cierre seguro

El retiro no se considera cerrado hasta evidenciar la eliminación, rotación o deshabilitación de credenciales, certificados, secretos, usuarios, conexiones y configuraciones que ya no sean requeridas en Temporal Cloud. Legal y Compras/Contratos conservarán las comunicaciones y evidencias de terminación. PEVE confirmará que no queden dependencias activas y emitirá el consolidado de cierre.

---

## 12. Pruebas, revisión y riesgo residual

### Pruebas mínimas por aplicación

- Conectividad, resolución, autenticación y autorización.
- Registro y ejecución de workflows y activities.
- Recuperación ante fallos, reintentos, compensaciones y reprocesos, sin duplicar efectos de negocio.
- Integración con dependencias de la aplicación.
- Registros, métricas, trazas, alertas y tableros.
- Rendimiento y capacidad para la carga de la aplicación.
- Conciliación funcional y técnica.
- Prueba de reversa antes de la migración productiva, si Cloud es el origen.

### Criterios de entrada a producción

- Arquitectura y controles de seguridad validados.
- Pruebas satisfactorias en desarrollo y certificación.
- Tratamiento de workflows activos e históricos definido para el modo ordenado y para el modo estresado.
- Plan de cambio, validación, conciliación y reversa aprobado, o declaración de ausencia de reversa en modo estresado.
- Observabilidad y soporte habilitados.
- Autorización de la instancia correspondiente.

### Pruebas del plan

| Nivel | Qué se prueba | Frecuencia |
|---|---|---|
| Revisión documental | Inventario, supuestos, costos, tiempos, capacidades, disparadores y compatibilidad residual del contrato | Anual o ante cambio material |
| Recorrido operativo | PEVE y las aplicaciones recorren las fases 0 a 5 y confirman que pueden ejecutarlas | Anual |
| Ejercicio técnico | Un caso no crítico en el destino: conexión dual si Self-Hosted, o flujo reescrito si 04.6; conclusión o reapertura; schedules; observabilidad | Anual |
| Ejercicio de mesa en modo estresado | Temporal Cloud no responde; conmutación al destino aprobado; conciliación de APOQ y NREM contra el estado de negocio; aviso a control | Anual, junto con las pruebas de continuidad |

La revisión de suficiencia del plan la realiza un área que no lo elaboró (RNF o Auditoría Interna, según el mandato interno).

### Información que debe mantenerse actualizada

| Información | Responsable |
|---|---|
| Inventario de aplicaciones, workflows, workers, namespaces y dependencias | Equipos de aplicación / PEVE |
| Responsables funcionales, técnicos y aprobadores | PEVE / dueños de aplicación |
| Tiempo máximo de recuperación, pérdida máxima de información y ventanas operativas | PO / Continuidad / equipo técnico |
| Arquitectura, capacidad, accesos y controles del destino aprobado | PEVE / Arquitectura / Seguridad |
| Receta técnica, pruebas, reversa y evidencias | PEVE / equipos de aplicación |
| Calendario, esfuerzo, bloqueos y riesgos | PEVE |
| Comunicaciones contractuales y derechos de salida | Legal / Compras |

### Riesgo residual

El riesgo residual se mantiene mientras la preparación preventiva no esté completa (plataforma destino, receta, exportación de historiales, matriz de workflows) o la información operativa no se encuentre actualizada. En Self-Hosted eso incluye clúster y conexión dual. En 04.6 incluye reescritura validada en certificación y ausencia de ejecución simultánea con Cloud. Completar la fase 0 permite ejecutar el retiro ante un cese del proveedor. El resultado financiero del proveedor, por sí solo, no reduce ese residual. El residual de Self-Hosted es operar sin soporte de Temporal Technologies Inc. El residual de Durable Functions o Dapr es lock-in Azure y madurez del modelo Durable Task. El residual de Restate Cloud es la continuidad de un proveedor más joven; el de Restate Self-Managed sin Enterprise es el mismo que el OSS de Temporal.

La versión vigente, sus actualizaciones relevantes y su cierre serán presentados a las áreas de control y a la instancia aprobadora, con trazabilidad de la revisión y de la conformidad.

---

## 13. Comunicación

| Momento | Audiencia | Mensaje | Responsable |
|---|---|---|---|
| Aprobación de esta versión | Instancia, RNF, Arquitectura, Seguridad, Continuidad, PO APOQ y PO NREM | Plan vigente. Se autoriza la fase 0. El paso 0.0 confirma el destino. No se ejecuta la migración productiva | PEVE |
| Vigilancia | Las mismas áreas y los equipos de aplicación | Congelar namespaces productivos nuevos en Cloud. Completar el Anexo F | PEVE / RNF |
| Activación en modo ordenado | Roles de la sección 07 y mesa de cambios | Cloud disponible. Conclusión de workflows abiertos. Conexión dual solo si el destino es Self-Hosted. Calendario por aplicación | Instancia aprobadora y PEVE |
| Activación en modo estresado | Las mismas áreas y operaciones de APOQ y NREM | Cloud no disponible. Conmutación. Conciliar contra el core. Sin reversa | PEVE y Continuidad |
| Ventana productiva | PO, operaciones y soporte | Qué opera en el destino, qué permanece en conclusión en Cloud y qué está en cola de excepción | Equipo de aplicación |
| Cierre | Legal, Seguridad, RNF e instancia | Sin dependencias activas en Cloud. Expediente del Anexo D | PEVE |
| Áreas de control y supervisor, si corresponde | Según mandato interno | Servicio significativo y, de ser el caso, cambio del proveedor de procesamiento | Legal / RNF |

No se requiere comunicado al cliente final: el cambio es de orquestación interna. Si APOQ o NREM afectan el servicio visible, se aplica el protocolo de incidente de la aplicación.

---

## 14. Hoja de ruta de la fase 0

El objetivo es completar el Anexo F. El orden siguiente es referencial. Las fechas las registra PEVE en el seguimiento.

| Paso | Entregable | Líder | Depende de |
|---|---|---|---|
| 0.0 | Acta de destino: Self-Hosted (primera versión) o una opción de la sección 04.6. Sin acta, rige Self-Hosted | Instancia / Arquitectura / Compras | Aprobación del plan |
| 0.1 | Conformidad de la arquitectura: sección 04 si Self-Hosted; patrón Durable Functions, Dapr o Restate si 0.0 lo eligió | Arquitectura / Seguridad | 0.0 |

Si el paso 0.0 confirma **Self-Hosted**, siguen 0.2 a 0.10. Si confirma una opción de **04.6**, se omiten 0.3 a 0.5 (namespaces y conexión dual) y rigen 0.2b a 0.5b, más 0.6 a 0.10.

| Paso | Entregable (Self-Hosted) | Líder | Depende de |
|---|---|---|---|
| 0.2 | Instalación no productiva: AKS PEVE, PostgreSQL, visibilidad, Key Vault y Monitor | PEVE | 0.1 |
| 0.3 | Namespaces de desarrollo y certificación; red privada desde los workers | PEVE y redes | 0.2 |
| 0.4 | Receta de conexión dual en un namespace no crítico (ejercicio F8) | PEVE y una aplicación | 0.3 |
| 0.5 | Conexión dual de APOQ y NREM en desarrollo y certificación | Equipos APOQ y NREM | 0.4 |

| Paso | Entregable (Durable Functions, Dapr o Restate) | Líder | Depende de |
|---|---|---|---|
| 0.2b | Plataforma no productiva del destino (Scheduler / sidecars Dapr / Restate Server o Cloud) según Anexo B.4 | PEVE | 0.1 |
| 0.3b | Identidad, red privada y secretos del destino; sin credenciales de Cloud reutilizadas | PEVE / Seguridad / redes | 0.2b |
| 0.4b | Un flujo no crítico reescrito y probado (equivalente F8; no hay conexión dual) | PEVE y una aplicación | 0.3b |
| 0.5b | APOQ y NREM reescritos en desarrollo y certificación, sin ejecución simultánea con Cloud | Equipos APOQ y NREM | 0.4b |

| Paso | Entregable (ambos destinos) | Líder | Depende de |
|---|---|---|---|
| 0.6 | Exportación de Cloud hacia Blob, mientras Cloud responda | PEVE / Seguridad | 0.2 o 0.2b |
| 0.7 | Instalación productiva del destino: alta disponibilidad, respaldo, restauración ensayada y capacidad para APOQ y NREM | PEVE | 0.5 o 0.5b, y 0.6 |
| 0.8 | Anexo C firmado con nombres reales, y tiempos de recuperación vigentes | PO y Continuidad | 0.5 o 0.5b |
| 0.9 | Ejercicio de mesa “Cloud no responde” con APOQ y NREM (F9) | PEVE y Continuidad | 0.7 y 0.8 |
| 0.10 | Inventario A con antigüedad no mayor a 90 días, contrato localizado e instancia informada (F10 a F12) | PEVE / Legal | 0.9 |

Al completar el paso 0.10, la plataforma objetivo queda lista para recibir las aplicaciones. La migración productiva sigue reservada a la activación descrita en la sección 06. Un destino 04.6 alarga la fase 0: la reescritura de APOQ y NREM no cabe en el calendario de un solo cambio de endpoint.

---

## 15. Glosario

| Término | Significado en este plan |
|---|---|
| Temporal Cloud | Servicio gestionado de Temporal Technologies Inc. |
| Self-Hosted | Servidor Temporal de código abierto operado por el Banco en Azure AKS. Destino vigente. Sin soporte de Temporal Technologies Inc. |
| Durable Functions | Opción adicional 1. Orquestación Azure (Durable Task Scheduler o Durable Task SDK). Soporte Microsoft |
| Dapr Workflows | Opción adicional 2. Ejecución durable en código sobre sidecars en AKS. Soporte Microsoft / extensión Dapr |
| Restate | Opción adicional 3. Motor de ejecución durable en código. Restate Cloud Enterprise o Self-Managed en AKS |
| PEVE | Frente que gobierna el plan y opera el plano de control |
| Vigilancia | Seguimiento de la continuidad del proveedor, sin iniciar la migración productiva |
| Activación | Orden de ejecutar el retiro en modo ordenado o estresado |
| Destino aprobado | Self-Hosted, salvo acta del paso 0.0 que elija Durable Functions, Dapr Workflows o Restate |
| Conexión dual | Solo si el destino es Self-Hosted. Mismo worker o cliente con dos endpoints Temporal. Un solo clúster activo por ejecución. No aplica a 04.6 |
| Conclusión en Cloud | Dejar terminar en Cloud los workflows cortos ya abiertos |
| Traslado de estado | Pasar el estado de una ejecución larga a una nueva ejecución en Self-Hosted |
| Reapertura desde negocio | Reabrir desde el core, outbox o colas, no desde el historial de Cloud |
| Ejecución simultánea | El mismo workflow o schedule activo en ambos clústeres. No está permitida |
| Efecto de negocio | Resultado no reversible (cargo, abono, remesa, liquidación interbancaria) |
| Fase 0 | Preparación preventiva. Condición para declarar el plan operativo |

---

## Anexo A. Inventario operativo

PEVE consolida. Cada equipo de aplicación completa y firma su fila. Los namespaces siguen el patrón de código de aplicación y ambiente, salvo que el inventario real documente una excepción.

| Aplicación | Namespace Cloud (esperado) | Namespace Self-Hosted | Ambiente | Workers (AKS) | Efectos de negocio no reversibles | RTO | RPO | Responsable técnico | PO |
|---|---|---|---|---|---|---|---|---|---|
| APOQ | apoq-prod | apoq-prod | Producción | Clúster AKS del Banco; endpoint a actualizar | Débito, crédito, compensación | *PO / Continuidad* | *PO / Continuidad* | *equipo APOQ* | *PO APOQ* |
| APOQ | apoq-cert / apoq-dev | apoq-cert / apoq-dev | Certificación / desarrollo | Igual | Igual (datos no productivos) | No aplica a cliente | No aplica a cliente | *equipo APOQ* | *PO APOQ* |
| NREM | nrem-prod | nrem-prod | Producción | Clúster AKS del Banco; endpoint a actualizar | Emisión y recepción de remesa | *PO / Continuidad* | *PO / Continuidad* | *equipo NREM* | *PO NREM* |
| NREM | nrem-cert / nrem-dev | nrem-cert / nrem-dev | Certificación / desarrollo | Igual | Igual (datos no productivos) | No aplica a cliente | No aplica a cliente | *equipo NREM* | *PO NREM* |
| CPCA | cpca-dev / cpca-cert | cpca-dev / cpca-cert | Desarrollo / certificación | AKS del Banco | Movimientos de ahorro, si se habilita | Antes de producción | Antes de producción | *equipo* | *dueño* |
| CPCC | cpcc-dev / cpcc-cert | cpcc-dev / cpcc-cert | Desarrollo / certificación | AKS del Banco | Movimientos de corriente, si se habilita | Antes de producción | Antes de producción | *equipo* | *dueño* |
| APTI / TUPI | apti / tupi, por ambiente | apti / tupi, por ambiente | Desarrollo / certificación | AKS del Banco | Pagos y transferencias digitales | Antes de producción | Antes de producción | *equipo* | *dueño* |
| CDPT | cdpt-dev / cdpt-cert | cdpt-dev / cdpt-cert | Desarrollo / certificación | AKS del Banco | Pagos y transferencias | Antes de producción | Antes de producción | *equipo* | *dueño* |
| SRCR | srcr-dev / srcr-cert | srcr-dev / srcr-cert | Desarrollo / certificación | AKS del Banco | Seguimiento de pagos | Antes de producción | Antes de producción | *equipo* | *dueño* |
| LBCL | lbcl-dev / lbcl-cert | lbcl-dev / lbcl-cert | Desarrollo / certificación | AKS del Banco | Transferencia interbancaria BCR / LBTR | Antes de producción | Antes de producción | *equipo* | *dueño* |
| CPCR | cpcr-dev / cpcr-cert | cpcr-dev / cpcr-cert | Desarrollo / certificación | AKS del Banco | Core de cuentas | Antes de producción | Antes de producción | *equipo* | *dueño* |

Cada fila debe adjuntar, en la hoja operativa: colas de tareas, imagen y réplicas del worker, schedules, atributos de búsqueda, mecanismo de cifrado del payload, secretos y certificados vigentes, pipeline, tablero de observabilidad y estrategia por tipo de workflow (Anexo C).

Ninguna aplicación no productiva habilitará un namespace productivo en Temporal Cloud. Si pasa a producción, el namespace o el equivalente del destino (task hub, app Dapr, deployment Restate) se crea en el destino aprobado.

---

## Anexo B. Receta Self-Hosted (PEVE)

Objetivo de la fase 0: el Banco puede recibir APOQ y NREM sin depender de Temporal Technologies Inc. en el momento de la activación. La topología de Self-Hosted es la de la sección 04. Si el paso 0.0 elige 04.6, rige B.4 y no B.1–B.2.

### B.1 Plataforma

| Ítem | Requisito | Evidencia | Estado |
|---|---|---|---|
| Arquitectura objetivo | Sección 04 conformada (diagrama y decisiones de diseño) | Acta de Arquitectura y Seguridad | |
| Clúster Temporal en Azure AKS | Alta disponibilidad, al menos equivalente al nivel de servicio interno de APOQ y NREM; instalación no productiva y productiva | Diagrama de despliegue e infraestructura como código | |
| Persistencia | Base de datos del Banco, con respaldo y restauración ensayados | Prueba de restauración con la pérdida de información declarada | |
| Capacidad no productiva | Desarrollo y certificación para las aplicaciones del inventario | Asignación de recursos AKS y prueba de arranque | |
| Capacidad productiva | Dimensionada para APOQ y NREM de forma concurrente | Plan de capacidad firmado por PEVE | |
| Namespaces | Creados según el Anexo A, segregados por ambiente | Listado de namespaces y responsables | |
| Identidad y mTLS o equivalente | Identidades distintas a las de Cloud; mínimo privilegio | Matriz de roles de Seguridad | |
| Secretos | En el repositorio de secretos del Banco; rotación documentada | Inventario de secretos | |
| Red | Resolución, puertos, balanceo y conectividad privada aplicable | Prueba de conectividad desde los workers | |
| Observabilidad | Registros, métricas, trazas, alertas y tableros | Tablero Self-Hosted operativo | |
| Residencia | Datos y respaldos en ubicaciones aceptadas por el Banco | Constancia de Arquitectura y Seguridad | |
| Exportación de historiales Cloud | Proceso periódico a almacenamiento del Banco, verificado | Muestra de archivos y política de retención | |
| Operación | Procedimiento de incidente, restauración, actualización y escalamiento | Procedimiento publicado | |

### B.2 Receta de aplicación

1. Namespace destino creado, sin ejecución simultánea con Cloud.
2. Secretos y certificados nuevos, no reutilizados de Cloud.
3. Cliente y workers con dos endpoints (Cloud y Self-Hosted) detrás de un indicador de configuración, y mecanismo de reversa.
4. Pipeline por ambiente actualizado, con trazabilidad del cambio.
5. Pruebas de la sección 12 en desarrollo y certificación.
6. Matriz del Anexo C firmada por el PO de la aplicación.
7. Plan de cambio productivo o declaración de conmutación en modo estresado, sin reversa a Cloud.

### B.3 Alcance técnico excluido en la activación

No se construye en el momento de la activación una réplica oficial de Cloud hacia Self-Hosted, una copia de la base de Temporal Cloud, la asistencia de Temporal Technologies Inc. ni un segundo motor (Durable Functions, Dapr Workflows o Restate), salvo que el paso 0.0 ya lo hubiera aprobado y la plataforma alternativa estuviera lista.

### B.4 Receta si el destino es 04.6

Sustituye B.1 y B.2 cuando el paso 0.0 elige Durable Functions, Dapr Workflows o Restate. No hay conexión dual ni namespaces Temporal.

| Ítem | Requisito | Evidencia |
|---|---|---|
| Patrón de Arquitectura | Conformidad del destino elegido (Functions + Scheduler, Dapr + PostgreSQL, o Restate AKS/Cloud) | Acta de Arquitectura y Seguridad |
| Plataforma no productiva y productiva | Alta disponibilidad y restauración ensayadas, capacidad concurrente para APOQ y NREM | Diagrama, IaC y prueba de restauración |
| Identidad | Identidades nuevas (Entra / managed identity / mTLS). No reutilizar secretos de Cloud | Matriz de roles |
| Red | Conectividad privada desde las aplicaciones hacia el plano de control del destino | Prueba de conectividad |
| Observabilidad | Registros, métricas, trazas, alertas y tablero del destino | Tablero operativo |
| Residencia | Datos y respaldos en ubicaciones aceptadas | Constancia de Arquitectura y Seguridad |
| Soporte de proveedor | Contrato o plan de soporte vigente: Microsoft (1 y 2) o Restate Enterprise (3, si se exige soporte) | Constancia de Compras |
| Receta de aplicación | Proceso reescrito; indicador que impida iniciar el mismo efecto en Cloud y en el destino; reversa solo mientras Cloud responda | Pruebas de la sección 12 en certificación |
| Anexo C | Firmado con el mecanismo del destino (no “namespace Self-Hosted”) | Acta del PO |

State store de Dapr: PostgreSQL. Cosmos DB queda excluido para APOQ y NREM. Durable Functions y Dapr no se despliegan a la vez: son el mismo Durable Task Framework. Restate se elige en lugar de esos dos, no junto con ellos.

---

## Anexo C. Matriz de workflow y estrategia

Los tipos siguientes corresponden al uso declarado por el Banco. Cada equipo sustituye el nombre interno real del workflow y confirma duración, schedules y clave de idempotencia. Un tipo no se inicia a la vez en Cloud y en el destino.

### C.1 APOQ, transferencias entre cuentas (producción)

| Tipo de proceso | Duración típica | Efecto de negocio | Clave de idempotencia | Modo ordenado (Cloud disponible) | Modo estresado (Cloud no disponible) | Evidencia de conciliación | Dueño |
|---|---|---|---|---|---|---|---|
| Débito de cuenta origen | Corta | Cargo en cuenta | Identificador de transferencia de negocio | Concluir en Cloud. Nuevos inicios solo en Self-Hosted | Si el core ya muestra el cargo, no reejecutar. Si no hay cargo y la solicitud sigue pendiente, nueva ejecución en Self-Hosted | Saldo y movimiento en core frente al resultado del workflow | PO APOQ |
| Crédito de cuenta destino | Corta | Abono en cuenta | Identificador de transferencia y lado crédito | Igual | Igual, para el abono | Movimiento de abono en core | PO APOQ |
| Compensación | Corta | Reverso de débito o crédito | Identificador de compensación ligado al original | Completar en Cloud si la ejecución está activa. Si no, compensar solo si el core confirma el lado a deshacer | Compensar únicamente contra el estado del core. No compensar de forma preventiva | Asiento de reverso y bitácora | PO APOQ |
| Recuperación ante fallos o reproceso | Corta a media | Puede reintentar débito, crédito o compensación | La misma clave del lado original | Reproceso en un solo clúster, el que posee la ejecución | Reproceso solo si el core no tiene el efecto. Si está indeterminado, cola de excepción | Cola de excepción y conciliación | PO APOQ y operaciones |

Una transferencia es un par débito y crédito. La conmutación no puede completar un lado que el otro ambiente ya confirmó. Si hay duda, se deriva a excepción operativa.

### C.2 NREM, remesas (producción)

| Tipo de proceso | Duración típica | Efecto de negocio | Clave de idempotencia | Modo ordenado | Modo estresado | Evidencia de conciliación | Dueño |
|---|---|---|---|---|---|---|---|
| Emisión de remesa | Corta a media | Orden de pago o instrucción de envío | Identificador de remesa de negocio | Concluir en Cloud. Nuevas emisiones en Self-Hosted | Si la remesa ya está instruida, no reemitir. Si solo existe la solicitud interna, nueva ejecución en Self-Hosted | Estado de remesa en NREM frente a core o corresponsal | PO NREM |
| Recepción de remesa | Corta a media | Abono o disponibilidad al beneficiario | Identificador de remesa entrante | Concluir en Cloud | Si el abono ya está en core, no reejecutar. Si la remesa está notificada y no abonada, ejecución en Self-Hosted | Abono en cuenta y seguimiento NREM | PO NREM |
| Reproceso o recupero de remesa | Corta a media | Reintento de emisión, recepción o aviso | La misma clave de remesa | Un solo clúster | Cola de excepción si el corresponsal o el core están indeterminados | Seguimiento y constancia de no doble pago | PO NREM y operaciones |

El seguimiento de la remesa no autoriza a reemitir. La fuente de verdad es el estado en el sistema de negocio y, si aplica, la confirmación del corresponsal.

### C.3 Aplicaciones no productivas

| Aplicación | Tratamiento | Condición para producción |
|---|---|---|
| CPCA, CPCC | Migrar la receta al destino aprobado o congelar | Producción solo en el destino aprobado |
| APTI / TUPI, CDPT, SRCR | Igual | Producción solo en el destino aprobado, con Anexo C propio antes del pase |
| LBCL | Igual | Producción solo en el destino aprobado, con Anexo C propio (BCR / LBTR) |
| CPCR | Igual | Producción solo en el destino aprobado, con Anexo C propio (core de cuentas) |

---

## Anexo D. Expediente de activación y cierre

Custodia: PEVE (expediente único). Copias: Legal/Compras (contractual), RNF (riesgo) y Seguridad (cierre de accesos).

| Código | Pieza | Quién aporta | Cuándo |
|---|---|---|---|
| D1 | Comunicación del proveedor o expediente de continuidad | Legal | Activación |
| D2 | Acta de vigilancia o de activación, con el modo (ordenado o estresado) | Instancia aprobadora | Activación |
| D3 | Inventario del Anexo A vigente, con fecha | PEVE y aplicaciones | Activación y cada fase |
| D4 | Matriz del Anexo C firmada (APOQ, NREM; resto si aplica) | PO y equipo técnico | Antes de producción o conmutación |
| D5 | Evidencias de la fase 0 (Anexo B o B.4 según destino) | PEVE, Arquitectura y Seguridad | Antes o al activar |
| D6 | Evidencias de desarrollo y certificación por aplicación | Equipo de aplicación | Fase 2 |
| D7 | Plan de cambio productivo o constancia de conmutación sin reversa | Equipo y Continuidad | Fase 3 |
| D8 | Conciliación de APOQ y NREM y conformidad del PO | PO | Cierre de ventana |
| D9 | Inventario de accesos Cloud antes y después, y revocación | Seguridad | Fase 4 |
| D10 | Terminación contractual o constancia de inexistencia de contraparte | Legal / Compras | Fase 5 |
| D11 | Riesgo residual y aprobación de cierre | RNF e instancia aprobadora | Fase 5 |
| D12 | Lecciones del ejercicio anual “Cloud no responde” | PEVE | Revisión del plan |
| D13 | Acta de destino del paso 0.0 (Self-Hosted o una opción 04.6) | Instancia / Arquitectura / Compras | Antes del paso 0.2 o 0.2b |

---

## Anexo E. Actuación en el día de activación

PEVE declara el modo en la primera hora. No se combinan las dos rutas.

### E.1 Temporal Cloud disponible (reorganización o venta)

| Tiempo | Acción | Responsable |
|---|---|---|
| Inicio | Acta de activación. Congelar nuevos inicios productivos hacia Cloud | Instancia aprobadora y PEVE |
| Primeras 2 horas | Indicador de destino: nuevos inicios de APOQ y NREM hacia el destino aprobado. Workers o funciones listos; sin ejecución simultánea con Cloud | Equipos APOQ y NREM |
| 2 a 24 horas | Conclusión de ejecuciones cortas en Cloud. Inventario de largos, fallidos y reprocesos | Equipos y PO |
| Día 2 en adelante | Traslado de ejecuciones largas. Pausa de schedules en Cloud y reanudación en el destino, con control de disparo único | Equipos |
| Ventana | Conciliación continua. Reversa solo si el destino no cumple criterios y Cloud sigue operable | PO y Continuidad |
| Cierre de ventana | Conformidad del PO. Cloud queda en consulta el tiempo de retención | PEVE |
| Retiro | Revocar secretos de Cloud. Expediente D9 a D11 | Seguridad y Legal |

### E.2 Temporal Cloud no disponible (liquidación o interrupción)

| Tiempo | Acción | Responsable |
|---|---|---|
| Inicio | Incidente de proveedor. Modo estresado. No se espera exportación ni soporte | PEVE y Continuidad |
| Primeras 2 horas | Workers, clientes o funciones solo hacia el destino aprobado. Schedules reanudados solo ahí | Equipos APOQ y NREM |
| 2 a 24 horas | Reabrir únicamente lo que el core, NREM o el outbox muestran como pendiente. Bloquear efectos de negocio ya confirmados | PO y operaciones |
| 1 a 7 días | Colas de excepción para casos indeterminados. Aviso a las áreas de control si el servicio es significativo | RNF y Continuidad |
| 30 días | Retener las exportaciones ya obtenidas. Documentar el historial no recuperable. Cerrar el contrato si queda entidad | PEVE y Legal |

En E.2 no hay reversa hacia Cloud.

---

## Anexo F. Criterio de fase 0 completa

La fase 0 se considera completa cuando PEVE puede marcar afirmativo en todos los puntos. F14 se resuelve primero: condiciona cómo se leen F1 a F3, F7 y F8. Mientras exista un negativo, se mantiene el riesgo residual descrito en la sección 12.

| Código | Criterio | Sí / No |
|---|---|---|
| F14 | Destino confirmado: Self-Hosted, o acta D13 de una opción 04.6 | |
| F1 | Plataforma destino con alta disponibilidad, respaldo y restauración ensayada (clúster Self-Hosted, o Scheduler / Dapr / Restate según F14) | |
| F2 | Segregación por ambiente de APOQ y NREM en el destino (namespaces Self-Hosted, o task hubs / apps Dapr / deployments Restate) | |
| F3 | Indicador que impide ejecución simultánea con Cloud, y reversa solo si Cloud responde. Conexión dual Temporal únicamente si F14 es Self-Hosted | |
| F4 | Exportación periódica de historiales de Cloud hacia almacenamiento del Banco, verificada | |
| F5 | Anexo C de APOQ y NREM firmado por el PO, con nombres reales de workflow | |
| F6 | Tiempos de recuperación y ventana de APOQ y NREM vigentes en Continuidad | |
| F7 | Observabilidad del destino con alertas equivalentes | |
| F8 | Ejercicio técnico no crítico ejecutado (conexión dual si Self-Hosted; flujo reescrito si 04.6) | |
| F9 | Ejercicio de mesa “Cloud no responde” ejecutado con APOQ y NREM | |
| F10 | Inventario A actualizado en los últimos 90 días | |
| F11 | Legal tiene localizado el contrato, el preaviso y los contactos de Temporal Technologies Inc. | |
| F12 | La instancia aprobadora ha recibido la versión vigente del plan | |
| F13 | Arquitectura conformada: sección 04 si Self-Hosted; patrón 04.6 si F14 cambió el destino | |

---

## Anexo G. Información a completar por los dueños

Los siguientes datos deben registrarse antes de declarar completa la fase 0.

| Dato | Dueño | Uso |
|---|---|---|
| Tiempo máximo de recuperación, pérdida máxima de información y ventana de APOQ y NREM | PO y Continuidad | Secciones 05 y 10, Anexo A |
| Nombres internos de workflows, colas de tareas y schedules | Equipos APOQ y NREM | Anexo C |
| Responsables nominativos | PEVE y dueños | Anexos A y D |
| Versión del servidor Temporal, particiones de historial y dimensionamiento AKS (si Self-Hosted) | PEVE | Anexo B |
| Runtime, SKU y región del Durable Task Scheduler o versión Dapr + state store, o versión Restate / plan Enterprise (si 04.6) | PEVE | Anexo B.4 |
| Lenguaje y SDK actuales de APOQ y NREM (condiciona Functions, Dapr o Restate) | Equipos APOQ y NREM | Sección 04.6 |
| Ubicación y retención de la exportación de historiales | PEVE y Seguridad | Sección 09 y fase 0 |
| Umbral de liquidez y de nivel de servicio para declarar vigilancia | RNF | Sección 06 |
| Instancia aprobadora concreta (comité o gerencia) | PEVE / gobierno | Sección 07 |
| Destino de la fase 0 (Self-Hosted o 04.6) | Instancia / Arquitectura / Compras | Sección 04.6 y paso 0.0 |
