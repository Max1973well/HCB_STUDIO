import ctypes
import time
import random
import os

# CONFIGURAÇÃO DA PISTA
DLL_PATH = r"F:\HCB_STUDIO\00_Core\engines\cpp_native\bin\hcb_core.dll"
ARRAY_SIZE = 10000000  # 10 Milhões de itens
ITERACOES = 3          # Rodadas para média

def python_pure_sum(data):
    # O Competidor Lento: Soma usando loop Python puro
    total = 0.0
    for x in data:
        total += x
    return total

def load_engine():
    if not os.path.exists(DLL_PATH):
        raise FileNotFoundError(f"Motor C++ não encontrado em: {DLL_PATH}")

    # Carregar DLL
    lib = ctypes.CDLL(DLL_PATH)

    # Definir Tipos (Essencial para não travar a memória)
    lib.hcb_fast_sum.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
    lib.hcb_fast_sum.restype = ctypes.c_double
    return lib

def run_race():
    print(f"--- HCB STUDIO: GRANDE PRÊMIO DE PROCESSAMENTO ---")
    print(f"Pista: {ARRAY_SIZE:,} números de ponto flutuante.")
    print("Preparando competidores (gerando dados)... aguarde.")

    # Gerar dados aleatórios (Lista Python)
    data_list = [random.random() for _ in range(ARRAY_SIZE)]

    # Converter para Array C (para o motor C++)
    # O ctypes converte a lista Python em um array de C nativo
    c_array = (ctypes.c_double * ARRAY_SIZE)(*data_list)

    print("\n--- INICIANDO BATERIAS ---")

    # 1. CORRIDA PYTHON (Interpretado)
    print("[PYTHON] Acelerando...")
    start_py = time.time()
    res_py = python_pure_sum(data_list) 
    end_py = time.time()
    time_py = end_py - start_py
    print(f"[PYTHON] Tempo: {time_py:.4f} segundos | Checksum: {res_py:.2f}")

    # 2. CORRIDA C++ (Compilado)
    engine = load_engine()
    print("[C++ NATIVE] Acelerando...")
    start_cpp = time.time()
    res_cpp = engine.hcb_fast_sum(c_array, ARRAY_SIZE)
    end_cpp = time.time()
    time_cpp = end_cpp - start_cpp
    print(f"[C++ NATIVE] Tempo: {time_cpp:.4f} segundos | Checksum: {res_cpp:.2f}")

    # --- RESULTADO FINAL ---
    if time_cpp > 0:
        speedup = time_py / time_cpp
    else:
        speedup = 0

    print("\n" + "="*40)
    print(f"VENCEDOR: {'C++' if time_cpp < time_py else 'PYTHON'}")
    print(f"Fator de Aceleração: {speedup:.2f}x mais rápido")
    print("="*40)

if __name__ == "__main__":
    run_race()
