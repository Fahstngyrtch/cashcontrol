# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства Штрих: ФРК, ФРФ, М
    Драйвер
"""
import time
import serial
import glob
import sys

from .utils import get_crc
from .shtrih_constants import PASSWORD, ENQ, ACK, NAK, STX, ST_NO_SIGNAL, \
    ST_READY, COMMANDS, TIME_DELTA_STEP, MAX_TRIES, DEF_TIMEOUT, RATES, \
    ST_READ, ST_RETRY, TIME_DELTA_ERRORS, CRITICAL_COMMANDS, \
    POST_CRITICAL_COMMANDS, PRN_NON_CRITICAL, PRN_CRITICAL, PRN_POST_CRITICAL, \
    ERR_OPENING_PORT, ERR_LOST_DEVICE, ERR_UNKNOWN_COMMAND, NO_NEED_PASSWORD, \
    FINAL_TIME
from .shtrih_exceptions import ShtrihConnectionError, ShtrihCommandError, \
    ShtrihError


class Shtrih(object):
    """ Класс работы с фискальными устройствами семейства "Штрих"
        Класс реализует основные методы записи и чтения данных с устройства
        Команды прикладного уровня реализуются в наследниках класса

        Диаграмма состояний обмена стандартного нижнего уровня со стороны ПК

                                       [Запуск программы]
