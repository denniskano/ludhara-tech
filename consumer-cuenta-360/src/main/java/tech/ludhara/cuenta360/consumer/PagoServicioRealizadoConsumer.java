package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.PagoServicioRealizado;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class PagoServicioRealizadoConsumer {

    private final ProyeccionCuenta360 proyeccion;

    PagoServicioRealizadoConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("pago-servicio-realizado")
    @Blocking(value = "pago-servicio-realizado-pool", ordered = false)
    public void consumir(PagoServicioRealizado evento) {
        proyeccion.aplicar("pago-servicio-realizado", evento.getPagoId(), evento.getOcurridoEn(), evento);
    }
}
