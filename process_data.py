import pandas as pd
import numpy as np
import os
import logging
from typing import List, Dict, Any, Set

# --- 1. Configurações Globais ---

# Caminhos principais (ajuste se necessário)
# Define o diretório base do script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_BRUTOS_PATH = os.path.join(BASE_DIR, 'dados_brutos')
PROCESSADOS_PATH = os.path.join(BASE_DIR, 'dados_processados')

# --- ALTERAÇÃO AQUI: DOIS DICIONÁRIOS ---
# 1. Dicionário Principal: Define o schema final (269 colunas e tipos)
DICIONARIO_PRINCIPAL_PATH = os.path.join(BASE_DIR, 'dicionario_colunas_269_COM_TIPOS.xlsx') 
# 2. Dicionário de Mapeamento: Contém todas as variações de nomes originais -> SQL
DICIONARIO_MAPA_PATH = os.path.join(BASE_DIR, 'dicionario_colunas_269_all.xlsx') 
# --- FIM DA ALTERAÇÃO ---

LOG_FILE_PATH = os.path.join(BASE_DIR, 'processamento_log.txt')

# Constantes para deduplicação
COLUNAS_CHAVE = [
    'cnpj',
    'ano_referencia',
    'periodo_referencia',
    'razao_social_nome_fantasia'
]
COLUNA_DATA = 'data_envio'

# Mapeamento de abreviações para nomes (usado para gerar nomes de arquivos e planilhas)
ESTADOS_MAPA = {
    'al': 'Alagoas',
    'am': 'Amazonas',
    'ap': 'Amapá',
    'ba': 'Bahia',
    'ce': 'Ceará',
    'df': 'Distrito Federal',
    'es': 'Espírito Santo',
    'go': 'Goiás',
    'hm': 'Hemominas',
    'ma': 'Maranhão',
    'mg': 'Minas Gerais',
    'ms': 'Mato Grosso do Sul',
    'mt': 'Mato Grosso',
    'pa': 'Pará',
    'pb': 'Paraíba',
    'pe': 'Pernambuco',
    'pi': 'Piauí',
    'pr': 'Paraná',
    'rj': 'Rio de Janeiro',
    'rn': 'Rio Grande do Norte',
    'ro': 'Rondônia',
    'rr': 'Roraima',
    'rs': 'Rio Grande do Sul',
    'sc': 'Santa Catarina',
    'se': 'Sergipe',
    'sp': 'São Paulo',
    'to': 'Tocantins',
}

ESTADOS_PLANILHA = {
    'al': 'HEMOPROD - ALAGOAS',
    'am': 'HEMOPROD - AMAZONAS',
    'ap': 'HEMOPROD - AMAPA',
    'ba': 'HEMOPROD - BAHIA',
    'ce': 'Planilha1',
    'df': 'HEMOPROD - DISTRITOFEDERAL',
    'es': 'HEMOPROD - ESPIRITOSANTO',
    'go': 'HEMOPROD - GOIAS',
    'hm': 'HEMOPROD - HEMOMINAS',
    'ma': 'HEMOPROD - MARANHAO',
    'mg': 'HEMOPROD - MINASGERAIS',
    'ms': 'HEMOPROD - MATOGROSSODOSUL',
    'mt': 'HEMOPROD - MATOGROSSO',
    'pa': 'HEMOPROD - PARA',
    'pb': 'HEMOPROD - PARAIBA',
    'pe': 'HEMOPROD - PERNAMBUCO',
    'pi': 'HEMOPROD - PIAUI',
    'pr': 'HEMOPROD - PARANA',
    'rj': 'Hemoprod_RJ',
    'rn': 'HEMOPROD - RIOGRANDEDONORTE',
    'ro': 'HEMOPROD - RONDONIA',
    'rr': 'HEMOPROD - RORAIMA',
    'rs': 'HEMOPROD - RIOGRANDEDOSUL',
    'sc': 'HEMOPROD - SANTACATARINA',
    'se': 'HEMOPROD - SERGIPE',
    'sp': 'Hemoprod_SP',
    'to': 'HEMOPROD - TOCANTINS',
}