,---,-------------------------------.    |                     ,----------.
|,--^-----------------------------. |    |                     |          |
||  |   [J=0]<------------------. | `->[Формирование команды]<-^----.     |
||  |     |                     | |      |                     |    |     |
||,-^-->[Ожидание STX]          | `--->[Посылка ENQ]<----------^-.--^--.  |
||| |     |                     |        |                     | |  |  |  |
||| `ДА-[Таймаут STX истек?]    |      [Ожидание ответа]       | |  |  |  |
|||       | НЕТ                 |        |                     | |  |  |  |
|||     [STX?]-НЕТ-------------.| ,-ДА-[Таймаут истек?]        | |  |  |  |
|||       |                    || |      | НЕТ                 | |  |  |  |
|||     [Ожидание длины]       |`-^-ДА-[ACK?]                  | |  |  |  |
|||       |                    |  |      | НЕТ                 | |  |  |  |
|||,-ДА-[Таймаут истек?]       |  |    [NAK?]-ДА---------------' |  |  |  |
||||      | НЕТ                |  |      | НЕТ                   |  |  |  |
||||    [Ожидание байта]<-----,|  |    [Ожидание конца           |  |  |  |
||||      |                   ||  |     передачи от ФР]----------'  |  |  |
||||-ДА-[Таймаут истек?]      ||  |                                 |  |  |
||||      | НЕТ               ||  |                                 |  |  |
||||    [Последний байт?]-НЕТ-'`--`--->[Нет связи]----------------->|  |  |
||||      | ДА                                                      |  |  |
||||    [Ожидание КС]             ,--->[Ответ ACK]                  |  |  |
||||      |                       |      |                          |  |  |
||||-ДА-[Таймаут истек?]          |    [Обработка ответа]           |  |  |
||||      | НЕТ                   |      |                          |  |  |
||||    [КС верна?]-ДА------------'  ,---`--------------------------'  |  |
||||      | НЕТ                ,-----'                                 |  |
||||----[посылка NAK]          |  ,------------------------------------'  |
||||                           |  |      ,--------------------------------'
|||`--->[J<10?]-ДА-----.       |  |    [I=0]
|||       | НЕТ        |       |  |      |
|||     [Нет связи] [J=J+1]    |  |    [Посылка]<----------------.
|`^-------'            |       |  |      |                       |
| |                    |       |  |    [Ожидание подтверждения]  |
`-^--------------------'       |  |      |                       |
  |                            |  `-ДА-[Таймаут истек?]          |
  |                            |         | НЕТ                   |
  |                            |  ,-ДА-[ACK?]                    |
  |                            |  |      | НЕТ                   |
  |                            |  |    [I<10?]-ДА----,           |
  |                            |  |      | НЕТ       |           |
  |                            `--^----[Нет связи] [I=I+1]-------'
  |                               |
  |                               `------.
  |                                      |
  |                                    [Переход в состояние ожидание ответа]
  |                                      |
  `--------------------------------------'
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
        self.__check_width = 38
        if port is not None:
            if not isinstance(port, str):
                port = port.encode('utf-8')
            else:
                port = str(port)
        self.__result = {}  # шаблон ответа
        self.__port = port
        self.__rate = rate
        self.__tm_read = read_timeout
        self.__tm_write = write_timeout
        self.__password = password
        self.__srl = None
        self.__is_opened = False
        # открытие порта
        if self.__port and self.__rate:
            self.__open_port()

        self.__print_zone = PRN_NON_CRITICAL
        self._last_command_is_printing = False
        self.__last_critical_command = ''

    def __del__(self):
        """ Закрытие порта """
        self.__close_port()

    def __open_port(self):
        """ Открытие порта """
        if not (self.__port and self.__rate):
            return
        try:
            self.__srl = serial.Serial(
                self.port,
                self.rate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.__tm_read,
                writeTimeout=self.__tm_write
            )
        except Exception:
            raise ShtrihConnectionError(ERR_OPENING_PORT)

        if not self.__srl.isOpen():
            raise ShtrihConnectionError(ERR_LOST_DEVICE)
        self.__is_opened = True

    def __close_port(self):
        """ Закрытие порта """
        if self.__srl:
            self.__srl.close()
        self.__is_opened = False

    @property
    def check_width(self):
        """ Ширина чека. Зависит от модели ККТ """
        return self.__check_width

    @property
    def time_delta_step(self):
        """ Минимальный шаг по времени выполнения """
        return TIME_DELTA_STEP

    @property
    def is_opened(self):
        """ Признак открытого порта """
        return self.__is_opened

    @property
    def port(self):
        """ Номер порта """
        return self.__port

    @port.setter
    def port(self, value):
        self.__close_port()
        self.__port = value
        self.__open_port()

    @property
    def rate(self):
        """ Скорость обмена данными """
        return self.__rate

    @rate.setter
    def rate(self, value):
        self.__close_port()
        self.__rate = value
        self.__open_port()

    @property
    def print_zone(self):
        """ Проверка на прохождение критической области печати """
        return self.__print_zone

    def find_device(self, port_group=None, rate=None):
        """ Поиск устройства
            :param port_group: семейство портов (tty, ttyS, ttyUSB, ttyACM)
            :param rate: скорость обмена данными
            :returns номер порта, скорость обмена данными
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        else:
            ports = glob.glob('/dev/tty[A-Za-z]*')
            if port_group:
                ports = [p for p in ports if port_group in p]
        rates = [rate, ] if rate in RATES else RATES
        for port in ports:
            try:
                self.port = port
            except:
                continue
            for rate in rates:
                self.rate = rate
                if self.__check_state() != ST_NO_SIGNAL:
                    return self.port, self.rate
        raise ShtrihConnectionError(ERR_LOST_DEVICE)

    def __check_state(self):
        """ Проверка готовности аппарата """
        answer = ST_NO_SIGNAL

        try:
            self.__srl.flush()
            self.__srl.write(ENQ)
            reply = self.__srl.read(1)
        except:
            pass
        else:
            if reply:
                if reply == NAK:
                    answer = ST_READY
                elif reply == ACK:
                    answer = ST_READ
        return answer

    def __write(self, command, parameters, wait_time=None):
        """ Отправка данных на устройство с учетом времени ожидания записи
            :param command: код команды на исполнение
            :param parameters: строка с аргументами
        """
        password = '' if command in NO_NEED_PASSWORD else self.__password
        data = chr(command) + password + parameters
        content = chr(len(data)) + data
        crc = get_crc(content)

        for _ in range(MAX_TRIES):
            self.__srl.write(STX + content + crc)
            if wait_time is not None:
                self.__tm_read = wait_time
                self.__srl.timeout = wait_time
            reply = self.__srl.read(1)
            if reply == ACK:
                return ST_READY

        return ST_NO_SIGNAL

    def __read(self):
        """ Чтение данных с устройства
            с проверкой длины ответа и контрольной суммы
        """
        bit = self.__srl.read(1)
        if bit != STX:
            return ST_RETRY, 0, None

        length = ord(self.__srl.read(1))
        ctrl_len = length - 2
        command = self.__srl.read(1)
        err_code = self.__srl.read(1)
        data = self.__srl.read(ctrl_len)

        crc_dev = self.__srl.read(1)
        crc_data = get_crc(chr(length) + command + err_code + data)
        if crc_dev != crc_data:
            self.__srl.write(NAK)
            return ST_RETRY, ord(err_code), None

        self.__srl.write(ACK)
        self.__srl.read(1)
        return ST_READY, ord(err_code), data

    def __call__(self, command, parameters, wait_time=None):
        """ Один рабочий цикл
            (проверка состояния, отправка команды, получение и анализ ответа)
            :param command: команда
            :param parameters: строка с параметрами
            :param wait_time: время ожидания отклика
        """
        if command not in COMMANDS:
            raise ShtrihCommandError(ERR_UNKNOWN_COMMAND)

        code, command_description = COMMANDS[command]
        self.__result.update(
            {'code': code, 'command': command_description, 'error': None,
             'data': '', 'delta': 0, 'last_cmd_delta': 0}
        )

        state = self.__check_state()
        if state == ST_READ:
            self.__read()
            # NOTE: В ККТ болтается ответ на предыдущую команду
        elif state != ST_READY:
            raise ShtrihConnectionError(ERR_LOST_DEVICE)

        state = self.__write(code, parameters, wait_time or DEF_TIMEOUT)
        if state == ST_NO_SIGNAL:
            raise ShtrihConnectionError(ERR_LOST_DEVICE)

        t_max = MAX_TRIES
        while t_max > 0:
            state, err_code, data = self.__read()

            if state == ST_RETRY:
                cmd_key = 'delta'
                if self._last_command_is_printing:
                    cmd_key = 'last_cmd_' + cmd_key
                self.__result[cmd_key] += TIME_DELTA_STEP
                time.sleep(TIME_DELTA_STEP)
                t_max -= 1
                continue
            else:
                if err_code in TIME_DELTA_ERRORS:
                    self.__result['last_cmd_delta'] += TIME_DELTA_STEP
                    time.sleep(TIME_DELTA_STEP)
                break
        else:
            raise ShtrihConnectionError(ERR_LOST_DEVICE)

        if self._last_command_is_printing:
            self._last_command_is_printing = False

        self.__result['data'] = data
        if err_code:
            self.__result['error'] = ShtrihError(err_code).serialize()
        else:
            if command in CRITICAL_COMMANDS:
                self.__print_zone = PRN_CRITICAL
                self.__last_critical_command = command
            elif command in POST_CRITICAL_COMMANDS:
                self.__print_zone = PRN_POST_CRITICAL

            if t_max == MAX_TRIES:
                self.__result['delta'] -= TIME_DELTA_STEP

            if command in FINAL_TIME:
                time.sleep(FINAL_TIME[command])

    @property
    def result(self):
        """ Результат выполнения операции
            returns: словарь вида {
                code: код команды,
                command: описание команды,
                error: возникшая ошибка,
                data: возвращаемый ответ (байты),
                delta: приращение ко времени ожидания ответа}
        """
        res = self.__result
        self.__result = {}
        return res

    @property
    def last_critical_command(self):
        """ Наименование последней выполненной команды,
            связанной со входом в критическую область печати документа
        """
        return self.__last_critical_command
