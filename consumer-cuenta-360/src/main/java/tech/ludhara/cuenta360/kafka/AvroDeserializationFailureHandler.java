package tech.ludhara.cuenta360.kafka;

import java.time.Duration;

import jakarta.enterprise.context.ApplicationScoped;

import org.apache.kafka.common.header.Headers;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import io.smallrye.common.annotation.Identifier;
import io.smallrye.mutiny.Uni;
import io.smallrye.reactive.messaging.kafka.DeserializationFailureHandler;

/**
 * Compartido por los 10 channels.
 *
 * <ul>
 * <li>Veneno (bytes corruptos, esquema incompatible con la clase lectora, id de esquema inexistente): devuelve
 * {@code null} con los headers de falla, y SmallRye manda los bytes originales a la DLQ del channel sin invocar el
 * {@code @Incoming}.</li>
 * <li>Schema Registry o red caídos: reintenta con backoff dentro del poll. Si la caída supera
 * {@code cuenta360.schema-registry.retry.max-duration}, la excepción cierra el consumer de ese channel y el liveness
 * del pod la reporta. Nunca se manda un mensaje válido a la DLQ por una falla de infraestructura.</li>
 * </ul>
 *
 * La duración máxima debe ser menor que {@code max.poll.interval.ms}: el reintento bloquea el hilo de poll.
 */
@ApplicationScoped
@Identifier("avro-schema-registry")
public class AvroDeserializationFailureHandler implements DeserializationFailureHandler<Object> {

    private static final Logger LOG = Logger.getLogger(AvroDeserializationFailureHandler.class);

    @ConfigProperty(name = "cuenta360.schema-registry.retry.initial-backoff", defaultValue = "PT0.5S")
    Duration backoffInicial;

    @ConfigProperty(name = "cuenta360.schema-registry.retry.max-backoff", defaultValue = "PT10S")
    Duration backoffMaximo;

    @ConfigProperty(name = "cuenta360.schema-registry.retry.max-duration", defaultValue = "PT2M")
    Duration duracionMaxima;

    @Override
    public Object decorateDeserialization(Uni<Object> deserialization, String topic, boolean isKey,
            String deserializer, byte[] data, Headers headers) {
        return deserialization
                .onFailure(FallasDeserializacion::esDeInfraestructura)
                .invoke(falla -> LOG.warnf("Schema Registry no disponible al leer %s, reintentando: %s",
                        topic, falla.getMessage()))
                .onFailure(FallasDeserializacion::esDeInfraestructura).retry()
                .withBackOff(backoffInicial, backoffMaximo)
                .expireIn(duracionMaxima.toMillis())
                .onFailure(falla -> !FallasDeserializacion.esDeInfraestructura(falla))
                .recoverWithItem(falla -> {
                    LOG.errorf("Mensaje ilegible en %s, va a la DLQ: %s", topic, falla.getMessage());
                    DeserializationFailureHandler.addFailureDetailsToHeaders(deserializer, topic, isKey, headers,
                            data, falla);
                    return null;
                })
                .await().indefinitely();
    }
}
