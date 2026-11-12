package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.MovimientoRegistrado;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class MovimientoRegistradoConsumer {

    private final ProyeccionCuenta360 proyeccion;

    MovimientoRegistradoConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("movimiento-registrado")
    @Blocking(value = "movimiento-registrado-pool", ordered = false)
    public void consumir(MovimientoRegistrado evento) {
        proyeccion.aplicar("movimiento-registrado", evento.getMovimientoId(), evento.getOcurridoEn(), evento);
    }
}
