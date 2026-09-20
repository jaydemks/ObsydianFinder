"""Windows 8+ IFileOperation recycling; no permanent-delete fallback."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import uuid


class GUID(ctypes.Structure):
    _fields_ = [('data', ctypes.c_ubyte * 16)]

    def __init__(self, value):
        super().__init__()
        self.data[:] = uuid.UUID(value).bytes_le


def recycle(path):
    if sys.platform != 'win32' or sys.getwindowsversion()[:2] < (6, 2):
        raise ValueError('Safe Windows recycling requires Windows 8 or later.')
    path = Path(path)
    ole = ctypes.OleDLL('ole32')
    shell = ctypes.OleDLL('shell32')
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    initialized = ole.CoInitializeEx(None, 2)
    if initialized < 0:
        raise OSError('Windows could not initialize the Recycle Bin operation.')
    operation, item = ctypes.c_void_p(), ctypes.c_void_p()

    def check(result):
        if result < 0:
            raise OSError(f'The item could not be recycled (Windows code 0x{result & 0xffffffff:08X}).')

    def method(pointer, index, *types):
        table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *types)(table[index])

    try:
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole.CoCreateInstance.restype = ctypes.c_long
        check(ole.CoCreateInstance(ctypes.byref(GUID('3ad05575-8857-4850-9277-11b85bdb8e09')),
                                   None, 1, ctypes.byref(GUID('947aab5f-0a5c-4c13-b4d6-4bf7836fc9f8')),
                                   ctypes.byref(operation)))
        # RECYCLEONDELETE + EARLYFAILURE + ADDUNDORECORD, and no progress/error/confirmation UI.
        # https://learn.microsoft.com/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags
        flags = 0x00080000 | 0x00100000 | 0x20000000 | 0x400 | 0x4 | 0x10
        check(method(operation, 5, wintypes.DWORD)(operation, flags))
        shell.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p,
                                                    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        shell.SHCreateItemFromParsingName.restype = ctypes.c_long
        check(shell.SHCreateItemFromParsingName(str(path), None,
                                               ctypes.byref(GUID('43826d1e-e718-42ee-bc55-a1e261c37bfe')),
                                               ctypes.byref(item)))
        check(method(operation, 18, ctypes.c_void_p, ctypes.c_void_p)(operation, item, None))
        check(method(operation, 21)(operation))
        aborted = wintypes.BOOL()
        check(method(operation, 22, ctypes.POINTER(wintypes.BOOL))(operation, ctypes.byref(aborted)))
        if aborted.value or path.exists():
            raise OSError('The Recycle Bin operation was cancelled or could not be completed.')
    finally:
        if item:
            method(item, 2)(item)
        if operation:
            method(operation, 2)(operation)
        ole.CoUninitialize()
