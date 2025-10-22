import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Dashboard HEMOPROD",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo customizado
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# Carregar dados
@st.cache_data
def load_data():
    df = pd.read_excel('./dados_processados/hemoprod_ce.xlsx')
    return df

df = load_data()

# Normalizar mês por extenso (PT-BR) + ano para criar um label AAAA-MM e um label amigável
MES_MAP = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def parse_mes_ano(valor):
    # Aceita formatos como "Janeiro", "Janeiro/2024", "Jan/2024", "Janeiro 2024", etc.
    if pd.isna(valor):
        return None, None, None
    s = str(valor).strip().lower()
    s = s.replace('-', ' ').replace('_', ' ').replace('.', ' ').replace(',', ' ')
    s = ' '.join(s.split())  # normaliza espaços
    # tentativas comuns
    tokens = s.replace('/', ' ').split()
    mes_num = None
    ano = None

    # procurar qualquer token que bata com mês PT-BR
    for t in tokens:
        if t in MES_MAP:
            mes_num = MES_MAP[t]
            break

    # procurar ano (4 dígitos) em qualquer token
    for t in tokens:
        if t.isdigit() and len(t) == 4:
            ano = int(t)
            break

    # fallback: se não houver ano, tente extrair de uma coluna ano_referencia
    return mes_num, ano, s

# Cria colunas padronizadas
df['periodo_key'] = pd.NA
df['periodo_label'] = pd.NA  # exibição amigável "Mês/AAAA"

if 'periodo_referencia' in df.columns:
    anos_aux = df['ano_referencia'] if 'ano_referencia' in df.columns else pd.Series([pd.NA]*len(df), index=df.index)

    keys = []
    labels = []
    for i, val in df['periodo_referencia'].items():
        mes_num, ano, _raw = parse_mes_ano(val)
        if pd.isna(ano) or ano is None:
            # tentar ano da coluna ano_referencia
            ano = anos_aux.iloc[i] if i in anos_aux.index else None
        if pd.isna(ano) or ano is None or pd.isna(mes_num) or mes_num is None:
            keys.append(pd.NA)
            labels.append(pd.NA)
        else:
            key = f"{int(ano):04d}-{int(mes_num):02d}"
            # mês por extenso capitalizado
            mes_nome = [k for k, v in MES_MAP.items() if v == mes_num][0].capitalize()
            label = f"{mes_nome}/{int(ano)}"
            keys.append(key)
            labels.append(label)

    df['periodo_key'] = keys
    df['periodo_label'] = labels


# Título principal
st.title("🩸 Dashboard de Hemoprodução - HEMOPROD")
st.markdown("---")
st.sidebar.header("🔍 Filtros")

df_filtrado = df.copy()

# Filtro de UF
if 'uf' in df_filtrado.columns:
    ufs = sorted(df_filtrado['uf'].dropna().unique())
    uf_selecionada = st.sidebar.multiselect("UF", ufs, default=ufs)
    if uf_selecionada:
        df_filtrado = df_filtrado[df_filtrado['uf'].isin(uf_selecionada)]

# 1) Ano
if 'ano_referencia' in df_filtrado.columns:
    anos = sorted(df_filtrado['ano_referencia'].dropna().unique())
    ano_selecionado = st.sidebar.multiselect("Ano de Referência", anos, default=anos)
    if ano_selecionado:
        df_filtrado = df_filtrado[df_filtrado['ano_referencia'].isin(ano_selecionado)]

# 2) Município
if 'municipio' in df_filtrado.columns:
    municipios = sorted(df_filtrado['municipio'].dropna().astype(str).unique())
    municipio_selecionado = st.sidebar.multiselect("Município", municipios)
    if municipio_selecionado:
        df_filtrado = df_filtrado[df_filtrado['municipio'].astype(str).isin(municipio_selecionado)]

# 3) Tipo de Estabelecimento
if 'tipo_estabelecimento' in df_filtrado.columns:
    tipos = sorted(df_filtrado['tipo_estabelecimento'].dropna().astype(str).unique())
    tipo_selecionado = st.sidebar.multiselect("Tipo de Estabelecimento", tipos)
    if tipo_selecionado:
        df_filtrado = df_filtrado[df_filtrado['tipo_estabelecimento'].astype(str).isin(tipo_selecionado)]

