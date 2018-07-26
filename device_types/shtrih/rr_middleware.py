# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства РР: 02-Ф
    Классы подготовки запроса и обработки результата
"""
from .shtrih_middleware import ShtrihPrepareRequest, ShtrihPrepareResponse


class RRPrepareRequest(ShtrihPrepareRequest):
    """ Класс для подготовки запроса """

    def get_autocut_param(self, *_, **__):
        # Значение автоотрезки: таблица 1, строка 1, поле 7
        return '\x01\x01\x00\x07'


class RRPrepareResponse(ShtrihPrepareResponse):
    """ Класс для обработки результата """
