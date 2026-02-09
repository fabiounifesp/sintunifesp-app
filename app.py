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

def converter_para_minutos(valor):
    """Calcula matematicamente para o total, mas não altera a exibição da tabela"""
    s = str(valor).lower().strip()
    if not s or s == 'nan': return 0
    if 'h' in s:
        h = re.search(r'(\d+)\s*h', s)
        m = re.search(r'(\d+)\s*min', s)
        total_min = 0
        if h: total_min += int(h.group(1)) * 60
        if m: total_min += int(m.group(1))
        return total_min
    try:
        s_limpo = s.replace(',', '.').replace(' ', '')
        val_float = float(re.sub(r'[^-0-9.]', '', s_limpo))
        return int(val_float * 60)
    except:
        return 0

def formatar_minutos_para_texto(minutos_totais):
    """Formata o total acumulado no padrão XhYYmin"""
    h = int(minutos_totais // 60)
    m = int(minutos_totais % 60)
    return f"{h}h{m:02d}min" if m > 0 else f"{h}h"

def tratar_janeiro(valor):
    """Correção para o erro de Janeiro/2010"""
    try:
        dt = pd.to_datetime(valor)
        if dt.year == 2010: return "05, 06, 10"
        return f"{dt.day:02d}"
    except:
        return str(valor).strip()

@st.cache_data
def carregar_dados():
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

st.markdown("<style>.stButton>button {width:100%; height:3.5em; background:#0f572d; color:white; font-weight:bold; border-radius:10px;}</style>", unsafe_allow_html=True)

dados = carregar_dados()
if dados:
    st.subheader("🔍 Consulta de Servidores")
    
    # Campo de busca e botão de pesquisa
    col_texto, col_btn = st.columns([3, 1])
    with col_texto:
        nome_pesquisa = st.text_input("Nome do Servidor:", placeholder="Digite o nome ou parte dele")
    with col_btn:
        st.write("<br>", unsafe_allow_html=True)
        btn_pesquisar = st.button("PESQUISAR")

    if nome_pesquisa or btn_pesquisar:
        nomes_encontrados = []
        for df in dados.values():
            if 'NOME' in df.columns:
                match = df[df['NOME'].astype(str).str.contains(nome_pesquisa, case=False, na=False)]
                nomes_encontrados.extend(match['NOME'].unique())
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in nomes_encontrados if str(n).strip() != 'nan'])))

        if opcoes:
            selecionado = st.selectbox("Resultado da busca:", opcoes)
            
            if st.button("GERAR RELATÓRIO"):
                lista_tabela, minutos_acumulados = [], 0
                for mes, df in dados.items():
                    if 'NOME' in df.columns:
                        res = df[df['NOME'].astype(str).str.strip().str.upper() == selecionado]
                        for _, row in res.iterrows():
                            val_original = str(row.get('HORAS /GREVE', '0')).strip()
                            minutos_acumulados += converter_para_minutos(val_original)
                            dias_f = tratar_janeiro(row.get('DATA', '-'))
                            # Na tabela, entra o val_original exatamente como está (ex: 42h48min)
                            lista_tabela.append([mes, dias_f, val_original])

                total_final_texto = formatar_minutos_para_texto(minutos_acumulados)

                # --- GERAÇÃO DA IMAGEM ---
                fig, ax = plt.subplots(figsize=(10, 2.5 + len(lista_tabela)*0.6))
                ax.axis('off')

                ax.text(0.5, 0.98, "CONSULTA-SEI nº 23089.001984/2026-66", fontsize=12, ha='center', weight='bold', transform=ax.transAxes)
                ax.text(0.5, 0.88, f"TOTAL ACUMULADO: {total_final_texto}", fontsize=16, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                ax.text(0.02, 0.81, f"Servidor: {selecionado}", fontsize=10, transform=ax.transAxes)

                tabela_dados = [[l[0], textwrap.fill(l[1], width=25), l[2]] for l in lista_tabela]
                tab = ax.table(cellText=tabela_dados, colLabels=['Mês', 'Dias de Greve', 'Horas'], 
                               loc='center', colWidths=[0.22, 0.56, 0.22], bbox=[0, 0, 1, 0.78])
                
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
                plt.savefig(buf, format="png", bbox_inches='tight', dpi=200)
                
                # --- LÓGICA DO NOME DO ARQUIVO (NOME E SOBRENOME) ---
                partes_nome = selecionado.split()
                if len(partes_nome) > 1:
                    nome_para_arquivo = f"{partes_nome[0]}_{partes_nome[-1]}"
                else:
                    nome_para_arquivo = partes_nome[0]
                
                st.image(buf.getvalue(), use_container_width=True)
                st.download_button(
                    label="💾 SALVAR", 
                    data=buf.getvalue(), 
                    file_name=f"{nome_para_arquivo}.png", 
                    mime="image/png"
                )

