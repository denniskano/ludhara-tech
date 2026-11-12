package tech.ludhara.cuenta360.kafka;

import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.net.http.HttpTimeoutException;

import javax.net.ssl.SSLException;

import io.confluent.kafka.schemaregistry.client.rest.exceptions.RestClientException;

/**
 * Separa un mensaje ilegible (veneno: va a la DLQ) de una falla de Schema Registry o de red
 * (infraestructura: se reintenta y nunca va a la DLQ, porque el mensaje es válido).
 */
public final class FallasDeserializacion {

    private static final int SCHEMA_NO_ENCONTRADO = 40403;

    private FallasDeserializacion() {
    }

    public static boolean esDeInfraestructura(Throwable falla) {
        for (Throwable t = falla; t != null; t = t.getCause()) {
            if (t instanceof RestClientException rest) {
                return rest.getErrorCode() != SCHEMA_NO_ENCONTRADO;
            }
            if (t instanceof SocketTimeoutException
                    || t instanceof SocketException
                    || t instanceof UnknownHostException
                    || t instanceof HttpTimeoutException
                    || t instanceof SSLException) {
                return true;
            }
        }
        return false;
    }
}
