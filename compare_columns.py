import pandas as pd

def compare_and_write_missing_columns():
    hemoprod_file = 'Hemoprod_CE.xlsx'
    dicionario_file = 'dicionario colunas v6.xlsx'
    original_col_name = 'Coluna (Nome Original)'
    output_file = 'colunas_faltantes.txt'

    try:
        # Load the main data file to get its columns
        df_hemoprod = pd.read_excel(hemoprod_file)
        hemoprod_columns = set(df_hemoprod.columns)

        # Load the dictionary file
        df_dicionario = pd.read_excel(dicionario_file)

        # Check if the specified column exists in the dictionary
        if original_col_name not in df_dicionario.columns:
            print(f"Erro: A coluna '{original_col_name}' não foi encontrada no arquivo '{dicionario_file}'.")
            print(f"Colunas disponíveis: {list(df_dicionario.columns)}")
            return

        dicionario_columns = set(df_dicionario[original_col_name].dropna())

        # Find columns in hemoprod but not in the dictionary
        missing_columns = hemoprod_columns - dicionario_columns

        if not missing_columns:
            print(f"Todas as colunas do arquivo '{hemoprod_file}' estão presentes no arquivo de dicionário.")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Nenhuma coluna faltante encontrada.\n")
            return

        # Write the missing columns to a text file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Colunas do '{hemoprod_file}' que não foram encontradas no dicionário:\n\n")
            for col in sorted(list(missing_columns)):
                f.write(f"- {col}\n")
        
        print(f"A comparação foi concluída. As {len(missing_columns)} colunas faltantes foram listadas no arquivo '{output_file}'.")

    except FileNotFoundError as e:
        print(f"Erro: O arquivo '{e.filename}' não foi encontrado. Verifique se os nomes dos arquivos estão corretos e no mesmo diretório.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    compare_and_write_missing_columns()
