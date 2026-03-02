
import streamlit as st
import pandas as pd
import os
import time
import shutil

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="HCB Studio | Vision",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNÇÕES DE SISTEMA ---
def get_dir_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024) # Retorna em MB

def count_files(start_path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        count += len(filenames)
    return count

# --- HEADER ---
st.title("👁️ HCB STUDIO: VISION DASHBOARD")
st.markdown("---")

# --- SIDEBAR (MENU) ---
st.sidebar.header("Status do Sistema")
st.sidebar.success("🟢 ONLINE")
st.sidebar.info(f"Unidade: F:\\")

# --- MÉTRICAS PRINCIPAIS ---
col1, col2, col3, col4 = st.columns(4)

# 1. Espaço em Disco (Simulado ou Real se F: existir)
root_path = r"F:\HCB_STUDIO"
if os.path.exists(root_path):
    storage_used = get_dir_size(os.path.join(root_path, "02_STORAGE"))
    temp_files = count_files(os.path.join(root_path, "04_TEMP"))

    col1.metric("Storage (Cofre)", f"{storage_used:.2f} MB", "+12KB")
    col2.metric("Arquivos em Quarentena", f"{temp_files}", "Aguardando Triagem")
    col3.metric("Motor Híbrido", "Ativo", "v1.0 (C++ x64)")
    col4.metric("Projetos Ativos", "2", "Sentinel / Vision")
else:
    st.error("Unidade F: Não detectada!")

# --- VISUALIZAÇÃO DE ARQUIVOS ---
st.markdown("### 📂 Últimas Atividades (02_STORAGE)")

storage_path = os.path.join(root_path, "02_STORAGE")
if os.path.exists(storage_path):
    file_data = []
    for root, dirs, files in os.walk(storage_path):
        for file in files:
            full_path = os.path.join(root, file)
            size_kb = os.path.getsize(full_path) / 1024
            mod_time = time.ctime(os.path.getmtime(full_path))
            folder = os.path.basename(root)
            file_data.append([file, folder, f"{size_kb:.2f} KB", mod_time])

    if file_data:
        df = pd.DataFrame(file_data, columns=["Arquivo", "Pasta (Contexto)", "Tamanho", "Última Modificação"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum arquivo arquivado ainda.")

# --- CONTROLE MANUAL ---
st.markdown("---")
st.subheader("🔧 Comandos de Orquestração")

if st.button("Limpar Quarentena (Forçar Saneamento)"):
    temp_path = os.path.join(root_path, "04_TEMP")
    files_removed = 0
    for f in os.listdir(temp_path):
        file_path = os.path.join(temp_path, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                files_removed += 1
        except Exception as e:
            st.error(f"Erro: {e}")
    st.success(f"Limpeza concluída! {files_removed} arquivos removidos.")
    time.sleep(1)
    st.rerun()

