import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import glob
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard HEMOPROD",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo customizado
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)


# Carregar dados
@st.cache_data
def load_data():
    parquet_path = "dados_processados/base_nacional.parquet"

    # 1. Tenta carregar o arquivo Parquet (preferencial)
    if os.path.exists(parquet_path):
        try:
            df = pd.read_parquet(parquet_path, engine="pyarrow")
            st.success(f"Dados carregados do arquivo Parquet: {parquet_path}")
            return df
        except Exception as e:
            st.error(f"ERRO ao carregar o arquivo Parquet ({parquet_path}): {e}")

    # 2. Se o Parquet não existir ou falhar, tenta carregar os XLSX (fallback)
    st.warning(
        "Arquivo Parquet não encontrado ou falhou ao carregar. Tentando carregar arquivos Excel (fallback)..."
    )

    path = "."
    brutos_files = glob.glob(os.path.join(path, "dados_brutos", "Hemoprod_*.xlsx"))
    processados_files = glob.glob(
        os.path.join(path, "dados_processados", "hemoprod_*.xlsx")
    )

    all_files = brutos_files + processados_files

    if not all_files:
        st.error(
            "Nenhum arquivo de dados encontrado. Verifique as pastas 'dados_brutos' e 'dados_processados'."
        )
        return pd.DataFrame()

    df_list = []
    for file in all_files:
        try:
            df_list.append(pd.read_excel(file))
        except Exception as e:
            st.warning(f"Erro ao ler o arquivo {file}: {e}")

    if not df_list:
        st.error(
            "Não foi possível carregar nenhum DataFrame. Verifique o conteúdo dos arquivos Excel."
        )
        return pd.DataFrame()

    df = pd.concat(df_list, ignore_index=True)
    st.success(
        "Dados carregados com sucesso a partir dos arquivos Excel (método fallback)."
    )
    return df


df = load_data()

# === Teste Temporário para conferir o total SEM FILTRO ===
coluna_descarte = "descarte_bolsas_total_bolsas_descartadas_auto_exclusao"
if coluna_descarte in df.columns:
    total_sem_filtro = df[coluna_descarte].sum()
    # Remova esta linha após o teste!
    st.sidebar.markdown(f"**Total SEM Filtro (DEBUG):** {int(total_sem_filtro):,}")
# =========================================================

# Normalizar mês por extenso (PT-BR) + ano
MES_MAP = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def parse_mes_ano(valor):
    if pd.isna(valor):
        return None, None, None
    s = str(valor).strip().lower()
    s = s.replace("-", " ").replace("_", " ").replace(".", " ").replace(",", " ")
    s = " ".join(s.split())
    tokens = s.replace("/", " ").split()
    mes_num = None
    ano = None

    for t in tokens:
        if t in MES_MAP:
            mes_num = MES_MAP[t]
            break

    for t in tokens:
        if t.isdigit() and len(t) == 4:
            ano = int(t)
            break

    return mes_num, ano, s


# Cria colunas padronizadas
df["periodo_key"] = pd.NA
df["periodo_label"] = pd.NA

if "periodo_referencia" in df.columns:
    anos_aux = (
        df["ano_referencia"]
        if "ano_referencia" in df.columns
        else pd.Series([pd.NA] * len(df), index=df.index)
    )

    keys = []
    labels = []
    for i, val in df["periodo_referencia"].items():
        mes_num, ano, _raw = parse_mes_ano(val)
        if pd.isna(ano) or ano is None:
            ano = anos_aux.iloc[i] if i in anos_aux.index else None
        if pd.isna(ano) or ano is None or pd.isna(mes_num) or mes_num is None:
            keys.append(pd.NA)
            labels.append(pd.NA)
        else:
            key = f"{int(ano):04d}-{int(mes_num):02d}"
            mes_nome = [k for k, v in MES_MAP.items() if v == mes_num][0].capitalize()
            label = f"{mes_nome}/{int(ano)}"
            keys.append(key)
            labels.append(label)

    df["periodo_key"] = keys
    df["periodo_label"] = labels


# Título principal
st.title("🩸 Dashboard de Hemoprodução - HEMOPROD")
st.markdown("---")
st.sidebar.header("🔍 Filtros")

df_filtrado = df.copy()

# Mapeamento de UFs para Nomes de Estados
if "uf" in df.columns:
    estado_map = {
        "ac": "Acre",
        "al": "Alagoas",
        "ap": "Amapá",
        "am": "Amazonas",
        "ba": "Bahia",
        "ce": "Ceará",
        "df": "Distrito Federal",
        "es": "Espírito Santo",
        "go": "Goiás",
        "ma": "Maranhão",
        "mt": "Mato Grosso",
        "ms": "Mato Grosso do Sul",
        "mg": "Minas Gerais",
        "pa": "Pará",
        "pb": "Paraíba",
        "pr": "Paraná",
        "pe": "Pernambuco",
        "pi": "Piauí",
        "rj": "Rio de Janeiro",
        "rn": "Rio Grande do Norte",
        "rs": "Rio Grande do Sul",
        "ro": "Rondônia",
        "rr": "Roraima",
        "sc": "Santa Catarina",
        "sp": "São Paulo",
        "se": "Sergipe",
        "to": "Tocantins",
        "hm": "Hemominas",
    }
    df_filtrado["estado"] = (
        df_filtrado["uf"].str.lower().map(estado_map).fillna("Não Mapeado")
    )