# 4) Nome Fantasia (primeiro filtra por nome para limitar os meses disponíveis)
nome_col = 'razao_social_nome_fantasia'
if nome_col in df_filtrado.columns:
    nomes_unicos = sorted(df_filtrado[nome_col].dropna().astype(str).unique())
    nomes_sel = st.sidebar.multiselect("Nome Fantasia", nomes_unicos)
    if nomes_sel:
        df_filtrado = df_filtrado[df_filtrado[nome_col].astype(str).isin(nomes_sel)]
    else:
        termo = st.sidebar.text_input("Filtrar por Nome Fantasia (contém)", "")
        if termo:
            termo_low = termo.lower().strip()
            df_filtrado = df_filtrado[df_filtrado[nome_col].astype(str).str.lower().str.contains(termo_low, na=False)]

# 5) Mês (Período) — opções montadas a partir do df já filtrado por nome
if {'periodo_key', 'periodo_label'}.issubset(df_filtrado.columns):
    periodo_opts = (
        df_filtrado[['periodo_key', 'periodo_label']]
        .dropna()
        .drop_duplicates()
        .sort_values('periodo_key')
        .to_dict('records')
    )
    labels = [p['periodo_label'] for p in periodo_opts]
    keys = [p['periodo_key'] for p in periodo_opts]

    sel_labels = st.sidebar.multiselect("Mês (Período)", labels, default=labels)
    if sel_labels:
        sel_keys = [keys[labels.index(lbl)] for lbl in sel_labels]
        df_filtrado = df_filtrado[df_filtrado['periodo_key'].isin(sel_keys)]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 Total de registros: {len(df_filtrado)}")

# # Filtro de município
# if 'municipio' in df.columns:
#     municipios = sorted(df_filtrado['municipio'].dropna().unique())
#     municipio_selecionado = st.sidebar.multiselect("Município", municipios)
#     if municipio_selecionado:
#         df_filtrado = df_filtrado[df_filtrado['municipio'].isin(municipio_selecionado)]

# # Filtro de tipo de estabelecimento
# if 'tipo_estabelecimento' in df.columns:
#     tipos = sorted(df_filtrado['tipo_estabelecimento'].dropna().unique())
#     tipo_selecionado = st.sidebar.multiselect("Tipo de Estabelecimento", tipos)
#     if tipo_selecionado:
#         df_filtrado = df_filtrado[df_filtrado['tipo_estabelecimento'].isin(tipo_selecionado)]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 Total de registros: {len(df_filtrado)}")

# ===== SEÇÃO 1: MÉTRICAS PRINCIPAIS =====
st.header("📊 Métricas Principais")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_aptos = df_filtrado[[c for c in df_filtrado.columns if 'aptos' in c.lower() and 'inaptos' not in c.lower()]].sum().sum()
    st.metric("Total de Candidatos Aptos", f"{int(total_aptos):,}")

with col2:
    total_inaptos = df_filtrado[[c for c in df_filtrado.columns if 'inaptos' in c.lower()]].sum().sum()
    st.metric("Total de Candidatos Inaptos", f"{int(total_inaptos):,}")

with col3:
    total_coletas = df_filtrado[['total_coletas_sangue_total', 'total_coletas_aferese']].sum().sum()
    st.metric("Total de Coletas", f"{int(total_coletas):,}")

with col4:
    if 'inaptidao_triagem_laboratorial_total_bolsas_testadas' in df_filtrado.columns:
        total_bolsas = df_filtrado['inaptidao_triagem_laboratorial_total_bolsas_testadas'].sum()
        st.metric("Bolsas Testadas", f"{int(total_bolsas):,}")

st.markdown("---")

# ===== SEÇÃO 2: TRIAGEM CLÍNICA =====
st.header("🔬 Triagem Clínica")

