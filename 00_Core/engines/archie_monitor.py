import ctypes
import time
import os


# Estrutura idêntica à do C++ para o Python entender os dados
class HcbMemoryCapsule(ctypes.Structure):
    _fields_ = [
        ("sentinel_active", ctypes.c_int),           # 4 bytes
        ("cortex_active", ctypes.c_int),             # 4 bytes
        ("last_action_code", ctypes.c_int),          # 4 bytes
        ("total_processed", ctypes.c_ulonglong),     # 8 bytes
        ("system_load", ctypes.c_float),             # 4 bytes
        ("last_command", ctypes.c_char * 256),       # 256 bytes
        ("last_file_path", ctypes.c_char * 512),     # 512 bytes
        ("heartbeat", ctypes.c_longlong)             # 8 bytes (O que você quer ler!)
    ]

DLL_PATH = r"F:\HCB_STUDIO\00_Core\engines\hcb_bridge.dll"
bridge = ctypes.WinDLL(DLL_PATH)


def iniciar_monitor():
    if bridge.InitializeBridge():
        # Pegamos o endereço de memória que o C++ gerou
        bridge.GetMemoryPointer.restype = ctypes.POINTER(HcbMemoryCapsule)
        ponteiro_ram = bridge.GetMemoryPointer()

        print("🖥️  PAINEL DE MONITORAMENTO HCB")
        print("--- Lendo Shared Memory em Tempo Real ---\n")

        try:
            while True:
                # Lemos o valor diretamente da RAM
                valor_atual = ponteiro_ram.contents.heartbeat

                # Limpa a tela para parecer um painel fixo
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Estado do Archie: {'🟢 ONLINE' if valor_atual > 0 else '🔴 OFFLINE'}")
                print(f"Último Pulso (Unix Time): {valor_atual}")
                print(f"Data/Hora: {time.ctime(valor_atual)}")
                print("\n(Pressione Ctrl+C para fechar o monitor)")

                time.sleep(0.5)
        except KeyboardInterrupt:
            bridge.CloseBridge()
            print("\nMonitor encerrado.")
    else:
        print("❌ Não foi possível acessar a ponte de memória.")


if __name__ == "__main__":
    iniciar_monitor()