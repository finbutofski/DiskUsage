import ctypes
import os
from ctypes import wintypes


class WIN32_FIND_STREAM_DATA(ctypes.Structure):
    _fields_ = [
        ("StreamSize", ctypes.c_longlong),
        ("cStreamName", wintypes.WCHAR * 260)
    ]


def get_ads_size(file_path):
    """Возвращает суммарный размер всех альтернативных потоков (ADS) для файла/директории"""
    if os.name != 'nt':
        return 0

    total_ads_size = 0
    find_data = WIN32_FIND_STREAM_DATA()

    # Инициализируем поиск потоков
    handle = ctypes.windll.kernel32.FindFirstStreamW(
        ctypes.c_wchar_p(file_path),
        0,
        ctypes.byref(find_data),
        0
    )

    if handle != -1 and handle != 0:
        try:
            while True:
                stream_name = find_data.cStreamName
                if stream_name != "::$DATA":
                    total_ads_size += find_data.StreamSize

                if not ctypes.windll.kernel32.FindNextStreamW(handle, ctypes.byref(find_data)):
                    break
        finally:
            ctypes.windll.kernel32.FindClose(handle)

    return total_ads_size