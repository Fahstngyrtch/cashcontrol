# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства Штрих: ФРК, ФРФ, М
"""
from shtrih_constants import MAX_TRIES, PRN_CRITICAL, ERR_COMMAND_TIMEOUT, \
    TIME_DELTA_ERRORS, TIME_DELTA_STEP, WAITING_ERRORS, ROLLBACKS
from shtrih_exceptions import ShtrihConnectionError, ShtrihError, \
    ShtrihCommandError
from shtrih import Shtrih
from shtrih_middleware import ShtrihPrepareRequest, ShtrihPrepareResponse


class ShtrihCashRegister(object):
    """ Класс предоставляет общий интерфейс для выполнения команд на ККТ """

    dev_type = "Shtrih"

    def __init__(self, port=None, rate=None):
        try:
            self.__device = Shtrih(port, rate)
        except ShtrihConnectionError:
            self.__device = Shtrih(None, None)

        self._prepare = ShtrihPrepareRequest()
        self._response = ShtrihPrepareResponse()

        self.check_width = self.__device.check_width

    def _check_for_ready(self):
        """ Проверка на готовность ККТ к работе """
        is_ready = None

        try:
            self.__device("get_short_status", '', None)
            result = self.__device.result
        except ShtrihError:
            pass
        else:
            if result['data']:
                data = self._response.get_short_status(result['data'])
                is_ready = data['cashcontrol_submode'] == 0

        return is_ready

    def is_opened(self):
        """ Признак, доступно ли устройство по указанному порту """
        return self.__device.is_opened

    def delta_step(self):
        """ Приращение ко времени выполнения команды """
        return self.__device.time_delta_step

    @staticmethod
    def prepare_response(**kwargs):
        """ Подготовка контейнера для ответа """
        resp = dict(action='continue', exception=None, is_critical=False,
                    data={}, delta=0, delta_for_last_command=0)
        resp.update(**kwargs)
        return resp

    def find_device(self, port_group=None, rate=None):
        """ Поиск устройства
            :param port_group: группа портов для снижения времени поиска
            :param rate: скорость обмена для снижения времени поиска
            :returns кортеж (порт, скорость обмена)
        """
        response = self.prepare_response(command='find_device')
        try:
            port, rate = self.__device.find_device(port_group, rate)
        except ShtrihConnectionError as exc:
            response['exception'] = exc.serialize()
            response['command'] = 'break'
        else:
            response['data'] = {'port': port, 'rate': rate}
        return response

    def init_cash_register(self, port, rate):
        """ Инициализация кассового аппарата
            :param port: номер порта
            :param rate: скорость обмена
            :returns признак успешного подключения
        """
        response = self.prepare_response()
        try:
            self.__device = Shtrih(port, rate)
        except ShtrihConnectionError as exc:
            self.__device = None
            response['exception'] = exc.serialize()
            response['command'] = 'break'
        else:
            response = self.check_dev_for_ready()
        response['command'] = 'init_cash_register'
        return response

    def check_dev_for_ready(self):
        """ Определение состояния ККТ на основе краткого опроса.
            Используется для фактической проверки готовности ККТ
            (открытый порт не означает готовность устройства к работе),
            а также определяет активность процесса печати
            (подрежим 0 означает, что печать завершена).
        """
        response = self.prepare_response(command='check_dev_for_ready')
        try:
            response['data']['ready'] = self._check_for_ready()
        except ShtrihConnectionError as exc:
            response['exception'] = exc.serialize()
            response['command'] = 'break'
        return response

    def rollback_action(self):
        """ Отмена предыдущего действия
            Предназначена для отката подвисшей операции, если это предусмотрено
            регламентом
        """
        rollback_cmd = ROLLBACKS.get(self.__device.last_critical_command)
        if rollback_cmd:
            return self.make_action(rollback_cmd, None)

    def make_action(self, command, timeout, *args, **kwargs):
        """ Выполнение команды на ККТ
            :param command: наименование команды
            :param timeout: возможное время ожидания
            :param args: позиционные аргументы
            :param kwargs: именованные аргументы
            :returns словарь вида {
                'action': константа (дальнейшее действие),
                'command': текущая команда,
                'exception': объект ошибки,
                'is_critical': признак нахождения в критической секции,
                'data': словарь с данными ответа,
                'delta': приращение ко времени выполнения команды,
                'delta_for_last_command': приращение ко времени выполнения
                                          предыдущей команды
                }
        """
        _delta, _last_delta = 0, 0
        data = getattr(self._prepare, command)(*args, **kwargs)

        for _ in range(MAX_TRIES):
            try:
                self.__device(command, data, timeout)
            except ShtrihError as exc:
                response = self.analyse_result(command, exc)
                break
            else:
                response = self.analyse_result(command)

                _delta += response['delta']
                _last_delta += response['delta_for_last_command']

                if response['action'] == 'retry':
                    continue
                else:
                    response['delta'] += _delta
                    response['delta_for_last_command'] += _last_delta
                    break
        else:
            exp = ShtrihCommandError(ERR_COMMAND_TIMEOUT)
            response = self.analyse_result(command, exp)

        return response

    def analyse_result(self, command, exception=None):
        """ Предварительный анализ результата выполнения команды
            :param command: выполняемая команда
            :param exception: возникшее исключение
            :returns словарь вида {
                'action': константа (дальнейшее действие),
                'command': текущая команда,
                'exception': объект ошибки,
                'is_critical': признак нахождения в критической секции,
                'data': словарь с данными ответа,
                'delta': приращение ко времени выполнения команды,
                'delta_for_last_command': приращение ко времени выполнения
                                          предыдущей команды
                }
        """
        response = self.prepare_response(command=command, exception=exception)
        response['is_critical'] = self.__device.print_zone == PRN_CRITICAL

        if exception:
            response['action'] = 'break'
            response['exception'] = exception
        else:
            result = self.__device.result

            if result['error']:
                error = result['error']
                code = int(error['code'])

                # Обработка ошибки типа "Идет печать предыдущей команды"
                if code in TIME_DELTA_ERRORS:
                    last_delta = 0
                    while True:
                        device_is_ready = self.check_dev_for_ready()
                        if device_is_ready:
                            response['action'] = 'retry'
                            response['delta_for_last_command'] = last_delta
                            break
                        elif device_is_ready is None:
                            break
                        else:
                            last_delta += TIME_DELTA_STEP
                # Обработка прочих ошибок ожидания
                elif code in WAITING_ERRORS:
                    response['action'] = 'wait'
                else:
                    response['exception'] = error
                    # код -1 -- признак повторения команды
                    if error['action'] == 'break':
                        response['action'] = 'break'
                    else:
                        response['action'] = 'retry'
                if not response['exception']:
                    response['exception'] = error
            else:
                data = getattr(self._response, command)(result['data'])
                response['data'] = data
                response['delta'] = result['delta']

        return response
