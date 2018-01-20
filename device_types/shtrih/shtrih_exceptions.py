# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства Штрих: ФРК, ФРФ, М
    Классы исключений
"""
import shtrih_constants


class ShtrihError(BaseException):
    """ Базовый класс для исключений,
        порождаемых драйвером ККТ и его окружением
    """
    # Ошибки, возникающие в ходе выполнения инструкций
    error_class = 'Runtime'

    def __init__(self, code, *args):
        """ Конструктор класса
            :param code: код ошибки
            :param args: аргументы для создания исключения
        """
        self.__code = code
        super(ShtrihError, self).__init__(*args)

    @property
    def code(self):
        """ Свойство, обозначающее код ошибки """
        return self.__code

    @property
    def description(self):
        """ Описание ошибки """
        return shtrih_constants.ERRORS.get(self.__code)[0] or "Ошибка"

    @property
    def action(self):
        if self.__code in shtrih_constants.ERRORS:
            return shtrih_constants.ERRORS[self.__code][1]
        return 'break'

    def serialize(self):
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'args': self.args,
            'code': self.code,
            'description': self.description,
            'action': self.action
        }


class ShtrihCustomError(ShtrihError):
    """ Класс для порождения исключений, вызванных ошибками работы с портом,
        формирования команды, вычисления контрольной суммы и пр.
    """
    error_class = 'Custom'

    @property
    def description(self):
        return shtrih_constants.CUSTOM_ERRORS.get(self.code) or u"Ошибка"


class ShtrihConnectionError(ShtrihCustomError):
    """ Ошибки установки соединения с устройством """


class ShtrihCommandError(ShtrihCustomError):
    """ Ошибки формирования команд и обработки ответов """
