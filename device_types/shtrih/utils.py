# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ
    Драйвер под устройства семейства "Штрих"
    Вспомогательные функции
"""


def get_crc(str_data):
    """ Вычисление контрольной суммы значения из строки
        :param str_data: строка с данными
    """
    res = 0
    for item in str_data:
        res ^= ord(item)
    return chr(res)


def hex2str(*codes):
    """ Преобразование кортежа целых чисел
        в строку символов с соответствующими кодами
        :param codes: кортеж целых чисел
    """
    numbers = [int(i) for i in codes]
    return ''.join([chr(i) for i in numbers])


def str2hex(char_string):
    """ Преобразованиме символов строки в шестнадцатиричные значения
        по коду символа
        :param char_string: строка символов
        :returns строка с шестнадцатиричными значениями кодов символов,
            разделенных символами пробела
    """
    return ' '.join([hex(ord(c)) for c in char_string])


def byte2array(bts):
    """ Перевод байтов в массив
        :param bts: последовательность байт
    """
    result = []

    for i in range(0, 8):
        if bts == bts >> 1 << 1:
            result.append(False)
        else:
            result.append(True)
        bts >>= 1
    return result
