package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.TarjetaBloqueada;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class TarjetaBloqueadaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    TarjetaBloqueadaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("tarjeta-bloqueada")
    @Blocking(value = "tarjeta-bloqueada-pool", ordered = false)
    public void consumir(TarjetaBloqueada evento) {
        proyeccion.aplicar("tarjeta-bloqueada", evento.getTarjetaId(), evento.getOcurridoEn(), evento);
    }
}
