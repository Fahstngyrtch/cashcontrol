# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ
"""


def make_device(dev_family, port=None, rate=None):
    """ Инициализация кассового аппарата """
    if dev_family == 'shtrih':
        from shtrih.shtrih_cash_register import ShtrihCashRegister as Register
    elif dev_family == 'rr':
        from shtrih.rr_cash_register import RRCashRegister as Register
    else:
        raise TypeError('Неизвестный тип устройства')

    return Register(port, rate)
