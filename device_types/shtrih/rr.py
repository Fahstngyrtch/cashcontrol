# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства РР: 02-Ф
    Драйвер
"""
from shtrih_constants import PASSWORD, DEF_TIMEOUT
from shtrih import Shtrih


class RR(Shtrih):
    """ Класс работы с фискальными устройствами семейства "РР"
        Класс унаследван от Shtrih в виду совместимости по набору команд
    """

    def __init__(self, port, rate, password=PASSWORD,
                 read_timeout=DEF_TIMEOUT, write_timeout=DEF_TIMEOUT):
        """ Открытие последовательного порта
            :param port: порт
            :param rate: скорость работы (в бодах)
            :param password: пароль
            :param read_timeout: время на чтение данных
            :param write_timeout: время на запись данных
        """
        super(RR, self).__init__(
            port, rate, password, read_timeout, write_timeout)
        self.__check_width = 48