# --- 2. Funções Auxiliares ---

def setup_logging():
    """Configura o sistema de logging para salvar em arquivo."""
    logging.basicConfig(
        filename=LOG_FILE_PATH,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8',
        filemode='w'  # 'w' para sobrescrever o log a cada execução
    )
    # Adiciona também o log no console
    logging.getLogger().addHandler(logging.StreamHandler())


def gerar_lista_arquivos() -> List[Dict[str, str]]:
    """
    Gera o dicionário de lista com os arquivos e planilhas a processar.
    """
    arquivos_para_processar = []
    
    for abrev, estado in ESTADOS_MAPA.items():
        
        # 1. Define o nome do ARQUIVO
        if abrev == 'hm':
            arquivo_bruto = 'Hemoprod_Hemominas.xlsx'
        else:
            arquivo_bruto = f'Hemoprod_{abrev.upper()}.xlsx'

        # 2. Busca o nome da PLANILHA
        planilha = ESTADOS_PLANILHA.get(abrev) 
        
        if not planilha:
            logging.warning(f"Nome da planilha não encontrado em ESTADOS_PLANILHA para a abreviação: '{abrev}'. Pulando este arquivo.")
            continue

        # 3. Define o nome do arquivo de SAÍDA
        arquivo_processado = f'hemoprod_{abrev.lower()}.xlsx'

        arquivos_para_processar.append({
            'arquivo_bruto': arquivo_bruto,
            'planilha': planilha,
            'arquivo_processado': arquivo_processado
        })
        
    return arquivos_para_processar


def carregar_dicionario(caminho_dicionario: str) -> pd.DataFrame:
    """Carrega e limpa o dicionário de colunas."""
    logging.info(f"Carregando dicionário de {caminho_dicionario}...")
    dicionario = pd.read_excel(caminho_dicionario)
    
    # Limpeza dos nomes originais no dicionário (essencial para o 'match')
    if 'nome_original' in dicionario.columns:
        dicionario['nome_original'] = dicionario['nome_original'].astype(str).str.strip().str.replace('\xa0', ' ')
    else:
        raise KeyError("Coluna 'nome_original' não encontrada no dicionário.")
        
    if 'nome_sql' not in dicionario.columns:
        raise KeyError("Coluna 'nome_sql' não encontrada no dicionário.")
        
    # Carrega e limpa a coluna de tipos (novo requisito)
    if 'tipo_dados' in dicionario.columns:
        dicionario['tipo_dados'] = dicionario['tipo_dados'].astype(str).str.strip().str.lower()
        # Garante 'object' como padrão se o tipo estiver vazio ou for 'nan'
        dicionario['tipo_dados'] = dicionario['tipo_dados'].replace('nan', 'object') 
        dicionario['tipo_dados'] = dicionario['tipo_dados'].fillna('object')
    else:
        # Se for o dicionário de mapeamento e não tiver tipos, assumimos 'object' e seguimos.
        if 'all.xlsx' not in caminho_dicionario:
            raise KeyError("Coluna 'tipo_dados' não encontrada no dicionário principal.")
        dicionario['tipo_dados'] = 'object'
        
    logging.info(f"Dicionário {os.path.basename(caminho_dicionario)} carregado e limpo com sucesso.")
    return dicionario


