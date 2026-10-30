"""Действия над файлами из контекстного меню."""
import ctypes
import os
import subprocess

from PyQt6.QtWidgets import QApplication


def open_in_explorer(path: str) -> None:
    if os.name == "nt":
        subprocess.Popen(f'explorer /select,"{path}"', shell=True)
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def move_to_trash(path: str, hwnd: int = 0) -> None:
    """Удаление в корзину (Windows: SHFileOperationW, иначе gio trash)."""
    if os.name != "nt":
        subprocess.Popen(["gio", "trash", path])
        return

    class SHFILEOPSTRUCT(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("wFunc", ctypes.c_uint),
            ("pFrom", ctypes.c_void_p),
            ("pTo", ctypes.c_void_p),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", ctypes.c_int),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", ctypes.c_void_p),
        ]

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040

    buf = ctypes.create_unicode_buffer(path + "\x00")
    op = SHFILEOPSTRUCT()
    op.hwnd = hwnd
    op.wFunc = FO_DELETE
    op.pFrom = ctypes.addressof(buf)
    op.fFlags = FOF_ALLOWUNDO
    ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))


def copy_path(path: str) -> None:
    QApplication.clipboard().setText(path)