# Filtros da sidebar
if "estado" in df_filtrado.columns:
    estados = sorted(df_filtrado["estado"].dropna().unique())
    if "Não Mapeado" in estados:
        estados.remove("Não Mapeado")
        estados.append("Não Mapeado")

    estado_selecionado = st.sidebar.multiselect("Estado", estados, default=[])
    if estado_selecionado:
        df_filtrado = df_filtrado[df_filtrado["estado"].isin(estado_selecionado)]

if "ano_referencia" in df_filtrado.columns:
    anos = sorted(df_filtrado["ano_referencia"].dropna().unique())
    ano_selecionado = st.sidebar.multiselect("Ano de Referência", anos, default=[])
    if ano_selecionado:
        df_filtrado = df_filtrado[df_filtrado["ano_referencia"].isin(ano_selecionado)]

if "municipio" in df_filtrado.columns:
    municipios = sorted(df_filtrado["municipio"].dropna().astype(str).unique())
    municipio_selecionado = st.sidebar.multiselect("Município", municipios)
    if municipio_selecionado:
        df_filtrado = df_filtrado[
            df_filtrado["municipio"].astype(str).isin(municipio_selecionado)
        ]

if "tipo_estabelecimento" in df_filtrado.columns:
    tipos = sorted(df_filtrado["tipo_estabelecimento"].dropna().astype(str).unique())
    tipo_selecionado = st.sidebar.multiselect("Tipo de Estabelecimento", tipos)
    if tipo_selecionado:
        df_filtrado = df_filtrado[
            df_filtrado["tipo_estabelecimento"].astype(str).isin(tipo_selecionado)
        ]

nome_col = "razao_social_nome_fantasia"
if nome_col in df_filtrado.columns:
    nomes_unicos = sorted(df_filtrado[nome_col].dropna().astype(str).unique())
    nomes_sel = st.sidebar.multiselect("Nome Fantasia", nomes_unicos)
    if nomes_sel:
        df_filtrado = df_filtrado[df_filtrado[nome_col].astype(str).isin(nomes_sel)]
    else:
        termo = st.sidebar.text_input("Filtrar por Nome Fantasia (contém)", "")
        if termo:
            termo_low = termo.lower().strip()
            df_filtrado = df_filtrado[
                df_filtrado[nome_col]
                .astype(str)
                .str.lower()
                .str.contains(termo_low, na=False)
            ]

if {"periodo_key", "periodo_label"}.issubset(df_filtrado.columns):
    periodo_opts = (
        df_filtrado[["periodo_key", "periodo_label"]]
        .dropna()
        .drop_duplicates()
        .sort_values("periodo_key")
        .to_dict("records")
    )
    labels = [p["periodo_label"] for p in periodo_opts]
    keys = [p["periodo_key"] for p in periodo_opts]

    # ALTERAÇÃO AQUI: default=[] (lista vazia)
    sel_labels = st.sidebar.multiselect("Mês (Período)", labels, default=[]) 
    
    # É FUNDAMENTAL manter a lógica 'if sel_labels:' para filtrar APENAS se houver seleções
    if sel_labels:
        sel_keys = [keys[labels.index(lbl)] for lbl in sel_labels]
        df_filtrado = df_filtrado[df_filtrado["periodo_key"].isin(sel_keys)]
    # Se sel_labels for [] (vazio), o filtro de período NÃO é aplicado,
    # o que deve resolver seu problema de o filtro estar ativo por padrão.

st.sidebar.markdown("---")
st.sidebar.info(f"📊 Total de registros: {len(df_filtrado)}")

# ===== SEÇÃO 1: MÉTRICAS PRINCIPAIS =====
st.header("📊 Métricas Principais")

col1, col2, col3, col4, col5 = st.columns(5)

# --- CORREÇÃO AQUI ---
# Use as colunas base da triagem para evitar contagem duplicada
cols_aptos = [
    "triagem_clinica_total_doacao_espontanea_aptos",
    "triagem_clinica_total_doacao_reposicao_aptos",
    "triagem_clinica_total_doacao_autologa_aptos",
]
cols_inaptos = [
    "triagem_clinica_total_doacao_espontanea_inaptos",
    "triagem_clinica_total_doacao_reposicao_inaptos",
    "triagem_clinica_total_doacao_autologa_inaptos",
]

with col1:
    total_aptos = 0
    for col in cols_aptos:
        if col in df_filtrado.columns:
            total_aptos += df_filtrado[col].sum()
    st.metric("Candidatos Aptos", f"{int(total_aptos):,}")

with col2:
    total_inaptos = 0
    for col in cols_inaptos:
        if col in df_filtrado.columns:
            total_inaptos += df_filtrado[col].sum()
    st.metric("Candidatos Inaptos", f"{int(total_inaptos):,}")
# --- FIM DA CORREÇÃO ---

with col3:
    # Esta métrica já estava correta
    total_coletas = 0
    if "total_coletas_sangue_total" in df_filtrado.columns:
        total_coletas += df_filtrado["total_coletas_sangue_total"].sum()
    if "total_coletas_aferese" in df_filtrado.columns:
        total_coletas += df_filtrado["total_coletas_aferese"].sum()
    st.metric("Total de Coletas", f"{int(total_coletas):,}")

with col4:
    # Esta métrica já estava correta
    if "inaptidao_triagem_laboratorial_total_bolsas_testadas" in df_filtrado.columns:
        total_bolsas = df_filtrado[
            "inaptidao_triagem_laboratorial_total_bolsas_testadas"
        ].sum()
        st.metric("Bolsas Testadas", f"{int(total_bolsas):,}")

with col5:
    # Esta métrica já estava correta
    if "descarte_bolsas_total_bolsas_descartadas_auto_exclusao" in df_filtrado.columns:
        total_descarte = df_filtrado[
            "descarte_bolsas_total_bolsas_descartadas_auto_exclusao"
        ].sum()
        st.metric("Bolsas Descartadas", f"{int(total_descarte):,}", delta=f"-{int(total_descarte):,}", delta_color="inverse")

