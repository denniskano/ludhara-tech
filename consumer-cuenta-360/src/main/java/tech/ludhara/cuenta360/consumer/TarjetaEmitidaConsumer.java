package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.TarjetaEmitida;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class TarjetaEmitidaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    TarjetaEmitidaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("tarjeta-emitida")
    @Blocking(value = "tarjeta-emitida-pool", ordered = false)
    public void consumir(TarjetaEmitida evento) {
        proyeccion.aplicar("tarjeta-emitida", evento.getTarjetaId(), evento.getOcurridoEn(), evento);
    }
}
