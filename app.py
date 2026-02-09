import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import textwrap
import re
from io import BytesIO

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="PAGAR - GREVE 25/26", layout="centered")

VERDE_SINDICATO = '#0f572d'
VERDE_BORDA = '#c4e1c5'
VERMELHO_DESTAQUE = '#c9302c'

def converter_tempo_para_decimal(valor):
    """Converte '42h48min' ou '7,5' para decimal (ex: 42.8)"""
    s = str(valor).lower().strip()
    if not s or s == 'nan': return 0.0
    
    # Caso 1: Formato "42h48min" ou "42h"
    if 'h' in s:
        try:
            horas = 0.0
            minutos = 0.0
            parts_h = re.search(r'(\d+)\s*h', s)
            parts_m = re.search(r'(\d+)\s*min', s)
            if parts_h: horas = float(parts_h.group(1))
            if parts_m: minutos = float(parts_m.group(1))
            return horas + (minutos / 60.0)
        except: pass

    # Caso 2: Formato decimal "7,50" ou "7.50"
    try:
        s_limpo = s.replace(',', '.').replace(' ', '')
        return float(re.sub(r'[^-0-9.]', '', s_limpo))
    except:
        return 0.0

def tratar_dias_janeiro(valor):
    """Mantém a correção de Janeiro aprovada"""
    try:
        dt = pd.to_datetime(valor)
        if dt.year == 2010: return "05, 06, 10"
        return f"{dt.day:02d}"
    except:
        # Limpa espaços duplos que geram gaps
        return re.sub(r'\s+', ' ', str(valor)).strip().replace(',', ', ')

@st.cache_data
def carregar_dados_planilha():
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
                processados[mapa.get(aba.upper().strip(), aba.upper())] = new_df
        return processados
    except: return None

# --- INTERFACE ---
st.markdown("<style>.stButton>button {width:100%; height:3.5em; background:#0f572d; color:white; font-weight:bold;}</style>", unsafe_allow_html=True)

abas = carregar_dados_planilha()
if abas:
    st.subheader("🔍 Painel de Pesquisa")
    
    # Campo de busca e Botão (conforme solicitado)
    col1, col2 = st.columns([3, 1])
    with col1:
        termo = st.text_input("Digite o nome:", placeholder="Nome do Servidor...")
    with col2:
        st.write("<br>", unsafe_allow_html=True)
        btn_pesquisar = st.button("PESQUISAR")

    # A busca só ocorre ao clicar no botão ou dar enter
    if termo or btn_pesquisar:
        encontrados = []
        for df in abas.values():
            if 'NOME' in df.columns:
                match = df[df['NOME'].astype(str).str.contains(termo, case=False, na=False)]
                encontrados.extend(match['NOME'].unique())
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in encontrados if str(n).strip() != 'nan'])))

        if opcoes:
            nome_sel = st.selectbox("Selecione o servidor:", opcoes)
            if st.button("GERAR COMPROVANTE"):
                lista_final, soma_h = [], 0.0
                for mes, df in abas.items():
                    if 'NOME' in df.columns:
                        df['N_AUX'] = df['NOME'].astype(str).str.strip().str.upper()
                        res = df[df['N_AUX'] == nome_sel]
                        for _, row in res.iterrows():
                            # CORREÇÃO DO CÁLCULO (42h48min)
                            val_h = converter_tempo_para_decimal(row.get('HORAS /GREVE', 0))
                            soma_h += val_h
                            dias_f = tratar_dias_janeiro(row.get('DATA', ''))
                            lista_final.append([mes, dias_f, f"{val_h:.2f}"])
                
                if lista_final:
                    # AJUSTE DE SOBREPOSIÇÃO: width=22 garante que o texto não invada o lado
                    dados_tabela = [[l[0], textwrap.fill(l[1], width=22), l[2]] for l in lista_final]
                    
                    fig, ax = plt.subplots(figsize=(10, 2.5 + len(lista_final)*0.7))
                    ax.axis('off')

                    # Títulos com coordenadas fixas e seguras
                    plt.text(0.5, 0.96, "CONSULTA-SEI nº 23089.001984/2026-66", fontsize=12, ha='center', weight='bold', transform=ax.transAxes)
                    plt.text(0.5, 0.88, f"TOTAL: {soma_h:.2f} HORAS", fontsize=16, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                    plt.text(0.02, 0.82, f"Servidor: {nome_sel}", fontsize=10, transform=ax.transAxes)

                    # Tabela com colunas blindadas (25% / 50% / 25%)
                    tab = ax.table(
                        cellText=dados_tabela,
                        colLabels=['Mês', 'Dias de Greve', 'Horas'],
                        loc='center',
                        colWidths=[0.25, 0.50, 0.25],
                        bbox=[0, 0, 1, 0.78]
                    )
                    tab.auto_set_font_size(False)
                    tab.set_fontsize(10)
                    
                    for (r, c), cell in tab.get_celld().items():
                        cell.set_edgecolor(VERDE_BORDA)
                        if r == 0:
                            cell.set_facecolor(VERDE_SINDICATO)
                            cell.set_text_props(color='white', weight='bold')
                        else:
                            cell.set_facecolor('white')

                    buf = BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight', dpi=250)
                    st.image(buf.getvalue(), use_container_width=True)
                    st.download_button("📥 SALVAR NO CELULAR", buf.getvalue(), f"Relatorio_{nome_sel.split()[0]}.png", "image/png")
