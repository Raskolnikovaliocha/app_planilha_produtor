import streamlit as st
import pandas as pd
# import seaborn as sns -> Não está sendo usado, pode ser removido
# import numpy as np -> Não está sendo usado, pode ser removido
# import os -> Não está sendo usado, pode ser removido
# import sys -> Não está sendo usado, pode ser removido
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials


# ====================================================================================
# PARTE 1: AUTENTICAÇÃO E FUNÇÕES (JÁ ESTAVA CORRETO)
# ====================================================================================


@st.cache_resource
def connect_to_gsheet():
    """Conecta ao Google Sheets usando as credenciais do secrets.toml no formato JSON string."""
    # Lê o JSON que está como uma string gigante e o converte para um dicionário
    creds_json = st.secrets["gspread"]["service_account_info"]
    creds = Credentials.from_service_account_info(
        info=eval(creds_json), # eval() converte a string de volta para um dicionário
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    return client
# VERSÃO FINAL E CORRIGIDA
@st.cache_data
def load_data_from_sheet(_client, sheet_name, month_name): # <-- MUDANÇA 1: Adicionado o _
    try:
        spreadsheet = _client.open(sheet_name) # <-- MUDANÇA 2: Usando o novo nome com _
        worksheet = spreadsheet.worksheet(month_name)
        # ... resto da função
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Não foi possível carregar dados de '{month_name}': {e}")
        return pd.DataFrame()

# <<< CORREÇÃO: REMOVIDA A FUNÇÃO load_data_from_sheet DUPLICADA >>>

def save_data_to_sheet(client, sheet_name, month_name, dataframe):
    try:
        spreadsheet = client.open(sheet_name)
        try:
            worksheet = spreadsheet.worksheet(month_name)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=month_name, rows=1, cols=1)
        data_to_upload = [dataframe.columns.values.tolist()] + dataframe.fillna("").values.tolist()
        worksheet.update('A1', data_to_upload)
        return True
    except Exception as e:
        st.error(f"Falha ao salvar dados em '{month_name}': {e}")
        return False


# ===================================================================================
# PARTE 2: SEU APLICATIVO STREAMLIT (VERSÃO FINAL)
# ===================================================================================

st.set_page_config(page_title="Custos Mensais", layout="wide")
st.title("🌾 Controle de Custos Mensais cafeeiro")

st.write('✱ (usado para multiplicação)')
st.write('／ (usado para divisão)')
st.write('➕ (usado para soma)')
st.write('➖ (usado para subtração)')
st.subheader('Exemplos')
st.warning('Escrita incorreta: 3,500.50')
st.success('Escrita correta: 3500.50')
st.caption('Não colocar vírgula para separar milhar e colocar ponto para separar decimal')


NOME_DA_PLANILHA = "planilha_agricultor"

try:
    gspread_client = connect_to_gsheet()
except Exception as e:
    st.error(
        "ERRO: Não foi possível conectar ao Google Sheets. Verifique o conteúdo do seu arquivo `.streamlit/secrets.toml`.")
    st.stop()

custos_totais, receitas_totais, lucros_totais = [], [], []

# <<< CORREÇÃO: Nomes dos meses sem espaço no início para garantir que o nome da aba seja "Janeiro" e não " Janeiro" >>>
meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro"]
abas = st.tabs([f"📅 {mes}" for mes in meses])

