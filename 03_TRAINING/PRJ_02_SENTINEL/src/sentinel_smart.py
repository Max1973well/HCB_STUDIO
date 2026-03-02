import os
import time
import shutil
import joblib
from datetime import datetime

# --- INFRAESTRUTURA ---
ROOT = r"F:\HCB_STUDIO"
WATCH_ZONE = os.path.join(ROOT, r"04_TEMP")
SAFE_STORAGE = os.path.join(ROOT, r"02_STORAGE")
MODEL_PATH = r"F:\HCB_STUDIO\00_Core\engines\brain_v1.pkl"
VEC_PATH = r"F:\HCB_STUDIO\00_Core\engines\vectorizer_v1.pkl"

# Carregar Inteligência Artificial
try:
    clf = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VEC_PATH)
    BRAIN_ACTIVE = True
    print("[IA] Cérebro carregado com sucesso.")
except:
    BRAIN_ACTIVE = False
    print("[AVISO] IA não encontrada. Usando modo básico.")


def predict_context(text):
    if not BRAIN_ACTIVE: return "GERAL"
    # A IA prevê a categoria baseada no treino
    X = vectorizer.transform([text])
    prediction = clf.predict(X)
    return prediction[0]


def smart_sort_v3():
    files = [f for f in os.listdir(WATCH_ZONE) if os.path.isfile(os.path.join(WATCH_ZONE, f))]

    for filename in files:
        filepath = os.path.join(WATCH_ZONE, filename)

        # Lendo o conteúdo para a IA analisar
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read(1024).lower()
        except:
            content = ""

        # Decisão por Inteligência Artificial
        context = predict_context(content) if content else "MIDIA"

        dest_folder = os.path.join(SAFE_STORAGE, f"AI_Classified_{context}")
        os.makedirs(dest_folder, exist_ok=True)

        try:
            shutil.move(filepath, os.path.join(dest_folder, filename))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] IA classificou '{filename}' como {context}")
        except Exception as e:
            print(f"Erro ao mover: {e}")


if __name__ == "__main__":
    print("--- SENTINEL v3.0 (PREDITIVO) EM OPERAÇÃO ---")
    while True:
        smart_sort_v3()
        time.sleep(2)