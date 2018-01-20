# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
"""
from cash_register.utils import execute_printing_script
from cash_register.cash_register import CashRegister
from cash_register.middleware import ProxyCashRegister

__version__ = "1.0.10"

TYPE_SHTRIH = 'shtrih'


def execute_script(
        template_name, data, context, reader=None, path=None, cls=CashRegister):
    """ Выполнение сценария печати на ККТ
        :param template_name: имя шаблона печати
        :param data: словарь с данными
        :param context: управляющая структура (словарь)
        :param reader: объект класса TemplateReader
        :param path: альтернативный путь к шаблонам
        :param cls: класс замещаемого объекта
        :returns генератор с последовательностью команд

        Шаблонизация построена на использовании jinja.
        Команды на печать посылаются путем вызова в шаблоне необходимого метода
            у объекта cash_reg
    """
    proxy = ProxyCashRegister(cls)
    execute_printing_script(
        template_name, {'cash_reg': proxy}, data, context, reader, path)
    return proxy
