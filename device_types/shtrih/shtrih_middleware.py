# -*- coding: utf-8 -*-
""" LoremCross
    Модуль работы с фискальными устройствами
    Интерфейсы печати на ККТ для устройств семейства Штрих: ФРК, ФРФ, М
    Классы подготовки запроса и обработки результата
"""
from struct import pack

from shtrih_constants import DEV_MODE, DEV_SUBMODE, CP_DEV
from utils import byte2array, hex2str


class ShtrihPrepareRequest(object):
    """ Класс для подготовки запроса """

    def beep(self, *_, **__):
        return ''

    def cancel_check(self, *_, **__):
        return ''

    def cash_income(self, cash=0.0):
        return pack('i', int(cash*100))+chr(0x0)

    def cash_outcome(self, cash=0.0):
        return pack('i', int(cash*100))+chr(0x0)

    def close_check(self, sum1=0.0, sum2=0.0, sum3=0.0, sum4=0.0, sale=0,
                    tax1=0, tax2=0, tax3=0, tax4=0, text=u" "):
        b_sums = "".join([pack('i', int(s*100))+chr(0x0)
                         for s in (sum1, sum2, sum3, sum4)])
        b_sale = pack('h', int(sale*100))
        taxes = (tax1, tax2, tax3, tax4)
        b_taxes = "%s" * len(taxes) % tuple([chr(t) for t in taxes])
        b_text = text.encode(CP_DEV).ljust(40, chr(0x0))
        return b_sums + b_sale + b_taxes + b_text

    def confirm_date(self, c_date):
        return ''.join(
            chr(i) for i in [c_date.day, c_date.month, c_date.year % 1000])

    def continue_print(self, *_, **__):
        return ''

    def cut_check(self, full_cut=True):
        return chr(1 if full_cut else 0)

    def feed_document(self, rows, check=True, journal=True, slip=True):
        flag = 0
        if check:
            flag |= 1
        if journal:
            flag |= 2
        if slip:
            flag |= 4
        return hex2str(flag, int(rows))

    def get_autocut_param(self, *_, **__):
        # Значение автоотрезки: таблица 1, строка 1, поле 8
        return '\x01\x01\x00\x08'

    def get_cash_reg(self, register):
        return chr(register)

    def get_device_metrics(self, *_, **__):
        return ''

    def get_exchange_param(self, port):
        return chr(port)

    def get_short_status(self, *_, **__):
        return ''

    def get_status(self, *_, **__):
        return ''

    def interrupt_test(self, *_, **__):
        return ''

    def open_session(self, *_, **__):
        return ''

    def print_barcode(self, number):
        return number

    def print_image(self, start_row=1, end_row=199):
        return chr(start_row) + chr(end_row)

    def print_report_with_cleaning(self, *_, **__):
        return ''

    def print_report_without_cleaning(self, *_, **__):
        return ''

    def print_string(self, string, on_check=True, on_journal=True):
        flag = 0
        if on_check:
            flag |= 1
        if on_journal:
            flag |= 2

        string = string.encode(CP_DEV)
        return hex2str(flag)+string

    def print_wide_string(self, string, on_check=True, on_journal=True):
        return self.print_string(
            string, on_check=on_check, on_journal=on_journal)

    def return_sale(self, price, count=1, department=1, taxes=[0]*4, text=u" "):
        b_count = pack('i', count*1000)+chr(0x0)
        b_price = pack('i', int(price*100))+chr(0x0)
        b_department = chr(department)
        b_taxes = "%s%s%s%s" % tuple(map(lambda x:chr(x), taxes))
        b_text = text.encode(CP_DEV).ljust(40, chr(0x0))
        return b_count + b_price + b_department + b_taxes + b_text

    def sale(self, price, count=1, text=u' ', department=1, taxes=[0]*4):
        b_count = pack('i', count*1000)+chr(0x0)
        b_price = pack('i', int(price*100))+chr(0x0)
        b_department = chr(department)
        b_taxes = "%s%s%s%s" % tuple(map(lambda x: chr(x), taxes))
        b_text = text.encode(CP_DEV).ljust(40, chr(0x0))
        return b_count + b_price + b_department + b_taxes + b_text

    def set_date(self, c_date):
        return ''.join(
            chr(i) for i in [c_date.day, c_date.month, c_date.year % 1000])

    def set_time(self, c_time):
        return ''.join(
            chr(i) for i in [c_time.hour, c_time.minute, c_time.second])

    def set_exchange_param(self, port, rate):
        return chr(port) + chr(rate)


