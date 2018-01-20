# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Вспомогательные функции
"""
from middleware import TemplateReader


def format_string(text, width, align='left', fill='', bold=False):
    """ Форматирование строки перед печатью
        :param text: шаблон строки
        :param width: ширина чековой ленты (в символах)
        :param align: выравнивание строки
        :param fill: символы для заполнения строки
        :param bold: печать жирной строки
    """
    width = width / 2 if bold is True else width
    aligns = {'left': u"{:%s<%d}" % (fill or '', width),
              'center': u"{:%s^%d}" % (fill or '', width),
              'right': u"{:%s>%d}" % (fill or '', width)}
    fmt = aligns.get(align) or aligns['left']
    return fmt.format(text)


def prepare_barcode(value):
    """ Преобразование числа в бинарное представление для печати штрих кода """
    number = hex(value)[2:].ljust(10, '0')
    chars = ''
    for i, c in list(enumerate(number))[::2]:
        chars += chr(int(c + number[i + 1], 16))
    return chars


def execute_printing_script(template_name, namespace, data, context,
                            reader=None, path=None):
    """ Выполнение сценария печати на ККТ
        :param template_name: имя шаблона печати
        :param namespace: словарь, оределяющий пространство имен для шаблона:
            {'cash_reg': объект класса CashRegister, }
        :param data: словарь с данными
        :param context: управляющая структура (словарь)
        :param reader: объект класса TemplateReader
        :param path: альтернативный путь к шаблонам
        :returns генератор с ходом выполнения команд
    """
    if reader is None:
        if path is None:
            raise ValueError("Не определен шаблонизатор")

        reader = TemplateReader(path)

    return reader.render_template(template_name, namespace, data, context)
