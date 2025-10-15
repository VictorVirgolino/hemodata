import pandas as pd
import os
import re
import unicodedata

def clean_col_name(col_name):
    if not isinstance(col_name, str):
        col_name = str(col_name)
    nfkd_form = unicodedata.normalize('NFKD', col_name)
    ascii_name = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    lower_name = ascii_name.lower()
    no_special_chars = re.sub(r'[^a-z0-9 ]', '', lower_name)
    single_space = re.sub(r'\s+', ' ', no_special_chars).strip()
    return single_space

def uniquify_cols(df_columns):
    seen = {}
    new_columns = []
    for col in df_columns:
        if col in seen:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_columns.append(col)
    return new_columns

# Carregar o dicionário de colunas
dicionario_df = pd.read_excel('dicionario_colunas.xlsx')
dicionario_df['nome_original_limpo'] = dicionario_df['nome_original'].apply(clean_col_name)
rename_map = dict(zip(dicionario_df['nome_original_limpo'], dicionario_df['nome_sql']))

# Caminhos
dados_brutos_path = 'dados_brutos'
dados_processados_path = 'dados_processados'

# Lista para armazenar os dataframes processados
all_dfs = []

# Listar arquivos na pasta dados_brutos
files = [f for f in os.listdir(dados_brutos_path) if f.endswith('.xlsx') and not f.startswith('~')]

for file in files:
    file_path = os.path.join(dados_brutos_path, file)
    try:
        # Ler o arquivo excel
        df = pd.read_excel(file_path)

        # Limpar e tornar as colunas únicas
        df.columns = [clean_col_name(col) for col in df.columns]
        df.columns = uniquify_cols(df.columns)
        
        # Renomear usando o mapa limpo
        df.rename(columns=rename_map, inplace=True)

        # Adicionar coluna 'uf'
        uf = file.split('_')[1].split('.')[0]
        df['uf'] = uf

        # Adicionar dataframe à lista
        all_dfs.append(df)
        print(f'Arquivo {file} processado com sucesso.')

    except Exception as e:
        print(f'Erro ao processar o arquivo {file}: {e}')

# Concatenar todos os dataframes
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)

    # Converter todas as colunas não numéricas para string
    for col in final_df.columns:
        if final_df[col].dtype not in ['int64', 'float64']:
            final_df[col] = final_df[col].astype(str)

    # Salvar em parquet
    output_path = os.path.join(dados_processados_path, 'hemoprod_nacional.parquet')
    final_df.to_parquet(output_path)
    print(f'\nArquivo consolidado salvo em: {output_path}')
else:
    print('\nNenhum arquivo foi processado.')