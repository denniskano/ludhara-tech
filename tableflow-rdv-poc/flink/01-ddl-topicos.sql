-- =============================================================================
-- PoC RDV: 4 tópicos con esquemas distintos, creados desde Flink SQL en
-- Confluent Cloud. Cada CREATE TABLE crea el tópico y registra en Schema
-- Registry los subjects <tópico>-key y <tópico>-value (Avro).
--
-- Ejecutar en el workspace de Flink con el catálogo = environment y la
-- base de datos = cluster Dedicated:
--   USE CATALOG `<environment>`;
--   USE `<cluster>`;
--
-- Reglas que exige Tableflow y que este DDL ya cumple:
--   * changelog append: RDV guarda cada evento, no el último estado por clave.
--   * La clave va solo en el key schema ('except-key'). En modo append,
--     Tableflow la agrega como columna; si también estuviera en el value,
--     la columna quedaría duplicada.
--   * Columnas opcionales = nullable, que en Avro queda ["null", tipo] con
--     default null: es la única forma de agregar campos después.
--   * TIMESTAMP_LTZ(3) se registra como timestamp-millis (soportado).
--     No usar precisión 6: timestamp-micros se materializa como bigint.
-- =============================================================================

-- 1. Apertura de cuenta: tipos simples.
CREATE TABLE `rdv-poc-cuenta-abierta` (
  `cuenta_id`   STRING NOT NULL,
  `evento_id`   STRING NOT NULL,
  `cliente_id`  STRING NOT NULL,
  `tipo_cuenta` STRING NOT NULL,
  `moneda`      STRING NOT NULL,
  `ocurrido_en` TIMESTAMP_LTZ(3) NOT NULL
)
DISTRIBUTED BY HASH(`cuenta_id`) INTO 6 BUCKETS
WITH (
  'changelog.mode'       = 'append',
  'key.format'           = 'avro-registry',
  'value.format'         = 'avro-registry',
  'value.fields-include' = 'except-key',
  'kafka.retention.time' = '7 d'
);

-- 2. Movimiento: decimal y un campo opcional.
CREATE TABLE `rdv-poc-movimiento-registrado` (
  `movimiento_id` STRING NOT NULL,
  `evento_id`     STRING NOT NULL,
  `cuenta_id`     STRING NOT NULL,
  `tipo`          STRING NOT NULL,
  `monto`         DECIMAL(18, 2) NOT NULL,
  `moneda`        STRING NOT NULL,
  `descripcion`   STRING,
  `ocurrido_en`   TIMESTAMP_LTZ(3) NOT NULL
)
DISTRIBUTED BY HASH(`movimiento_id`) INTO 6 BUCKETS
WITH (
  'changelog.mode'       = 'append',
  'key.format'           = 'avro-registry',
  'value.format'         = 'avro-registry',
  'value.fields-include' = 'except-key',
  'kafka.retention.time' = '7 d'
);

-- 3. Cliente: record anidado y array.
-- Tableflow no admite agregar campos dentro de un record anidado existente:
-- `direccion` debe nacer con todos sus campos.
CREATE TABLE `rdv-poc-cliente-actualizado` (
  `cliente_id`  STRING NOT NULL,
  `evento_id`   STRING NOT NULL,
  `email`       STRING,
  `telefonos`   ARRAY<STRING>,
  `direccion`   ROW<`linea` STRING, `distrito` STRING, `ciudad` STRING>,
  `ocurrido_en` TIMESTAMP_LTZ(3) NOT NULL
)
DISTRIBUTED BY HASH(`cliente_id`) INTO 6 BUCKETS
WITH (
  'changelog.mode'       = 'append',
  'key.format'           = 'avro-registry',
  'value.format'         = 'avro-registry',
  'value.fields-include' = 'except-key',
  'kafka.retention.time' = '7 d'
);

-- 4. Pago de servicio: decimal y map.
CREATE TABLE `rdv-poc-pago-servicio-realizado` (
  `pago_id`           STRING NOT NULL,
  `evento_id`         STRING NOT NULL,
  `cuenta_id`         STRING NOT NULL,
  `empresa`           STRING NOT NULL,
  `numero_suministro` STRING NOT NULL,
  `monto`             DECIMAL(18, 2) NOT NULL,
  `atributos`         MAP<STRING, STRING>,
  `ocurrido_en`       TIMESTAMP_LTZ(3) NOT NULL
)
DISTRIBUTED BY HASH(`pago_id`) INTO 6 BUCKETS
WITH (
  'changelog.mode'       = 'append',
  'key.format'           = 'avro-registry',
  'value.format'         = 'avro-registry',
  'value.fields-include' = 'except-key',
  'kafka.retention.time' = '7 d'
);

-- Verificación: los 4 tópicos y sus esquemas.
SHOW TABLES LIKE 'rdv-poc-%';
SHOW CREATE TABLE `rdv-poc-cliente-actualizado`;
