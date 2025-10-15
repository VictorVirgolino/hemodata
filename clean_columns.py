
'''
Este script realiza o pré-processamento das colunas de um arquivo Excel.
Ele lê um arquivo de dados e um dicionário de colunas, limpa os nomes das colunas do arquivo de dados 
removendo espaços extras, quebras de linha e convertendo para minúsculas.
Em seguida, ele gera e salva um novo script Python que aplica a limpeza e o mapeamento de colunas.
'''
import pandas as pd
import re

def clean_text(text):
    '''Remove espaços extras, quebras de linha e converte para minúsculas.'''
    if isinstance(text, str):
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ')
        return text.lower()
    return text

def create_rename_script(data_file, dictionary_file, output_script_path):
    '''
    Cria um script Python para renomear as colunas de um arquivo de dados com base em um dicionário.

    Args:
        data_file (str): O caminho para o arquivo de dados Excel.
        dictionary_file (str): O caminho para o arquivo de dicionário Excel.
        output_script_path (str): O caminho para salvar o script Python gerado.
    '''
    # Carregar os dados e o dicionário
    df_data = pd.read_excel(data_file)
    df_dict = pd.read_excel(dictionary_file)

    # Limpar as colunas do DataFrame de dados
    cleaned_columns = {col: clean_text(col) for col in df_data.columns}
    df_data.rename(columns=cleaned_columns, inplace=True)

    # Criar o mapeamento de colunas a partir do dicionário
    # Certifique-se de que as colunas no dicionário também estão limpas
    df_dict['Nome Original'] = df_dict['Nome Original'].apply(clean_text)
    column_mapping = pd.Series(df_dict['Novo Nome'].values, index=df_dict['Nome Original']).to_dict()

    # Gerar o conteúdo do script
    script_content = f"""
import pandas as pd
import re

def clean_text(text):
    if isinstance(text, str):
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ')
        return text.lower()
    return text

df = pd.read_excel(r'{data_file}')

# Limpa os nomes das colunas do DataFrame
cleaned_columns = {{col: clean_text(col) for col in df.columns}}
df.rename(columns=cleaned_columns, inplace=True)

# Dicionário para renomear as colunas
column_mapping = {column_mapping}

# Renomeia as colunas
df.rename(columns=column_mapping, inplace=True)

# Exibe as 5 primeiras linhas do DataFrame com as colunas renomeadas
print(df.head())

# Exibe as colunas para verificação
print(df.columns)
"""