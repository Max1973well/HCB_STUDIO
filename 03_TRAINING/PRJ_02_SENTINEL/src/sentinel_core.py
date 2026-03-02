import os
import time
import shutil
from datetime import datetime

# --- ZONAS DE VIGILÂNCIA ---
ROOT = r"F:\HCB_STUDIO"
WATCH_ZONE = os.path.join(ROOT, r"04_TEMP")
SAFE_STORAGE = os.path.join(ROOT, r"02_STORAGE")

# --- REGRAS DE TRIAGEM ---
EXTENSION_MAP = {
    '.txt': 'Documentos\\Texto',
    '.pdf': 'Documentos\\PDF',
    '.jpg': 'Midia\\Imagens',
    '.png': 'Midia\\Imagens',
    '.py': 'Scripts',
    '.cpp': 'Scripts',
    '.zip': 'Arquivos_Compactados'
}


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [SENTINEL] {msg}")


def sort_files():
    # Listar arquivos na zona de quarentena (04_TEMP)
    files = [f for f in os.listdir(WATCH_ZONE) if os.path.isfile(os.path.join(WATCH_ZONE, f))]

    for filename in files:
        file_path = os.path.join(WATCH_ZONE, filename)
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        # Decidir destino
        subfolder = EXTENSION_MAP.get(ext, 'Outros')
        dest_folder = os.path.join(SAFE_STORAGE, subfolder)
        dest_path = os.path.join(dest_folder, filename)

        # Criar pasta se não existir
        os.makedirs(dest_folder, exist_ok=True)

        # Mover
        try:
            # Se já existe arquivo com mesmo nome, adiciona timestamp para não sobrescrever
            if os.path.exists(dest_path):
                name, e = os.path.splitext(filename)
                new_name = f"{name}_{int(time.time())}{e}"
                dest_path = os.path.join(dest_folder, new_name)

            shutil.move(file_path, dest_path)
            log(f"Processado: {filename} -> {subfolder}")
        except Exception as e:
            log(f"Erro ao mover {filename}: {e}")


def start_watch():
    print(f"--- HCB SENTINEL ATIVO ---")
    print(f"Vigiando: {WATCH_ZONE}")
    print("Pressione Ctrl+C (na janela de execução) para encerrar o turno.\n")

    try:
        while True:
            sort_files()
            time.sleep(2)  # Pulso de 2 segundos (Baixo consumo de CPU)
    except KeyboardInterrupt:
        print("\n--- TURNO ENCERRADO ---")


if __name__ == "__main__":
    start_watch()