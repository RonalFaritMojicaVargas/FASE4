"""Punto de entrada de la simulación y colección de objetos en memoria."""

import logging
from decimal import Decimal
from pathlib import Path

from modelos import (
    AlquilerEquipo, Asesoria, Cliente, DatoInvalido, ErrorSoftwareFJ,
    Estado, OperacionInvalida, Reserva, ReservaSala, ServicioNoDisponible, texto,
)


class Sistema:
    """Gestiona clientes, servicios y reservas mediante listas internas."""

    def __init__(self):
        self.__clientes = []
        self.__servicios = []
        self.__reservas = []

    @staticmethod
    def _buscar(lista, codigo):
        codigo = texto(codigo, "Código").upper()
        for objeto in lista:
            if objeto.codigo == codigo:
                return objeto
        raise OperacionInvalida(f"No existe un registro con el código {codigo}.")

    @staticmethod
    def _agregar(lista, objeto):
        if any(actual.codigo == objeto.codigo for actual in lista):
            raise OperacionInvalida(f"El código {objeto.codigo} ya existe.")
        lista.append(objeto)
        return objeto.describir()

    def registrar_cliente(self, codigo, nombre, correo):
        return self._agregar(self.__clientes, Cliente(codigo, nombre, correo))

    def registrar_servicio(self, tipo, *args, **kwargs):
        return self._agregar(self.__servicios, tipo(*args, **kwargs))

    def reservar(self, codigo, cliente, servicio, horas, unidades=1, **ajustes):
        cliente = self._buscar(self.__clientes, cliente)
        servicio = self._buscar(self.__servicios, servicio)
        reserva = Reserva(codigo, cliente, servicio, horas, unidades)
        reserva.procesar(**ajustes)
        reserva.confirmar(self.__reservas)
        # Una solicitud fallida nunca ingresa en la lista de reservas.
        return self._agregar(self.__reservas, reserva)

    def cancelar(self, codigo):
        reserva = self._buscar(self.__reservas, codigo)
        reserva.cancelar()
        return reserva.describir()

    def obtener_reserva(self, codigo):
        return self._buscar(self.__reservas, codigo)


def ejecutar_caso(log, numero, nombre, operacion, error_esperado):
    """Verifica cada resultado y registra el final aun si ocurre una excepción."""
    etiqueta = f"{numero:02d} {nombre}"
    correcto = False
    try:
        resultado = operacion()
    except ErrorSoftwareFJ as error:
        correcto = type(error) is error_esperado
        mensaje = f"{'Rechazo esperado' if correcto else 'Error inesperado'}: {error}"
        log.exception("%s | %s", etiqueta, mensaje)
    except Exception as error:
        mensaje = f"Fallo inesperado ({type(error).__name__}): {error}"
        log.exception("%s | %s", etiqueta, mensaje)
    else:
        correcto = error_esperado is None
        mensaje = resultado if correcto else "Se esperaba un error y la operación continuó."
        log.log(logging.INFO if correcto else logging.ERROR, "%s | %s", etiqueta, mensaje)
    finally:
        log.info("%s | Fin de la operación", etiqueta)
    print(f"{etiqueta} | {'OK' if correcto else 'FALLO'} | {mensaje}")
    return correcto


def simular(log):
    """Ejecuta registros, reservas, cancelaciones y controles de integridad."""
    sistema = Sistema()

    def verificar_reserva(codigo, estado, esperado):
        reserva = sistema.obtener_reserva(codigo)
        if reserva.estado is not estado or reserva.total != Decimal(esperado):
            raise AssertionError("El estado o el costo no coincide con lo esperado.")
        return reserva.describir()

    casos = [
        ("Cliente válido", lambda: sistema.registrar_cliente("C1", "Ana Pérez", "ana@example.com"), None),
        ("Correo inválido", lambda: sistema.registrar_cliente("C2", "Luis", "sin-arroba"), DatoInvalido),
        ("Nombre faltante", lambda: sistema.registrar_cliente("C3", "", "luis@example.com"), DatoInvalido),
        ("Cliente duplicado", lambda: sistema.registrar_cliente("c1", "Luis", "luis@example.com"), OperacionInvalida),
        ("Crear sala", lambda: sistema.registrar_servicio(ReservaSala, "S1", "Reuniones", 50000, 10), None),
        ("Crear equipos", lambda: sistema.registrar_servicio(AlquilerEquipo, "S2", "Portátiles", 10000, 4), None),
        ("Crear asesoría", lambda: sistema.registrar_servicio(Asesoria, "S3", "Python", 60000, 15000), None),
        ("Tarifa inválida", lambda: sistema.registrar_servicio(ReservaSala, "X", "Sala", "abc", 4), DatoInvalido),
        ("Registrar sala desactivada", lambda: sistema.registrar_servicio(ReservaSala, "S4", "Auditorio", 90000, 20, False), None),
        ("Reservar sala", lambda: sistema.reservar("R1", "C1", "S1", 2, 5), None),
        ("Verificar precio base", lambda: verificar_reserva("R1", Estado.CONFIRMADA, "100000"), None),
        ("Sala ocupada", lambda: sistema.reservar("R2", "C1", "S1", 1), ServicioNoDisponible),
        ("Sin registro de la reserva fallida", lambda: sistema.obtener_reserva("R2"), OperacionInvalida),
        ("Reservar equipos con descuento e impuesto", lambda: sistema.reservar("R3", "C1", "S2", 2, 3, descuento=10, impuesto=19), None),
        ("Verificar costo de equipos", lambda: verificar_reserva("R3", Estado.CONFIRMADA, "64260"), None),
        ("Duración inválida", lambda: sistema.reservar("R4", "C1", "S3", 0), DatoInvalido),
        ("Servicio desactivado", lambda: sistema.reservar("R5", "C1", "S4", 1), ServicioNoDisponible),
        ("Cuota de descuento inválida", lambda: sistema.reservar("R6", "C1", "S3", 1, descuento=110), DatoInvalido),
        ("Reservar asesoría con impuesto", lambda: sistema.reservar("R7", "C1", "S3", 1, impuesto=19), None),
        ("Verificar costo de asesoría", lambda: verificar_reserva("R7", Estado.CONFIRMADA, "89250"), None),
        ("Cancelar reserva de sala", lambda: sistema.cancelar("R1"), None),
        ("Verificar cancelación", lambda: verificar_reserva("R1", Estado.CANCELADA, "100000"), None),
        ("Cancelar de nuevo", lambda: sistema.cancelar("R1"), OperacionInvalida),
        ("Aforo superado", lambda: sistema.reservar("R8", "C1", "S1", 1, 11), DatoInvalido),
        ("Reservar sala liberada con descuento", lambda: sistema.reservar("R9", "C1", "S1", 1, descuento=10), None),
        ("Verificar descuento", lambda: verificar_reserva("R9", Estado.CONFIRMADA, "45000"), None),
    ]
    aprobados = 0
    for numero, (nombre, operacion, error) in enumerate(casos, start=1):
        aprobados += ejecutar_caso(log, numero, nombre, operacion, error)
    resumen = f"{aprobados}/{len(casos)} casos con el resultado esperado."
    log.info(resumen)
    print(resumen)
    return 0 if aprobados == len(casos) else 1


def main():
    ruta = Path(__file__).with_name("software_fj.log")
    log = logging.getLogger("software_fj")
    log.setLevel(logging.INFO)
    try:
        manejador = logging.FileHandler(ruta, encoding="utf-8")
    except OSError as error:
        print(f"No se pudo abrir el log: {error}. El registro saldrá por consola.")
        manejador = logging.StreamHandler()
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
