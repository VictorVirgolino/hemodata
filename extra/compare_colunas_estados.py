
import pandas as pd
import os

# --- Configuração ---
# Caminho para a pasta com os arquivos de dados brutos
dados_brutos_path = r'd:\Documentos\STTP\hemoce\src\dados_brutos'

# Arquivo que servirá como padrão de colunas
arquivo_padrao_path = os.path.join(dados_brutos_path, 'Hemoprod_CE.xlsx')

# Lista de arquivos dos outros estados para comparar com o padrão
arquivos_estados_a_comparar = [
    'Hemoprod_AL.xlsx',
    'Hemoprod_AM.xlsx',
    'Hemoprod_BA.xlsx',
    'hemoprod_ultimos_envios.xlsx' # Adicionando o arquivo que você mencionou
]

print(f"Usando '{os.path.basename(arquivo_padrao_path)}' como padrão de colunas.")
print("=" * 60)

try:
    # Carrega o arquivo padrão e obtém o conjunto de suas colunas
    df_padrao = pd.read_excel(arquivo_padrao_path, nrows=0)
    colunas_padrao = set(df_padrao.columns)
    print(f"O padrão tem {len(colunas_padrao)} colunas.")

    # Itera sobre cada arquivo de estado para fazer a comparação
    for nome_arquivo_estado in arquivos_estados_a_comparar:
        # Alguns arquivos podem estar em 'src', outros em 'dados_brutos'
        path_tentativa1 = os.path.join(dados_brutos_path, nome_arquivo_estado)
        path_tentativa2 = os.path.join(r'd:\Documentos\STTP\hemoce\src', nome_arquivo_estado)

        if os.path.exists(path_tentativa1):
            arquivo_estado_path = path_tentativa1
        elif os.path.exists(path_tentativa2):
            arquivo_estado_path = path_tentativa2
        else:
            print(f"\n--- AVISO: Arquivo '{nome_arquivo_estado}' não encontrado. Pulando. ---")
            continue
            
        print(f"\n--- Comparando com '{nome_arquivo_estado}' ---")

        # Carrega o arquivo do estado e obtém suas colunas
        df_estado = pd.read_excel(arquivo_estado_path, nrows=0)
        colunas_estado = set(df_estado.columns)
        
        # Lógica de comparação que você forneceu
        colunas_faltantes = list(colunas_padrao - colunas_estado)
        colunas_a_mais = list(colunas_estado - colunas_padrao)

        print(f"Colunas neste estado: {len(colunas_estado)}")

        if colunas_faltantes:
            print(f"Colunas FALTANTES ({len(colunas_faltantes)}): {colunas_faltantes}")
        else:
            print("Nenhuma coluna do padrão está faltando neste estado.")

        if colunas_a_mais:
            print(f"Colunas A MAIS ({len(colunas_a_mais)}): {colunas_a_mais}")
        else:
            print("Nenhuma coluna extra encontrada neste estado.")

except FileNotFoundError:
    print(f"ERRO CRÍTICO: O arquivo padrão '{arquivo_padrao_path}' não foi encontrado.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