tab1, tab2, tab3, tab4 = st.tabs(["Tipo de Doação", "Tipo de Doador", "Gênero", "Faixa Etária"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Doação por tipo
        doacao_data = {
            'Tipo': ['Espontânea', 'Reposição', 'Autóloga'],
            'Aptos': [
                df_filtrado['triagem_clinica_total_doacao_espontanea_aptos'].sum(),
                df_filtrado['triagem_clinica_total_doacao_reposicao_aptos'].sum(),
                df_filtrado['triagem_clinica_total_doacao_autologa_aptos'].sum()
            ],
            'Inaptos': [
                df_filtrado['triagem_clinica_total_doacao_espontanea_inaptos'].sum(),
                df_filtrado['triagem_clinica_total_doacao_reposicao_inaptos'].sum(),
                df_filtrado['triagem_clinica_total_doacao_autologa_inaptos'].sum()
            ]
        }
        df_doacao = pd.DataFrame(doacao_data)
        
        fig = px.bar(df_doacao, x='Tipo', y=['Aptos', 'Inaptos'], 
                     title='Candidatos por Tipo de Doação',
                     barmode='group', color_discrete_sequence=['#2ecc71', '#e74c3c'])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Pizza de aptidão
        total_aptos_doacao = df_doacao['Aptos'].sum()
        total_inaptos_doacao = df_doacao['Inaptos'].sum()
        
        fig = go.Figure(data=[go.Pie(
            labels=['Aptos', 'Inaptos'],
            values=[total_aptos_doacao, total_inaptos_doacao],
            hole=0.4,
            marker_colors=['#2ecc71', '#e74c3c']
        )])
        fig.update_layout(title='Proporção de Aptidão Geral')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Tipo de doador
    doador_data = {
        'Tipo': ['Primeira Vez', 'Repetição', 'Esporádico'],
        'Aptos': [
            df_filtrado['total_doador_primeira_vez_aptos'].sum(),
            df_filtrado['total_doador_repeticao_aptos'].sum(),
            df_filtrado['total_doador_esporadico_aptos'].sum()
        ],
        'Inaptos': [
            df_filtrado['total_doador_primeira_vez_inaptos'].sum(),
            df_filtrado['total_doador_repeticao_inaptos'].sum(),
            df_filtrado['total_doador_esporadico_inaptos'].sum()
        ]
    }
    df_doador = pd.DataFrame(doador_data)
    
    fig = px.bar(df_doador, x='Tipo', y=['Aptos', 'Inaptos'],
                 title='Candidatos por Tipo de Doador',
                 barmode='stack', color_discrete_sequence=['#3498db', '#e67e22'])
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    # Gênero
    genero_data = {
        'Gênero': ['Masculino', 'Feminino'],
        'Aptos': [
            df_filtrado['total_doador_masculino_aptos'].sum(),
            df_filtrado['total_doador_feminino_aptos'].sum()
        ],
        'Inaptos': [
            df_filtrado['total_doador_masculino_inaptos'].sum(),
            df_filtrado['total_doador_feminino_inaptos'].sum()
        ]
    }
    df_genero = pd.DataFrame(genero_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(df_genero, x='Gênero', y=['Aptos', 'Inaptos'],
                     title='Candidatos por Gênero',
                     barmode='group', color_discrete_sequence=['#9b59b6', '#f39c12'])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Taxa de aptidão por gênero
        df_genero['Taxa_Aptidao'] = (df_genero['Aptos'] / (df_genero['Aptos'] + df_genero['Inaptos']) * 100)
        fig = px.bar(df_genero, x='Gênero', y='Taxa_Aptidao',
                     title='Taxa de Aptidão por Gênero (%)',
                     color='Gênero', color_discrete_sequence=['#9b59b6', '#f39c12'])
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    # Faixa etária
    idade_data = {
        'Faixa Etária': ['< 18 anos', '18-29 anos', '> 29 anos'],
        'Aptos': [
            df_filtrado['total_doador_menor_de_18_anos_aptos'].sum(),
            df_filtrado['total_doador_18_ate_29_anos_aptos'].sum(),
            df_filtrado['total_doador_acima_de_29_anos_aptos'].sum()
        ],
        'Inaptos': [
            df_filtrado['total_doador_menor_de_18_anos_inaptos'].sum(),
            df_filtrado['total_doador_18_ate_29_anos_inaptos'].sum(),
            df_filtrado['total_doador_acima_de_29_anos_inaptos'].sum()
        ]
    }
    df_idade = pd.DataFrame(idade_data)
    
    fig = px.bar(df_idade, x='Faixa Etária', y=['Aptos', 'Inaptos'],
                 title='Candidatos por Faixa Etária',
                 barmode='group', color_discrete_sequence=['#1abc9c', '#e74c3c'])
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 3: MOTIVOS DE INAPTIDÃO =====
st.header("⚠️ Motivos de Inaptidão")

motivos_cols = {
    'Anemia': ['total_candidatos_inaptos_anemia_masculino', 'total_candidatos_inaptos_anemia_feminino'],
    'Hipertensão': ['total_candidatos_inaptos_hipertensao_masculino', 'total_candidatos_inaptos_hipertensao_feminino'],
    'Hipotensão': ['total_candidatos_inaptos_hipotensao_masculino', 'total_candidatos_inaptos_hipotensao_feminino'],
    'Alcoolismo': ['total_candidatos_inaptos_alcoolismo_masculino', 'total_candidatos_inaptos_alcoolismo_feminino'],
    'Comportamento de Risco DST': ['total_candidatos_inaptos_comportamento_risco_dst_masculino', 'total_candidatos_inaptos_comportamento_risco_dst_feminino'],
    'Uso de Drogas': ['total_candidatos_inaptos_uso_drogas_masculino', 'total_candidatos_inaptos_uso_drogas_feminino'],
    'Hepatite': ['total_candidatos_inaptos_hepatite_masculino', 'total_candidatos_inaptos_hepatite_feminino'],
    'Doença de Chagas': ['total_candidatos_inaptos_doenca_chagas_masculino', 'total_candidatos_inaptos_doenca_chagas_feminino'],
    'Malária': ['total_candidatos_inaptos_malaria_masculino', 'total_candidatos_inaptos_malaria_feminino'],
    'Outras': ['total_candidatos_inaptos_outras_masculino', 'total_candidatos_inaptos_outras_feminino']
}

motivos_data = []
for motivo, cols in motivos_cols.items():
    masculino = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
    feminino = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
    motivos_data.append({'Motivo': motivo, 'Masculino': masculino, 'Feminino': feminino, 'Total': masculino + feminino})

df_motivos = pd.DataFrame(motivos_data).sort_values('Total', ascending=False)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_motivos, x='Motivo', y='Total',
                 title='Total de Inaptidões por Motivo',
                 color='Total', color_continuous_scale='Reds')
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_motivos, x='Motivo', y=['Masculino', 'Feminino'],
                 title='Inaptidões por Motivo e Gênero',
                 barmode='stack', color_discrete_sequence=['#3498db', '#e91e63'])
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 4: COLETA E INTERRUPÇÕES =====
st.header("💉 Coleta de Sangue")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Sangue Total", f"{int(df_filtrado['total_coletas_sangue_total'].sum()):,}")

with col2:
    st.metric("Por Aférese", f"{int(df_filtrado['total_coletas_aferese'].sum()):,}")

with col3:
    desistentes = df_filtrado['coleta_total_candidatos_desistentes'].sum()
    st.metric("Candidatos Desistentes", f"{int(desistentes):,}")

# Interrupções
interrupcoes_data = {
    'Motivo': ['Dificuldade de Punção', 'Reação Vagal', 'Outros Motivos'],
    'Quantidade': [
        df_filtrado['total_interrupcoes_coleta_dificuldade_puncao_venosa'].sum(),
        df_filtrado['total_interrupcoes_coleta_reacao_vagal'].sum(),
        df_filtrado['total_interrupcoes_coleta_outros_motivos'].sum()
    ]
}
df_interrupcoes = pd.DataFrame(interrupcoes_data)

fig = px.pie(df_interrupcoes, values='Quantidade', names='Motivo',
             title='Motivos de Interrupção na Coleta',
             color_discrete_sequence=px.colors.sequential.RdBu)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 5: EXAMES E TRIAGEM LABORATORIAL =====
st.header("🧪 Exames e Triagem Laboratorial")

# Doenças transmissíveis
doencas = {
    'Doença de Chagas': ['exames_triagem_doenca_doenca_chagas_amostras_testadas', 'exames_triagem_doenca_doenca_chagas_amostras_reagentes'],
    'HIV': ['exames_triagem_doenca_hiv_amostras_testadas', 'exames_triagem_doenca_hiv_amostras_reagentes'],
    'Sífilis': ['exames_triagem_doenca_sifilis_amostras_testadas', 'exames_triagem_doenca_sifilis_amostras_reagentes'],
    'Hepatite B (HBsAg)': ['exames_triagem_doenca_hepatite_b_hbs_ag_amostras_testadas', 'exames_triagem_doenca_hepatite_b_hbs_ag_amostras_reagentes'],
    'Hepatite B (Anti-HBc)': ['exames_triagem_doenca_hepatite_b_anti_hbc_amostras_testadas', 'exames_triagem_doenca_hepatite_b_anti_hbc_amostras_reagentes'],
    'Hepatite C': ['exames_triagem_doenca_hepatite_c_amostras_testadas', 'exames_triagem_doenca_hepatite_c_amostras_reagentes'],
    'HTLV I e II': ['exames_triagem_doenca_htlv_i_ii_amostras_testadas', 'exames_triagem_doenca_htlv_i_ii_amostras_reagentes'],
    'Malária': ['exames_triagem_doenca_malaria_amostras_testadas', 'exames_triagem_doenca_malaria_amostras_reagentes']
}

doencas_data = []
for doenca, cols in doencas.items():
    testadas = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
    reagentes = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
    taxa = (reagentes / testadas * 100) if testadas > 0 else 0
    doencas_data.append({
        'Doença': doenca,
        'Testadas': testadas,
        'Reagentes': reagentes,
        'Taxa (%)': taxa
    })

df_doencas = pd.DataFrame(doencas_data)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_doencas, x='Doença', y='Testadas',
                 title='Amostras Testadas por Doença',
                 color='Testadas', color_continuous_scale='Blues')
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_doencas, x='Doença', y='Reagentes',
                 title='Amostras Reagentes por Doença',
                 color='Reagentes', color_continuous_scale='Reds')
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# Taxa de reagentes
fig = px.bar(df_doencas, x='Doença', y='Taxa (%)',
             title='Taxa de Amostras Reagentes (%)',
             color='Taxa (%)', color_continuous_scale='OrRd')
