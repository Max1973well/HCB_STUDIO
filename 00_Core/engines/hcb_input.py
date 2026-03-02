import ctypes
import time


class HcbMemoryCapsule(ctypes.Structure):
    _fields_ = [
        ("sentinel_active", ctypes.c_int), ("cortex_active", ctypes.c_int),
        ("last_action_code", ctypes.c_int), ("total_processed", ctypes.c_ulonglong),
        ("system_load", ctypes.c_float), ("last_command", ctypes.c_char * 256),
        ("last_file_path", ctypes.c_char * 512), ("heartbeat", ctypes.c_longlong)
    ]


bridge = ctypes.WinDLL(r"F:\HCB_STUDIO\00_Core\engines\hcb_bridge.dll")

if bridge.InitializeBridge():
    bridge.GetMemoryPointer.restype = ctypes.POINTER(HcbMemoryCapsule)
    ram = bridge.GetMemoryPointer()

    cmd = input("Digite um comando para o Archie (SAY_HELLO / LIMPAR_TEMP): ")
    ram.contents.last_command = cmd.encode('utf-8')
    print(f"📡 Comando '{cmd}' injetado na RAM!")