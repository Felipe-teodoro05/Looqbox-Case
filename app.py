import streamlit as st
import pandas as pd
import mysql.connector
import seaborn as sns
import matplotlib.pyplot as plt

# Config da página 
st.set_page_config(page_title="Looqbox Challenge - Data App", layout="wide")

# Título
st.title("Looqbox Data Explorer - Feito por Felipe Teodoro")
st.markdown("---")

# Conexão BD
try:
    # Acessa as configurações definidas nos secrets
    db_secrets = st.secrets["mysql"]
    
    config = {
        'user': db_secrets['user'],
        'password': db_secrets['password'],
        'host': db_secrets['host'],
        'database': db_secrets['database'],
        'raise_on_warnings': True
    }
except Exception as e:
    st.error("Erro: Credenciais do banco de dados não encontradas.")
    st.stop()

#Funções de carregamento
@st.cache_data(ttl=3600) # Cache de 1 hora
def catalogo():
    """
    Busca todas as combinações de Produtos e Lojas que possuem vendas.
    Traz também os nomes para o filtro ficar flexívelk.
    """
    try:
        conn = mysql.connector.connect(**config)
        # Query para criar o mapa de filtros
        query = """
        SELECT DISTINCT 
            s.PRODUCT_CODE,
            p.PRODUCT_NAME,
            s.STORE_CODE,
            st.STORE_NAME
        FROM data_product_sales s
        INNER JOIN data_product p ON s.PRODUCT_CODE = p.PRODUCT_COD
        INNER JOIN data_store_cad st ON s.STORE_CODE = st.STORE_CODE
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar catálogo: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_sales_data(prod_code, store_code, data_ini, data_fim):
    """
    Aqui é a mesma função criada para o Case 1, eu quis tirar a questão de código
    e trazer uma interface gráfica para explorar os dados.
    """
    try:
        conn = mysql.connector.connect(**config)
        query = """
        SELECT * FROM data_product_sales 
        WHERE PRODUCT_CODE = %s 
        AND STORE_CODE = %s 
        AND DATE BETWEEN %s AND %s
        """
        params = (int(prod_code), int(store_code), data_ini, data_fim)
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro na busca de vendas: {e}")
        return pd.DataFrame()

# Filtros
st.sidebar.header("🔍 Filtros Dinâmicos")

# Opções
df_map = catalogo()

if not df_map.empty:
    # Filtragem cruzada entre Produto e Loja
    
    # Lista de opções únicas
    produtos = df_map[['PRODUCT_CODE', 'PRODUCT_NAME']].drop_duplicates().sort_values('PRODUCT_NAME')
    lojas = df_map[['STORE_CODE', 'STORE_NAME']].drop_duplicates().sort_values('STORE_NAME')

    # Selectbox de Produto
    # Formatado para mostrar o nome e o ID
    product_options = produtos.apply(lambda x: f"{x['PRODUCT_NAME']} (ID: {x['PRODUCT_CODE']})", axis=1)
    
    # Dica: index=None deixa o campo vazio inicialmente se quiser
    selected_product_label = st.sidebar.selectbox("Selecione o Produto", product_options)
    
    # Extrair o ID do produto selecionado
    if selected_product_label:
        product_id = int(selected_product_label.split("(ID: ")[1].replace(")", ""))
        
        # Atualizando a lista de lojas com base no produto selecionado
        valid_stores = df_map[df_map['PRODUCT_CODE'] == product_id]
        store_options_filtered = valid_stores.apply(lambda x: f"{x['STORE_NAME']} (ID: {x['STORE_CODE']})", axis=1).unique()
        store_options_filtered.sort()
        
        st.sidebar.markdown(f"**Lojas com este produto:** {len(store_options_filtered)}")
        selected_store_label = st.sidebar.selectbox("Selecione a Loja", store_options_filtered)
    else:
        selected_store_label = st.sidebar.selectbox("Selecione a Loja", [])

    # Extrair ID da Loja
    if selected_store_label:
        store_id = int(selected_store_label.split("(ID: ")[1].replace(")", ""))
        
    # Filtro de Data
    st.sidebar.markdown("---")
    start_date = st.sidebar.date_input("Data Inicial", pd.to_datetime("2019-01-01"))
    end_date = st.sidebar.date_input("Data Final", pd.to_datetime("2019-03-31"))

    filtrar = st.sidebar.button("Buscar Análise")

else:
    st.error("Não foi possível carregar a lista de produtos/lojas.")
    filtrar = False

# --- ÁREA PRINCIPAL ---

if filtrar and selected_product_label and selected_store_label:
    
    # Mostrar o que foi selecionado de forma bonita
    st.info(f"Analisando: **{selected_product_label.split(' (')[0]}** na loja **{selected_store_label.split(' (')[0]}**")
    
    with st.spinner('Processando dados...'):
        df = get_sales_data(product_id, store_id, start_date, end_date)
        
        if not df.empty:
            # Layout de Métricas
            total_vendas = df['SALES_VALUE'].sum()
            total_qtd = df['SALES_QTY'].sum()
            ticket_medio = total_vendas / total_qtd if total_qtd > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Faturamento", f"R$ {total_vendas:,.2f}")
            col2.metric("Vendas (Qtd)", f"{int(total_qtd)}")
            col3.metric("Preço Médio Realizado", f"R$ {ticket_medio:,.2f}")
            
            st.markdown("---")
            
            # Gráfico
            col_chart, col_data = st.columns([2, 1])
            
            with col_chart:
                st.subheader("Tendência Temporal")
                df['DATE'] = pd.to_datetime(df['DATE'])
                df_chart = df.sort_values('DATE')
                
                fig, ax = plt.subplots(figsize=(8, 4))
                sns.lineplot(data=df_chart, x='DATE', y='SALES_VALUE', marker='o', color='#2c3e50', ax=ax)
                ax.set_ylabel("Valor ($)")
                ax.set_xlabel("")
                ax.grid(True, linestyle='--', alpha=0.5)
                sns.despine()
                st.pyplot(fig)
            
            with col_data:
                st.subheader("Dados Detalhados")
                st.dataframe(df[['DATE', 'SALES_VALUE', 'SALES_QTY']].set_index('DATE'), height=300)
                
        else:
            st.warning(f"Nenhuma venda encontrada neste período para esta combinação.")
elif filtrar:
    st.warning("Por favor, selecione um Produto e uma Loja.")
else:
    st.markdown("""
    ### Bem-vindo à um extra que eu fiz para o Case da Looqbox!
    
    Utilize os filtros à esquerda para explorar os dados.
    
    Os filtros são inteligentes! Ao selecionar um produto, 
    a lista de lojas se atualiza automaticamente para mostrar apenas onde ele é vendido.
    """)