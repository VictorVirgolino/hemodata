import pandas as pd
import logging
import os
from pathlib import Path
from datetime import datetime
import numpy as np

# ==================== CONFIGURAÇÕES DE CAMINHOS ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_PROCESSADOS_PATH = os.path.join(BASE_DIR, "dados_processados")
OUTPUT_PARQUET_PATH = os.path.join(BASE_DIR, "base_nacional.parquet")
LOG_FILE_PATH = os.path.join(BASE_DIR, "consolidacao_nacional_log.txt")
DICIONARIO_TIPOS_PATH = os.path.join(BASE_DIR, "dicionario_colunas_269_COM_TIPOS.xlsx")

# ==================== CONFIGURAÇÃO DE LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==================== FUNÇÕES ====================
def carregar_dicionario_tipos(caminho_dicionario):
    """
    Carrega o dicionário de tipos de dados.
    Retorna um dict: {nome_sql: tipo_dados}
    """
    try:
        logger.info(f"Carregando dicionário de tipos: {caminho_dicionario}")
        df_dict = pd.read_excel(caminho_dicionario)
        
        # Criar mapeamento nome_sql -> tipo_dados
        tipo_map = dict(zip(df_dict['nome_sql'], df_dict['tipo_dados']))
        logger.info(f"✓ Dicionário carregado: {len(tipo_map)} colunas mapeadas")
        
        return tipo_map
    except Exception as e:
        logger.error(f"Erro ao carregar dicionário de tipos: {str(e)}")
        return {}

def converter_tipo_coluna(serie, tipo_esperado):
    """
    Converte uma série para o tipo esperado de forma segura.
    """
    try:
        tipo_lower = str(tipo_esperado).lower()
        
        # Tipos de data/timestamp
        if any(x in tipo_lower for x in ['date', 'timestamp', 'datetime']):
            return pd.to_datetime(serie, errors='coerce')
        
        # Tipos numéricos inteiros
        elif any(x in tipo_lower for x in ['int', 'integer', 'bigint', 'smallint']):
            return pd.to_numeric(serie, errors='coerce').astype('Int64')
        
        # Tipos numéricos decimais
        elif any(x in tipo_lower for x in ['float', 'double', 'decimal', 'numeric', 'real']):
            return pd.to_numeric(serie, errors='coerce').astype('float64')
        
        # Tipos booleanos
        elif 'bool' in tipo_lower:
            return serie.astype('boolean')
        
        # Tipos texto (padrão)
        else:
            return serie.astype('string')
            
    except Exception as e:
        logger.warning(f"Erro ao converter coluna para {tipo_esperado}: {str(e)}")
        return serie.astype('string')  # Fallback para string

def aplicar_tipos_corretos(df, tipo_map):
    """
    Aplica os tipos corretos ao DataFrame baseado no dicionário.
    """
    logger.info("\nAplicando tipos corretos às colunas...")
    colunas_convertidas = 0
    colunas_com_erro = 0
    
    for coluna in df.columns:
        if coluna == 'arquivo_origem':
            continue
            
        if coluna in tipo_map:
            tipo_esperado = tipo_map[coluna]
            try:
                df[coluna] = converter_tipo_coluna(df[coluna], tipo_esperado)
                colunas_convertidas += 1
                
                if colunas_convertidas % 50 == 0:
                    logger.info(f"  Convertidas {colunas_convertidas} colunas...")
                    
            except Exception as e:
                logger.warning(f"  Erro ao converter coluna '{coluna}' para {tipo_esperado}: {str(e)}")
                colunas_com_erro += 1
                # Manter como string em caso de erro
                df[coluna] = df[coluna].astype('string')
        else:
            logger.warning(f"  Coluna '{coluna}' não encontrada no dicionário de tipos")
            # Converter para string por segurança
            df[coluna] = df[coluna].astype('string')
    
    logger.info(f"✓ Conversão concluída:")
    logger.info(f"  - Colunas convertidas com sucesso: {colunas_convertidas}")
    logger.info(f"  - Colunas com erro: {colunas_com_erro}")
    
    return df

