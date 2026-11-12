package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.TransferenciaRecibida;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class TransferenciaRecibidaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    TransferenciaRecibidaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("transferencia-recibida")
    @Blocking(value = "transferencia-recibida-pool", ordered = false)
    public void consumir(TransferenciaRecibida evento) {
        proyeccion.aplicar("transferencia-recibida", evento.getTransferenciaId(), evento.getOcurridoEn(), evento);
    }
}