st.markdown("---")

# ===== SEÇÃO 2: TRIAGEM CLÍNICA =====
st.header("🔬 Triagem Clínica")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Tipo de Doação", "Tipo de Doador", "Gênero", "Faixa Etária"]
)

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        doacao_data = {
            "Tipo": ["Espontânea", "Reposição", "Autóloga"],
            "Aptos": [
                (
                    df_filtrado["triagem_clinica_total_doacao_espontanea_aptos"].sum()
                    if "triagem_clinica_total_doacao_espontanea_aptos"
                    in df_filtrado.columns
                    else 0
                ),
                (
                    df_filtrado["triagem_clinica_total_doacao_reposicao_aptos"].sum()
                    if "triagem_clinica_total_doacao_reposicao_aptos"
                    in df_filtrado.columns
                    else 0
                ),
                (
                    df_filtrado["triagem_clinica_total_doacao_autologa_aptos"].sum()
                    if "triagem_clinica_total_doacao_autologa_aptos"
                    in df_filtrado.columns
                    else 0
                ),
            ],
            "Inaptos": [
                (
                    df_filtrado["triagem_clinica_total_doacao_espontanea_inaptos"].sum()
                    if "triagem_clinica_total_doacao_espontanea_inaptos"
                    in df_filtrado.columns
                    else 0
                ),
                (
                    df_filtrado["triagem_clinica_total_doacao_reposicao_inaptos"].sum()
                    if "triagem_clinica_total_doacao_reposicao_inaptos"
                    in df_filtrado.columns
                    else 0
                ),
                (
                    df_filtrado["triagem_clinica_total_doacao_autologa_inaptos"].sum()
                    if "triagem_clinica_total_doacao_autologa_inaptos"
                    in df_filtrado.columns
                    else 0
                ),
            ],
        }
        df_doacao = pd.DataFrame(doacao_data)

        fig = px.bar(
            df_doacao,
            x="Tipo",
            y=["Aptos", "Inaptos"],
            title="Candidatos por Tipo de Doação",
            barmode="group",
            color_discrete_sequence=["#2ecc71", "#e74c3c"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        total_aptos_doacao = df_doacao["Aptos"].sum()
        total_inaptos_doacao = df_doacao["Inaptos"].sum()

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["Aptos", "Inaptos"],
                    values=[total_aptos_doacao, total_inaptos_doacao],
                    hole=0.4,
                    marker_colors=["#2ecc71", "#e74c3c"],
                )
            ]
        )
        fig.update_layout(title="Proporção de Aptidão Geral")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    doador_data = {
        "Tipo": ["Primeira Vez", "Repetição", "Esporádico"],
        "Aptos": [
            (
                df_filtrado["total_doador_primeira_vez_aptos"].sum()
                if "total_doador_primeira_vez_aptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_repeticao_aptos"].sum()
                if "total_doador_repeticao_aptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_esporadico_aptos"].sum()
                if "total_doador_esporadico_aptos" in df_filtrado.columns
                else 0
            ),
        ],
        "Inaptos": [
            (
                df_filtrado["total_doador_primeira_vez_inaptos"].sum()
                if "total_doador_primeira_vez_inaptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_repeticao_inaptos"].sum()
                if "total_doador_repeticao_inaptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_esporadico_inaptos"].sum()
                if "total_doador_esporadico_inaptos" in df_filtrado.columns
                else 0
            ),
        ],
    }
    df_doador = pd.DataFrame(doador_data)

    fig = px.bar(
        df_doador,
        x="Tipo",
        y=["Aptos", "Inaptos"],
        title="Candidatos por Tipo de Doador",
        barmode="stack",
        color_discrete_sequence=["#3498db", "#e67e22"],
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    genero_data = {
        "Gênero": ["Masculino", "Feminino"],
        "Aptos": [
            (
                df_filtrado["total_doador_masculino_aptos"].sum()
                if "total_doador_masculino_aptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_feminino_aptos"].sum()
                if "total_doador_feminino_aptos" in df_filtrado.columns
                else 0
            ),
        ],
        "Inaptos": [
            (
                df_filtrado["total_doador_masculino_inaptos"].sum()
                if "total_doador_masculino_inaptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_feminino_inaptos"].sum()
                if "total_doador_feminino_inaptos" in df_filtrado.columns
                else 0
            ),
        ],
    }
    df_genero = pd.DataFrame(genero_data)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_genero,
            x="Gênero",
            y=["Aptos", "Inaptos"],
            title="Candidatos por Gênero",
            barmode="group",
            color_discrete_sequence=["#9b59b6", "#f39c12"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_genero["Total"] = df_genero["Aptos"] + df_genero["Inaptos"]
        df_genero_valid = df_genero[df_genero["Total"] > 0].copy()
        df_genero_valid["Taxa_Aptidao"] = (
            df_genero_valid["Aptos"] / df_genero_valid["Total"]
        ) * 100

        fig = px.bar(
            df_genero_valid,
            x="Gênero",
            y="Taxa_Aptidao",
            title="Taxa de Aptidão por Gênero (%)",
            color="Gênero",
            color_discrete_sequence=["#9b59b6", "#f39c12"],
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    idade_data = {
        "Faixa Etária": ["< 18 anos", "18-29 anos", "> 29 anos"],
        "Aptos": [
            (
                df_filtrado["total_doador_menor_de_18_anos_aptos"].sum()
                if "total_doador_menor_de_18_anos_aptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_18_ate_29_anos_aptos"].sum()
                if "total_doador_18_ate_29_anos_aptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_acima_de_29_anos_aptos"].sum()
                if "total_doador_acima_de_29_anos_aptos" in df_filtrado.columns
                else 0
            ),
        ],
        "Inaptos": [
            (
                df_filtrado["total_doador_menor_de_18_anos_inaptos"].sum()
                if "total_doador_menor_de_18_anos_inaptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_18_ate_29_anos_inaptos"].sum()
                if "total_doador_18_ate_29_anos_inaptos" in df_filtrado.columns
                else 0
            ),
            (
                df_filtrado["total_doador_acima_de_29_anos_inaptos"].sum()
                if "total_doador_acima_de_29_anos_inaptos" in df_filtrado.columns
                else 0
            ),
        ],
    }
    df_idade = pd.DataFrame(idade_data)

    fig = px.bar(
        df_idade,
        x="Faixa Etária",
        y=["Aptos", "Inaptos"],
        title="Candidatos por Faixa Etária",
        barmode="group",
        color_discrete_sequence=["#1abc9c", "#e74c3c"],
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 3: MOTIVOS DE INAPTIDÃO =====
st.header("⚠️ Motivos de Inaptidão")

motivos_cols = {
    "Anemia": [
        "total_candidatos_inaptos_anemia_masculino",
        "total_candidatos_inaptos_anemia_feminino",
    ],
    "Hipertensão": [
        "total_candidatos_inaptos_hipertensao_masculino",
        "total_candidatos_inaptos_hipertensao_feminino",
    ],
    "Hipotensão": [
        "total_candidatos_inaptos_hipotensao_masculino",
        "total_candidatos_inaptos_hipotensao_feminino",
    ],
    "Alcoolismo": [
        "total_candidatos_inaptos_alcoolismo_masculino",
        "total_candidatos_inaptos_alcoolismo_feminino",
    ],
    "Comportamento de Risco DST": [
        "total_candidatos_inaptos_comportamento_risco_dst_masculino",
        "total_candidatos_inaptos_comportamento_risco_dst_feminino",
    ],
    "Uso de Drogas": [
        "total_candidatos_inaptos_uso_drogas_masculino",
        "total_candidatos_inaptos_uso_drogas_feminino",
    ],
    "Hepatite": [
        "total_candidatos_inaptos_hepatite_masculino",
        "total_candidatos_inaptos_hepatite_feminino",
    ],
    "Doença de Chagas": [
        "total_candidatos_inaptos_doenca_chagas_masculino",
        "total_candidatos_inaptos_doenca_chagas_feminino",
    ],
    "Malária": [
        "total_candidatos_inaptos_malaria_masculino",
        "total_candidatos_inaptos_malaria_feminino",
    ],
    "Outras": [
        "total_candidatos_inaptos_outras_masculino",
        "total_candidatos_inaptos_outras_feminino",
    ],
}

motivos_data = []
for motivo, cols in motivos_cols.items():
    masculino = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
    feminino = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
    motivos_data.append(
        {
            "Motivo": motivo,
            "Masculino": masculino,
            "Feminino": feminino,
            "Total": masculino + feminino,
        }
    )

df_motivos = pd.DataFrame(motivos_data).sort_values("Total", ascending=False)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        df_motivos,
        x="Motivo",
        y="Total",
        title="Total de Inaptidões por Motivo",
        color="Total",
        color_continuous_scale="Reds",
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        df_motivos,
        x="Motivo",
        y=["Masculino", "Feminino"],
        title="Inaptidões por Motivo e Gênero",
        barmode="stack",
        color_discrete_sequence=["#3498db", "#e91e63"],
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 4: COLETA E INTERRUPÇÕES =====
st.header("💉 Coleta de Sangue")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Sangue Total",
        (
            f"{int(df_filtrado['total_coletas_sangue_total'].sum()):,}"
            if "total_coletas_sangue_total" in df_filtrado.columns
            else "N/A"
        ),
    )

