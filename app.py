import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import textwrap
import re
from io import BytesIO

# --- CONFIGURAÇÃO MOBILE ---
st.set_page_config(page_title="Greve 25/26", layout="centered")

VERDE_SINDICATO = '#0f572d'
VERDE_BORDA = '#c4e1c5'
VERMELHO_DESTAQUE = '#c9302c'

def limpeza_profunda_texto(valor):
    """Elimina 'gaps' (buracos brancos) e espaços duplos"""
    # Remove tabs, quebras de linha e múltiplos espaços
    s = re.sub(r'\s+', ' ', str(valor)).strip()
    return s.replace(',', ', ')

def tratar_valor_data(valor):
    """Garante apenas os números dos dias, corrigindo Janeiro"""
    try:
        dt = pd.to_datetime(valor)
        if dt.year == 2010: return "05, 06, 10" # Reverte erro do Excel
        return f"{dt.day:02d}"
    except:
        return limpeza_profunda_texto(valor)

@st.cache_data
def carregar_dados():
    # RESTAURADO: Abreviações solicitadas NOV/2025, DEZ/2025, JAN/2026
    mapa = {'NOVEMBRO25': 'NOV/2025', 'DEZEMBRO 25': 'DEZ/2025', 'JANEIRO 26': 'JAN/2026'}
    try:
        dict_abas = pd.read_excel("horas_greve__1_.ods", engine="odf", sheet_name=None, header=None)
        processados = {}
        for aba, df in dict_abas.items():
            for i, linha in df.iterrows():
                if 'NOME' in [str(v).strip().upper() for v in linha.values]:
                    new_df = df.iloc[i+1:].copy()
                    new_df.columns = [str(c).strip().upper() for c in df.iloc[i].values]
                    label_mes = mapa.get(aba.upper().strip(), aba.upper())
                    processados[label_mes] = new_df
                    break
        return processados
    except: return None

# Interface otimizada para toque
st.markdown("<style>.stButton>button {width:100%; height:4em; background:#0f572d; color:white; font-weight:bold; border-radius:12px;}</style>", unsafe_allow_html=True)

dados_abas = carregar_dados()
if dados_abas:
    busca = st.text_input("👤 Digite o nome do servidor:")
    if busca:
        nomes = []
        for df in dados_abas.values():
            if 'NOME' in df.columns:
                m = df[df['NOME'].astype(str).str.contains(busca, case=False, na=False)]
                nomes_lista = m['NOME'].unique()
                nomes.extend(nomes_lista)
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in nomes if str(n).strip() != 'nan'])))
        if opcoes:
            selecionado = st.selectbox("Selecione:", opcoes)
            if st.button("GERAR COMPROVANTE"):
                lista_final, total_h = [], 0.0
                for mes, df in dados_abas.items():
                    if 'NOME' in df.columns:
                        res = df[df['NOME'].astype(str).str.strip().str.upper() == selecionado]
                        for _, row in res.iterrows():
                            dias_f = tratar_valor_data(row['DATA'])
                            h_val = pd.to_numeric(row['HORAS /GREVE'], errors='coerce') or 0.0
                            total_h += h_val
                            # Limpeza de gaps aplicada aqui
                            lista_final.append([mes, limpeza_profunda_texto(dias_f), f"{h_val:.2f}"])
                
                if lista_final:
                    # Ajuste de quebra de texto (width=35) para manter longe das bordas
                    dados_tabela = [[l[0], textwrap.fill(l[1], width=35), l[2]] for l in lista_final]
                    
                    # Altura dinâmica para evitar buracos brancos
                    fig, ax = plt.subplots(figsize=(8, 2.0 + len(lista_final)*0.5))
                    ax.axis('off')
                    
                    # Títulos com coordenadas fixas para ZERO sobreposição
                    ax.text(0.5, 0.98, "CONSULTA - OFICIAL", fontsize=11, ha='center', weight='bold', transform=ax.transAxes)
                    ax.text(0.5, 0.88, f"TOTAL: {total_h:.2f} HORAS", fontsize=15, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                    ax.text(0.02, 0.81, f"Servidor: {selecionado}", fontsize=10, transform=ax.transAxes)

                    # Tabela com colunas alargadas para NÃO sobrepor o Mês e Dias
                    tab = ax.table(
                        cellText=dados_tabela, 
                        colLabels=['Mês', 'Dias de Greve', 'Horas'], 
                        loc='center', 
                        colWidths=[0.22, 0.56, 0.22], 
                        bbox=[0, 0, 1, 0.78]
                    )
                    tab.auto_set_font_size(False)
                    tab.set_fontsize(9)
                    
                    for (r, c), cell in tab.get_celld().items():
                        cell.set_edgecolor(VERDE_BORDA)
                        if r == 0:
                            cell.set_facecolor(VERDE_SINDICATO)
                            cell.set_text_props(color='white', weight='bold')
                        else:
                            cell.set_height(0.12) # Compacta a linha removendo vácuo
                    
                    buf = BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight', dpi=200)
                    st.image(buf.getvalue(), use_container_width=True)
                    st.download_button("💾 SALVAR NO CELULAR", buf.getvalue(), f"GREVE_{selecionado}.png", "image/png")
