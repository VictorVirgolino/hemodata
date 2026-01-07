import pandas as pd
import numpy as np
import os
import re
import logging
from typing import List, Dict, Any, Set
import sys

# --- 1. Configurações Globais ---

# Caminhos principais (ajuste se necessário)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_BRUTOS_PATH = os.path.join(BASE_DIR, "dados_brutos")
PROCESSADOS_PATH = os.path.join(BASE_DIR, "dados_processados")
LOGS_PATH = os.path.join(PROCESSADOS_PATH, "logs")

# Dicionários
DICIONARIO_PRINCIPAL_PATH = os.path.join(
    BASE_DIR, "dicionario_colunas_269_COM_TIPOS.xlsx"
)
DICIONARIO_MAPA_PATH = os.path.join(BASE_DIR, "dicionario_colunas_269_all.xlsx")

LOG_FILE_PATH = os.path.join(BASE_DIR, "processamento_log.txt")

# Constantes para deduplicação
COLUNAS_CHAVE = [
    "cnpj",
    "ano_referencia",
    "periodo_referencia",
    "razao_social_nome_fantasia",
]
COLUNA_DATA = "data_envio"

# Mapeamento de abreviações para nomes
ESTADOS_MAPA = {
    "al": "Alagoas",
    "am": "Amazonas",
    "ap": "Amapá",
    "ba": "Bahia",
    "ce": "Ceará",
    "df": "Distrito Federal",
    "es": "Espírito Santo",
    "go": "Goiás",
    "hm": "Hemominas",
    "ma": "Maranhão",
    "mg": "Minas Gerais",
    "ms": "Mato Grosso do Sul",
    "mt": "Mato Grosso",
    "pa": "Pará",
    "pb": "Paraíba",
    "pe": "Pernambuco",
    "pi": "Piauí",
    "pr": "Paraná",
    "rj": "Rio de Janeiro",
    "rn": "Rio Grande do Norte",
    "ro": "Rondônia",
    "rr": "Roraima",
    "rs": "Rio Grande do Sul",
    "sc": "Santa Catarina",
    "se": "Sergipe",
    "sp": "São Paulo",
    "to": "Tocantins",
}

ESTADOS_PLANILHA = {
    "al": "HEMOPROD - ALAGOAS",
    "am": "HEMOPROD - AMAZONAS",
    "ap": "HEMOPROD - AMAPA",
    "ba": "HEMOPROD - BAHIA",
    "ce": "Planilha1",
    "df": "HEMOPROD - DISTRITOFEDERAL",
    "es": "HEMOPROD - ESPIRITOSANTO",
    "go": "HEMOPROD - GOIAS",
    "hm": "HEMOPROD - HEMOMINAS",
    "ma": "HEMOPROD - MARANHAO",
    "mg": "HEMOPROD - MINASGERAIS",
    "ms": "HEMOPROD - MATOGROSSODOSUL",
    "mt": "HEMOPROD - MATOGROSSO",
    "pa": "HEMOPROD - PARA",
    "pb": "HEMOPROD - PARAIBA",
    "pe": "HEMOPROD - PERNAMBUCO",
    "pi": "HEMOPROD - PIAUI",
    "pr": "HEMOPROD - PARANA",
    "rj": "Hemoprod_RJ",
    "rn": "HEMOPROD - RIOGRANDEDONORTE",
    "ro": "HEMOPROD - RONDONIA",
    "rr": "HEMOPROD - RORAIMA",
    "rs": "HEMOPROD - RIOGRANDEDOSUL",
    "sc": "HEMOPROD - SANTACATARINA",
    "se": "HEMOPROD - SERGIPE",
    "sp": "Hemoprod_SP",
    "to": "HEMOPROD - TOCANTINS",
}


# --- 2. Funções Auxiliares ---