def processar_arquivo(
    info_arquivo: Dict[str, str],
    df_dicionario: pd.DataFrame,
    mapa_renomeacao: Dict[str, str],
    colunas_sql_desejadas: Set[str]
):
    """
    Executa o pipeline completo de processamento para um único arquivo.
    """
    arquivo_dados_path = os.path.join(DADOS_BRUTOS_PATH, info_arquivo['arquivo_bruto'])
    nome_planilha = info_arquivo['planilha']
    log_prefix = f"[{info_arquivo['arquivo_bruto']}]"

    logging.info(f"\n{'-'*30}\n{log_prefix} Iniciando processamento...")

    try:
        # --- 1. Carregar Dados ---
        if not os.path.exists(arquivo_dados_path):
            logging.warning(f"{log_prefix} Arquivo não encontrado em: {arquivo_dados_path}. Pulando.")
            return

        # Tentativa de leitura do Excel (pode falhar com KeyboardInterrupt em arquivos grandes/corrompidos)
        try:
            df = pd.read_excel(arquivo_dados_path, sheet_name=nome_planilha)
        except Exception as e:
            # Captura erros de leitura de I/O, corrupção, ou interrupção.
            logging.error(f"{log_prefix} Falha CRÍTICA ao carregar o arquivo {arquivo_dados_path} | {nome_planilha}: {e}. Pulando.")
            return

        # (MÉTRICA) Contagens Iniciais
        col_count_original = len(df.columns)
        row_count_original = len(df)
        logging.info(f"{log_prefix} (Métrica) Colunas Originais: {col_count_original}")
        logging.info(f"{log_prefix} (Métrica) Linhas Originais: {row_count_original}")

        # --- 2. Limpeza e Renomeação ---
        # 2.1. Limpeza inicial de espaços em branco e caracteres invisíveis
        mapa_limpeza = {col: col.strip().replace('\xa0', ' ') for col in df.columns}
        df.rename(columns=mapa_limpeza, inplace=True)
        
        # 2.2. Aplica o mapa de renomeação abrangente (mapa_renomeacao é carregado do dicionário 'all')
        df.rename(columns=mapa_renomeacao, inplace=True)
        
        # --- REMOÇÃO DO BLOCO DE CORREÇÃO DINÂMICA ANTERIOR ---
        # A coluna longa deve ser mapeada pelo novo 'dicionario_colunas_269_all.xlsx'
        # --- FIM DA REMOÇÃO ---

        colunas_apos_renomeacao = set(df.columns)
        logging.info(f"{log_prefix} Colunas limpas e renomeadas.")

        # --- 3. Aplicação de Tipos (Baseado no Dicionário PRINCIPAL) ---
        logging.info(f"{log_prefix} Iniciando aplicação de tipos definidos...")
        mapa_tipos = pd.Series(df_dicionario['tipo_dados'].values, index=df_dicionario['nome_sql']).to_dict()

        for col in df.columns:
            # Só aplica tipo em colunas que estão no padrão SQL e que são desejadas
            if col not in colunas_sql_desejadas:
                continue 

            tipo_desejado = mapa_tipos.get(col, 'object')

            try:
                if tipo_desejado in ('int', 'integer', 'int64'):
                    
                    # 1. Pré-limpeza: Remove vírgulas e pontos se a coluna for string
                    if df[col].dtype == 'object':
                        # Remove separadores de milhares (',' e '.') para valores que DEVEM ser inteiros
                        df[col] = df[col].astype(str).str.replace(r'[.,]', '', regex=True)

                    # 2. Converte para numérico
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 3. Força a conversão para Int64, arredondando (resolve o cast inseguro)
                    df[col] = df[col].round(0).astype('Int64')
                
                elif tipo_desejado in ('float', 'decimal', 'float64'):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].astype('float64')

                elif tipo_desejado in ('datetime', 'date', 'datetime64[ns]'):
                    df[col] = pd.to_datetime(df[col], errors='coerce')

                elif tipo_desejado in ('string', 'text', 'object'):
                    df[col] = df[col].astype('object')

            except Exception as e:
                logging.warning(f"{log_prefix} Falha ao converter coluna '{col}' para {tipo_desejado}: {e}. Mantendo como 'object'.")
                try:
                    df[col] = df[col].astype('object')
                except Exception as e_obj:
                    logging.error(f"{log_prefix} Falha CRÍTICA ao forçar '{col}' para 'object': {e_obj}")
        
        logging.info(f"{log_prefix} Aplicação de tipos concluída.")
        
        # --- 4. Análise de Schema (Colunas Faltantes/A Mais) ---
        colunas_faltantes = list(colunas_sql_desejadas - colunas_apos_renomeacao)
        colunas_a_mais = list(colunas_apos_renomeacao - colunas_sql_desejadas)

        # (MÉTRICA) Mudanças de Schema
        logging.info(f"{log_prefix} (Métrica) Colunas Adicionadas (Faltantes): {len(colunas_faltantes)}")
        if colunas_faltantes:
             logging.info(f"{log_prefix}      -> {colunas_faltantes}")
        logging.info(f"{log_prefix} (Métrica) Colunas Removidas (A Mais): {len(colunas_a_mais)}")
        if colunas_a_mais:
             logging.info(f"{log_prefix}      -> {colunas_a_mais}")

        # --- 5. Padronização do Schema ---
        
        # 5.1. REMOVE Colunas a Mais
        if colunas_a_mais:
            colunas_para_dropar = [col for col in colunas_a_mais if col in df.columns]
            df.drop(columns=colunas_para_dropar, inplace=True)

        # 5.2. ADICIONA Colunas Faltantes (OTIMIZADO com concat)
        if colunas_faltantes:
            logging.info(f"{log_prefix} Adicionando colunas faltantes de forma otimizada...")

            # 1. Cria um DataFrame auxiliar com as colunas faltantes e valores NaN
            df_faltantes = pd.DataFrame(index=df.index, columns=colunas_faltantes)
            
            dicionario_faltante = df_dicionario[df_dicionario['nome_sql'].isin(colunas_faltantes)]
            
            # 2. Aplica o tipo correto a cada coluna no DataFrame auxiliar
            for col_sql in colunas_faltantes:
                tipo_desejado_row = dicionario_faltante[dicionario_faltante['nome_sql'] == col_sql]
                
                if not tipo_desejado_row.empty:
                    tipo_desejado = tipo_desejado_row['tipo_dados'].iloc[0]

                    try:
                        if tipo_desejado in ('int', 'integer', 'int64'):
                            df_faltantes[col_sql] = df_faltantes[col_sql].astype('Int64') 
                        elif tipo_desejado in ('float', 'decimal', 'float64'):
                            df_faltantes[col_sql] = df_faltantes[col_sql].astype('float64')
                        elif tipo_desejado in ('datetime', 'date', 'datetime64[ns]'):
                            df_faltantes[col_sql] = pd.to_datetime(df_faltantes[col_sql])
                        else: 
                            df_faltantes[col_sql] = df_faltantes[col_sql].astype('object')
                    except Exception as e:
                         logging.warning(f"{log_prefix} Falha ao converter tipo da coluna adicionada '{col_sql}' para {tipo_desejado}: {e}")
                         df_faltantes[col_sql] = df_faltantes[col_sql].astype('object') # Fallback seguro
                else:
                    df_faltantes[col_sql] = df_faltantes[col_sql].astype('object')

            # 3. Concatena o DataFrame principal com o auxiliar (operação única e eficiente)
            df = pd.concat([df, df_faltantes], axis=1)


        # 5.3. Reordena as colunas
        colunas_finais_ordenadas = [col for col in df_dicionario['nome_sql'] if col in df.columns]
        df = df[colunas_finais_ordenadas]
        
        logging.info(f"{log_prefix} Schema padronizado.")

        # (MÉTRICA) Colunas Finais
        col_count_final = len(df.columns)
        logging.info(f"{log_prefix} (Métrica) Colunas Finais: {col_count_final}")

        # --- 6. Deduplicação ---
        colunas_necessarias_dedup = COLUNAS_CHAVE + [COLUNA_DATA]
        
        if not all(col in df.columns for col in colunas_necessarias_dedup):
            colunas_faltantes_dedup = [col for col in colunas_necessarias_dedup if col not in df.columns]
            logging.error(f"{log_prefix} ERRO: Colunas necessárias para deduplicação não encontradas: {colunas_faltantes_dedup}. Pulando etapa de deduplicação.")
            df_deduplicado = df
        else:
            # Garante que a coluna de data seja datetime antes de ordenar
            if not pd.api.types.is_datetime64_any_dtype(df[COLUNA_DATA]):
                 logging.warning(f"{log_prefix} Coluna '{COLUNA_DATA}' não é datetime. Tentando converter para deduplicação.")
                 df[COLUNA_DATA] = pd.to_datetime(df[COLUNA_DATA], errors='coerce')

            df_ordenado = df.sort_values(by=COLUNA_DATA, ascending=True)
            
            mascara_duplicatas = df_ordenado.duplicated(subset=COLUNAS_CHAVE, keep='last')
            df_deduplicado = df_ordenado[~mascara_duplicatas]
            logging.info(f"{log_prefix} Deduplicação concluída.")

        # (MÉTRICA) Linhas Finais
        row_count_final = len(df_deduplicado)
        logging.info(f"{log_prefix} (Métrica) Linhas Finais (Pós-filtro): {row_count_final}")

        # --- 7. Salvar ---
        output_path = os.path.join(PROCESSADOS_PATH, info_arquivo['arquivo_processado'])
        df_deduplicado.to_excel(output_path, index=False)
        
        logging.info(f"{log_prefix} ✅ Processamento concluído. Salvo em: {output_path}")

    except Exception as e:
        # (MÉTRICA) Erro
        logging.error(f"{log_prefix} FALHA NO PROCESSAMENTO: {e}", exc_info=True)


