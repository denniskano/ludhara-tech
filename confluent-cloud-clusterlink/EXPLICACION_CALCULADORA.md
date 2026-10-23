# Explicación Detallada: Calculadora Private Link - Confluent Cloud Dedicated

## Tabla de Contenidos
1. [Introducción](#introducción)
2. [Conceptos Fundamentales](#conceptos-fundamentales)
3. [Arquitectura de la Calculadora](#arquitectura-de-la-calculadora)
4. [Componentes Principales](#componentes-principales)
5. [Lógica de Cálculo](#lógica-de-cálculo)
6. [Costos y Tarifas](#costos-y-tarifas)
7. [Casos de Uso](#casos-de-uso)
8. [Consideraciones y Limitaciones](#consideraciones-y-limitaciones)
9. [Guía de Uso](#guía-de-uso)

---

## Introducción

### ¿Qué es esta calculadora?

La **Calculadora Private Link para Confluent Cloud Dedicated** es una herramienta que estima los costos mensuales de ejecutar clusters Kafka Dedicated en Confluent Cloud con conectividad privada (Private Link / Private Service Connect) y opcionalmente con Cluster Linking entre diferentes clouds o regiones.

### Propósito

- **Planificación de costos**: Estimar el costo total mensual antes de implementar
- **Comparación de escenarios**: Evaluar diferentes configuraciones (intra-cloud vs cross-cloud, unidireccional vs bidireccional)
- **Dimensionamiento**: Calcular los CKU necesarios basados en throughput
- **Infraestructura CSP**: Determinar cuántos endpoints del cloud provider se necesitan

### Versiones Disponibles

1. **HTML** (`calculadora-privatelink.html`): Interfaz web interactiva, funciona en el navegador
2. **Excel** (`calculadora-privatelink.xlsx`): Hoja de cálculo con fórmulas nativas, generada por `build_excel.py`

---

## Conceptos Fundamentales

### 1. CSP (Cloud Service Provider)

**CSP = Cloud Service Provider** (Proveedor de Servicios en la Nube)

En el contexto de esta calculadora, CSP se refiere específicamente a los **costos que cobra el proveedor de la nube** (AWS, Azure o GCP) por los servicios de conectividad privada, **no** los costos de Confluent.

#### Componentes del Costo CSP:

##### a) **CSP Endpoint ($/hora)**
- **AWS**: VPC Endpoint costo por hora por zona de disponibilidad
- **Azure**: Private Endpoint costo por hora
- **GCP**: Private Service Connect endpoint costo por hora

**Precio por defecto**: $0.01/hora

##### b) **CSP Data Processed ($/GB)**
- Costo por GB de datos procesados a través de los endpoints privados
- Se aplica tanto a datos de entrada (produce) como de salida (consume)

**Precio por defecto**: $0.01/GB

#### Diferencia CSP vs Confluent:

```
┌─────────────────────────────────────┐
│   COSTO TOTAL MENSUAL               │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────┐     │
│  │  COSTOS CONFLUENT         │     │
│  │  - CKU (compute)          │     │
│  │  - Kafka ingress/egress   │     │
│  │  - Storage                │     │
│  │  - Cluster Linking hourly │     │
│  │  - ClusterLinkingRead     │     │
│  │  - ClusterLinkingWrite    │     │
│  └───────────────────────────┘     │
│                                     │
│  ┌───────────────────────────┐     │
│  │  COSTOS CSP               │     │
│  │  - Endpoints ($/hora)     │     │
│  │  - Data processed ($/GB)  │     │
│  └───────────────────────────┘     │
│                                     │
└─────────────────────────────────────┘
```

### 2. Cluster Linking

**Cluster Linking** es la funcionalidad de Confluent Cloud que permite replicar topics entre clusters Kafka, incluso entre diferentes clouds o regiones.

#### Características:
- **Dirección**:
  - **Unidirectional**: Un link A → B (1 link)
  - **Bidirectional**: Dos links A ⇄ B (2 links)
  - **None**: Sin Cluster Linking
  
- **Se cobra el objeto del link**: Hay cargo aunque no exista mirror topic ni throughput
- **Metadata incluida**: El throughput facturable incluye configs, offsets y ACLs

#### Componentes de Costo:

##### a) **Hourly Rate ($/hora por cluster)**
Depende de la configuración:

| Escenario | Precio Base | Condición |
|-----------|-------------|-----------|
| Internet endpoints | $0.25/h | Por cluster con endpoints públicos |
| Intra-cloud private | $0.50/h | Mismo cloud, ambos con Private Link |
| Cross-cloud private | $2.50/h | Diferentes clouds, ambos private |
| Cross-cloud private Premium | $5.00/h | Cross-cloud + región Premium |

**Importante**: 
- Ambos clusters pagan el hourly
- Bidirectional = 2 links, así que se multiplica por 2
- El multiplier regional se aplica al $0.50 intra-cloud, pero NO a los $2.50/$5.00 cross-cloud

##### b) **ClusterLinkingRead ($/GB)**
- **Precio fijo**: $0.25/GB
- Se aplica al cluster **source** (el que lee los datos)
- Incluye metadata (configs, consumer offsets, ACLs)
- **Confluent paga el egress del cloud provider** (no se cobra aparte)
- Se multiplica por el regional multiplier del source cluster

##### c) **ClusterLinkingWrite ($/GB)**
- Mismo precio que **KafkaNetworkWrite** del destination cluster
- **NO se cobra Kafka ingress adicional** (solo el ClusterLinkingWrite)
- Se aplica al cluster **destination** (el que recibe los datos)

### 3. Private Link / Private Service Connect

Conectividad privada entre tu VPC/VNet y Confluent Cloud, sin pasar por internet público.

#### Por Cloud Provider:

##### **AWS PrivateLink**
- **Objeto**: VPC Endpoint
- **Multi-zone**: 1 VPC Endpoint con subnet en cada AZ del cluster (3 AZ = 3 subnets)
- **Single-zone**: 1 VPC Endpoint con 1 subnet
- **Unidades CSP**: Se cuenta por AZ-hora (1 endpoint × N AZ)
- **Limitación**: Las AZ del VPC deben coincidir con las del cluster
- **Sin soporte cross-region**: PrivateLink Attachment no funciona entre regiones

##### **Azure Private Link**
- **Objeto**: Private Endpoint (PE)
- **Multi-zone**: 3 Private Endpoints (uno por Service Alias zonal)
- **Single-zone**: 1 Private Endpoint
- **Unidades CSP**: Por endpoint (multi = 3 endpoints)
- **Ventaja**: El PE puede estar en otra región que el Private Link Service

##### **Google Cloud Private Service Connect (PSC)**
- **Objeto**: PSC Endpoint
- **Multi-zone**: 3 PSC endpoints (uno por Service Attachment zonal)
- **Single-zone**: 1 PSC endpoint
- **Unidades CSP**: Por endpoint (multi = 3 endpoints)
- **Limitación inicial**: El attachment es same-region
- **Post-setup**: Se puede habilitar PSC Global Access

### 4. CKU (Confluent Kafka Unit)

**CKU** es la unidad de capacidad en Confluent Cloud Dedicated.

#### Capacidad por CKU:
- **Ingress**: 60 MBps (megabytes por segundo)
- **Egress**: 180 MBps
- **Partitions**: 4,500 (pre-replication)

#### Mínimos:
- **Multi-zone**: Mínimo 2 CKU
- **Single-zone**: Mínimo 1 CKU

#### Máximos (soft limits):
- **AWS**: 252 CKU
- **Azure**: 100 CKU
- **GCP**: 152 CKU

#### Compra:
- **Credit card**: Hasta 4 CKU
- **Invoice / Cloud billing**: Hasta 24 CKU (más por request especial)

### 5. Regiones Premium

Algunas regiones son marcadas como **Premium** y afectan el costo del Cluster Linking cross-cloud private.

#### Impacto:
- **Solo afecta**: Cluster Linking cross-cloud private networking
- **Hourly rate**: $5.00/h en lugar de $2.50/h
- **NO afecta**: Tarifas intra-cloud (siguen usando el multiplier normal)

#### Ejemplos de regiones Premium:
- AWS: sa-east-1 (São Paulo), eu-central-1 (Frankfurt), eu-west-2 (London), ap-south-1 (Mumbai), etc.
- Azure: brazilsouth, mexicocentral, uksouth, japaneast, etc.
- GCP: southamerica-east1, europe-west2, asia-south1, etc.

### 6. Regional Multiplier

El **multiplier regional** es un factor que se aplica a ciertos precios base de Dedicated.

#### Se aplica a:
- CKU hourly base
- KafkaNetworkWrite (ingress) base
- KafkaNetworkRead (egress) base
- ClusterLinkingRead

#### NO se aplica a:
- Cluster Linking hourly cross-cloud ($2.50 / $5.00 ya son finales)
- Storage

#### Valores comunes:
- **1.0×**: Regiones estándar (us-east-1, eastus, us-central1, etc.)
- **1.1×**: Algunas regiones Asia-Pacífico y Europa
- **1.2×**: Regiones más costosas (LATAM, India, Middle East, África)

---

## Arquitectura de la Calculadora

### Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUTS DEL USUARIO                        │
├─────────────────────────────────────────────────────────────┤
│  Cluster A              Cluster B           Cluster Linking │
│  - Cloud (AWS/Azure/GCP) - Cloud           - Dirección      │
│  - Región                - Región          - GB A→B         │
│  - Multi/Single-zone     - Multi/Single    - GB B→A         │
│  - CKU                   - CKU             - Tarifas (edit) │
│  - VNets/VPCs            - VNets/VPCs                       │
│  - Produce GB/mes        - Produce                          │
│  - Consume GB/mes        - Consume                          │
│  - Storage GB            - Storage                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   LOOKUPS Y VALIDACIÓN                       │
├─────────────────────────────────────────────────────────────┤
│  - Lookup región → Premium flag, Jio flag, Multiplier      │
│  - Validación: región existe en cloud                        │
│  - Cross-cloud detection (A.cloud ≠ B.cloud)               │
│  - Cálculo de links (0, 1 o 2)                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  CÁLCULOS INTERMEDIOS                        │
├─────────────────────────────────────────────────────────────┤
│  - Hourly rate A/B (determinar $0.50, $2.50 o $5.00)       │
│  - Unidades CSP (AZ × nets)                                 │
│  - GB efectivos (0 si direction=None)                       │
│  - MBps requeridos → CKU sugeridos                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CÁLCULO DE COSTOS                         │
├─────────────────────────────────────────────────────────────┤
│  CONFLUENT                                                   │
│  - CKU: CKU × $base × multiplier × hours                   │
│  - Kafka ingress: GB × $base × multiplier                  │
│  - Kafka egress: GB × $base × multiplier                   │
│  - Storage: GB × RF × $base                                 │
│  - Link hourly: rate × links × hours                        │
│  - ClusterLinkingRead: GB × $0.25 × multiplier             │
│  - ClusterLinkingWrite: GB × KafkaNetworkWrite dest        │
│                                                              │
│  CSP                                                         │
│  - Endpoints: units × $/h × hours + GB × $/GB              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       OUTPUTS                                │
├─────────────────────────────────────────────────────────────┤
│  - Total mensual (Confluent + CSP)                          │
│  - Desglose por concepto                                     │
│  - Endpoints a provisionar                                   │
│  - CKU sugeridos                                            │
│  - Alertas (Jio, bajo CKU, premium, etc.)                  │
│  - Consideraciones oficiales                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. Base de Datos de Regiones

Contiene información de todas las regiones soportadas:

```javascript
{
  id: "us-east-1",           // ID de la región
  name: "N. Virginia",        // Nombre descriptivo
  premium: false,             // ¿Es premium para cross-cloud private?
  jio: false,                 // ¿Es Jio (sin Private Link)?
  mult: 1.0                   // Multiplier regional
}
```

**Total de regiones**: ~120 regiones (AWS: 29, Azure: 35, GCP: 25)

### 2. Constantes de Tarifas

#### Cluster Linking (Oficiales - documentadas)
```javascript
CL_PUBLIC_HOUR        = $0.25  // Hourly con internet endpoints
CL_PRIVATE_HOUR       = $0.50  // Hourly intra-cloud private
CL_XCLOUD_HOUR        = $2.50  // Hourly cross-cloud private
CL_XCLOUD_PREMIUM_HOUR = $5.00 // Hourly cross-cloud private + Premium
CL_READ_GB            = $0.25  // ClusterLinkingRead por GB
```

#### Dedicated (Editables - no son list price público)
```javascript
CKU_HOUR           = $1.50  // Base por defecto
KAFKA_IN_GB        = $0.10  // KafkaNetworkWrite base
KAFKA_OUT_GB       = $0.05  // KafkaNetworkRead base
STORAGE_GB_MONTH   = $0.08  // Post-replication
CSP_PE_HOUR        = $0.01  // Endpoint CSP por hora
CSP_PE_GB          = $0.01  // Data processed CSP por GB
```

#### Otras Constantes
```javascript
HOURS_MONTH        = 730    // 24 × 365 / 12
REPL_FACTOR        = 3      // Replication factor Dedicated
CKU_IN_MBPS        = 60     // Ingress MBps por CKU
CKU_OUT_MBPS       = 180    // Egress MBps por CKU
CKU_PARTITIONS     = 4500   // Partitions pre-RF por CKU
```

### 3. Inputs del Usuario

#### Por Cluster (A y B)
- **Cloud**: AWS / Azure / GCP
- **Region**: Lista filtrada según el cloud seleccionado
- **Availability**: Multi-zone (3 AZ) / Single-zone
- **CKU**: Número de CKUs (≥1 single, ≥2 multi)
- **VNets/VPCs cliente**: Cuántas redes del cliente se conectan
- **Produce GB/mes**: Tráfico de entrada desde clientes
- **Consume GB/mes**: Tráfico de salida hacia clientes
- **Storage pre-RF GB**: Almacenamiento antes de replicación

#### Cluster Linking
- **Dirección**: Unidirectional / Bidirectional / None
- **Mirror A→B GB/mes**: Datos replicados de A a B
- **Mirror B→A GB/mes**: Datos replicados de B a A (solo bidireccional)

### 4. Cálculos Intermedios

#### Detección de Escenario
```javascript
cross_cloud = (cluster_a.cloud !== cluster_b.cloud)
links = direction === "none" ? 0 : direction === "bi" ? 2 : 1
gb_ab_effective = direction === "none" ? 0 : gb_ab
gb_ba_effective = direction === "bi" ? gb_ba : 0
```

#### Hourly Rate del Link
```javascript
function linkHourly(cluster, other_cluster) {
  if (no_links) return 0;
  
  if (cross_cloud) {
    // Cross-cloud private
    if (cluster.region.premium) {
      return $5.00;  // Premium region
    } else {
      return $2.50;  // Standard region
    }
  } else {
    // Intra-cloud private
    return $0.50 × cluster.multiplier;
  }
}
```

#### Unidades CSP
```javascript
function cspUnits(cloud, availability, num_nets) {
  az_per_net = availability === "single" ? 1 : 3;
  
  if (cloud === "aws") {
    // AWS: 1 VPC endpoint × N AZ
    return {
      units: num_nets × az_per_net,  // AZ-horas
      endpoints: num_nets             // Número de objetos
    };
  } else {
    // Azure/GCP: 1 endpoint por AZ
    return {
      units: num_nets × az_per_net,
      endpoints: num_nets × az_per_net
    };
  }
}
```

#### CKU Sugeridos
```javascript
function suggestedCKU(cluster, incoming_gb, outgoing_gb) {
  // Convertir GB/mes a MBps
  incoming_mbps = (incoming_gb × 1024) / (HOURS_MONTH × 3600);
  outgoing_mbps = (outgoing_gb × 1024) / (HOURS_MONTH × 3600);
  
  // CKU por ingress
  cku_in = Math.ceil(incoming_mbps / CKU_IN_MBPS);
  
  // CKU por egress
  cku_out = Math.ceil(outgoing_mbps / CKU_OUT_MBPS);
  
  // Mínimo según availability
  min_cku = cluster.availability === "multi" ? 2 : 1;
  
  return Math.max(min_cku, cku_in, cku_out);
}

// Para cluster A
incoming_a = produce_a + gb_ba;  // Cliente + mirror desde B
outgoing_a = consume_a + gb_ab;  // Cliente + mirror hacia B
suggested_cku_a = suggestedCKU(cluster_a, incoming_a, outgoing_a);

// Para cluster B
incoming_b = produce_b + gb_ab;  // Cliente + mirror desde A
outgoing_b = consume_b + gb_ba;  // Cliente + mirror hacia A
suggested_cku_b = suggestedCKU(cluster_b, incoming_b, outgoing_b);
```

---

## Lógica de Cálculo

### Desglose Completo de Costos

#### 1. CKU (Compute)
```
Costo = CKU × CKU_HOUR_BASE × MULTIPLIER × HOURS_MONTH

Cluster A: 2 × $1.50 × 1.0 × 730 = $2,190.00
Cluster B: 2 × $1.50 × 1.0 × 730 = $2,190.00
```

#### 2. Kafka Ingress (KafkaNetworkWrite)
```
Costo = GB_producidos × KAFKA_IN_GB_BASE × MULTIPLIER

Cluster A: 400 GB × $0.10 × 1.0 = $40.00
Cluster B: 0 GB × $0.10 × 1.0 = $0.00

Nota: Mirror NO se cobra como Kafka ingress en destination
```

#### 3. Kafka Egress (KafkaNetworkRead)
```
Costo = GB_consumidos × KAFKA_OUT_GB_BASE × MULTIPLIER

Cluster A: 800 GB × $0.05 × 1.0 = $40.00
Cluster B: 400 GB × $0.05 × 1.0 = $20.00

Nota: Mirror NO se cobra como Kafka egress en source (está en ClusterLinkingRead)
```

#### 4. Storage
```
Costo = GB_pre_RF × REPL_FACTOR × STORAGE_GB_MONTH

Cluster A: 200 GB × 3 × $0.08 = $48.00
Cluster B: 200 GB × 3 × $0.08 = $48.00

Nota: Se cobra post-replication (RF=3 ≈ 3× el volumen)
```

#### 5. Cluster Linking Hourly
```
Costo = HOURLY_RATE × NUM_LINKS × HOURS_MONTH

Escenario: Azure eastus2 → AWS us-east-1 (cross-cloud, no premium)
Cluster A: $2.50 × 1 × 730 = $1,825.00
Cluster B: $2.50 × 1 × 730 = $1,825.00

Si fuera bidirectional: $2.50 × 2 × 730 = $3,650.00 (cada cluster)
```

#### 6. ClusterLinkingRead (Egress de Mirror)
```
Costo = GB_mirror × CL_READ_GB × MULTIPLIER_SOURCE

A→B: 500 GB × $0.25 × 1.0 = $125.00  (paga A, el source)
B→A: 0 GB × $0.25 × 1.0 = $0.00      (no hay bidirectional)
```

#### 7. ClusterLinkingWrite (Ingress de Mirror)
```
Costo = GB_mirror × KAFKA_IN_GB_BASE × MULTIPLIER_DEST

A→B: 500 GB × $0.10 × 1.0 = $50.00   (paga B, el destination)
B→A: 0 GB × $0.10 × 1.0 = $0.00
```

#### 8. CSP Endpoints
```
Costo = UNITS × CSP_PE_HOUR × HOURS_MONTH + GB_cliente × CSP_PE_GB

Cluster A (Azure multi-zone, 1 VNet):
  Units = 1 VNet × 3 AZ = 3 endpoints
  GB_cliente = 400 produce + 800 consume = 1,200 GB
  Costo = 3 × $0.01 × 730 + 1,200 × $0.01 = $21.90 + $12.00 = $33.90

Cluster B (AWS multi-zone, 1 VPC):
  Units = 1 VPC × 3 AZ = 3 AZ-horas (pero 1 endpoint)
  GB_cliente = 0 produce + 400 consume = 400 GB
  Costo = 3 × $0.01 × 730 + 400 × $0.01 = $21.90 + $4.00 = $25.90
```

### Resumen Total (Ejemplo)

```
CONFLUENT:
  CKU A + B                        $4,380.00
  Kafka ingress A + B              $40.00
  Kafka egress A + B               $60.00
  Storage A + B                    $96.00
  Cluster Linking hourly A + B     $3,650.00
  ClusterLinkingRead A→B           $125.00
  ClusterLinkingWrite A→B          $50.00
  ────────────────────────────────────────
  Subtotal Confluent               $8,401.00

CSP:
  Endpoints A                      $33.90
  Endpoints B                      $25.90
  ────────────────────────────────────────
  Subtotal CSP                     $59.80

TOTAL USD / MES                    $8,460.80
```

---

## Costos y Tarifas

### Matriz de Precios de Cluster Linking Hourly

| Escenario | Source | Destination | Cross-cloud? | Premium? | Price/cluster/h |
|-----------|--------|-------------|--------------|----------|-----------------|
| Internet | Public | Any | N/A | N/A | $0.25 |
| Intra-cloud private | AWS Private | AWS Private | No | N/A | $0.50 × mult |
| Intra-cloud private | Azure Private | Azure Private | No | N/A | $0.50 × mult |
| Intra-cloud private | GCP Private | GCP Private | No | N/A | $0.50 × mult |
| Cross-cloud private | AWS Private | Azure Private | Yes | No | $2.50 |
| Cross-cloud private | AWS Private | GCP Private | Yes | No | $2.50 |
| Cross-cloud private | Azure Private | GCP Private | Yes | No | $2.50 |
| Cross-cloud private + Premium | Any Private | Premium region | Yes | Yes | $5.00 |

**Notas**:
- Ambos clusters pagan
- Bidirectional multiplica por 2 el número de links
- El multiplier regional solo se aplica al $0.50 intra-cloud

### Costos de CSP por Cloud Provider

#### AWS PrivateLink (Precios de referencia US)
```
VPC Endpoint: ~$0.01/hora por AZ
Data Processed: ~$0.01/GB

Multi-zone (3 AZ):
  - 1 VPC endpoint con 3 subnets
  - Costo: 3 AZ × $0.01/h = $0.03/h = $21.90/mes

Single-zone (1 AZ):
  - 1 VPC endpoint con 1 subnet
  - Costo: 1 AZ × $0.01/h = $0.01/h = $7.30/mes
```

#### Azure Private Link
```
Private Endpoint: ~$0.01/hora
Data Processed: ~$0.01/GB

Multi-zone (3 AZ):
  - 3 Private Endpoints (uno por Service Alias zonal)
  - Costo: 3 PE × $0.01/h = $0.03/h = $21.90/mes

Single-zone (1 AZ):
  - 1 Private Endpoint
  - Costo: 1 PE × $0.01/h = $0.01/h = $7.30/mes
```

#### Google Cloud PSC
```
PSC Endpoint: ~$0.01/hora
Data Processed: ~$0.01/GB

Multi-zone (3 zones):
  - 3 PSC endpoints (uno por Service Attachment)
  - Costo: 3 PSC × $0.01/h = $0.03/h = $21.90/mes

Single-zone (1 zone):
  - 1 PSC endpoint
  - Costo: 1 PSC × $0.01/h = $0.01/h = $7.30/mes
```

### Ejemplo de Sensibilidad al Volumen

**Escenario Base**: 500 GB/mes de mirror A→B

| Concepto | Formula | Costo |
|----------|---------|-------|
| ClusterLinkingRead | 500 × $0.25 | $125.00 |
| ClusterLinkingWrite | 500 × $0.10 | $50.00 |
| **Total egress** | | **$175.00** |

**Escenario 10× volumen**: 5,000 GB/mes

| Concepto | Formula | Costo |
|----------|---------|-------|
| ClusterLinkingRead | 5,000 × $0.25 | $1,250.00 |
| ClusterLinkingWrite | 5,000 × $0.10 | $500.00 |
| **Total egress** | | **$1,750.00** |

**Incremento**: 10× volumen → 10× costo de egress (lineal)

**Cluster Linking hourly NO cambia con el volumen** (fijo por hora)

---

## Casos de Uso

### Caso 1: Disaster Recovery (DR) Intra-Cloud

**Requisitos**:
- Cluster primario en Azure East US 2
- Cluster secundario en Azure West US 2 (misma organization)
- Replicación unidireccional asíncrona
- 1 TB/mes de mirror

**Configuración**:
```
Cluster A (Primary):
  Cloud: Azure
  Region: eastus2 (multiplier 1.0)
  Availability: Multi-zone
  CKU: 4
  VNets: 2 (producción + staging)
  Produce: 2,000 GB/mes
  Consume: 3,000 GB/mes
  Storage: 1,000 GB

Cluster B (DR):
  Cloud: Azure
  Region: westus2 (multiplier 1.0)
  Availability: Multi-zone
  CKU: 3 (menor porque solo consume DR)
  VNets: 1 (solo para validación)
  Produce: 0 GB/mes
  Consume: 500 GB/mes (validación ocasional)
  Storage: 1,000 GB

Cluster Linking:
  Direction: Unidirectional A→B
  Mirror A→B: 1,000 GB/mes
```

**Resultado**:
```
CONFLUENT:
  CKU (4+3) × $1.50 × 1.0 × 730h           $7,665.00
  Kafka ingress A: 2,000 GB × $0.10         $200.00
  Kafka egress A: 3,000 GB × $0.05          $150.00
  Kafka egress B: 500 GB × $0.05            $25.00
  Storage (1000+1000) × 3 × $0.08           $480.00
  Link hourly (0.50×1.0) × 1 × 730 × 2      $730.00
  ClusterLinkingRead: 1,000 × $0.25 × 1.0   $250.00
  ClusterLinkingWrite: 1,000 × $0.10 × 1.0  $100.00
  ────────────────────────────────────────
  Subtotal Confluent                        $9,600.00

CSP (Azure PE):
  A: 6 PE × $0.01 × 730 + 5,000 GB × $0.01  $93.80
  B: 3 PE × $0.01 × 730 + 500 GB × $0.01    $26.90
  ────────────────────────────────────────
  Subtotal CSP                              $120.70

TOTAL                                       $9,720.70/mes
```

**Insights**:
- Intra-cloud private es económico ($0.50/h vs $2.50 cross-cloud)
- El hourly del link ($730) es significativo pero fijo
- El DR cluster puede ser más pequeño (3 CKU vs 4 CKU)

### Caso 2: Multi-Cloud Aggregation

**Requisitos**:
- Clusters regionales en AWS (us-east-1) y GCP (us-central1)
- Cluster central en Azure (eastus2)
- Bidirectional linking para agregación y back-sync
- Alta throughput

**Configuración**:
```
Cluster A (AWS Regional):
  Cloud: AWS
  Region: us-east-1 (multiplier 1.0, no premium)
  Availability: Multi-zone
  CKU: 6
  VPCs: 3
  Produce: 5,000 GB/mes
  Consume: 4,000 GB/mes
  Storage: 3,000 GB

Cluster B (Azure Central):
  Cloud: Azure
  Region: eastus2 (multiplier 1.0, no premium)
  Availability: Multi-zone
  CKU: 8
  VNets: 4
  Produce: 8,000 GB/mes
  Consume: 6,000 GB/mes
  Storage: 5,000 GB

Cluster Linking A↔B:
  Direction: Bidirectional
  Mirror A→B: 3,000 GB/mes
  Mirror B→A: 2,000 GB/mes

(También hay un Cluster C en GCP con linking similar)
```

**Resultado (solo A↔B)**:
```
CONFLUENT:
  CKU (6+8) × $1.50 × 1.0 × 730h            $15,330.00
  Kafka ingress: (5,000+8,000) × $0.10      $1,300.00
  Kafka egress: (4,000+6,000) × $0.05       $500.00
  Storage: (3,000+5,000) × 3 × $0.08        $1,920.00
  Link hourly: $2.50 × 2 links × 730 × 2    $7,300.00  ⚠️ Cross-cloud
  ClusterLinkingRead A→B: 3,000 × $0.25     $750.00
  ClusterLinkingWrite A→B: 3,000 × $0.10    $300.00
  ClusterLinkingRead B→A: 2,000 × $0.25     $500.00
  ClusterLinkingWrite B→A: 2,000 × $0.10    $200.00
  ────────────────────────────────────────
  Subtotal Confluent                        $28,100.00

CSP:
  AWS: 3 VPC × 3 AZ × $0.01 × 730 + 9,000 GB  $155.70
  Azure: 4 VNet × 3 PE × $0.01 × 730 + 14,000  $227.60
  ────────────────────────────────────────
  Subtotal CSP                              $383.30

TOTAL                                       $28,483.30/mes
```

**Insights**:
- Cross-cloud private es 5× más caro en hourly ($2.50 vs $0.50)
- Bidirectional duplica el número de links (2× el costo hourly)
- El hourly del link ($7,300) es ~26% del costo total de Confluent
- Multi-cloud aggregation es costoso pero necesario para ciertos casos

### Caso 3: Hybrid Cloud Bridge

**Requisitos**:
- Cluster en AWS (legacy, internet endpoints)
- Cluster en Azure (nuevo, Private Link)
- Migración gradual con Cluster Linking

**Configuración**:
```
Cluster A (AWS Legacy):
  Cloud: AWS
  Region: us-west-2 (multiplier 1.0)
  Availability: Single-zone
  CKU: 2
  VPCs: 0 (internet)  ⚠️ No Private Link
  Produce: 1,000 GB/mes
  Consume: 1,500 GB/mes
  Storage: 500 GB

Cluster B (Azure New):
  Cloud: Azure
  Region: eastus (multiplier 1.0)
  Availability: Multi-zone
  CKU: 4
  VNets: 2
  Produce: 500 GB/mes
  Consume: 800 GB/mes
  Storage: 800 GB

Cluster Linking:
  Direction: Unidirectional A→B
  Mirror A→B: 1,200 GB/mes
```

**Resultado**:
```
CONFLUENT:
  CKU (2+4) × $1.50 × 1.0 × 730h            $6,570.00
  Kafka ingress: (1,000+500) × $0.10        $150.00
  Kafka egress: (1,500+800) × $0.05         $115.00
  Storage: (500+800) × 3 × $0.08            $312.00
  Link hourly A: $0.25 × 1 × 730            $182.50   ⚠️ A tiene internet
  Link hourly B: $2.50 × 1 × 730            $1,825.00 ⚠️ B private cross-cloud
  ClusterLinkingRead: 1,200 × $0.25         $300.00
  ClusterLinkingWrite: 1,200 × $0.10        $120.00
  ────────────────────────────────────────
  Subtotal Confluent                        $9,574.50

CSP:
  AWS: N/A (internet)                       $0.00
  Azure: 2 VNet × 3 PE × $0.01 × 730 + 1,300  $56.80
  ────────────────────────────────────────
  Subtotal CSP                              $56.80

TOTAL                                       $9,631.30/mes
```

**Insights**:
- Internet + Private = diferentes hourly rates
- Cluster A paga $0.25/h (internet)
- Cluster B paga $2.50/h (private cross-cloud)
- Asimétrico pero funcional para migración

---

## Consideraciones y Limitaciones

### Restricciones Importantes

#### 1. Misma Organization
```
❌ NO SOPORTADO:
  Organization A (AWS) → Organization B (Azure)

✅ SOPORTADO:
  Organization X:
    - Cluster A (AWS)
    - Cluster B (Azure)
```

Dedicated private-to-private Cluster Linking **requiere la misma Confluent Cloud Organization**.

#### 2. No Conversión de Clusters
```
❌ IMPOSIBLE:
  Cluster existente (internet) → Convertir a Private Link

✅ SOLUCIÓN:
  1. Crear nueva Confluent Cloud Network (tipo PRIVATELINK)
  2. Crear cluster nuevo en esa network
  3. Usar Cluster Linking para migrar datos
  4. Deprecar cluster viejo
```

Un cluster Dedicated existente **NO se puede cambiar** a Private Link después de creado.

#### 3. Regiones Jio sin Private Link
```
❌ NO DISPONIBLE Private Link:
  - jioindiawest (Azure)
  - jioindiacentral (Azure)

✅ ALTERNATIVA:
  - VNet Peering para Dedicated (solo Azure)
```

#### 4. Limitaciones por Cloud Provider

##### AWS PrivateLink
- **AZ matching requerido**: Las AZ del VPC deben coincidir con las del cluster
- **No cross-region**: PrivateLink Attachment Connections no funciona entre regiones
- **use1-az3 no se usa**: En us-east-1, esta AZ no está disponible para Confluent
- **Security Group**: Permitir TCP 80, 443, 9092
- **DNS**: Desmarcar "Enable DNS name" en el VPC endpoint

##### Azure Private Link
- **Multi-zone = 3 PE**: Requiere tres Private Endpoints distintos
- **Registro de Subscription**: El Subscription ID debe registrarse en Private Link Access
- **Zone name**: Omitir el "lkc-" si viene en el DNS domain

##### Google Cloud PSC
- **Attach same-region inicial**: El Service Attachment no es cross-region al inicio
- **PSC Global Access**: Se puede habilitar después en el forwarding rule
- **Subnets deben cubrir zones**: Las subnets del cliente deben estar en las mismas zonas que el cluster

### Servicios que Requieren Internet

Aunque uses Private Link para Kafka, estos servicios **aún requieren internet**:

```
✅ Private Link:
  - Kafka brokers
  - ksqlDB (después de provisioned)
  - Algunos casos de Flink/Schema Registry

❌ Requieren Internet:
  - Schema Registry (en general)
  - Confluent CLI (control plane)
  - Provisioning de ksqlDB (inicial)
  - Cloud Console (requiere config extra)
```

**Connectors**:
- Source/Sink hacia recursos privados: Usar **Egress Private Link Endpoints** (diferente del inbound PL del cluster)

### DNS y Brokers

#### Recomendaciones:
- **Private DNS** es la opción recomendada
- **Records necesarios**:
  - `*` (wildcard para bootstrap)
  - Records zonales por AZ (A records o CNAME)
  
#### Advertencias:
- ❌ NO hardcodear nombres de brokers (no son estáticos)
- ❌ NO asumir que los brokers son estables
- ✅ Usar bootstrap servers y dejar que el cliente resuelva

### Capacidad y Escalado

#### Guía de Dimensionamiento CKU:

```python
def calculate_cku_needed(ingress_mbps, egress_mbps, partitions, availability):
    # Por throughput
    cku_for_ingress = ceil(ingress_mbps / 60)
    cku_for_egress = ceil(egress_mbps / 180)
    
    # Por partitions
    cku_for_partitions = ceil(partitions / 4500)
    
    # Máximo de los tres
    needed = max(cku_for_ingress, cku_for_egress, cku_for_partitions)
    
    # Mínimo según availability
    minimum = 2 if availability == "multi-zone" else 1
    
    return max(needed, minimum)
```

#### Límites de Compra:
```
Credit Card:      ≤ 4 CKU
Invoice Billing:  ≤ 24 CKU (más por request)

Soft Max:
  AWS:   252 CKU
  Azure: 100 CKU
  GCP:   152 CKU
```

### Consideraciones de Costo

#### Descuentos por Volumen
**ClusterLinkingRead** (egress) tiene descuentos por volumen disponibles:
- ✅ Contactar al account team para descuentos en alto volumen
- 📊 Los descuentos no están publicados (no son self-service)

#### Qué NO se Cobra Dos Veces
```
✅ Mirror NO suma:
  - Kafka ingress en destination (solo ClusterLinkingWrite)
  - Kafka egress en source (solo ClusterLinkingRead)

✅ Storage:
  - Se cobra post-replication (RF=3 ≈ 3× volumen escrito)
  - NO se cobra por replication en sí

❌ Produce REST v3:
  - Suma $0.01/GB EXTRA antes del multiplier
```

---

## Guía de Uso

### Versión HTML

#### Paso 1: Abrir la Calculadora
```bash
# Desde el directorio del proyecto
open calculadora-privatelink.html
# o
firefox calculadora-privatelink.html
```

#### Paso 2: Configurar Cluster A (Source)
1. **Cloud**: Seleccionar AWS / Azure / GCP
2. **Región**: Elegir de la lista (filtrada por cloud)
3. **Availability**: Multi-zone (3 AZ) o Single-zone
4. **CKU**: Ingresar número (≥2 para multi-zone)
5. **VNets/VPCs cliente**: Número de redes que se conectan
6. **Produce cliente (GB/mes)**: Tráfico de entrada desde clientes
7. **Consume cliente (GB/mes)**: Tráfico de salida hacia clientes
8. **Storage pre-RF (GB)**: Almacenamiento antes de replicación

#### Paso 3: Configurar Cluster B (Destination)
(Mismos campos que Cluster A)

#### Paso 4: Configurar Cluster Linking
1. **Dirección del link**:
   - Unidirectional A→B (1 link)
   - Bidirectional (2 links)
   - Sin Cluster Linking (0 links)
2. **Mirror A→B (GB/mes)**: Datos replicados de A a B
3. **Mirror B→A (GB/mes)**: Solo si es bidirectional

#### Paso 5: Ajustar Tarifas (Opcional)
Expandir "Tarifas Dedicated editables":
- CKU ($/hora) base
- Kafka ingress ($/GB) base
- Kafka egress ($/GB) base
- Storage ($/GB-mes post-RF)
- Multiplier región A/B
- CSP endpoint ($/hora)
- CSP data processed ($/GB)
- Horas / mes (default 730)

#### Paso 6: Revisar Resultados
**Panel derecho - Estimado mensual**:
- Total USD/mes (grande, en teal)
- Desglose por concepto (tabla)
- Badges de alertas (Jio, Premium, bajo CKU, etc.)

**Private Link a provisionar**:
- Cantidad de endpoints por cluster
- Tipo de endpoint (VPCE / PE / PSC)
- DNS records necesarios
- CKU sugerido vs configurado

**Consideraciones oficiales**:
- Alertas rojas (Jio, conversión imposible)
- Advertencias amarillas (cross-cloud, Premium)
- Notas informativas (DNS, Internet residual)

### Versión Excel

#### Generar el Archivo
```bash
cd confluent-cloud-clusterlink
python3 build_excel.py
# Genera: calculadora-privatelink.xlsx
```

#### Hojas del Libro

##### 1. **Calculadora** (Principal)
**Celdas amarillas = inputs editables**

```
┌──────────────────────────────────────────────────┐
│  Cluster A              Cluster B                │
│  ┌────────────┐        ┌────────────┐           │
│  │ Cloud      │        │ Cloud      │           │
│  │ Region     │        │ Region     │           │
│  │ ...        │        │ ...        │           │
│  └────────────┘        └────────────┘           │
│                                                   │
│  Cluster Linking        Diagnóstico              │
│  ┌────────────┐        ┌────────────┐           │
│  │ Direccion  │        │ Premium A  │           │
│  │ Mirror GB  │        │ Cross-cloud│           │
│  └────────────┘        │ CKU suggest│           │
│                         └────────────┘           │
│                                                   │
│  Estimado mensual       Private Link             │
│  ┌────────────────┐    ┌────────────┐           │
│  │ Concepto  USD  │    │ A: N endpoints│        │
│  │ ───────── ───  │    │ B: N endpoints│        │
│  │ ...       ...  │    │ CKU A/B guide │        │
│  │ TOTAL    $X,XXX│    └────────────┘           │
│  └────────────────┘                              │
│                                                   │
│  Gráfico (barras)       Cómo usar                │
│  ┌────────────────┐    ┌────────────┐           │
│  │ ████████  CKU  │    │ 1. Cloud+Reg│          │
│  │ ████  Kafka    │    │ 2. Multi-zone│         │
│  │ ████████ Link  │    │ 3. Mirror GB │         │
│  │ █ CSP          │    │ ...         │          │
│  └────────────────┘    └────────────┘           │
└──────────────────────────────────────────────────┘
```

**Validaciones automáticas**:
- Dropdowns de Cloud (AWS/Azure/GCP)
- Dropdowns de Region (filtrado por Cloud con INDIRECT)
- Dropdowns de Availability (Multi-zone/Single-zone)
- Dropdowns de Dirección (Unidirectional/Bidirectional/None)

**Formato condicional**:
- Rojo si región Jio (sin Private Link)
- Ámbar si región Premium (cross-cloud $5/h)
- Rojo si región no válida para el cloud seleccionado

##### 2. **Tarifas**
Constantes editables:
- **Cluster Linking**: List prices oficiales (amarillo)
- **Dedicated**: Precios base no públicos (amarillo)
- **CKU caps**: Límites por cloud
- **Fuentes**: Links a documentación oficial

##### 3. **Regiones**
Base de datos completa:
- 120+ regiones (AWS/Azure/GCP)
- Columnas: Cloud, Region, Ubicación, Premium, Jio, Multiplier, Clave
- Auto-filter habilitado
- Usada por los dropdowns de la hoja Calculadora

##### 4. **Listas**
Valores para dropdowns:
- Clouds: AWS, Azure, GCP
- Availability: Multi-zone, Single-zone
- Dirección: Unidirectional, Bidirectional, None

##### 5. **Consideraciones**
Tabla de reglas oficiales:
- Fuente (doc oficial)
- Regla (nombre corto)
- Detalle (explicación larga)
- ~24 consideraciones críticas

#### Workflow Típico en Excel

```
1. Abrir calculadora-privatelink.xlsx

2. Ir a hoja "Calculadora"

3. Configurar Cluster A:
   B5: Azure ▼
   B6: eastus2 ▼  (se filtra por B5)
   B7: Multi-zone ▼
   B8: 4 (CKU)
   B9: 2 (VNets)
   B10: 3000 (Produce GB)
   B11: 5000 (Consume GB)
   B12: 2000 (Storage GB)

4. Configurar Cluster B:
   F5: AWS ▼
   F6: us-east-1 ▼
   F7: Multi-zone ▼
   F8: 3 (CKU)
   F9: 1 (VPC)
   F10: 1000
   F11: 2000
   F12: 1500

5. Configurar Linking:
   B15: Unidirectional ▼
   B16: 2500 (GB A→B)
   B17: 0 (GB B→A, disabled si no bi)

6. (Opcional) Editar tarifas en hoja "Tarifas":
   - Pegar precios reales de `confluent billing price list`

7. Revisar resultados (columnas I-L):
   - J24: TOTAL USD/mes (grande, azul marino)
   - Tabla J6:J21: Desglose por concepto
   - F38-F40: CKU sugerido y alertas
   - I27-I30: Private Link a provisionar

8. Gráfico en I38: Visualización por bloque

9. Imprimir o exportar PDF:
   - Print Area = A1:L48
   - Landscape, fit to 1 page
```

### Obtener Tarifas Reales de Dedicated

Las tarifas de Dedicated **no son list price público**. Para obtener precios reales:

```bash
# 1. Login a Confluent Cloud CLI
confluent login

# 2. Seleccionar environment
confluent environment use env-xxxxx

# 3. Obtener price list
confluent billing price list \
  --cloud azure \
  --region eastus2 \
  --cluster-type dedicated \
  --network-type private-link
```

**Output esperado**:
```
Product              | Unit          | Price USD
───────────────────────────────────────────────────
CKU                  | hour          | 1.50
KafkaNetworkWrite    | GB            | 0.10
KafkaNetworkRead     | GB            | 0.05
KafkaStorage         | GB-month      | 0.08
...
```

**Pegar en la calculadora**:
- Excel: Hoja "Tarifas", celdas B14-B17 (amarillas)
- HTML: Expandir "Tarifas Dedicated editables" y actualizar campos

### Ejemplo Completo: Calcular Costo para Proyecto Real

**Escenario**: E-commerce con Kafka cross-region DR

**Requisitos**:
- Production: Azure East US 2
- DR: Azure West US 2
- 8 TB/mes de tráfico cliente en prod
- 4 TB/mes de mirror para DR
- 5 TB de storage por cluster

**Paso a Paso**:

1. **Estimar throughput**:
```
Production:
  Produce: 4 TB/mes = 4,000 GB/mes
  Consume: 4 TB/mes = 4,000 GB/mes
  
  Mbps = (4,000 GB/mes × 1024 MB/GB) / (730 h × 3600 s)
       = 4,096,000 MB / 2,628,000 s
       = 1.56 MBps

DR (solo mirror + validación):
  Incoming: 4 TB mirror/mes = 1.56 MBps
  Outgoing: 500 GB validation = 0.19 MBps
```

2. **Calcular CKU necesarios**:
```
Production:
  Ingress: 1.56 MBps / 60 = 0.026 CKU → 1 CKU
  Egress: 1.56 + 1.56 = 3.12 MBps / 180 = 0.017 CKU → 1 CKU
  Min multi-zone: 2 CKU
  → Usar 2 CKU (suficiente)

DR:
  Ingress: 1.56 MBps / 60 = 0.026 CKU → 1 CKU
  Egress: 0.19 MBps / 180 = 0.001 CKU → 1 CKU
  Min multi-zone: 2 CKU
  → Usar 2 CKU (mínimo)
```

3. **Configurar en la calculadora**:
```
Cluster A (Production):
  Cloud: Azure
  Region: eastus2
  Availability: Multi-zone
  CKU: 2
  VNets: 3 (prod, staging, ops)
  Produce: 4,000 GB
  Consume: 4,000 GB
  Storage: 5,000 GB

Cluster B (DR):
  Cloud: Azure
  Region: westus2
  Availability: Multi-zone
  CKU: 2
  VNets: 1 (monitoring only)
  Produce: 0 GB
  Consume: 500 GB
  Storage: 5,000 GB

Cluster Linking:
  Direction: Unidirectional A→B
  Mirror A→B: 4,000 GB
```

4. **Resultado estimado**:
```
CONFLUENT:
  CKU: (2+2) × $1.50 × 1.0 × 730      = $4,380.00
  Kafka ingress A: 4,000 × $0.10 × 1.0 = $400.00
  Kafka egress A: 4,000 × $0.05 × 1.0  = $200.00
  Kafka egress B: 500 × $0.05 × 1.0    = $25.00
  Storage: (5,000+5,000) × 3 × $0.08    = $2,400.00
  Link hourly: $0.50 × 1.0 × 1 × 730 × 2= $730.00
  ClusterLinkingRead: 4,000 × $0.25 × 1.0= $1,000.00
  ClusterLinkingWrite: 4,000 × $0.10 × 1.0=$400.00
  ────────────────────────────────────────
  Subtotal Confluent                    = $9,535.00

CSP (Azure):
  A: 3 VNet × 3 PE × $0.01 × 730 + 8,000 × $0.01 = $145.70
  B: 1 VNet × 3 PE × $0.01 × 730 + 500 × $0.01   = $26.90
  ────────────────────────────────────────
  Subtotal CSP                          = $172.60

TOTAL                                   = $9,707.60/mes
```

5. **Validación**:
- ✅ CKU suficientes (2 vs mínimo 2)
- ✅ Mismo cloud (intra-cloud $0.50/h, no $2.50)
- ✅ Multi-zone compliance (2 CKU minimum)
- ⚠️ Alertas: Ninguna

6. **Optimizaciones posibles**:
- Si el DR puede ser single-zone: Ahorrar ~$180/mes en CSP (3 PE → 1 PE)
- Si mirror puede ser menor (e.g., solo topics críticos): Ahorrar en ClusterLinkingRead/Write

---

## Recursos Adicionales

### Documentación Oficial de Confluent

1. **Billing Dimensions**:
   https://docs.confluent.io/cloud/current/billing/billing-dimensions.html
   
2. **Cluster Linking Private Networking**:
   https://docs.confluent.io/cloud/current/multi-cloud/cluster-linking/private-networking.html
   
3. **Regiones y Premium Regions**:
   https://docs.confluent.io/cloud/current/get-started/regions.html
   
4. **Azure Private Link para Dedicated**:
   https://docs.confluent.io/cloud/current/networking/private-links/azure-privatelink.html
   
5. **AWS PrivateLink para Dedicated**:
   https://docs.confluent.io/cloud/current/networking/private-links/aws-privatelink.html
   
6. **GCP Private Service Connect para Dedicated**:
   https://docs.confluent.io/cloud/current/networking/private-links/gcp-private-service-connect.html
   
7. **Cluster Types y CKU**:
   https://docs.confluent.io/cloud/current/clusters/cluster-types.html
   
8. **Confluent CLI - Price List**:
   https://docs.confluent.io/confluent-cli/current/command-reference/billing/price/confluent_billing_price_list.html

### Comandos Útiles

```bash
# Ver price list
confluent billing price list \
  --cloud {aws|azure|gcp} \
  --region REGION \
  --cluster-type dedicated \
  --network-type private-link

# Listar regiones disponibles
confluent kafka region list --cloud {aws|azure|gcp}

# Ver detalles de un cluster
confluent kafka cluster describe CLUSTER_ID

# Ver billing dimensions activas
confluent billing dimension list
```

### Preguntas Frecuentes

**P: ¿Por qué CSP está separado de Confluent en el total?**
R: Porque son dos proveedores distintos. Confluent te cobra por su servicio Kafka; el cloud provider (AWS/Azure/GCP) te cobra por sus endpoints de conectividad privada. Son facturas separadas.

**P: ¿El multiplier regional se aplica al Cluster Linking cross-cloud?**
R: NO. Los precios de $2.50 y $5.00 para cross-cloud private ya son finales y no se multiplican. El multiplier solo se aplica al $0.50 intra-cloud y a las tarifas base de CKU/ingress/egress.

**P: ¿Puedo usar Cluster Linking entre organizations distintas?**
R: NO para private-to-private. Requiere la misma Confluent Cloud Organization. Solo funciona cross-org si al menos uno de los clusters tiene endpoints públicos.

**P: ¿Necesito Private Link en ambos clusters para replicación?**
R: NO necesariamente. Puedes hacer private→public o public→private. Pero para private-to-private (ambos), se aplican las reglas especiales de hourly cross-cloud.

**P: ¿Los descuentos por volumen son automáticos?**
R: NO. Los descuentos en ClusterLinkingRead (egress) no son self-service. Contacta a tu account team para negociar descuentos en alto volumen.

**P: ¿Cómo obtengo los precios reales de Dedicated si no son públicos?**
R: Usa `confluent billing price list` con tu CLI autenticada, o contacta a tu account manager. Los precios varían por región y acuerdo comercial.

**P: ¿GB significa gigabyte (1000^3) o gibibyte (1024^3)?**
R: **GiB (gibibyte, 2^30)**. La documentación de Confluent usa GB pero significa GiB en el billing.

---

## Glosario

| Término | Definición |
|---------|------------|
| **CSP** | Cloud Service Provider (AWS, Azure, GCP) |
| **CKU** | Confluent Kafka Unit (unidad de capacidad en Dedicated) |
| **PE** | Private Endpoint (Azure) |
| **VPCE** | VPC Endpoint (AWS) |
| **PSC** | Private Service Connect (GCP) |
| **PL** | Private Link |
| **AZ** | Availability Zone |
| **VNet** | Virtual Network (Azure) |
| **VPC** | Virtual Private Cloud (AWS, GCP) |
| **RF** | Replication Factor (usualmente 3 en Dedicated) |
| **Mirror** | Replicación de topics vía Cluster Linking |
| **Source** | Cluster origen en Cluster Linking (el que lee) |
| **Destination** | Cluster destino en Cluster Linking (el que escribe) |
| **Multiplier** | Factor regional que se aplica a precios base |
| **Premium Region** | Región con $5.00/h en cross-cloud private (vs $2.50) |
| **Jio** | Regiones de Jio Cloud (sin Private Link) |
| **Cross-cloud** | Linking entre clouds distintos (AWS↔Azure, etc.) |
| **Intra-cloud** | Linking dentro del mismo cloud |
| **Hourly** | Cargo por hora del objeto Cluster Link |
| **Egress** | Tráfico de salida (ClusterLinkingRead, KafkaNetworkRead) |
| **Ingress** | Tráfico de entrada (ClusterLinkingWrite, KafkaNetworkWrite) |
| **Data Processed** | Cargo CSP por GB que pasa por el endpoint |

---

## Actualizaciones y Mantenimiento

### Regenerar Excel desde Python

Cuando se actualiza la base de datos de regiones o las fórmulas:

```bash
cd confluent-cloud-clusterlink
python3 build_excel.py
```

Esto genera un nuevo `calculadora-privatelink.xlsx` con:
- Regiones actualizadas desde `REGIONS` dict
- Fórmulas nativas de Excel (no macros)
- Validaciones y formato condicional
- Gráficos automáticos

### Actualizar Regiones

Editar en ambos archivos:

**HTML** (`calculadora-privatelink.html`):
```javascript
// Línea ~280
const REGIONS = {
  aws: [
    {id:"nueva-region", name:"Descripción", premium:false, jio:false, mult:1.0},
    // ...
  ],
  // ...
};
```

**Python** (`build_excel.py`):
```python
# Línea ~12
REGIONS = {
    "AWS": [
        ("nueva-region", "Descripción", False, False, 1.0),
        # ...
    ],
    # ...
}
```

Luego regenerar Excel:
```bash
python3 build_excel.py
```

### Actualizar Tarifas

**Cluster Linking** (list prices oficiales):
- Consultar: https://docs.confluent.io/cloud/current/billing/billing-dimensions.html
- Actualizar en líneas ~270-291 de `calculadora-privatelink.html`
- Actualizar en líneas ~270-291 de `build_excel.py`

**Dedicated** (editables por usuario):
- NO hardcodear valores específicos
- Mantener valores de ejemplo razonables
- Los usuarios deben usar `confluent billing price list` para precios reales

---

## Conclusión

Esta calculadora es una herramienta de estimación para **planificación de costos** de Confluent Cloud Dedicated con Private Link y Cluster Linking. 

### Precisión:
- ✅ **Exacto**: Cluster Linking hourly y egress (list prices documentados)
- ⚠️ **Estimado**: Dedicated CKU/ingress/egress/storage (no son públicos)
- ⚠️ **Aproximado**: Costos CSP (varían por región y contrato)

### Úsala para:
- Comparar escenarios (intra-cloud vs cross-cloud, uni vs bidirectional)
- Dimensionar CKU necesarios
- Estimar orden de magnitud del costo mensual
- Identificar componentes más costosos

### NO uses para:
- Facturación exacta (usa Confluent Cloud billing dashboard)
- Compromisos contractuales (consulta a tu account manager)
- Subestimación (siempre agrega buffer)

### Próximos Pasos:
1. Configurar tus clusters en la calculadora
2. Obtener precios reales con `confluent billing price list`
3. Validar el CKU sugerido con tus métricas reales
4. Consultar con tu account team para descuentos y pricing final
5. Provisionar en Confluent Cloud con Private Link configurado

**¿Preguntas?** Consulta la documentación oficial de Confluent o contacta a tu customer success team.