def setup_logging_geral():
    """Configura o logging geral (arquivo principal)."""
    # Remove todos os handlers existentes
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    root.setLevel(logging.INFO)

    # Formato
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    # Handler para arquivo geral
    fh = logging.FileHandler(LOG_FILE_PATH, mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Handler para console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    root.addHandler(ch)


def criar_logger_arquivo(nome_arquivo: str):
    """
    Cria um logger isolado para um arquivo específico.
    Retorna o logger e os handlers para fechar depois.
    """
    # Cria diretório de logs se não existir
    os.makedirs(LOGS_PATH, exist_ok=True)

    # Nome do logger único
    logger_name = f"etl_arquivo_{nome_arquivo}"
    logger = logging.getLogger(logger_name)

    # Remove handlers anteriores (caso exista)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False  # NÃO propaga para o root logger

    # Formato com prefixo do arquivo
    fmt = f"%(asctime)s - [%(levelname)s] - [{nome_arquivo}] - %(message)s"
    formatter = logging.Formatter(fmt)

    # Handler para arquivo específico
    log_file_path = os.path.join(LOGS_PATH, f'{nome_arquivo.replace(".xlsx", "")}.log')
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Handler para console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger, [fh, ch]


def fechar_logger(logger, handlers):
    """Fecha e remove todos os handlers de um logger."""
    for handler in handlers:
        try:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
        except Exception:
            pass


def normalizar_periodo_referencia(df: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Normaliza o campo periodo_referencia quando vier com ano junto.
    Exemplos: 'Outubro/2022', 'Consolidado/2023', 'Consolidado 2022', '10/2022'
    Extrai o ano (4 dígitos) para ano_referencia e deixa apenas o período em periodo_referencia.
    """
    if 'periodo_referencia' not in df.columns:
        logger.warning("Coluna 'periodo_referencia' não encontrada. Pulando normalização.")
        return df
    
    # Cria a coluna ano_referencia se não existir
    if 'ano_referencia' not in df.columns:
        logger.info("Coluna 'ano_referencia' não existe. Criando...")
        df['ano_referencia'] = pd.NA
    
    registros_alterados = 0
    
    for idx in df.index:
        valor = df.at[idx, 'periodo_referencia']
        
        if pd.isna(valor):
            continue
            
        valor_str = str(valor).strip()
        
        # Busca por 4 dígitos consecutivos (ano)
        ano_match = re.search(r'\b(\d{4})\b', valor_str)
        
        if ano_match:
            ano_encontrado = int(ano_match.group(1))
            
            # Remove o ano do texto do período (e também remove / ou espaços extras)
            periodo_limpo = re.sub(r'\s*/?\s*\d{4}\b', '', valor_str).strip()
            periodo_limpo = re.sub(r'/\s*$', '', periodo_limpo).strip()  # Remove barra final se sobrar
            periodo_limpo = re.sub(r'^\s*/', '', periodo_limpo).strip()  # Remove barra inicial se sobrar
            
            # Atualiza periodo_referencia (sem o ano)
            if periodo_limpo:
                df.at[idx, 'periodo_referencia'] = periodo_limpo
            
            # Atualiza ano_referencia
            ano_atual = df.at[idx, 'ano_referencia']
            
            # Verifica se está vazio (NaN, None, string vazia, etc.)
            ano_vazio = pd.isna(ano_atual) or ano_atual == '' or ano_atual is None
            
            if ano_vazio:
                df.at[idx, 'ano_referencia'] = ano_encontrado
                registros_alterados += 1
            else:
                # Se já existe um ano, verifica se é diferente
                try:
                    ano_atual_int = int(ano_atual)
                    if ano_atual_int != ano_encontrado:
                        logger.warning(f"Conflito de ano na linha {idx}: ano_referencia={ano_atual_int}, encontrado no período={ano_encontrado}. Mantendo {ano_encontrado}.")
                        df.at[idx, 'ano_referencia'] = ano_encontrado
                        registros_alterados += 1
                except (ValueError, TypeError):
                    # Se não conseguir converter, sobrescreve
                    df.at[idx, 'ano_referencia'] = ano_encontrado
                    registros_alterados += 1
    
    if registros_alterados > 0:
        logger.info(f"✓ Normalizados {registros_alterados} registros com ano no período")
    else:
        logger.info("✓ Nenhum registro necessitou normalização de período/ano")
    
    return df

def normalizar_municipio_estado(df: pd.DataFrame, logger) -> pd.DataFrame:  
    """  
    Normaliza o campo municipio quando vier com estado junto.  
    Exemplos: 'Maceió, Alagoas', 'São Paulo, SP', 'Rio de Janeiro,RJ'  
    Extrai o estado para a coluna 'estado' e deixa apenas o município em 'municipio'.  
    """  
    if 'municipio' not in df.columns:  
        logger.warning("Coluna 'municipio' não encontrada. Pulando normalização.")  
        return df  
      
    # Cria a coluna estado se não existir  
    if 'estado' not in df.columns:  
        logger.info("Coluna 'estado' não existe. Criando...")  
        df['estado'] = ""  
      
    registros_alterados = 0  
      
    for idx in df.index:  
        valor = df.at[idx, 'municipio']  
          
        if pd.isna(valor) or valor == '':  
            continue  
              
        valor_str = str(valor).strip()  
          
        # Verifica se tem vírgula (separador comum entre município e estado)  
        if ',' in valor_str:  
            partes = valor_str.split(',')  
              
            if len(partes) >= 2:  
                municipio_limpo = partes[0].strip()  
                estado_extraido = partes[1].strip()  
                  
                # Atualiza municipio (sem o estado)  
                df.at[idx, 'municipio'] = municipio_limpo  
                  
                # Atualiza estado  
                estado_atual = df.at[idx, 'estado']  
                  
                # Verifica se está vazio  
                estado_vazio = pd.isna(estado_atual) or estado_atual == '' or estado_atual is None  
                  
                if estado_vazio:  
                    df.at[idx, 'estado'] = estado_extraido  
                    registros_alterados += 1  
                else:  
                    # Se já existe um estado, verifica se é diferente  
                    if str(estado_atual).strip() != estado_extraido:  
                        logger.warning(f"Conflito de estado na linha {idx}: estado={estado_atual}, encontrado no município={estado_extraido}. Mantendo {estado_extraido}.")  
                        df.at[idx, 'estado'] = estado_extraido  
                        registros_alterados += 1  
      
    if registros_alterados > 0:  
        logger.info(f"✓ Normalizados {registros_alterados} registros com estado no município")  
    else:  
        logger.info("✓ Nenhum registro necessitou normalização de município/estado")  
      
    return df


def gerar_lista_arquivos() -> List[Dict[str, str]]:
    """Gera o dicionário de lista com os arquivos e planilhas a processar."""
    arquivos_para_processar = []

    for abrev, estado in ESTADOS_MAPA.items():
        # Define o nome do ARQUIVO
        if abrev == "hm":
            arquivo_bruto = "Hemoprod_Hemominas.xlsx"
        else:
            arquivo_bruto = f"Hemoprod_{abrev.upper()}.xlsx"

        # Busca o nome da PLANILHA
        planilha = ESTADOS_PLANILHA.get(abrev)

        if not planilha:
            logging.warning(f"Nome da planilha não encontrado para '{abrev}'. Pulando.")
            continue

        # Define o nome do arquivo de SAÍDA
        arquivo_processado = f"hemoprod_{abrev.lower()}.xlsx"

        arquivos_para_processar.append(
            {
                "arquivo_bruto": arquivo_bruto,
                "planilha": planilha,
                "arquivo_processado": arquivo_processado,
                "sigla": abrev.upper(),
            }
        )

    return arquivos_para_processar


def carregar_dicionario(caminho_dicionario: str) -> pd.DataFrame:
    """Carrega e limpa o dicionário de colunas."""
    logging.info(f"Carregando dicionário de {caminho_dicionario}...")
    dicionario = pd.read_excel(caminho_dicionario)

    # Limpeza dos nomes originais no dicionário
    if "nome_original" in dicionario.columns:
        dicionario["nome_original"] = (
            dicionario["nome_original"].astype(str).str.strip().str.replace("\xa0", " ")
        )
    else:
        raise KeyError("Coluna 'nome_original' não encontrada no dicionário.")

    if "nome_sql" not in dicionario.columns:
        raise KeyError("Coluna 'nome_sql' não encontrada no dicionário.")

    # Carrega e limpa a coluna de tipos
    if "tipo_dados" in dicionario.columns:
        dicionario["tipo_dados"] = (
            dicionario["tipo_dados"].astype(str).str.strip().str.lower()
        )
        dicionario["tipo_dados"] = dicionario["tipo_dados"].replace("nan", "object")
        dicionario["tipo_dados"] = dicionario["tipo_dados"].fillna("object")
    else:
        if "all.xlsx" not in caminho_dicionario:
            raise KeyError(
                "Coluna 'tipo_dados' não encontrada no dicionário principal."
            )
        dicionario["tipo_dados"] = "object"

    logging.info(
        f"Dicionário {os.path.basename(caminho_dicionario)} carregado com sucesso."
    )
    return dicionario


def processar_arquivo(
    info_arquivo: Dict[str, str],
    df_dicionario: pd.DataFrame,
    mapa_renomeacao: Dict[str, str],
    colunas_sql_desejadas: Set[str],
):
    """Executa o pipeline completo de processamento para um único arquivo."""

    arquivo_dados_path = os.path.join(DADOS_BRUTOS_PATH, info_arquivo["arquivo_bruto"])
    nome_planilha = info_arquivo["planilha"]
    nome_saida = info_arquivo["arquivo_processado"]
    sigla = info_arquivo["sigla"]

    # Cria logger isolado para este arquivo
    logger, handlers = criar_logger_arquivo(nome_saida)

    try:
        logger.info("=" * 60)
        logger.info(f"INICIANDO PROCESSAMENTO: {sigla}")
        logger.info("=" * 60)

        # --- 1. Carregar Dados ---
        if not os.path.exists(arquivo_dados_path):
            logger.warning(f"Arquivo não encontrado: {arquivo_dados_path}")
            logger.warning("PULANDO ARQUIVO")
            return

        logger.info(f"Carregando arquivo: {info_arquivo['arquivo_bruto']}")
        logger.info(f"Planilha: {nome_planilha}")

        try:
            df = pd.read_excel(arquivo_dados_path, sheet_name=nome_planilha)
        except Exception as e:
            logger.error(f"ERRO ao carregar arquivo: {e}")
            logger.error("PULANDO ARQUIVO")
            return

        # Métricas iniciais
        col_count_original = len(df.columns)
        row_count_original = len(df)
        logger.info(f"✓ Colunas Originais: {col_count_original}")
        logger.info(f"✓ Linhas Originais: {row_count_original}")

        # --- 2. Limpeza e Renomeação ---
        logger.info("Iniciando limpeza e renomeação de colunas...")
        print(f"   🔧 Limpando e renomeando colunas...")
        sys.stdout.flush()

        mapa_limpeza = {
            col: str(col).strip().replace("\xa0", " ") for col in df.columns
        }
        df.rename(columns=mapa_limpeza, inplace=True)
        df.rename(columns=mapa_renomeacao, inplace=True)

        # # ===== DEBUG TEMPORÁRIO - REMOVER DEPOIS =====
        # if sigla == 'DF':
        #     logger.info("🔍 DEBUG - Colunas problemáticas do DF:")
        #     for col in df.columns:
        #         if 'Razão Social' in str(col) or 'razao_social' in str(col).lower():
        #             logger.info(f"  Coluna encontrada: '{col}'")
        #             logger.info(f"  Tamanho: {len(str(col))} caracteres")
        #             logger.info(f"  Repr: {repr(col)}")
        #             logger.info(f"  Está no mapa? {col in mapa_renomeacao}")
        #             if col in mapa_renomeacao:
        #                 logger.info(f"  Mapeia para: {mapa_renomeacao[col]}")
        #             logger.info("")

        #     logger.info("🔍 DEBUG - Verificando dicionário de mapeamento:")
        #     for key in mapa_renomeacao.keys():
        #         if 'Razão Social' in str(key):
        #             logger.info(f"  Chave no dicionário: '{key}'")
        #             logger.info(f"  Tamanho: {len(str(key))} caracteres")
        #             logger.info(f"  Repr: {repr(key)}")
        #             logger.info(f"  Mapeia para: {mapa_renomeacao[key]}")
        #             logger.info("")
        # # ===== FIM DO DEBUG =====

        # # ===== DEBUG TEMPORÁRIO - MUNICÍPIO =====  
        # logger.info("🔍 DEBUG - Investigando campo Município:")  
        # logger.info(f"Total de colunas no DataFrame: {len(df.columns)}")  
          
        # # Procura por qualquer coluna que contenha "Município" ou "municipio"  
        # for col in df.columns:  
        #     col_lower = str(col).lower()  
        #     if 'município' in col_lower or 'municipio' in col_lower:  
        #         logger.info(f"\n  ✓ Coluna encontrada: '{col}'")  
        #         logger.info(f"    Tamanho: {len(str(col))} caracteres")  
        #         logger.info(f"    Repr: {repr(col)}")  
        #         logger.info(f"    Bytes: {str(col).encode('utf-8')}")  
        #         logger.info(f"    Está no mapa? {col in mapa_renomeacao}")  
        #         if col in mapa_renomeacao:  
        #             logger.info(f"    Mapeia para: {mapa_renomeacao[col]}")  
        #         else:  
        #             logger.info(f"    ❌ NÃO está no mapa de renomeação!")  
                  
        #         # Mostra amostra dos dados  
        #         valores_nao_nulos = df[col].dropna().head(3)  
        #         if len(valores_nao_nulos) > 0:  
        #             logger.info(f"    Amostra de dados:")  
        #             for val in valores_nao_nulos:  
        #                 logger.info(f"      - {val}")  
  
        # logger.info("\n🔍 DEBUG - Verificando dicionário de mapeamento:")  
        # logger.info(f"Total de chaves no mapa: {len(mapa_renomeacao)}")  
          
        # # Procura por chaves que contenham "Município" ou "municipio"  
        # encontrou_no_mapa = False  
        # for key in mapa_renomeacao.keys():  
        #     key_lower = str(key).lower()  
        #     if 'município' in key_lower or 'municipio' in key_lower:  
        #         encontrou_no_mapa = True  
        #         logger.info(f"\n  ✓ Chave no dicionário: '{key}'")  
        #         logger.info(f"    Tamanho: {len(str(key))} caracteres")  
        #         logger.info(f"    Repr: {repr(key)}")  
        #         logger.info(f"    Bytes: {str(key).encode('utf-8')}")  
        #         logger.info(f"    Mapeia para: {mapa_renomeacao[key]}")  
          
        # if not encontrou_no_mapa:  
        #     logger.warning("  ❌ Nenhuma chave com 'município' encontrada no mapa!")  
          
        # logger.info("\n" + "="*60)  
        # # ===== FIM DO DEBUG MUNICÍPIO =====

        colunas_apos_renomeacao = set(df.columns)
        logger.info("✓ Colunas limpas e renomeadas")

        # --- 2.5. Normalização de Período/Ano (ANTES da aplicação de tipos) ---
        logger.info("Normalizando período e ano de referência...")
        print(f"   📅 Normalizando período/ano...")
        sys.stdout.flush()
        df = normalizar_periodo_referencia(df, logger)
        logger.info("✓ Período/Ano normalizado")

        # --- 2.6. Normalização de Município/Estado ---  
        logger.info("Normalizando município e estado...")  
        print(f"   🗺️  Normalizando município/estado...")  
        sys.stdout.flush()  
        df = normalizar_municipio_estado(df, logger)  
        logger.info("✓ Município/Estado normalizado")
        
        # --- 3. Aplicação de Tipos ---
        logger.info("Aplicando tipos de dados...")

        mapa_tipos = pd.Series(
            df_dicionario["tipo_dados"].values, index=df_dicionario["nome_sql"]
        ).to_dict()

        for col in df.columns:
            if col not in colunas_sql_desejadas:
                continue

            tipo_desejado = mapa_tipos.get(col, "object")

            try:
                if tipo_desejado in ("int", "integer", "int64"):
                    if df[col].dtype == "object":
                        df[col] = (
                            df[col].astype(str).str.replace(r"[.,]", "", regex=True)
                        )
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df[col] = df[col].round(0).astype("Int64")

                elif tipo_desejado in ("float", "decimal", "float64"):
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df[col] = df[col].astype("float64")

                elif tipo_desejado in ("datetime", "date", "datetime64[ns]"):
                    df[col] = pd.to_datetime(df[col], errors="coerce")

                elif tipo_desejado in ("string", "text", "object"):
                    df[col] = df[col].astype("object")

            except Exception as e:
                logger.warning(f"Falha ao converter '{col}' para {tipo_desejado}: {e}")
                try:
                    df[col] = df[col].astype("object")
                except Exception as e_obj:
                    logger.error(
                        f"ERRO CRÍTICO ao forçar '{col}' para 'object': {e_obj}"
                    )

        logger.info("✓ Tipos aplicados")

        # --- 4. Análise de Schema ---
        colunas_faltantes = list(colunas_sql_desejadas - colunas_apos_renomeacao)
        colunas_a_mais = list(colunas_apos_renomeacao - colunas_sql_desejadas)

        logger.info(f"✓ Colunas Faltantes: {len(colunas_faltantes)}")
        if colunas_faltantes:
            logger.info(
                f"  → {colunas_faltantes[:5]}{'...' if len(colunas_faltantes) > 5 else ''}"
            )

        logger.info(f"✓ Colunas A Mais: {len(colunas_a_mais)}")
        if colunas_a_mais:
            logger.info(
                f"  → {colunas_a_mais[:5]}{'...' if len(colunas_a_mais) > 5 else ''}"
            )

      # --- 5. Padronização do Schema ---
        logger.info("Padronizando schema...")

        # Remove colunas a mais
        if colunas_a_mais:
            colunas_para_dropar = [col for col in colunas_a_mais if col in df.columns]
            df.drop(columns=colunas_para_dropar, inplace=True)

        # Adiciona colunas faltantes
        if colunas_faltantes:
            dicionario_faltante = df_dicionario[
                df_dicionario["nome_sql"].isin(colunas_faltantes)
            ]

            for col_sql in colunas_faltantes:
                # IMPORTANTE: Só cria se a coluna NÃO existir
                if col_sql in df.columns:
                    logger.info(f"Coluna '{col_sql}' já existe, mantendo valores atuais")
                    continue
                
                tipo_desejado_row = dicionario_faltante[
                    dicionario_faltante["nome_sql"] == col_sql
                ]

                if not tipo_desejado_row.empty:
                    tipo_desejado = tipo_desejado_row["tipo_dados"].iloc[0]

                    try:
                        if tipo_desejado in ("int", "integer", "int64"):
                            df[col_sql] = pd.Series(0, index=df.index, dtype="Int64")
                        elif tipo_desejado in ("float", "decimal", "float64"):
                            df[col_sql] = pd.Series(0.0, index=df.index, dtype="float64")
                        elif tipo_desejado in ("datetime", "date", "datetime64[ns]"):
                            df[col_sql] = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
                        else:
                            df[col_sql] = pd.Series("", index=df.index, dtype="object")
                    except Exception as e:
                        logger.warning(
                            f"Falha ao criar coluna '{col_sql}' com tipo {tipo_desejado}: {e}"
                        )
                        df[col_sql] = pd.Series("", index=df.index, dtype="object")
                else:
                    # Se não encontrar no dicionário, cria como string vazia
                    df[col_sql] = pd.Series("", index=df.index, dtype="object")

        # Reordena as colunas
        colunas_finais_ordenadas = [
            col for col in df_dicionario["nome_sql"] if col in df.columns
        ]
        df = df[colunas_finais_ordenadas]

        logger.info(f"✓ Schema padronizado - Colunas Finais: {len(df.columns)}")

        # --- 5.5. Preenchimento de valores nulos em colunas Int64 ---
        logger.info("Preenchendo valores nulos em colunas Int64 com 0...")
        print(f"   🔢 Preenchendo valores nulos em colunas Int64...")
        sys.stdout.flush()
        
        colunas_int64_preenchidas = 0
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                valores_nulos = df[col].isna().sum()
                if valores_nulos > 0:
                    df[col] = df[col].fillna(0)
                    colunas_int64_preenchidas += 1
                    logger.info(f"  → Coluna '{col}': {valores_nulos} valores nulos preenchidos com 0")
        
        if colunas_int64_preenchidas > 0:
            logger.info(f"✓ {colunas_int64_preenchidas} colunas Int64 preenchidas com 0")
        else:
            logger.info("✓ Nenhuma coluna Int64 necessitou preenchimento")

        # --- 6. Deduplicação ---
        logger.info("Iniciando deduplicação...")

        colunas_necessarias_dedup = COLUNAS_CHAVE + [COLUNA_DATA]

        if not all(col in df.columns for col in colunas_necessarias_dedup):
            colunas_faltantes_dedup = [
                col for col in colunas_necessarias_dedup if col not in df.columns
            ]
            logger.error(
                f"Colunas necessárias para deduplicação não encontradas: {colunas_faltantes_dedup}"
            )
            logger.warning("Pulando deduplicação")
            df_deduplicado = df
        else:
            if not pd.api.types.is_datetime64_any_dtype(df[COLUNA_DATA]):
                logger.info(f"Convertendo '{COLUNA_DATA}' para datetime...")
                df[COLUNA_DATA] = pd.to_datetime(df[COLUNA_DATA], errors="coerce")

            df_ordenado = df.sort_values(by=COLUNA_DATA, ascending=True)
            mascara_duplicatas = df_ordenado.duplicated(
                subset=COLUNAS_CHAVE, keep="last"
            )
            df_deduplicado = df_ordenado[~mascara_duplicatas]

            duplicatas_removidas = len(df) - len(df_deduplicado)
            logger.info(
                f"✓ Deduplicação concluída - Removidas {duplicatas_removidas} linhas duplicadas"
            )

        row_count_final = len(df_deduplicado)
        logger.info(f"✓ Linhas Finais: {row_count_final}")

        # --- 7. Salvar ---
        logger.info("Salvando arquivo processado...")

        output_path = os.path.join(PROCESSADOS_PATH, nome_saida)
        df_deduplicado.to_excel(output_path, index=False)

        logger.info("=" * 60)
        logger.info(f"✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
        logger.info(f"✅ Arquivo salvo em: {output_path}")
        logger.info("=" * 60)
        logger.info("")  # Linha em branco para separação

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ FALHA NO PROCESSAMENTO: {e}")
        logger.error("=" * 60)
        logger.error("", exc_info=True)

    finally:
        # Fecha e limpa o logger deste arquivo
        fechar_logger(logger, handlers)
        # Força flush do stdout
        sys.stdout.flush()


# --- 3. Execução Principal ---


def main():
    """Orquestra o processo de ETL."""

    # Setup do logging geral
    setup_logging_geral()

    logging.info("")
    logging.info("#" * 80)
    logging.info("### INÍCIO DO SCRIPT DE PROCESSAMENTO ETL ###")
    logging.info("#" * 80)
    logging.info("")

    # Garante que os diretórios existam
    os.makedirs(PROCESSADOS_PATH, exist_ok=True)
    os.makedirs(LOGS_PATH, exist_ok=True)

    # Gera a lista de arquivos
    arquivos_para_processar = gerar_lista_arquivos()
    if not arquivos_para_processar:
        logging.warning("Nenhum arquivo configurado para processamento.")
        return

    logging.info(f"Total de arquivos a processar: {len(arquivos_para_processar)}")
    logging.info("")

    # Carrega os Dicionários
    try:
        dicionario_principal = carregar_dicionario(DICIONARIO_PRINCIPAL_PATH)
        df_dicionario = dicionario_principal
        colunas_sql_desejadas = set(df_dicionario["nome_sql"].tolist())
        logging.info(f"✓ Dicionário Principal: {len(colunas_sql_desejadas)} colunas")

        dicionario_mapa = carregar_dicionario(DICIONARIO_MAPA_PATH)
        mapa_renomeacao = pd.Series(
            dicionario_mapa["nome_sql"].values, index=dicionario_mapa["nome_original"]
        ).to_dict()
        logging.info(f"✓ Dicionário de Mapeamento: {len(mapa_renomeacao)} mapeamentos")
        logging.info("")

    except Exception as e:
        logging.critical(f"❌ Falha ao carregar os dicionários: {e}")
        logging.critical("ABORTANDO SCRIPT")
        return

    # Loop de Processamento - UM ARQUIVO POR VEZ
    for idx, info_arquivo in enumerate(arquivos_para_processar, 1):
        logging.info(f"\n{'='*80}")
        logging.info(
            f"Processando arquivo {idx}/{len(arquivos_para_processar)}: {info_arquivo['arquivo_bruto']}"
        )
        logging.info(f"{'='*80}\n")

        # Processa o arquivo (com logger isolado)
        processar_arquivo(
            info_arquivo, df_dicionario, mapa_renomeacao, colunas_sql_desejadas
        )

        # Força flush entre arquivos
        sys.stdout.flush()

        # Pequena pausa para garantir que tudo foi escrito
        import time

        time.sleep(0.1)

    logging.info("")
    logging.info("#" * 80)
    logging.info("### PROCESSAMENTO CONCLUÍDO ###")
    logging.info("#" * 80)
    logging.info("")


if __name__ == "__main__":
    main()

