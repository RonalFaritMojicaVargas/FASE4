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


