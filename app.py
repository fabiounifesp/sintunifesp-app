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

def extrair_valor_numerico(valor):
    """Calcula o valor matemático para a soma, mas mantém o texto original para exibição"""
    s = str(valor).lower().strip()
    if not s or s == 'nan': return 0.0
    if 'h' in s:
        try:
            h = re.search(r'(\d+)\s*h', s)
            m = re.search(r'(\d+)\s*min', s)
            total = 0.0
            if h: total += float(h.group(1))
            if m: total += float(m.group(1)) / 60.0
            return total
        except: return 0.0
    try:
        s_limpo = s.replace(',', '.').replace(' ', '')
        return float(re.sub(r'[^-0-9.]', '', s_limpo))
    except: return 0.0

@st.cache_data
def carregar_dados():
    arquivo = "horas_greve__1_.ods"
    mapa = {'NOVEMBRO25': 'NOV/2025', 'DEZEMBRO 25': 'DEZ/2025', 'JANEIRO 26': 'JAN/2026'}
    try:
        dict_abas = pd.read_excel(arquivo, engine="odf", sheet_name=None, header=None)
        processados = {}
        for aba, df in dict_abas.items():
            for i, linha in df.iterrows():
                if 'NOME' in [str(v).strip().upper() for v in linha.values]:
                    new_df = df.iloc[i+1:].copy()
                    cols = [str(c).strip().upper() for c in df.iloc[i].values]
                    new_df.columns = [c if c and str(c) != 'nan' else f"COL_{k}" for k, c in enumerate(cols)]
                    processados[mapa.get(aba.upper().strip(), aba.upper())] = new_df
                    break
        return processados
    except: return None

# --- INTERFACE ---
st.markdown("<style>.stButton>button {width:100%; height:3.5em; background:#0f572d; color:white; font-weight:bold; border-radius:10px;}</style>", unsafe_allow_html=True)

abas = carregar_dados()
if abas:
    st.subheader("🔍 Pesquisa de Servidor")
    
    # Campo de busca e Botão de Pesquisa [Image of a search interface with a button]
    col1, col2 = st.columns([3, 1])
    with col1:
        nome_busca = st.text_input("Digite o nome:", placeholder="Ex: Carlos Eduardo")
    with col2:
        st.write("<br>", unsafe_allow_html=True)
        clicou_pesquisar = st.button("PESQUISAR")

    # A lógica só executa se o botão for clicado
    if clicou_pesquisar or (nome_busca and 'ultimo_nome' in st.session_state):
        st.session_state['ultimo_nome'] = nome_busca
        encontrados = []
        for df in abas.values():
            if 'NOME' in df.columns:
                m = df[df['NOME'].astype(str).str.contains(nome_busca, case=False, na=False)]
                encontrados.extend(m['NOME'].unique())
        
        opcoes = sorted(list(set([str(n).strip().upper() for n in encontrados if str(n).strip() != 'nan'])))

        if opcoes:
            selecionado = st.selectbox("Selecione na lista:", opcoes)
            if st.button("GERAR RELATÓRIO"):
                lista_tabela, total_decimal = [], 0.0
                for mes, df in abas.items():
                    if 'NOME' in df.columns:
                        res = df[df['NOME'].astype(str).str.strip().str.upper() == selecionado]
                        for _, row in res.iterrows():
                            val_original = str(row.get('HORAS /GREVE', '0')).strip()
                            total_decimal += extrair_valor_numerico(val_original)
                            
                            # Tratamento de Janeiro (apenas os dias)
                            dias_raw = str(row.get('DATA', '-'))
                            try:
                                dt = pd.to_datetime(dias_raw)
                                dias_f = "05, 06, 10" if dt.year == 2010 else f"{dt.day:02d}"
                            except:
                                dias_f = dias_raw
                            
                            lista_tabela.append([mes, dias_f, val_original])

                # Converter total decimal de volta para o formato h/min para o título
                h_inteira = int(total_decimal)
                m_restante = int(round((total_decimal - h_inteira) * 60))
                total_texto = f"{h_inteira}h{m_restante:02d}min" if m_restante > 0 else f"{h_inteira}h"

                # Geração da Imagem
                fig, ax = plt.subplots(figsize=(10, 2.5 + len(lista_tabela)*0.6))
                ax.axis('off')
                
                plt.text(0.5, 0.98, "CONSULTA-SEI nº 23089.001984/2026-66", fontsize=12, ha='center', weight='bold', transform=ax.transAxes)
                plt.text(0.5, 0.88, f"TOTAL ACUMULADO: {total_texto}", fontsize=16, ha='center', color=VERMELHO_DESTAQUE, weight='bold', transform=ax.transAxes)
                plt.text(0.02, 0.81, f"Servidor: {selecionado}", fontsize=10, transform=ax.transAxes)

                # Tabela blindada contra sobreposição
                tab = ax.table(
                    cellText=[[l[0], textwrap.fill(l[1], width=25), l[2]] for l in lista_tabela],
                    colLabels=['Mês', 'Dias de Greve', 'Horas'],
                    loc='center', colWidths=[0.22, 0.56, 0.22], bbox=[0, 0, 1, 0.78]
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
                plt.savefig(buf, format="png", bbox_inches='tight', dpi=200)
                st.image(buf.getvalue(), use_container_width=True)
                st.download_button("💾 SALVAR NO CELULAR", buf.getvalue(), f"SINTUNIFESP_{selecionado[:10]}.png", "image/png")
        else:
            st.error("Nenhum servidor encontrado.")
