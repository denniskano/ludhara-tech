package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.TransferenciaEnviada;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class TransferenciaEnviadaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    TransferenciaEnviadaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("transferencia-enviada")
    @Blocking(value = "transferencia-enviada-pool", ordered = false)
    public void consumir(TransferenciaEnviada evento) {
        proyeccion.aplicar("transferencia-enviada", evento.getTransferenciaId(), evento.getOcurridoEn(), evento);
    }
}
