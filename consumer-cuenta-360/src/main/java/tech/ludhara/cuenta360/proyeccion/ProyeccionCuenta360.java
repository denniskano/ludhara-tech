package tech.ludhara.cuenta360.proyeccion;

import java.time.Instant;

import org.apache.avro.specific.SpecificRecord;

/**
 * Vista de cuenta alimentada por los 10 tópicos.
 *
 * Los channels procesan en paralelo y sin orden ({@code ordered = false}), y la entrega es at-least-once. Toda
 * implementación debe ser idempotente y descartar un evento si ya aplicó uno más reciente para la misma entidad. En
 * una base de datos: {@code UPSERT ... WHERE ocurrido_en < :ocurridoEn}.
 */
public interface ProyeccionCuenta360 {

    /**
     * @return {@code false} si el evento es un duplicado o llegó después de uno más reciente.
     */
    boolean aplicar(String tipoEvento, String entidadId, Instant ocurridoEn, SpecificRecord evento);
}
