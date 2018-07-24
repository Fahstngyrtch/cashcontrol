# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства РР: 02-Ф
"""
from rr import RR
from shtrih_cash_register import ShtrihCashRegister
from rr_middleware import RRPrepareRequest, RRPrepareResponse


class RRCashRegister(ShtrihCashRegister):
    """ Класс предоставляет общий интерфейс
        для выполнения команд на ККТ семейств "Штрих", "РР"
    """

    dev_type = "RR"
    dev_class = RR

    def __init__(self, port=None, rate=None):
        super(RRCashRegister, self).__init__(port, rate)
        self._prepare = RRPrepareRequest()
        self._response = RRPrepareResponse()