with col2:
    st.metric(
        "Por Aférese",
        (
            f"{int(df_filtrado['total_coletas_aferese'].sum()):,}"
            if "total_coletas_aferese" in df_filtrado.columns
            else "N/A"
        ),
    )

with col3:
    desistentes = (
        df_filtrado["coleta_total_candidatos_desistentes"].sum()
        if "coleta_total_candidatos_desistentes" in df_filtrado.columns
        else 0
    )
    st.metric("Candidatos Desistentes", f"{int(desistentes):,}")

interrupcoes_data = {
    "Motivo": ["Dificuldade de Punção", "Reação Vagal", "Outros Motivos"],
    "Quantidade": [
        (
            df_filtrado["total_interrupcoes_coleta_dificuldade_puncao_venosa"].sum()
            if "total_interrupcoes_coleta_dificuldade_puncao_venosa"
            in df_filtrado.columns
            else 0
        ),
        (
            df_filtrado["total_interrupcoes_coleta_reacao_vagal"].sum()
            if "total_interrupcoes_coleta_reacao_vagal" in df_filtrado.columns
            else 0
        ),
        (
            df_filtrado["total_interrupcoes_coleta_outros_motivos"].sum()
            if "total_interrupcoes_coleta_outros_motivos" in df_filtrado.columns
            else 0
        ),
    ],
}
df_interrupcoes = pd.DataFrame(interrupcoes_data)
df_interrupcoes_valid = df_interrupcoes[df_interrupcoes["Quantidade"] > 0]

