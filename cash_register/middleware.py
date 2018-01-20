# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Промежуточные обработчики, классы-примеси для основного интерфейса
"""
import json
import logging
import os
from threading import Lock

from jinja2 import FileSystemLoader, Environment


class TemplateReader(object):
    """ Чтение шаблонов и построение списка команд """
    templates_map = {}

    def __init__(self, path=None):
        """ Конструктор класса
            :param path: путь к каталогу с шаблонами
        """
        self.__path = None
        self.__loader = None
        self.__env = None

        if path:
            self.init_template_path(path)

    def init_template_path(self, path):
        self.__path = path
        self.__loader = FileSystemLoader(self.__path)
        self.__env = Environment(loader=self.__loader)

    def get_template(self, template, path=None, namespace=None):
        """ Получение шаблона
            :param template: имя файла с шаблоном
            :param path: альтернативный путь к каталогу с шаблонами
            :param namespace: глобальные переменные
        """
        if (path is not None) and (os.path.exists(path)):
            env = Environment(loader=FileSystemLoader(path))
        else:
            env = self.__env

        return env.get_template(template, globals=namespace)

    def render_template(self, name, namespace, data, context):
        """ Рендер шаблона
            :param name:
            :param namespace:
            :param data:
            :param context:
            :returns
        """
        template = self.get_template(name, namespace=namespace)
        return template.render(data=data, control_context=context)


class ProxyCashRegister(object):
    """ Прокси класс для формирования списка команд
        во время выполнения шаблона
    """
    def __init__(self, CashRegisterClass):
        self._CashRegister = CashRegisterClass
        self.__commands = []

    @property
    def cash_register_class(self):
        return self._CashRegister

    @property
    def commands(self):
        return self.__commands

    def __call__(self, instance):
        assert isinstance(instance, self._CashRegister)
        cmd_metrics = self._CashRegister.get_commands_metric()
        last_command = ''
        for item in self.__commands:
            cmd, args, kwargs = item
            if cmd.__name__ in cmd_metrics:
                timeout, fixed = cmd_metrics[cmd.__name__]
                kwargs['timeout'] = abs(timeout)

                if (last_command in cmd_metrics) \
                        and (last_command != cmd.__name__):
                    last_timeout, _ = cmd_metrics[last_command]
                    if last_timeout > timeout:
                        kwargs['timeout'] += abs(last_timeout)
            yield cmd(instance, *args, **kwargs)
        yield

    def init_cash_register(self, port, rate):
        self.__commands.append(
            [self._CashRegister.init_cash_register, (port, rate), {}])

    def find_device(self, port_group=None, rate=None):
        self.__commands.append(
            [self._CashRegister.find_device, (),
             {'port_group': port_group, 'rate': rate}])

    def beep(self, timeout=None):
        self.__commands.append(
            [self._CashRegister.beep, (), {'timeout': timeout}])

    def cancel_check(self, timeout=None):
        self.__commands.append(
            [self._CashRegister.beep, (), {'timeout': timeout}])

    def cancel_check(self, timeout=None):
        self.__commands.append([
            self._CashRegister.cancel_check, (), {'timeout': timeout}])

    def cash_income(self, timeout=None, cash=0.0):
        self.__commands.append([
            self._CashRegister.cash_income, (),
            {'timeout': timeout, 'cash': cash}])

    def cash_outcome(self, timeout=None, cash=0.0):
        self.__commands.append([
            self._CashRegister.cash_outcome, (),
            {'timeout': timeout, 'cash': cash}])

    def close_check(self, timeout=None, sum1=0.0, sum2=0.0, sum3=0.0, sum4=0.0,
                    sale=0, tax1=0, tax2=0, tax3=0, tax4=0, text=u" "):
        self.__commands.append(
            [self._CashRegister.close_check, (),
             {'sum1': sum1, 'sum2': sum2, 'sum3': sum3, 'sum4': sum4,
              'sale': sale, 'tax1': tax1, 'tax2': tax2, 'tax3': tax3,
              'tax4': tax4, 'text': text, 'timeout': timeout}])

    def confirm_date(self, c_date, timeout=None):
        self.__commands.append([
            self._CashRegister.confirm_date, (c_date, ), {'timeout': timeout}])

    def continue_print(self, timeout=None):
        self.__commands.append([
            self._CashRegister.continue_print, (), {'timeout': timeout}])

    def cut_check(self, timeout=None, full_cut=True):
        self.__commands.append([
            self._CashRegister.cut_check, (),
            {'full_cut': full_cut, 'timeout': timeout}])

    def feed_document(
            self, rows, timeout=None, check=True, slip=True, journal=True):
        self.__commands.append([
            self._CashRegister.feed_document, (rows, ),
            {'check': check, 'journal': journal, 'slip': slip,
             'timeout': timeout}])

    def get_autocut_param(self, timeout=None):
        self.__commands.append([
            self._CashRegister.get_autocut_param, (), {'timeout': timeout}])

    def get_cash_reg(self, register, timeout=None):
        self.__commands.append([
            self._CashRegister.get_cash_reg, (register, ),
            {'timeout': timeout}])

    def get_device_metrics(self, timeout=None):
        self.__commands.append([
            self._CashRegister.get_device_metrics, (), {'timeout': timeout}])

    def get_exchange_param(self, port, timeout=None):
        self.__commands.append([
            self._CashRegister.get_exchange_param, (port, ),
            {'timeout': timeout}])

    def get_short_status(self, timeout=None):
        self.__commands.append([
            self._CashRegister.get_short_status, (), {'timeout': timeout}])

    def get_status(self, timeout=None):
        self.__commands.append([
            self._CashRegister.get_status, (), {'timeout': timeout}])

    def interrupt_test(self, timeout=None):
        self.__commands.append([
            self._CashRegister.interrupt_test, (), {'timeout': timeout}])

    def open_session(self, timeout=None):
        self.__commands.append([
            self._CashRegister.open_session, (), {'timeout': timeout}])

    def print_barcode(self, number, timeout=None):
        self.__commands.append(
            [self._CashRegister.print_barcode, (timeout, number), {}])

    def print_image(self, timeout=None, start_row=1, end_row=199):
        self.__commands.append([
            self._CashRegister.print_image, (),
            {'start_row': start_row, 'end_row': end_row, 'timeout': timeout}])

    def print_line_barcode(self, bar_code, line_number, bar_code_type,
                           bar_width, bar_code_alignment, print_barcode_text,
                           timeout=None):
        self.__commands.append([
            self._CashRegister.print_line_barcode,
            (bar_code, line_number, bar_code_type, bar_width,
             bar_code_alignment, print_barcode_text), {'timeout': timeout}])

    def print_report_with_cleaning(self, timeout=None):
        self.__commands.append([
            self._CashRegister.print_report_with_cleaning, (),
            {'timeout': timeout}])

    def print_report_without_cleaning(self, timeout=None):
        self.__commands.append([
            self._CashRegister.print_report_without_cleaning, (),
            {'timeout': timeout}])

    def print_string(self, string, timeout=None, on_check=True, on_journal=True,
                     align='left', fill=''):
        self.__commands.append([
            self._CashRegister.print_string, (string, ),
            {'on_check': on_check, 'on_journal': on_journal, 'align': align,
             'fill': fill, 'timeout': timeout}])

    def print_wide_string(self, string, timeout=None, on_check=True,
                          on_journal=True, align='left', fill=''):
        self.__commands.append([
            self._CashRegister.print_wide_string, (string, ),
            {'on_check': on_check, 'on_journal': on_journal, 'align': align,
             'fill': fill, 'timeout': timeout}])

    def return_sale(self, price, timeout=None, count=1, department=1,
                    taxes=[0] * 4, text=u" "):
        self.__commands.append([
            self._CashRegister.return_sale, (price, ),
            {'count': count, 'department': department, 'taxes': taxes,
             'text': text, 'timeout': timeout}])

    def sale(self, price, count=1, text=u' ', department=1, taxes=[0] * 4,
             timeout=None):
        self.__commands.append([
            self._CashRegister.sale, (price, ),
            {'count': count, 'text': text, 'department': department,
             'taxes': taxes, 'timeout': timeout}])

    def set_date(self, c_date, timeout=None):
        self.__commands.append([
            self._CashRegister.set_date, (c_date, ), {'timeout': timeout}])

    def set_time(self, c_time, timeout=None):
        self.__commands.append([
            self._CashRegister.set_time, (c_time, ), {'timeout': timeout}])

    def set_exchange_param(self, port, rate, timeout=None):
        self.__commands.append([
            self._CashRegister.set_exchange_param, (port, rate),
            {'timeout': timeout}])


class SMARTDescriptor(object):
    """ Класс управления метрикой устройства
        Реализует чтение и запись метрики устройства в текстовый файл
        с промежуточным кэшированием.
        Реализован на основе дескрипторов.
    """

    def __init__(self, path, cache_name):
        self.__lock = Lock()

        if path.endswith(os.sep):
            path = path[:-1]

        file_name = [path, cache_name] if path else [cache_name, ]
        self.__file_name = os.sep.join(file_name)
        if os.path.exists(self.__file_name):
            with open(os.sep.join(file_name)) as handle:
                try:
                    self.__cache = json.load(handle)
                except:
                    self.__cache = {}
        else:
            self.__cache = {}

    def __del__(self):
        self.__write()

    def __get__(self, *_):
        return self.__cache

    def __set__(self, _, value):
        self.__cache.update(**value)
        self.__write()

    def __write(self):
        if self.__cache:
            with self.__lock:
                json.dump(self.__cache, open(self.__file_name, 'w'))


class SmartMixin(object):
    """ Интерфейс взаимодействия со SMART объектом """

    smart = None

    @classmethod
    def register_smart(cls, metric_path, metric_name):
        cls.smart = SMARTDescriptor(metric_path, metric_name)

    @classmethod
    def get_device_metric(cls):
        metric = cls.smart or {}
        return metric.get('device') or {}

    @classmethod
    def get_commands_metric(cls):
        metric = cls.smart or {}
        return metric.get('commands') or {}


class Log(object):
    """ Интерфейс логирования """
    def __init__(self):
        self.__log = None

    def register_log(self, log):
        self.__log = log

    def log_debug(self, msg, *args, **kwargs):
        if self.__log:
            self.__log.debug(msg, args, kwargs)

    def log_info(self, msg, *args, **kwargs):
        if self.__log:
            self.__log.info(msg, args, kwargs)

    def log_warning(self, msg, *args, **kwargs):
        if self.__log:
            self.__log.warning(msg, args, kwargs)

    def log_error(self, msg, *args, **kwargs):
        if self.__log:
            self.__log.error(msg, args, kwargs)

    def log_critical(self, msg, *args, **kwargs):
        if self.__log:
            self.__log.critical(msg, args, kwargs)