for k, aba in enumerate(abas):
    with aba:
        # <<< CORREÇÃO: Variável definida no início do loop para ser usada abaixo >>>
        mes_atual = meses[k]
        st.subheader(f"💵 Custos de {mes_atual}")

        dados_salvos = load_data_from_sheet(gspread_client, NOME_DA_PLANILHA, mes_atual)

        nomes_colunas_originais = ["Descrição", "Custo (R$)", "Atividade Comercialização", "Receita (R$)", "Lucro (R$)"]

        if dados_salvos.empty:
            df_inicial = pd.DataFrame(columns=nomes_colunas_originais)
        else:
            df_inicial = dados_salvos.reindex(columns=nomes_colunas_originais)

        # 🔧 Transformar colunas em texto ANTES do data_editor
        for col in ["Custo (R$)", "Receita (R$)"]:
            df_inicial[col] = df_inicial[col].astype(str)

        #tabela_editada = st.data_editor(df_inicial, num_rows="dynamic", use_container_width=True, key=f"edit_{k}")
        # 🔧 Correção: converte as colunas para string pra permitir expressões como "10+5"
        tabela_editada = st.data_editor(
            df_inicial,
            num_rows="dynamic",
            use_container_width=True,
            key=f"edit_{k}",
            column_config={
                "Custo (R$)": st.column_config.TextColumn("Custo (R$)"),
                "Receita (R$)": st.column_config.TextColumn("Receita (R$)")
            }
        )

        
        
        tabela_editada["Custo (R$)"] = tabela_editada["Custo (R$)"].astype(str)
        tabela_editada["Receita (R$)"] = tabela_editada["Receita (R$)"].astype(str)
        st.divider()
        if st.button(f"💾 Salvar Dados de {mes_atual} na Planilha", key=f"save_{k}"):
            with st.spinner("Salvando..."):
                tabela_para_salvar = tabela_editada.dropna(how='all').reset_index(drop=True)
                if not tabela_para_salvar.empty:
                    success = save_data_to_sheet(gspread_client, NOME_DA_PLANILHA, mes_atual, tabela_para_salvar)
                    if success: st.success("Dados salvos com sucesso!")
                    st.cache_data.clear()
                else:
                    st.warning("Tabela está vazia. Nada para salvar.")
        st.divider()


        # <<< CORREÇÃO FATAL: O BLOCO DE CÁLCULO ANTIGO FOI TOTALMENTE REMOVIDO DAQUI >>>

        # A lógica de cálculo agora está aqui, de forma segura e limpa
        

        def calcular_expressao(valor):
            if valor is None:
                return 0.0

            valor = str(valor).strip()
        
            if valor == "":
                return 0.0

            try:
                return float(eval(valor))
            except:
                return 0.0


        tabela_calculada = tabela_editada.copy()
        tabela_calculada["Custo (R$)"] = tabela_calculada["Custo (R$)"].apply(calcular_expressao)
        tabela_calculada["Receita (R$)"] = tabela_calculada["Receita (R$)"].apply(calcular_expressao)
        #Vou calcular a receita total - custo total
        custo_total = tabela_calculada["Custo (R$)"].sum()
        receita_total = tabela_calculada["Receita (R$)"].sum()
        lucro = receita_total - custo_total
        tabela_calculada["Lucro (R$)"] = lucro
        #tabela_calculada["Lucro (R$)"] = tabela_calculada["Receita (R$)"] - tabela_calculada["Custo (R$)"]

        st.caption("🔍 Tabela com cálculos e destaques:")
        st.dataframe(
            tabela_calculada.style
            .highlight_max(color='#5A5A5A', subset=["Custo (R$)" ])
            .highlight_min(color='#b2b2b2', subset=["Custo (R$)"])
            .format({'Custo (R$)': 'R$ {:,.2f}', 'Receita (R$)': 'R$ {:,.2f}', 'Lucro (R$)': 'R$ {:,.2f}'})
        )

        Custo_tot = tabela_calculada["Custo (R$)"].sum()
        Receita_tot = tabela_calculada["Receita (R$)"].sum()
        Diferenca = Receita_tot - Custo_tot

        custos_totais.append(Custo_tot)
        receitas_totais.append(Receita_tot)
        lucros_totais.append(Diferenca)

       


        st.header('Valores brutos')

        col1, col2, col3 = st.columns(3)
        col1.metric("Receita total ", f"R$:{Receita_tot}")
        col2.metric("Custo total: ", f"R$:{Custo_tot}")
        col3.metric("Lucro total: ", f"R$:{Diferenca}")
        if Diferenca == 0:
            st.success(f' 💹 Sua receita cobriu  os custos e não sobrou nada: R$:{Diferenca} ')

        elif Diferenca >0:
            st.success(f'💹Sua receita cobriu os custos e sobrou dinheiro: R$:{Diferenca} ')

        else:
            st.warning(f'Sua receita não cobriu os custos e você ficou no vermelho: R$:{Diferenca} ')

        # CÓDIGO CORRIGIDO
        media_custos = tabela_calculada["Custo (R$)"].mean()
        media_receita = tabela_calculada["Receita (R$)"].mean()
        lucro_medio = media_receita - media_custos

       
        st.header('Gráfico de barras para acompanhamento de custos ao longo do mês')


        fig = px.bar(tabela_calculada, x='Descrição', y='Custo (R$)', color = 'Descrição')
        st.plotly_chart(fig, use_container_width=True, key = f'fl_{k}')

        st.header('Gráfico de barras para acompanhamento de receitas ao longo do mês')

        fig = px.bar(tabela_calculada, x='Atividade Comercialização', y='Receita (R$)', color =  "Atividade Comercialização")
        st.plotly_chart(fig, use_container_width=True,key = f'casa_{k}')

        st.header('Gráfico de barras para acompanhamento de lucro ao longo do mês')

        fig = px.bar(tabela_calculada, x='Atividade Comercialização', y='Lucro (R$)')
        st.plotly_chart(fig, use_container_width=True, key=f'casa2_{k}')



# --- Cálculo final após o loop ---
st.divider()
st.header("📊 Rentabilidade Anual")

Custo_anual = sum(custos_totais)
Receita_anual = sum(receitas_totais)
Lucro_anual = sum(lucros_totais)

col1, col2, col3 = st.columns(3)
col1.metric("Receita Anual", f"R$ {Receita_anual:,.2f}")
col2.metric("Custo Anual", f"R$ {Custo_anual:,.2f}")
col3.metric("Lucro Anual", f"R$ {Lucro_anual:,.2f}")

# Indicador de rentabilidade
if Lucro_anual == 0:
    st.info(f"💹 Sua receita anual cobriu os custos, mas não gerou lucro. Lucro: R$ {Lucro_anual:,.2f}")
elif Lucro_anual > 0:
    st.success(f"💹 Sua receita anual superou os custos! Lucro total: R$ {Lucro_anual:,.2f}")
else:
    st.warning(f"⚠️ Sua receita anual não cobriu os custos. Prejuízo: R$ {Lucro_anual:,.2f}")


st.subheader("📈 Receita estimada")

qtd_sacas = st.number_input(
    "📦 Quantidade de sacas produzidas:",
    min_value=0.0,
    step=0.1,
    format="%.2f"
)

valor_saca = st.number_input(
    "💰 Valor da saca (R$):",
    min_value=0.0,
    step=0.5,
    format="%.2f"
)

if qtd_sacas > 0 and valor_saca > 0:
    receita_ha = qtd_sacas * valor_saca
    lucro_ha = receita_ha - Custo_anual
    n_sacas = Custo_anual/valor_saca
    st.success(f"Receita estimada por hectare: R$ {receita_ha:,.2f}")
    st.success(f"Lucro estimado: R$ {lucro_ha:,.2f}")
    st.write('☕Quantidade de sacas a se produzir para cobrir os custos')
    st.success(n_sacas)






