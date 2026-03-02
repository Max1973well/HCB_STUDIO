import ctypes
import time
import threading
import os


# 1. Definição da Estrutura (Precisa ser idêntica ao Monitor e ao C++)
class HcbMemoryCapsule(ctypes.Structure):
    _fields_ = [
        ("sentinel_active", ctypes.c_int),
        ("cortex_active", ctypes.c_int),
        ("last_action_code", ctypes.c_int),
        ("total_processed", ctypes.c_ulonglong),
        ("system_load", ctypes.c_float),
        ("last_command", ctypes.c_char * 256),
        ("last_file_path", ctypes.c_char * 512),
        ("heartbeat", ctypes.c_longlong)
    ]


# Variável Global para ser acessada em qualquer lugar do script
ponteiro_ram = None

# 2. Configuração da Ponte
DLL_PATH = r"F:\HCB_STUDIO\00_Core\engines\hcb_bridge.dll"
bridge = ctypes.WinDLL(DLL_PATH)


def gerenciar_memoria():
    """Thread que inicializa e mantém a pulsação na RAM"""
    global ponteiro_ram
    if bridge.InitializeBridge():
        bridge.GetMemoryPointer.restype = ctypes.POINTER(HcbMemoryCapsule)
        ponteiro_ram = bridge.GetMemoryPointer()

        print("🌐 [SISTEMA] Shared Memory Vinculada e Ativa.")

        try:
            while True:
                if ponteiro_ram:
                    ponteiro_ram.contents.sentinel_active = 1
                    ponteiro_ram.contents.heartbeat = int(time.time())
                time.sleep(1)
        finally:
            bridge.CloseBridge()
    else:
        print("⚠️ [ERRO] Falha crítica ao inicializar ponte C++.")


# Iniciar Thread de Memória
threading.Thread(target=gerenciar_memoria, daemon=True).start()

# Aguarda um segundo para a thread inicializar o ponteiro
time.sleep(1)

print("🚀 Archie Core Ativo e Escutando a RAM...")

# 3. Loop Principal de Execução
try:
    while True:
        if ponteiro_ram:
            # Lê o comando da RAM
            comando_raw = ponteiro_ram.contents.last_command
            comando = comando_raw.decode('utf-8').strip('\x00').strip()

            if comando != "" and comando != "AGUARDANDO":
                print(f"⚡ [COMANDO RECEBIDO]: {comando}")

                # Execução de Tarefas
                if comando == "SAY_HELLO":
                    print("🤖 Archie: 'Olá, Maxwell! Sistema HCB Studio operando via RAM.'")
                elif comando == "LIMPAR_TEMP":
                    print("🧹 Archie: 'Limpando rastros do sistema...'")

                # Limpa o comando para não repetir infinitamente
                ponteiro_ram.contents.last_command = b"AGUARDANDO"

        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n🛑 Archie desligando...")