if not df_interrupcoes_valid.empty:
    fig = px.pie(
        df_interrupcoes_valid,
        values="Quantidade",
        names="Motivo",
        title="Motivos de Interrupção na Coleta",
        color_discrete_sequence=px.colors.sequential.RdBu,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma interrupção de coleta registrada no período selecionado.")

st.markdown("---")

# ===== SEÇÃO 5: EXAMES E TRIAGEM LABORATORIAL =====
st.header("🧪 Exames e Triagem Laboratorial")

doencas = {
    "Doença de Chagas": [
        "exames_triagem_doenca_doenca_chagas_amostras_testadas",
        "exames_triagem_doenca_doenca_chagas_amostras_reagentes",
    ],
    "HIV": [
        "exames_triagem_doenca_hiv_amostras_testadas",
        "exames_triagem_doenca_hiv_amostras_reagentes",
    ],
    "Sífilis": [
        "exames_triagem_doenca_sifilis_amostras_testadas",
        "exames_triagem_doenca_sifilis_amostras_reagentes",
    ],
    "Hepatite B (HBsAg)": [
        "exames_triagem_doenca_hepatite_b_hbs_ag_amostras_testadas",
        "exames_triagem_doenca_hepatite_b_hbs_ag_amostras_reagentes",
    ],
    "Hepatite B (Anti-HBc)": [
        "exames_triagem_doenca_hepatite_b_anti_hbc_amostras_testadas",
        "exames_triagem_doenca_hepatite_b_anti_hbc_amostras_reagentes",
    ],
    "Hepatite C": [
        "exames_triagem_doenca_hepatite_c_amostras_testadas",
        "exames_triagem_doenca_hepatite_c_amostras_reagentes",
    ],
    "HTLV I e II": [
        "exames_triagem_doenca_htlv_i_ii_amostras_testadas",
        "exames_triagem_doenca_htlv_i_ii_amostras_reagentes",
    ],
    "Malária": [
        "exames_triagem_doenca_malaria_amostras_testadas",
        "exames_triagem_doenca_malaria_amostras_reagentes",
    ],
}

doencas_data = []
for doenca, cols in doencas.items():
    testadas = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
    reagentes = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
    taxa = (reagentes / testadas * 100) if testadas > 0 else 0
    doencas_data.append(
        {
            "Doença": doenca,
            "Testadas": testadas,
            "Reagentes": reagentes,
            "Taxa (%)": taxa,
        }
    )

df_doencas = pd.DataFrame(doencas_data)
df_doencas_valid = df_doencas[df_doencas["Testadas"] > 0]

if not df_doencas_valid.empty:
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_doencas_valid,
            x="Doença",
            y="Testadas",
            title="Amostras Testadas por Doença",
            color="Testadas",
            color_continuous_scale="Blues",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df_doencas_valid,
            x="Doença",
            y="Reagentes",
            title="Amostras Reagentes por Doença",
            color="Reagentes",
            color_continuous_scale="Reds",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        df_doencas_valid,
        x="Doença",
        y="Taxa (%)",
        title="Taxa de Amostras Reagentes (%)",
        color="Taxa (%)",
        color_continuous_scale="OrRd",
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        "Não há dados de exames e triagem laboratorial disponíveis para o filtro atual."
    )

st.markdown("---")

# ===== SEÇÃO 6: IMUNOHEMATOLOGIA =====
st.header("🩸 Imunohematologia - Tipos Sanguíneos")

tab1, tab2 = st.tabs(["Tipos Sanguíneos", "Exames Especializados"])

with tab1:
    tipos_sanguineos = ["A+", "B+", "AB+", "O+", "A-", "B-", "AB-", "O-"]
    tipo_map = {
        "A+": [
            "imunohematologia_a_positivo_doador",
            "imunohematologia_a_positivo_receptor",
        ],
        "B+": [
            "imunohematologia_b_positivo_doador",
            "imunohematologia_b_positivo_receptor",
        ],
        "AB+": [
            "imunohematologia_ab_positivo_doador",
            "imunohematologia_ab_positivo_receptor",
        ],
        "O+": [
            "imunohematologia_o_positivo_doador",
            "imunohematologia_o_positivo_receptor",
        ],
        "A-": [
            "imunohematologia_a_negativo_doador",
            "imunohematologia_a_negativo_receptor",
        ],
        "B-": [
            "imunohematologia_b_negativo_doador",
            "imunohematologia_b_negativo_receptor",
        ],
        "AB-": [
            "imunohematologia_ab_negativo_doador",
            "imunohematologia_ab_negativo_receptor",
        ],
        "O-": [
            "imunohematologia_o_negativo_doador",
            "imunohematologia_o_negativo_receptor",
        ],
    }

    tipo_data = []
    for tipo, cols in tipo_map.items():
        doador = df_filtrado[cols[0]].sum() if cols[0] in df_filtrado.columns else 0
        receptor = df_filtrado[cols[1]].sum() if cols[1] in df_filtrado.columns else 0
        tipo_data.append({"Tipo Sanguíneo": tipo, "Doador": doador, "Receptor": receptor})

    df_tipos = pd.DataFrame(tipo_data)

    if df_tipos["Doador"].sum() > 0 or df_tipos["Receptor"].sum() > 0:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                df_tipos,
                x="Tipo Sanguíneo",
                y="Doador",
                title="Distribuição de Tipos Sanguíneos - Doadores",
                color="Tipo Sanguíneo",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                df_tipos,
                x="Tipo Sanguíneo",
                y="Receptor",
                title="Distribuição de Tipos Sanguíneos - Receptores",
                color="Tipo Sanguíneo",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de imunohematologia disponíveis para o filtro atual.")

