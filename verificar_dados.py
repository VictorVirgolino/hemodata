
import pandas as pd
import os

dados_brutos_path = 'dados_brutos'
files = [f for f in os.listdir(dados_brutos_path) if f.endswith('.xlsx') and not f.startswith('~')]

for file in files:
    file_path = os.path.join(dados_brutos_path, file)
    try:
        df = pd.read_excel(file_path)
        print(f'Arquivo: {file}')
        print('Colunas:', df.columns.tolist())
        print('5 primeiras linhas:')
        print(df.head())
        print('-' * 50)
    except Exception as e:
        print(f'Erro ao ler o arquivo {file}: {e}')
