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

