import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import textwrap
from io import BytesIO

# --- CONFIGURAÇÃO MOBILE ---
st.set_page_config(page_title="SINTUNIFESP", layout="centered")

VERDE_SINDICATO = '#0f572d'
VERDE_BORDA = '#c4e1c5'
VERMELHO_DESTAQUE = '#c9302c'

def limpar_dados_dias(valor):
    """Extrai apenas os números, corrigindo o erro de Janeiro"""
    s = str(valor).strip()
    try:
        dt = pd.to_datetime(valor)
        if dt.year == 2010: return "05, 06, 10"
        return f"{dt.day:02d}"
    except:
        return s.replace('  ', ' ')

@st.cache_data
def carregar_dados():
    # Abreviações solicitadas: NOV/2025, DEZ/2025, JAN/2026
    mapa = {'NOVEMBRO25': 'NOV/2025', 'DEZEMBRO 25': 'DEZ/2025', 'JANEIRO 26': 'JAN/2026'}
    try:
        dict_abas = pd.read_excel("horas_greve__1_.ods", engine="odf", sheet_name=None, header=None)
        processados = {}
        for aba, df in dict_abas.items():
            for i, linha in df.iterrows():
                if 'NOME' in [str(v).strip().upper() for v in linha.values]:
                    new_df = df.iloc[i+1:].copy()
                    new_df.columns = [str(c).strip().upper() for c in df.iloc[i].values]
                    processados[mapa.get(aba.upper().strip(), aba.upper())] = new_df
                    break
        return processados
    except: return None

# Estilo de botão grande para toque no celular
st.markdown("<style>.stButton>button {width:100%; height:4em; background:#0f572d; color:white; font-weight:bold; border-radius:12px;}</style>", unsafe_allow_html=True)

dados = carregar_dados()
if dados:
    st.subheader("📲 Consulta SINTUNIFESP")
    busca = st.text_input("Digite o nome do servidor:")
    
    if busca:
        nomes = []
        for df in dados.values():
            if 'NOME' in df.columns:
                m = df[df['NOME'].astype(str).str.contains(busca, case=False, na=False)]
                nomes.extend(m['NOME'].unique())
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in nomes if str(n).strip() != 'nan'])))
        
        if opcoes:
            selecionado = st.selectbox("Selecione o nome:", opcoes)
            if st.button("GERAR RELATÓRIO"):
                final, total_h = [], 0.0
                for mes, df in dados.items():
                    if 'NOME' in df.columns:
                        res = df[df['NOME'].astype(str).str.strip().str.upper() == selecionado]
                        for _, r in res.iterrows():
                            d = limpar_dados_dias(r['DATA'])
                            h = pd.to_numeric(r['HORAS /GREVE'], errors='coerce') or 0.0
                            total_h += h
                            final.append([mes, d, f"{h:.2f}"])
                
                if final:
                    # Geração da Imagem Compacta e Sem Sobreposição
                    fig, ax = plt.subplots(figsize=(8, 2.2 + len(final)*0.45))
                    ax.axis('off')
                    
                    # Títulos com coordenadas Y bem separadas para evitar sobreposição
                    ax.text(0.5, 0.97, "SINTUNIFESP - OFICIAL", fontsize=12, ha='center', weight='bold', transform=ax.transAxes)
                    ax.text(0.5, 0.88, f"TOTAL: {total_h:.2f} HORAS", fontsize=16, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                    ax.text(0.02, 0.81, f"Servidor: {selecionado}", fontsize=10, transform=ax.transAxes)

                    # Tabela achatada para remover espaços brancos (vácuos vermelhos)
                    tab = ax.table(cellText=final, colLabels=['Mês', 'Dias', 'Hrs'], loc='center', bbox=[0, 0, 1, 0.76])
                    tab.auto_set_font_size(False)
                    tab.set_fontsize(10)
                    
                    for (r, c), cell in tab.get_celld().items():
                        cell.set_edgecolor(VERDE_BORDA)
                        if r == 0:
                            cell.set_facecolor(VERDE_SINDICATO)
                            cell.set_text_props(color='white', weight='bold')
                        else:
                            cell.set_height(0.08) # Achata a linha eliminando o espaço
                    
                    buf = BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight', dpi=200)
                    st.image(buf.getvalue(), use_container_width=True)
                    st.download_button("💾 SALVAR NO CELULAR", buf.getvalue(), f"Horas_{selecionado}.png")