import pandas as pd

def read_excel_head():
    file_path = 'dicionario colunas v6.xlsx'
    num_rows = 100
    try:
        df = pd.read_excel(file_path, nrows=num_rows)
        print(f"As primeiras {num_rows} linhas do arquivo '{file_path}' são:\n")
        print(df.to_string())
    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro ao ler o arquivo: {e}")

if __name__ == "__main__":
    read_excel_head()