with tab2:
    exames_especializados = {
        "Fenotipagem Doador": "imunohematologia_fenotipagem_doador",
        "Fenotipagem Receptor": "imunohematologia_fenotipagem_receptor",
        "Coombs Direto Doador": "imunohematologia_combs_direto_doador",
        "Coombs Direto Receptor": "imunohematologia_combs_direto_receptor",
        "Pesquisa Anticorpo Irregular + Doador": "imunohematologia_pesquisa_anticorpo_irregular_positivo_doador",
        "Pesquisa Anticorpo Irregular + Receptor": "imunohematologia_pesquisa_anticorpo_irregular_positivo_receptor",
        "D Fraco Doador": "imunohematologia_dfraco_doador",
        "D Fraco Receptor": "imunohematologia_dfraco_receptor",
    }
    
    exames_data = []
    for exame, col in exames_especializados.items():
        quantidade = df_filtrado[col].sum() if col in df_filtrado.columns else 0
        exames_data.append({"Exame": exame, "Quantidade": quantidade})
    
    df_exames = pd.DataFrame(exames_data)
    df_exames_valid = df_exames[df_exames["Quantidade"] > 0]
    
    if not df_exames_valid.empty:
        fig = px.bar(
            df_exames_valid,
            x="Exame",
            y="Quantidade",
            title="Exames Especializados de Imunohematologia",
            color="Quantidade",
            color_continuous_scale="Teal",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de exames especializados para o filtro atual.")

st.markdown("---")

# ===== SEÇÃO 7: PRODUÇÃO HEMOTERÁPICA =====
st.header("🏭 Produção Hemoterápica")

componentes = {
    "Sangue Total": "sangue_total",
    "Plasma Fresco Congelado": "plasma_fresco_congelado",
    "Plasma Comum": "plasma_comum",
    "Concentrado de Hemácias": "concentrado_hemacias",
    "Concentrado de Plaquetas": "concentrado_plaquetas",
    "Crioprecipitado": "crioprecipitado",
}

producao_data = []
producao_total = 0
for componente, nome_col in componentes.items():
    produzidas = df_filtrado.get(
        f"producao_hemoterapica_entradas_{nome_col}_produzidas", pd.Series([0])
    ).sum()
    recebidas = df_filtrado.get(
        f"producao_hemoterapica_entradas_{nome_col}_recebidas", pd.Series([0])
    ).sum()
    devolvidas = df_filtrado.get(
        f"producao_hemoterapica_entradas_{nome_col}_devolvidas", pd.Series([0])
    ).sum()

    producao_data.append(
        {
            "Componente": componente,
            "Produzidas": produzidas,
            "Recebidas": recebidas,
            "Devolvidas": devolvidas,
        }
    )
    producao_total += produzidas + recebidas + devolvidas

df_producao = pd.DataFrame(producao_data)

if producao_total > 0:
    fig = px.bar(
        df_producao,
        x="Componente",
        y=["Produzidas", "Recebidas", "Devolvidas"],
        title="Produção Hemoterápica - Entradas",
        barmode="group",
        color_discrete_sequence=["#27ae60", "#3498db", "#f39c12"],
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há dados de produção hemoterápica disponíveis para o filtro atual.")

st.markdown("---")

# ===== SEÇÃO 8: ENVIO DE PLASMA PARA HEMODERIVADOS =====
st.header("🧬 Envio de Plasma para Produção de Hemoderivados")

col1, col2, col3 = st.columns(3)

plasma_fresco = (
    df_filtrado["envio_plasma_producao_hemoderivados_plasma_fresco_congelado"].sum()
    if "envio_plasma_producao_hemoderivados_plasma_fresco_congelado" in df_filtrado.columns
    else 0
)

plasma_comum = (
    df_filtrado["envio_plasma_producao_hemoderivados_plasma_comum"].sum()
    if "envio_plasma_producao_hemoderivados_plasma_comum" in df_filtrado.columns
    else 0
)

total_plasma_enviado = plasma_fresco + plasma_comum

with col1:
    st.metric("Plasma Fresco Congelado", f"{int(plasma_fresco):,}")

with col2:
    st.metric("Plasma Comum", f"{int(plasma_comum):,}")

with col3:
    st.metric("Total Enviado", f"{int(total_plasma_enviado):,}")

if total_plasma_enviado > 0:
    fig = go.Figure(data=[
        go.Pie(
            labels=["Plasma Fresco Congelado", "Plasma Comum"],
            values=[plasma_fresco, plasma_comum],
            hole=0.4,
            marker_colors=["#3498db", "#9b59b6"],
        )
    ])
    fig.update_layout(title="Distribuição de Plasma Enviado para Hemoderivados")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há dados de envio de plasma para hemoderivados no período selecionado.")

st.markdown("---")

# ===== SEÇÃO 9: DISTRIBUIÇÃO PARA OUTROS SERVIÇOS =====
st.header("🚚 Distribuição para Outros Serviços")

tab1, tab2 = st.tabs(["Por Componente", "Análise de Exames Pré-Transfusionais"])

with tab1:
    distribuicao_data = []
    for componente, nome_col in componentes.items():
        sem_exame = df_filtrado.get(
            f"distribuicao_para_outros_servicos_{nome_col}_sem_exame_pre_transfusional",
            pd.Series([0])
        ).sum()
        com_exame = df_filtrado.get(
            f"distribuicao_para_outros_servicos_{nome_col}_com_exame_pre_transfusional",
            pd.Series([0])
        ).sum()
        total = df_filtrado.get(
            f"distribuicao_para_outros_servicos_{nome_col}_total",
            pd.Series([0])
        ).sum()

        distribuicao_data.append({
            "Componente": componente,
            "Sem Exame Pré-Transfusional": sem_exame,
            "Com Exame Pré-Transfusional": com_exame,
            "Total": total,
        })

    df_distribuicao = pd.DataFrame(distribuicao_data)
    df_distribuicao_valid = df_distribuicao[df_distribuicao["Total"] > 0]

    if not df_distribuicao_valid.empty:
        fig = px.bar(
            df_distribuicao_valid,
            x="Componente",
            y=["Sem Exame Pré-Transfusional", "Com Exame Pré-Transfusional"],
            title="Distribuição por Tipo de Exame",
            barmode="stack",
            color_discrete_sequence=["#e74c3c", "#27ae60"],
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de distribuição para outros serviços.")

with tab2:
    if not df_distribuicao_valid.empty:
        df_distribuicao_valid["Taxa Com Exame (%)"] = (
            df_distribuicao_valid["Com Exame Pré-Transfusional"] / 
            df_distribuicao_valid["Total"] * 100
        ).fillna(0)

        fig = px.bar(
            df_distribuicao_valid,
            x="Componente",
            y="Taxa Com Exame (%)",
            title="Taxa de Distribuição com Exame Pré-Transfusional (%)",
            color="Taxa Com Exame (%)",
            color_continuous_scale="Greens",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== SEÇÃO 10: PERDAS =====
st.header("📉 Perdas de Hemocomponentes")

perdas_data = []
perdas_total = 0
for componente, nome_col in componentes.items():
    rompimento = df_filtrado.get(
        f"perdas_{nome_col}_rompimento_de_bolsa", pd.Series([0])
    ).sum()
    validade = df_filtrado.get(f"perdas_{nome_col}_validade", pd.Series([0])).sum()
    outros = df_filtrado.get(f"perdas_{nome_col}_outros_motivos", pd.Series([0])).sum()

    perdas_data.append(
        {
            "Componente": componente,
            "Rompimento": rompimento,
            "Validade": validade,
            "Outros": outros,
            "Total": rompimento + validade + outros,
        }
    )
    perdas_total += rompimento + validade + outros

df_perdas = pd.DataFrame(perdas_data)
df_perdas_valid = df_perdas[df_perdas["Total"] > 0]

if perdas_total > 0:
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_perdas_valid,
            x="Componente",
            y=["Rompimento", "Validade", "Outros"],
            title="Perdas por Motivo",
            barmode="stack",
            color_discrete_sequence=["#e74c3c", "#e67e22", "#95a5a6"],
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            df_perdas_valid,
            values="Total",
            names="Componente",
            title="Distribuição Total de Perdas",
            color_discrete_sequence=px.colors.sequential.RdBu,
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há perdas de hemocomponentes registradas no período selecionado.")

st.markdown("---")

# ===== SEÇÃO 11: TRANSFUSÕES =====
st.header("💉 Transfusões Realizadas")

transfusoes_data = []
transfusoes_total = 0
for componente, nome_col in componentes.items():
    ambulatorial = df_filtrado.get(
        f"tranfusoes_{nome_col}_ambulatorial", pd.Series([0])
    ).sum()
    hospitalar = df_filtrado.get(
        f"tranfusoes_{nome_col}_hospitalar", pd.Series([0])
    ).sum()
    total = df_filtrado.get(f"tranfusoes_{nome_col}_total", pd.Series([0])).sum()

    transfusoes_data.append(
        {
            "Componente": componente,
            "Ambulatorial": ambulatorial,
            "Hospitalar": hospitalar,
            "Total": total,
        }
    )
    transfusoes_total += total

df_transfusoes = pd.DataFrame(transfusoes_data)
df_transfusoes_valid = df_transfusoes[df_transfusoes["Total"] > 0]

if transfusoes_total > 0:
    fig = px.bar(
        df_transfusoes_valid,
        x="Componente",
        y=["Ambulatorial", "Hospitalar"],
        title="Transfusões por Ambiente",
        barmode="stack",
        color_discrete_sequence=["#16a085", "#2980b9"],
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há dados de transfusões realizadas no período selecionado.")

st.markdown("---")

# ===== SEÇÃO 12: REAÇÕES TRANSFUSIONAIS =====
st.header("⚠️ Reações Transfusionais")

reacoes_cols = {
    "Reação Febril não Hemolítica": "reacoes_transfusionais_reacao_febril_nao_hemolitica",
    "Reação Hemolítica": "reacoes_transfusionais_reacao_hemolitica",
    "Reação Alérgica": "reacoes_transfusionais_reacao_alergica",
    "Choque Bacteriano": "reacoes_transfusionais_choque_bacteriano",
    "Alterações Metabólicas": "reacoes_transfusionais_alteracoes_metabolicas",
    "Sobrecarga Volêmica": "reacoes_transfusionais_sobrecarga_volemica",
    "Outras Reações": "reacoes_transfusionais_outras_reacoes",
}

reacoes_data = []
reacoes_total = 0
for reacao, col in reacoes_cols.items():
    quantidade = df_filtrado.get(col, pd.Series([0])).sum()
    reacoes_data.append({"Tipo de Reação": reacao, "Quantidade": quantidade})
    reacoes_total += quantidade

df_reacoes = pd.DataFrame(reacoes_data).sort_values("Quantidade", ascending=False)
df_reacoes_valid = df_reacoes[df_reacoes["Quantidade"] > 0]

if reacoes_total > 0:
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_reacoes_valid,
            x="Tipo de Reação",
            y="Quantidade",
            title="Reações Transfusionais por Tipo",
            color="Quantidade",
            color_continuous_scale="Reds",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            df_reacoes_valid,
            values="Quantidade",
            names="Tipo de Reação",
            title="Distribuição de Reações Transfusionais",
            color_discrete_sequence=px.colors.sequential.Reds,
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há reações transfusionais registradas no período selecionado.")

st.markdown("---")

# ===== SEÇÃO 13: PROCEDIMENTOS DE MODIFICAÇÃO =====
st.header("🔧 Procedimentos de Modificação")

procedimentos_cols = {
    "Lavagem": "procedimentos_de_modificacao_dos_hemocomponentes_lavagem",
    "Irradiação": "procedimentos_de_modificacao_dos_hemocomponentes_irradiacao",
    "Filtração em Plaquetas": "procedimentos_de_modificacao_dos_hemocomponentes_filtracao_em_concentrado_de_plaquetas",
    "Filtração em Hemácias": "procedimentos_de_modificacao_dos_hemocomponentes_filtracao_em_concentrado_de_hemacias",
    "Fracionamento Pediátrico": "procedimentos_de_modificacao_dos_hemocomponentes_fracionamento_pediatrico",
}

procedimentos_data = []
procedimentos_total = 0
for proc, col in procedimentos_cols.items():
    quantidade = df_filtrado.get(col, pd.Series([0])).sum()
    procedimentos_data.append({"Procedimento": proc, "Quantidade": quantidade})
    procedimentos_total += quantidade

df_procedimentos = pd.DataFrame(procedimentos_data)
df_procedimentos_valid = df_procedimentos[df_procedimentos["Quantidade"] > 0]

if procedimentos_total > 0:
    fig = px.bar(
        df_procedimentos_valid,
        x="Procedimento",
        y="Quantidade",
        title="Procedimentos de Modificação Realizados",
        color="Quantidade",
        color_continuous_scale="Viridis",
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        "Não há procedimentos de modificação de hemocomponentes registrados no período selecionado."
    )

st.markdown("---")
# ===== SEÇÃO 14: ANÁLISE GEOGRÁFICA =====
if "municipio" in df_filtrado.columns:
    st.header("🗺️ Análise por Município")

    municipio_stats = (
        # 1. CORREÇÃO: Use df_filtrado para que os filtros funcionem
        df_filtrado.groupby("municipio") 
        .agg(
            {
                "total_coletas_sangue_total": "sum",
            }
        )
        # 2. ADIÇÃO: Use .fillna(0) para corresponder ao seu teste
        #    Isso garante que valores 'NaN' na soma se tornem 0
        .fillna(0) 
        .reset_index()
    )

    municipio_stats["Total Coletas"] = (
        municipio_stats["total_coletas_sangue_total"]
    )
    municipio_stats = municipio_stats.sort_values("Total Coletas", ascending=False)
    
    # Opcional, mas recomendado: Limitar a exibição aos Top 50, como no seu teste
    # Se você quiser mostrar TODOS, pode remover a linha abaixo.
    municipio_stats_top = municipio_stats.head(50) 

    municipio_total_coletas = municipio_stats["Total Coletas"].sum()

    if municipio_total_coletas > 0:
        fig = px.bar(
            # Use a variável 'municipio_stats_top' (ou 'municipio_stats' se quiser todos)
            municipio_stats_top, 
            x="municipio",
            y="Total Coletas",
            title="Municípios por Total de Coletas (Top 50)", # Título atualizado
            color="Total Coletas",
            color_continuous_scale="Blues",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma coleta registrada na análise geográfica para os filtros selecionados.")

# ===== SEÇÃO 15: OBSERVAÇÕES IMPORTANTES =====
st.header("📝 Observações Importantes")

obs_cols = ["hemoprod_1_observacoes", "hemoprod_2_observacoes", "hemoprod_3_observacoes"]
obs_existentes = [col for col in obs_cols if col in df_filtrado.columns]

if obs_existentes:
    tem_observacoes = False
    for col in obs_existentes:
        obs_list = df_filtrado[col].dropna().unique()
        if len(obs_list) > 0:
            tem_observacoes = True
            with st.expander(f"📌 {col.replace('_', ' ').title()}", expanded=False):
                for obs in obs_list[:10]:  # Limita a 10 observações por categoria
                    if str(obs).strip() and str(obs).lower() not in ['nan', 'none', '']:
                        st.info(obs)
    
    if not tem_observacoes:
        st.info("Não há observações registradas para os filtros selecionados.")
else:
    st.info("Colunas de observações não disponíveis no dataset.")

st.markdown("---")

# ===== SEÇÃO 16: TABELA DE DADOS =====
st.header("📋 Dados Detalhados")

colunas_importantes = [
    "estado",
    "municipio",
    "razao_social_nome_fantasia",
    "tipo_estabelecimento",
    "ano_referencia",
    "periodo_referencia",
    "total_coletas_sangue_total",
    "total_coletas_aferese",
    "inaptidao_triagem_laboratorial_total_bolsas_testadas",
    "descarte_bolsas_total_bolsas_descartadas_auto_exclusao",
]

colunas_disponiveis = [col for col in colunas_importantes if col in df_filtrado.columns]

if colunas_disponiveis:
    st.dataframe(df_filtrado[colunas_disponiveis].head(50), use_container_width=True)
else:
    st.dataframe(df_filtrado.head(50), use_container_width=True)

st.download_button(
    label="📥 Download dos Dados Filtrados (CSV)",
    data=df_filtrado.to_csv(index=False).encode("utf-8"),
    file_name="hemoprod_filtrado.csv",
    mime="text/csv",
)

st.markdown("---")
st.info(
    "💡 **Dica:** Use os filtros na barra lateral para explorar os dados de forma mais específica!"
)