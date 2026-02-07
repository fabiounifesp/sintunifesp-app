import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import textwrap
import re
from io import BytesIO

# --- CONFIGURAÇÃO APP ---
st.set_page_config(page_title="SINTUNIFESP", layout="centered")

VERDE_SINDICATO = '#0f572d'
VERDE_BORDA = '#c4e1c5'
VERMELHO_DESTAQUE = '#c9302c'

def limpar_horas(valor):
    """Converte valores como '7,50' ou '8.0' para número real"""
    if pd.isna(valor) or str(valor).strip() == '':
        return 0.0
    try:
        # Troca vírgula por ponto e remove qualquer símbolo que não seja número ou ponto
        s = str(valor).replace(',', '.').strip()
        s = re.sub(r'[^-0-9.]', '', s)
        return float(s)
    except:
        return 0.0

def limpar_texto_dias(valor):
    """Remove espaços invisíveis e garante que o texto não quebre o layout"""
    s = re.sub(r'\s+', ' ', str(valor)).strip()
    return s.replace(',', ', ')

def tratar_janeiro(valor):
    """Fix para o erro de Janeiro/2010 e limpeza de datas"""
    try:
        dt = pd.to_datetime(valor)
        if dt.year == 2010: return "05, 06, 10"
        return f"{dt.day:02d}"
    except:
        return limpar_texto_dias(valor)

@st.cache_data
def carregar_dados():
    arquivo = "horas_greve__1_.ods"
    mapa = {'NOVEMBRO25': 'NOV/2025', 'DEZEMBRO 25': 'DEZ/2025', 'JANEIRO 26': 'JAN/2026'}
    try:
        dict_abas = pd.read_excel(arquivo, engine="odf", sheet_name=None, header=None)
        processados = {}
        for aba, df in dict_abas.items():
            cabecalho = None
            for i, linha in df.iterrows():
                if 'NOME' in [str(v).strip().upper() for v in linha.values]:
                    cabecalho = i
                    break
            if cabecalho is not None:
                new_df = df.iloc[cabecalho+1:].copy()
                cols = [str(c).strip().upper() for c in df.iloc[cabecalho].values]
                new_df.columns = [c if c and str(c) != 'nan' else f"COL_{k}" for k, c in enumerate(cols)]
                label = mapa.get(aba.upper().strip(), aba.upper())
                processados[label] = new_df
        return processados
    except: return None

# Interface
st.markdown("<style>.stButton>button {width:100%; height:4em; background:#0f572d; color:white; font-weight:bold;}</style>", unsafe_allow_html=True)

abas = carregar_dados()
if abas:
    busca = st.text_input("🔍 Digite o nome do servidor:")
    if busca:
        nomes = []
        for df in abas.values():
            if 'NOME' in df.columns:
                match = df[df['NOME'].astype(str).str.contains(busca, case=False, na=False)]
                nomes.extend(match['NOME'].unique())
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in nomes if str(n).strip() != 'nan'])))

        if opcoes:
            nome_sel = st.selectbox("Selecione:", opcoes)
            if st.button("GERAR COMPROVANTE"):
                final_dados, soma_h = [], 0.0
                for mes, df in abas.items():
                    if 'NOME' in df.columns:
                        df['N_LIMPO'] = df['NOME'].astype(str).str.strip().str.upper()
                        res = df[df['N_LIMPO'] == nome_sel]
                        for _, row in res.iterrows():
                            # Limpeza de horas para evitar 'nan' no Carlos Eduardo
                            h_val = limpar_horas(row.get('HORAS /GREVE', 0))
                            soma_h += h_val
                            dias_f = tratar_janeiro(row.get('DATA', '-'))
                            final_dados.append([mes, dias_f, f"{h_val:.2f}"])
                
                if final_dados:
                    # AJUSTE DE SOBREPOSIÇÃO: width=25 força a quebra de linha mais cedo
                    dados_tabela = [[l[0], textwrap.fill(l[1], width=25), l[2]] for l in final_dados]
                    
                    # Altura dinâmica proporcional
                    fig, ax = plt.subplots(figsize=(10, 2.5 + len(final_dados)*0.7))
                    ax.axis('off')

                    # Títulos
                    plt.text(0.5, 0.96, "SINTUNIFESP - OFICIAL", fontsize=12, ha='center', weight='bold', transform=ax.transAxes)
                    plt.text(0.5, 0.88, f"TOTAL: {soma_h:.2f} HORAS", fontsize=16, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                    plt.text(0.02, 0.82, f"Servidor: {nome_sel}", fontsize=10, transform=ax.transAxes)

                    # Tabela com larguras fixas para NÃO sobrepor
                    # Mês=20%, Dias=60%, Horas=20%
                    tab = ax.table(
                        cellText=dados_tabela,
                        colLabels=['Mês', 'Dias de Greve', 'Horas'],
                        loc='center',
                        colWidths=[0.20, 0.60, 0.20],
                        bbox=[0, 0, 1, 0.78]
                    )
                    
                    tab.auto_set_font_size(False)
                    tab.set_fontsize(10) 
                    
                    for (r, c), cell in tab.get_celld().items():
                        cell.set_edgecolor(VERDE_BORDA)
                        if r == 0:
                            cell.set_facecolor(VERDE_SINDICATO)
                            cell.set_text_props(weight='bold', color='white')
                        else:
                            cell.set_facecolor('white')

                    buf = BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight', dpi=250)
                    img_data = buf.getvalue()
                    st.image(img_data, use_container_width=True)
                    
                    # Download corrigido para Android (sem .bin)
                    nome_arquivo = f"SINT_{nome_sel.split()[0]}.png"
                    st.download_button("📥 SALVAR IMAGEM", img_data, nome_arquivo, "image/png")