class ShtrihPrepareResponse(object):
    """ Класс для обработки результата """

    def beep(self, data):
        return {'operator': ord(data[0])}

    def cancel_check(self, data):
        return {'operator': ord(data[0])}

    def cash_income(self, data):
        return {'operator': ord(data[0]), 'document': ord(data[1])}

    def cash_outcome(self, data):
        return {'operator': ord(data[0]), 'document': ord(data[1])}

    def close_check(self, data):
        return {'operator': ord(data[0])}

    def confirm_date(self, data):
        return {'error': data[0]}

    def continue_print(self, data):
        return {'operator': ord(data[0])}

    def cut_check(self, data):
        return {'operator': ord(data[0])}

    def feed_document(self, data):
        return {'operator': ord(data[0])}

    def get_autocut_param(self, data):
        return {'auto_cut': bool(ord(data[0]))}

    def get_cash_reg(self, data):
        operator = data[0]
        value = 0
        cash_reg = map(lambda x: x.encode('hex'), data.rstrip('\x00')[1:])
        cash_reg.reverse()
        if cash_reg:
            value = int('0x'+''.join(cash_reg), 16) * 1.0 / 100
        return {'operator': ord(operator), 'value': value}

    def get_device_metrics(self, data):
        return {'major_prot_version': ord(data[0]),
                'minor_prot_version': ord(data[1]),
                'device_type': ord(data[2]),
                'device_subtype': ord(data[3]),
                'device_model': ord(data[4]),
                'device_codepage': ord(data[5]),
                'description': data[6:].decode(CP_DEV)}

    def get_exchange_param(self, data):
        return {'operator': ord(data[0]), 'rate': ord(data[1])}

    def get_short_status(self, data):
        info = {}
        # флаги ККТ
        flags = byte2array(ord(data[2]))
        flags.extend(byte2array(ord(data[1])))

        info['operator'] = ord(data[0])
        info['flags'] = data[1] + data[2]
        info.update(
            {
                'chkeck_ribbon': flags[0],
                'journal_ribbon': flags[1],
                'slip_ribbon': flags[2],
                'slip_control': flags[3],
                'dec_point_position': flags[4],
                'eklz_present': flags[5],
                'journal_optic_control': flags[6],
                'check_optic_control': flags[7],
                'journal_lever': flags[8],
                'check_lever': flags[9],
                'cover_is_opened': flags[10],
                'print_left_control': flags[11],
                'print_right_control': flags[12],
                'drawer_state': flags[13],
                'eklz_is_over': flags[14],
                'quantity_dec_point': flags[15]
            }
        )
        # текущие режимы и подрежимы работы
        mode, submode = ord(data[3]), ord(data[4])
        info.update({'cashcontrol_mode': mode, 'cashcontrol_submode': submode})

        info['cashcontrol_mode_description'] = DEV_MODE.get(mode) or "?"
        info['cashcontrol_submode_description'] = (DEV_SUBMODE.get(mode) or {})\
            .get(submode) or "?"
        info['cashcontrol_8_mode_state'] = '?'
        info['cashcontrol_13_14_mode_state'] = '?'
        info['registrations_count'] = ord(data[5])
        info['reserve_battery_voltage'] = ord(data[6])
        info['main_battery_voltage'] = ord(data[7])
        info['fp_error'] = ord(data[8])
        info['eklz_error'] = ord(data[9])
        info['reserve'] = data[10:]

        return info

    def get_status(self, data):
        info = {
            'operator': ord(data[0]),
            'soft_version': data[1:3],
            'soft_build_number': data[3:5],
            'soft_build_date': "%s.%s.%s" % (str(ord(data[5])).rjust(2, '0'),
                                             str(ord(data[6])).rjust(2, '0'),
                                             str(ord(data[7])).rjust(2, '0')),
            'logical_cash_number': ord(data[8]),
            'last_document_number': ord(data[9])
        }
        # флаги ККТ
        flags = byte2array(ord(data[11]))
        flags.extend(byte2array(ord(data[10])))
        info.update({
            'chkeck_ribbon': flags[0],
            'journal_ribbon': flags[1],
            'slip_ribbon': flags[2],
            'slip_control': flags[3],
            'dec_point_position': flags[4],
            'eklz_present': flags[5],
            'journal_optic_control': flags[6],
            'check_optic_control': flags[7],
            'journal_lever': flags[8],
            'check_lever': flags[9],
            'cover_is_opened': flags[10],
            'print_left_control': flags[11],
            'print_right_control': flags[12],
            'drawer_state': flags[13],
            'eklz_is_over': flags[14],
            'quantity_dec_point': flags[15]
        })
        # текущие режимы и подрежимы работы
        mode, submode = ord(data[13]), ord(data[14])
        info['cashcontrol_mode'] = mode
        info['cashcontrol_submode'] = submode
        info['cashcontrol_mode_description'] = DEV_MODE.get(mode) or "?"
        info['cashcontrol_submode_description'] = (DEV_SUBMODE.get(mode) or {})\
            .get(submode) or "?"

        return info

    def interrupt_test(self, data):
        return {'operator': ord(data[0])}

    def open_session(self, data):
        return {'operator': ord(data[0])}

    def print_barcode(self, data):
        return {'operator': ord(data[0])}

    def print_image(self, data):
        return {'operator': ord(data[0])}

    def print_report_with_cleaning(self, data):
        return {'operator': ord(data[0])}

    def print_report_without_cleaning(self, data):
        return {'operator': ord(data[0])}

    def print_string(self, data):
        return {'operator': ord(data[0])}

    def print_wide_string(self, data):
        return self.print_string(data)

    def return_sale(self, data):
        return {'operator': ord(data[0])}

    def sale(self, data):
        return {'operator', ord(data[0])}

    def set_date(self, data):
        return {'error', ord(data[0])}

    def set_time(self, data):
        return {'error': data[0]}

    def set_exchange_param(self, data):
        return {'operator': ord(data[0])}


# def print_line_barcode(dev, bar_code, line_number, bar_code_type, bar_width,
#                        bar_code_alignment, print_barcode_text,
#                        timeout=None):
#     """ Печать штрих-кода линией
#         Параметры: номер
#         ВОЗВРАТ: код ошибки, номер оператора
#         РЕЖИМ:
#         ПЕРЕХОД: нет
#         :param dev: объект для работы с устройством
#         :param bar_code:
#         :param line_number:
#         :param bar_code_type:
#         :param bar_width:
#         :param bar_code_alignment:
#         :param print_barcode_text:
#         :param timeout: время ожидания ответа
#         :returns объект типа BaseCommandState
#     """
#     s_number = ''.join([chr(int(i)) for i in bar_code])
#     s_number += chr(10) + chr(0) + chr(100) + chr(2) + chr(0)
#     response = make_action(dev, "print_line_barcode", s_number, timeout)
#
#     if response.data:
#         data = {'operator': ord(response.data[0])}
#         response.data = data
#     return response