# --- 3. Execução Principal ---

def main():
    """
    Orquestra o processo de ETL.
    """
    setup_logging()
    logging.info("--- INÍCIO DO SCRIPT DE PROCESSAMENTO ---")
    
    # Garante que o diretório de saída exista
    os.makedirs(PROCESSADOS_PATH, exist_ok=True)
    
    # 1. Gera a lista de arquivos
    arquivos_para_processar = gerar_lista_arquivos()
    if not arquivos_para_processar:
        logging.warning("Nenhum arquivo configurado para processamento.")
        return

    # 2. Carrega os Dicionários
    try:
        # 2.1. Carrega o dicionário PRINCIPAL (para tipos e 269 colunas desejadas)
        dicionario_principal = carregar_dicionario(DICIONARIO_PRINCIPAL_PATH)
        df_dicionario = dicionario_principal # Passado para processar_arquivo para tipos e schema
        colunas_sql_desejadas = set(df_dicionario['nome_sql'].tolist())
        logging.info(f"Dicionário Principal carregado. Colunas desejadas para schema final: {len(colunas_sql_desejadas)}")


        # 2.2. Carrega o dicionário de MAPA (para renomeação abrangente)
        dicionario_mapa = carregar_dicionario(DICIONARIO_MAPA_PATH)
        # O mapa é construído a partir do novo dicionário abrangente
        mapa_renomeacao = pd.Series(dicionario_mapa['nome_sql'].values, index=dicionario_mapa['nome_original']).to_dict()
        logging.info(f"Dicionário de Mapeamento carregado. {len(mapa_renomeacao)} mapeamentos detectados.")

    except Exception as e:
        logging.critical(f"Falha ao carregar os dicionários: {e}. Abortando script.")
        return

    # 3. Loop de Processamento
    logging.info(f"--- Iniciando processamento de {len(arquivos_para_processar)} arquivos ---")
    
    for info_arquivo in arquivos_para_processar:
        processar_arquivo(
            info_arquivo,
            df_dicionario,
            mapa_renomeacao,
            colunas_sql_desejadas
        )

    logging.info("--- PROCESSAMENTO CONCLUÍDO ---")


if __name__ == "__main__":
    main()