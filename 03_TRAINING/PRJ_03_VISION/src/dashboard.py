import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Paths base do Studio
ROOT = Path(r"F:\HCB_STUDIO")
STORAGE_PATH = ROOT / "02_STORAGE"
TEMP_PATH = ROOT / "04_TEMP"
AI_CONFIG = ROOT / "00_Core" / "config" / "ai_engine.json"
HCB_SCRIPTS = ROOT / "00_Core" / "scripts"
AI_LOG_PATH = ROOT / "00_Core" / "logs" / "vision_chat_history.json"

# Permite importar o motor de IA do 00_Core/scripts/arms
if str(HCB_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HCB_SCRIPTS))

from arms.ai_engine import generate_with_active_provider, load_engine_config


st.set_page_config(
    page_title="HCB Studio | Vision",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_dir_size(start_path: Path):
    total_size = 0
    if not start_path.exists():
        return 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = Path(dirpath) / f
            if not fp.is_symlink():
                total_size += fp.stat().st_size
    return total_size / (1024 * 1024)


def count_files(start_path: Path):
    if not start_path.exists():
        return 0
    count = 0
    for _, _, filenames in os.walk(start_path):
        count += len(filenames)
    return count


def save_chat_history(messages):
    AI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    AI_LOG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


st.title("👁️ HCB STUDIO: VISION DASHBOARD")
st.markdown("---")

st.sidebar.header("Status do Sistema")
st.sidebar.success("🟢 ONLINE")
st.sidebar.info("Unidade: F:\\")
st.sidebar.caption("Motor de IA ativo via 00_Core/config/ai_engine.json")

gemini_key_input = st.sidebar.text_input(
    "GEMINI_API_KEY (sessão atual)",
    type="password",
    help="Opcional. Se preenchido, vale só enquanto este app estiver rodando.",
)
if gemini_key_input:
    os.environ["GEMINI_API_KEY"] = gemini_key_input.strip()
    st.sidebar.success("Chave carregada na sessão.")

col1, col2, col3, col4 = st.columns(4)

if ROOT.exists():
    storage_used = get_dir_size(STORAGE_PATH)
    temp_files = count_files(TEMP_PATH)

    col1.metric("Storage (Cofre)", f"{storage_used:.2f} MB")
    col2.metric("Arquivos em Quarentena", f"{temp_files}")
    col3.metric("Motor Híbrido", "Ativo")
    col4.metric("Projetos Ativos", "2", "Sentinel / Vision")
else:
    st.error("Unidade F: Não detectada.")

st.markdown("### 📂 Últimas Atividades (02_STORAGE)")
if STORAGE_PATH.exists():
    file_data = []
    for root, _, files in os.walk(STORAGE_PATH):
        for file in files:
            full_path = Path(root) / file
            size_kb = full_path.stat().st_size / 1024
            mod_time = time.ctime(full_path.stat().st_mtime)
            folder = Path(root).name
            file_data.append([file, folder, f"{size_kb:.2f} KB", mod_time])

    if file_data:
        df = pd.DataFrame(
            file_data,
            columns=["Arquivo", "Pasta (Contexto)", "Tamanho", "Última Modificação"],
        )
        st.dataframe(df, use_container_width=True, height=280)
    else:
        st.info("Nenhum arquivo arquivado ainda.")

st.markdown("---")
st.subheader("🤖 Console IA (Teste)")

try:
    cfg = load_engine_config(AI_CONFIG)
    active_provider = cfg.get("active_provider", "unknown")
    active_model = (cfg.get("providers", {}).get(active_provider, {}) or {}).get("model", "unknown")
    st.caption(f"Provider: {active_provider} | Modelo: {active_model}")
except Exception as e:
    st.error(f"Falha ao carregar config de IA: {e}")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Digite uma mensagem para testar o motor de IA...")
if prompt:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando motor IA..."):
            try:
                result = generate_with_active_provider(AI_CONFIG, prompt)
                answer = result.get("text", "").strip() or "(sem texto retornado)"
            except Exception as e:
                answer = f"Erro no motor IA: {e}"
        st.markdown(answer)
    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    save_chat_history(st.session_state.chat_messages)

col_a, col_b = st.columns(2)
with col_a:
    st.caption("Cápsula só no encerramento/troca de sessão (não a cada mensagem).")
    capsule_reason = st.selectbox(
        "Motivo de cápsula",
        [
            "troca_de_chat",
            "limite_de_contexto",
            "troca_de_estudo_teacher",
            "troca_de_pesquisa",
            "troca_de_trabalho_producao",
            "encerramento_manual",
        ],
    )
    capsule_confirm = st.checkbox("Confirmo que a sessão será encerrada/trocada agora")
    if st.button("Gerar cápsula de transição", disabled=not capsule_confirm):
        if not st.session_state.chat_messages:
            st.warning("Sem mensagens para encapsular nesta sessão.")
        else:
            checkpoint = {
                "id": f"vision_session_capsule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "modulo": "vision_session_transition",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "atividade": "Capsula de transicao de sessao",
                "motivo_transicao": capsule_reason,
                "politica": "capsula_apenas_em_troca_ou_encerramento",
                "mensagens": st.session_state.chat_messages[-20:],
            }
            out = ROOT / "00_Core" / "logs" / f"{checkpoint['id']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False), encoding="utf-8")
            st.success(f"Cápsula de transição salva: {out}")

with col_b:
    if st.button("Limpar conversa"):
        st.session_state.chat_messages = []
        save_chat_history(st.session_state.chat_messages)
        st.rerun()

st.markdown("---")
st.subheader("🔧 Comandos de Orquestração")
if st.button("Limpar Quarentena (Forçar Saneamento)"):
    files_removed = 0
    if TEMP_PATH.exists():
        for f in TEMP_PATH.iterdir():
            try:
                if f.is_file():
                    f.unlink()
                    files_removed += 1
            except Exception as e:
                st.error(f"Erro ao remover {f.name}: {e}")
    st.success(f"Limpeza concluída. {files_removed} arquivos removidos.")
    time.sleep(1)
    st.rerun()