fig.update_xaxes(tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 6: IMUNOHEMATOLOGIA =====
st.header("🩸 Imunohematologia - Tipos Sanguíneos")

tipos_sanguineos = ['A+', 'B+', 'AB+', 'O+', 'A-', 'B-', 'AB-', 'O-']
tipo_map = {
    'A+': ['imunohematologia_a_positivo_doador', 'imunohematologia_a_positivo_receptor'],
    'B+': ['imunohematologia_b_positivo_doador', 'imunohematologia_b_positivo_receptor'],
    'AB+': ['imunohematologia_ab_positivo_doador', 'imunohematologia_ab_positivo_receptor'],
    'O+': ['imunohematologia_o_positivo_doador', 'imunohematologia_o_positivo_receptor'],
    'A-': ['imunohematologia_a_negativo_doador', 'imunohematologia_a_negativo_receptor'],
    'B-': ['imunohematologia_b_negativo_doador', 'imunohematologia_b_negativo_receptor'],
    'AB-': ['imunohematologia_ab_negativo_doador', 'imunohematologia_ab_negativo_receptor'],
    'O-': ['imunohematologia_o_negativo_doador', 'imunohematologia_o_negativo_receptor']
}

tipo_data = []
for tipo, cols in tipo_map.items():
    doador = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
    receptor = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
    tipo_data.append({'Tipo Sanguíneo': tipo, 'Doador': doador, 'Receptor': receptor})

df_tipos = pd.DataFrame(tipo_data)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_tipos, x='Tipo Sanguíneo', y='Doador',
                 title='Distribuição de Tipos Sanguíneos - Doadores',
                 color='Tipo Sanguíneo', color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_tipos, x='Tipo Sanguíneo', y='Receptor',
                 title='Distribuição de Tipos Sanguíneos - Receptores',
                 color='Tipo Sanguíneo', color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 7: PRODUÇÃO HEMOTERÁPICA =====
st.header("🏭 Produção Hemoterápica")

componentes = {
    'Sangue Total': 'sangue_total',
    'Plasma Fresco Congelado': 'plasma_fresco_congelado',
    'Plasma Comum': 'plasma_comum',
    'Concentrado de Hemácias': 'concentrado_hemacias',
    'Concentrado de Plaquetas': 'concentrado_plaquetas',
    'Crioprecipitado': 'crioprecipitado'
}

producao_data = []
for componente, nome_col in componentes.items():
    produzidas = df_filtrado[f'producao_hemoterapica_entradas_{nome_col}_produzidas'].sum() if f'producao_hemoterapica_entradas_{nome_col}_produzidas' in df_filtrado.columns else 0
    recebidas = df_filtrado[f'producao_hemoterapica_entradas_{nome_col}_recebidas'].sum() if f'producao_hemoterapica_entradas_{nome_col}_recebidas' in df_filtrado.columns else 0
    devolvidas = df_filtrado[f'producao_hemoterapica_entradas_{nome_col}_devolvidas'].sum() if f'producao_hemoterapica_entradas_{nome_col}_devolvidas' in df_filtrado.columns else 0
    
    producao_data.append({
        'Componente': componente,
        'Produzidas': produzidas,
        'Recebidas': recebidas,
        'Devolvidas': devolvidas
    })

df_producao = pd.DataFrame(producao_data)

fig = px.bar(df_producao, x='Componente', y=['Produzidas', 'Recebidas', 'Devolvidas'],
             title='Produção Hemoterápica - Entradas',
             barmode='group', color_discrete_sequence=['#27ae60', '#3498db', '#f39c12'])
fig.update_xaxes(tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 8: PERDAS =====
st.header("📉 Perdas de Hemocomponentes")

perdas_data = []
for componente, nome_col in componentes.items():
    rompimento = df_filtrado[f'perdas_{nome_col}_rompimento_de_bolsa'].sum() if f'perdas_{nome_col}_rompimento_de_bolsa' in df_filtrado.columns else 0
    validade = df_filtrado[f'perdas_{nome_col}_validade'].sum() if f'perdas_{nome_col}_validade' in df_filtrado.columns else 0
    outros = df_filtrado[f'perdas_{nome_col}_outros_motivos'].sum() if f'perdas_{nome_col}_outros_motivos' in df_filtrado.columns else 0
    
    perdas_data.append({
        'Componente': componente,
        'Rompimento': rompimento,
        'Validade': validade,
        'Outros': outros,
        'Total': rompimento + validade + outros
    })

df_perdas = pd.DataFrame(perdas_data)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_perdas, x='Componente', y=['Rompimento', 'Validade', 'Outros'],
                 title='Perdas por Motivo',
                 barmode='stack', color_discrete_sequence=['#e74c3c', '#e67e22', '#95a5a6'])
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.pie(df_perdas, values='Total', names='Componente',
                 title='Distribuição Total de Perdas',
                 color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 9: TRANSFUSÕES =====
st.header("💉 Transfusões Realizadas")

transfusoes_data = []
for componente, nome_col in componentes.items():
    ambulatorial = df_filtrado[f'tranfusoes_{nome_col}_ambulatorial'].sum() if f'tranfusoes_{nome_col}_ambulatorial' in df_filtrado.columns else 0
    hospitalar = df_filtrado[f'tranfusoes_{nome_col}_hospitalar'].sum() if f'tranfusoes_{nome_col}_hospitalar' in df_filtrado.columns else 0
    total = df_filtrado[f'tranfusoes_{nome_col}_total'].sum() if f'tranfusoes_{nome_col}_total' in df_filtrado.columns else 0
    
    transfusoes_data.append({
        'Componente': componente,
        'Ambulatorial': ambulatorial,
        'Hospitalar': hospitalar,
        'Total': total
    })

df_transfusoes = pd.DataFrame(transfusoes_data)

fig = px.bar(df_transfusoes, x='Componente', y=['Ambulatorial', 'Hospitalar'],
             title='Transfusões por Ambiente',
             barmode='stack', color_discrete_sequence=['#16a085', '#2980b9'])
fig.update_xaxes(tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 10: REAÇÕES TRANSFUSIONAIS =====
st.header("⚠️ Reações Transfusionais")

reacoes_cols = {
    'Reação Febril não Hemolítica': 'reacoes_transfusionais_reacao_febril_nao_hemolitica',
    'Reação Hemolítica': 'reacoes_transfusionais_reacao_hemolitica',
    'Reação Alérgica': 'reacoes_transfusionais_reacao_alergica',
    'Choque Bacteriano': 'reacoes_transfusionais_choque_bacteriano',
    'Alterações Metabólicas': 'reacoes_transfusionais_alteracoes_metabolicas',
    'Sobrecarga Volêmica': 'reacoes_transfusionais_sobrecarga_volemica',
    'Outras Reações': 'reacoes_transfusionais_outras_reacoes'
}

reacoes_data = []
for reacao, col in reacoes_cols.items():
    quantidade = df_filtrado[col].sum() if col in df_filtrado.columns else 0
    reacoes_data.append({'Tipo de Reação': reacao, 'Quantidade': quantidade})

df_reacoes = pd.DataFrame(reacoes_data).sort_values('Quantidade', ascending=False)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df_reacoes, x='Tipo de Reação', y='Quantidade',
                 title='Reações Transfusionais por Tipo',
                 color='Quantidade', color_continuous_scale='Reds')
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.pie(df_reacoes, values='Quantidade', names='Tipo de Reação',
                 title='Distribuição de Reações Transfusionais',
                 color_discrete_sequence=px.colors.sequential.Reds)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 11: PROCEDIMENTOS DE MODIFICAÇÃO =====
st.header("🔧 Procedimentos de Modificação")

procedimentos_cols = {
    'Lavagem': 'procedimentos_de_modificacao_dos_hemocomponentes_lavagem',
    'Irradiação': 'procedimentos_de_modificacao_dos_hemocomponentes_irradiacao',
    'Filtração em Plaquetas': 'procedimentos_de_modificacao_dos_hemocomponentes_filtracao_em_concentrado_de_plaquetas',
    'Filtração em Hemácias': 'procedimentos_de_modificacao_dos_hemocomponentes_filtracao_em_concentrado_de_hemacias',
    'Fracionamento Pediátrico': 'procedimentos_de_modificacao_dos_hemocomponentes_fracionamento_pediatrico'
}

procedimentos_data = []
for proc, col in procedimentos_cols.items():
    quantidade = df_filtrado[col].sum() if col in df_filtrado.columns else 0
    procedimentos_data.append({'Procedimento': proc, 'Quantidade': quantidade})

df_procedimentos = pd.DataFrame(procedimentos_data)

fig = px.bar(df_procedimentos, x='Procedimento', y='Quantidade',
             title='Procedimentos de Modificação Realizados',
             color='Quantidade', color_continuous_scale='Viridis')
fig.update_xaxes(tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 12: ANÁLISE GEOGRÁFICA =====
if 'municipio' in df_filtrado.columns:
    st.header("🗺️ Análise por Município")
    
    municipio_stats = df_filtrado.groupby('municipio').agg({
        'total_coletas_sangue_total': 'sum',
        'total_coletas_aferese': 'sum',
        'inaptidao_triagem_laboratorial_total_bolsas_testadas': 'sum'
    }).reset_index()
    
    municipio_stats['Total Coletas'] = municipio_stats['total_coletas_sangue_total'] + municipio_stats['total_coletas_aferese']
    municipio_stats = municipio_stats.sort_values('Total Coletas', ascending=False).head(10)
    
    fig = px.bar(municipio_stats, x='municipio', y='Total Coletas',
                 title='Top 10 Municípios por Total de Coletas',
                 color='Total Coletas', color_continuous_scale='Blues')
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 13: TABELA DE DADOS =====
st.header("📋 Dados Detalhados")

# Seletor de colunas para exibir
colunas_importantes = [
    'municipio', 'razao_social_nome_fantasia', 'tipo_estabelecimento',
    'ano_referencia', 'periodo_referencia', 'total_coletas_sangue_total',
    'total_coletas_aferese', 'inaptidao_triagem_laboratorial_total_bolsas_testadas'
]

colunas_disponiveis = [col for col in colunas_importantes if col in df_filtrado.columns]

if colunas_disponiveis:
    st.dataframe(df_filtrado[colunas_disponiveis].head(50), use_container_width=True)
else:
    st.dataframe(df_filtrado.head(50), use_container_width=True)

# Download dos dados filtrados
st.download_button(
    label="📥 Download dos Dados Filtrados (CSV)",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name='hemoprod_filtrado.csv',
    mime='text/csv'
)

st.markdown("---")
st.info("💡 **Dica:** Use os filtros na barra lateral para explorar os dados de forma mais específica!")