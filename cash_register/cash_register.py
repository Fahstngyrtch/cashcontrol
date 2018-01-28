# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ
    Общий интерфейс печати и выполнения команд на ККТ
"""
import functools
from collections import OrderedDict

import time

from lc_cashcontrol.device_types.shtrih.shtrih_constants import WAITING_COMMANDS
from middleware import Log, SmartMixin
from utils import format_string, prepare_barcode


def define_user_case(exception, action, is_critical):
    """ Определение вариантов реакции пользователя
        на основе константы, обозначающей дальнейшее действие
        :param exception: описание ошибки
        :param action: характер дальнейшего действия
            continue | retry | break | wait
        :param is_critical: признак нахождения в критической области печати
        :returns упорядоченный словарь
    """
    cases = []

    if action == 'break':
        cases.append(('break', u"Прервать"))
        if not is_critical:
            cases.append(('retry', u"Повторить"))
    elif action == 'retry':
        cases.append(('retry', u"Повторить"))
    elif action == 'wait':
        cases += [
            ('skip', u"Пропустить"),
            ('retry', u"Повторить"),
            ('break', u"Прервать")]
    else:
        cases.append(('continue', u"Продолжить"))
    return {'exception': exception, 'cases': OrderedDict(cases)}


def command(method):
    """ Обертка над процессом выполнения команды """
    tries_to_exec = 10

    @functools.wraps(method)
    def wrap(self, *args, **kwargs):
        def gen_wrap():
            response = {}
            for _ in range(tries_to_exec):
                name = method.__name__
                self.log_info('Make {}'.format(name))
                self.log_debug("Args: {}".format(args))
                self.log_debug("Kwargs: {}".format(kwargs))

                response = method(self, *args, **kwargs)
                self.log_debug("Response: {}".format(response))

                if response['exception']:
                    exception = response['exception']
                    self.log_error("{0}: {1}".format(
                        exception.code, exception.description))

                call_again = False
                action = response['action']
                self.log_info("Action: {}".format(action))

                if action != 'continue':
                    if response['exception']:
                        reaction = yield define_user_case(
                            response['exception'],
                            response['action'],
                            response['is_critical'])
                    else:
                        reaction = [response['action']]

                    self.log_info("User choice: {}".format(reaction))
                    for action in reaction:
                        if action == 'break':
                            if response['is_critical']:
                                self.log_warning(u"Аннулирование чека")
                                self.make_cancel_check()
                        if action == 'retry':
                            self.log_info(u"Повтор выполнения {}".format(name))
                            call_again = True
                            break
                        if action == 'wait':
                            wait_time = response['delta'] or 1
                            time.sleep(wait_time)
                            response['delta'] += wait_time
                        else:
                            break
                if not call_again:
                    break
            else:
                messages = (
                    "'{}': Не удалось выолнить команду",
                    "Нет связи с устройством"
                )
                self.log_error(messages)
                response['exception'] = messages
            yield response
        return gen_wrap()
    return wrap


class CashRegister(Log, SmartMixin):
    """ Класс реализует общий набор команд к ККТ """

    def __init__(self, device):
        """ Класс агрегирует при создании экземпляр профильного класса,
            реализующего протокол обмена информацией с определенным
            типом устройства. Передаваемый объект содержит открытое
            соединение с устройством.
        """
        super(CashRegister, self).__init__()
        self.__device = device

        self.metric = self.get_commands_metric()
        self.last_command = ''
        self.delta_step = self.__device.delta_step()

        self.init_connection_parameters()

    def check_dev_for_ready(self):
        """ Проверка на готовностоь ККТ к работе """
        return self.__device.check_dev_for_ready()

    def set_connection_parameters(self, port, rate):
        """ Установка параметров подключения ККТ
            :param port: порт
            :param rate: скорость обмена
        """
        params = {"rate": rate, "type": self.__device.dev_type,
                  "port": port, "check_width": self.__device.check_width}
        metric = self.smart
        metric_device = metric.get('device') or {}
        metric_device.update(**params)
        metric['device'] = metric_device
        self.smart = metric

    def init_connection_parameters(self):
        dev_metric = self.get_device_metric()
        if dev_metric:
            port = dev_metric.get('port') or ''
            rate = dev_metric.get('rate') or 0

            if port:
                self.__device.port = port

            if rate:
                self.__device.rate = int(rate)

            self.init_cash_register(port, rate)

    def fix_in_smart(self, result):
        """ Определение времени, затраченного на выполнение команды,
            корректировка метрики команд для ККТ при необходимости
        """
        try:
            assert isinstance(result, dict)
            assert "command" in result
            assert "delta" in result
            assert "delta_for_last_command" in result
        except AssertionError:
            return

        name = result['command']
        timeout, need_to_calibrate = 0, False

        if self.smart:
            cmd_metric = self.smart.get('commands') or {}
            if name in cmd_metric:
                timeout, need_to_calibrate = cmd_metric[name]
            else:
                need_to_calibrate = True

        cmd_timeout_changed, last_cmd_timeout_changed = False, False

        if result['delta_for_last_command'] > 0:
            last_delta = result['delta_for_last_command']
            if self.last_command in self.metric:
                last_cmd_timeout_changed = True
                last_timeout, _ = self.metric[self.last_command]
                new_metric = [abs(last_timeout + last_delta), False]
                self.metric[self.last_command] = new_metric

        delta = result['delta'] or 0
        if delta < 0:
            timeout = timeout + delta
            if timeout < 0:
                timeout = self.delta_step
                need_to_calibrate = False
            cmd_timeout_changed = True
        elif (delta > 0) and (name not in WAITING_COMMANDS):
            timeout += delta
            need_to_calibrate = False
            cmd_timeout_changed = True

        if cmd_timeout_changed or last_cmd_timeout_changed:
            self.metric[name] = [abs(timeout), need_to_calibrate]
            metric = self.smart
            metric_commands = metric.get('commands') or {}
            metric_commands.update(**self.metric)
            metric['commands'] = metric_commands
            self.smart = metric
        self.last_command = name

    def make_cancel_check(self):
        """ Аннулирование незакрытого чека
            Метод применяется при автоматическом выполнении операции
        """
        return self.__device.make_action("cancel_check", None)

    @command
    def init_cash_register(self, port, rate):
        """ * Интерфейс работы с ККТ *
            Инициализация ККТ
            :param port: порт
            :param rate: скорость обмена
            returns: словарь с результатом выполнения команды
        """
        return self.__device.init_cash_register(port, rate)

    @command
    def find_device(self, port_group=None, rate=None):
        """ * Интерфейс работы с ККТ *
            Поиск устройства
            :param port_group: группа портов для снижения времени поиска
            :param rate: скорость обмена для снижения времени поиска
            returns: словарь с результатом выполнения команды
        """
        return self.__device.find_device(port_group, rate)

    @command
    def beep(self, timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Подача звукового сигнала
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("beep", timeout)

    @command
    def cancel_check(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Аннулирование незакрытого чека
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("cancel_check", timeout)

    @command
    def cash_income(self, timeout=None, cash=0.0):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Приходный чек
            :param timeout: время ожидания ответа
            :param cash: размер вносимой суммы
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("cash_income", timeout, cash=cash)

    @command
    def cash_outcome(self, timeout=None, cash=0.0):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Расходный чек
            :param timeout: время ожидания ответа
            :param cash: размер возвращаемой суммы
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("cash_outcome", timeout, cash=cash)

    @command
    def close_check(self, timeout=None, sum1=0.0, sum2=0.0, sum3=0.0, sum4=0.0,
                    sale=0, tax1=0, tax2=0, tax3=0, tax4=0, text=u" "):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Закрытие чека
            :param timeout: время ожидания ответа
            :param sum1: Сумма наличными
            :param sum2: Сумма типом оплаты 2
            :param sum3: Сумма типом оплаты 3
            :param sum4: Сумма типом оплаты 4
            :param sale: Скидка в %
            :param tax1: Налог 1
            :param tax2: Налог 2
            :param tax3: Налог 3
            :param tax4: Налог 4
            :param text: Сопроводительный текст
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("close_check", timeout, sum1=sum1,
                                         sum2=sum2, sum3=sum3, sum4=sum4,
                                         sale=sale, tax1=tax1, tax2=tax2,
                                         tax3=tax3, tax4=tax4, text=text)

    @command
    def confirm_date(self, c_date, timeout=None):
        """ * Интерфейс работы с ККТ *
            Подтверждение установки даты
            :param c_date: дата
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("confirm_date", timeout, c_date)

    @command
    def continue_print(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Возобновление печати
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("continue_print", timeout)

    @command
    def cut_check(self, timeout=None, full_cut=True):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Отрезка чека
            :param timeout: время ожидания ответа
            :param full_cut: Признак полной отрезки чека
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "cut_check", timeout, full_cut=full_cut)

    @command
    def feed_document(
            self, rows, timeout=None, check=True, slip=True, journal=True):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Протяжка чековой ленты
            :param rows: количество строк
            :param timeout: время ожидания ответа
            :param check: протяжка чековой ленты
            :param slip: протяжка подкладного документа
            :param journal: протяжка журнальной ленты
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "feed_document", timeout, rows, check=check, journal=journal,
            slip=slip)

    @command
    def get_autocut_param(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Определение состояния автоотрезки чека
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_autocut_param", timeout)

    @command
    def get_cash_reg(self, register, timeout=None):
        """ * Интерфейс работы с ККТ *
            Определение значения денежного регистра
            :param register: номер регистра
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_cash_reg", timeout, register)

    @command
    def get_device_metrics(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_device_metrics", timeout)

    @command
    def get_exchange_param(self, port, timeout=None):
        """ * Интерфейс работы с ККТ *
            Определение параметров работы устройства на порту
            :param port: номер порта
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_exchange_param", timeout, port)

    @command
    def get_short_status(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Краткий запрос стостояния устройства
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_short_status", timeout)

    @command
    def get_status(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Запрос стостояния устройства
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("get_status", timeout)

    @command
    def interrupt_test(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Прерывание тестового прогона
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("interrupt_test", timeout)

    @command
    def open_session(self, timeout=None):
        """ * Интерфейс работы с ККТ *
            Открытие смены
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("open_session", timeout)

    @command
    def print_barcode(self, number, timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать штрих-кода (стандарт EAN-13)
            :param number: номер для печати
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        code = prepare_barcode(number)
        return self.__device.make_action("print_barcode", timeout, code)

    @command
    def print_image(self, timeout=None, start_row=1, end_row=199):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать загруженного изображения
            :param timeout: время ожидания ответа
            :param start_row: номер начальной строки
            :param end_row: номер конечной строки
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("print_image", timeout,
                                         start_row=start_row, end_row=end_row)

    @command
    def print_line_barcode(self, bar_code, line_number, bar_code_type,
                           bar_width, bar_code_alignment, print_barcode_text,
                           timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать штрих-кода линией
            :param bar_code:
            :param line_number:
            :param bar_code_type:
            :param bar_width:
            :param bar_code_alignment:
            :param print_barcode_text:
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "print_line_barcode", timeout, bar_code, line_number, bar_code_type,
            bar_width, bar_code_alignment, print_barcode_text)

    @command
    def print_report_with_cleaning(self, timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать суточного отчета с гашением
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("print_report_with_cleaning", timeout)

    @command
    def print_report_without_cleaning(self, timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать суточного отчета с гашением
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "print_report_without_cleaning", timeout)

    @command
    def print_string(self, string, timeout=None, on_check=True, on_journal=True,
                     align='left', fill=''):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать строки
            :param string: строка для печати
            :param timeout: время ожидания ответа
            :param on_check: печать на чековой ленте
            :param on_journal: печать на журнальной ленте
            :param align: выравнивание текста в строке
            :param fill: символ или строка заполнения
            :returns объект типа BaseCommandState
        """
        fmt_text = format_string(string, self.__device.check_width, align, fill)
        return self.__device.make_action(
            "print_string", timeout, fmt_text, on_check=on_check,
            on_journal=on_journal)

    @command
    def print_wide_string(self, string, timeout=None, on_check=True,
                          on_journal=True, align='left', fill=''):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Печать жирной строки
            :param string: строка для печати
            :param timeout: время ожидания ответа
            :param on_check: печать на чековой ленте
            :param on_journal: печать на журнальной ленте
            :param align: выравнивание текста в строке
            :param fill: символ или строка заполнения
            :returns объект типа BaseCommandState
        """
        fmt_text = format_string(
            string, self.__device.check_width, align, fill, bold=True)
        return self.__device.make_action(
            "print_wide_string", timeout, fmt_text, on_check=on_check,
            on_journal=on_journal)

    @command
    def return_sale(
            self, price, timeout=None, count=1, department=1,
            taxes=[0]*4, text=u" "):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Возврат продажи
            :param price: Цена
            :param count: Количество
            :param department: Номер отдела
            :param taxes: Налоги 1-4
            :param text: Сопроводительный текст
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "return_sale", timeout, price, count=count, department=department,
            taxes=taxes, text=text)

    @command
    def sale(self, price, count=1, text=u' ', department=1, taxes=[0]*4,
             timeout=None):
        """ * Интерфейс работы с ККТ с поддержкой поправки времени выполнения *
            Продажа
            :param price: цена
            :param count: количество
            :param text: сопроводительный текст
            :param department: номер отдела
            :param taxes: налоги 1-4
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "sale", timeout, price, count=count, text=text,
            department=department, taxes=taxes)

    @command
    def set_date(self, c_date, timeout=None):
        """ * Интерфейс работы с ККТ *
            Установка даты
            :param c_date: дата
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("set_date", timeout, c_date)

    @command
    def set_time(self, c_time, timeout=None):
        """ * Интерфейс работы с ККТ *
            Установка времени
            :param c_time: время
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action("set_time", timeout, c_time)

    @command
    def set_exchange_param(self, port, rate, timeout=None):
        """ * Интерфейс работы с ККТ *
            Установка параметров связи
            :param port: номер порта
            :param rate: скорость обмена данными
            :param timeout: время ожидания ответа
            :returns объект типа BaseCommandState
        """
        return self.__device.make_action(
            "set_exchange_param", timeout, port, rate)
