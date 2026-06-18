import os
import ctypes
from ctypes import wintypes


# Жестко объявляем структуру Windows API с правильным выравниванием типов данных
class WIN32_FIND_STREAM_DATA(ctypes.Structure):
    _fields_ = [
        ("StreamSize", ctypes.c_longlong),
        ("cStreamName", wintypes.WCHAR * 296)
        # В NTFS максимальная длина имени потока + обвесы составляет 296 символов WCHAR
    ]


def get_ads_size(file_path):
    """Возвращает суммарный размер всех альтернативных потоков (ADS) для файла/директории"""
    if os.name != 'nt':
        return 0

    # Превращаем путь в абсолютную строку для WinAPI
    file_path = os.path.abspath(str(file_path))
    total_ads_size = 0
    find_data = WIN32_FIND_STREAM_DATA()

    kernel32 = ctypes.windll.kernel32
    kernel32.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.FindFirstStreamW.restype = wintypes.HANDLE

    kernel32.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.FindNextStreamW.restype = wintypes.BOOL

    handle = kernel32.FindFirstStreamW(file_path, 0, ctypes.byref(find_data), 0)

    if handle != -1 and handle != 0 and handle is not None:
        try:
            while True:
                stream_name = find_data.cStreamName

                if stream_name:
                    # Приводим к верхнему регистру для надежности сравнения
                    stream_name_upper = stream_name.upper()

                    # Пропускаем стандартный главный поток данных файла
                    if stream_name_upper != "::$DATA" and stream_name_upper != "":
                        total_ads_size += find_data.StreamSize

                if not kernel32.FindNextStreamW(handle, ctypes.byref(find_data)):
                    break
        finally:
            kernel32.FindClose(handle)

    return total_ads_size