def consolidar_arquivos_excel(input_folder, output_file, dicionario_tipos_path):
    """
    Consolida todos os arquivos Excel de uma pasta em um único arquivo Parquet.
    """
    try:
        logger.info("=" * 80)
        logger.info("INICIANDO CONSOLIDAÇÃO NACIONAL")
        logger.info("=" * 80)
        
        # Carregar dicionário de tipos
        tipo_map = carregar_dicionario_tipos(dicionario_tipos_path)
        
        # Buscar todos os arquivos Excel
        input_path = Path(input_folder)
        excel_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls"))
        
        if not excel_files:
            logger.warning(f"Nenhum arquivo Excel encontrado em: {input_folder}")
            return
        
        logger.info(f"Encontrados {len(excel_files)} arquivos Excel para consolidar")
        
        # Lista para armazenar os DataFrames
        dataframes = []
        
        # Ler cada arquivo
        for idx, file_path in enumerate(excel_files, 1):
            try:
                logger.info(f"[{idx}/{len(excel_files)}] Lendo: {file_path.name}")
                df = pd.read_excel(file_path)
                
                # Adicionar coluna com nome do arquivo de origem
                df['arquivo_origem'] = file_path.stem
                
                dataframes.append(df)
                logger.info(f"  ✓ {len(df):,} registros carregados")
                
            except Exception as e:
                logger.error(f"  ✗ Erro ao ler {file_path.name}: {str(e)}")
                continue
        
        if not dataframes:
            logger.error("Nenhum arquivo foi carregado com sucesso")
            return
        
        # Consolidar todos os DataFrames
        logger.info("\nConsolidando dados...")
        df_consolidado = pd.concat(dataframes, ignore_index=True)
        
        logger.info(f"Total de registros consolidados: {len(df_consolidado):,}")
        logger.info(f"Total de colunas: {len(df_consolidado.columns)}")
        
        # Aplicar tipos corretos
        if tipo_map:
            df_consolidado = aplicar_tipos_corretos(df_consolidado, tipo_map)
        else:
            logger.warning("Dicionário de tipos não disponível. Convertendo tudo para string...")
            for col in df_consolidado.columns:
                if col != 'arquivo_origem':
                    df_consolidado[col] = df_consolidado[col].astype('string')
        
        # Salvar como Parquet
        logger.info(f"\nSalvando arquivo Parquet: {output_file}")
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df_consolidado.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Informações do arquivo gerado
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Arquivo salvo com sucesso!")
        logger.info(f"  Tamanho: {file_size_mb:.2f} MB")
        logger.info(f"  Registros: {len(df_consolidado):,}")
        logger.info(f"  Colunas: {len(df_consolidado.columns)}")
        
        # Resumo por arquivo de origem
        logger.info("\nResumo por arquivo de origem:")
        resumo = df_consolidado['arquivo_origem'].value_counts().sort_index()
        for arquivo, count in resumo.items():
            logger.info(f"  {arquivo}: {count:,} registros")
        
        # Mostrar tipos finais das colunas
        logger.info("\nTipos de dados finais (amostra):")
        for col in list(df_consolidado.columns)[:10]:
            logger.info(f"  {col}: {df_consolidado[col].dtype}")
        
        logger.info("=" * 80)
        logger.info("CONSOLIDAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Erro na consolidação: {str(e)}", exc_info=True)
        raise

# ==================== EXECUÇÃO ====================
if __name__ == "__main__":
    start_time = datetime.now()
    
    try:
        consolidar_arquivos_excel(
            DADOS_PROCESSADOS_PATH, 
            OUTPUT_PARQUET_PATH,
            DICIONARIO_TIPOS_PATH
        )
        
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
    
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"\nTempo total de execução: {duration}")