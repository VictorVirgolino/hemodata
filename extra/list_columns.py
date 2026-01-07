import pandas as pd

def save_hemoprod_columns_to_csv():
    excel_file_path = 'Hemoprod_CE.xlsx'
    output_csv_path = 'lista_colunas_hemoprod.csv'
    try:
        # Read the Excel file to get the column names
        df_excel = pd.read_excel(excel_file_path)
        
        # Create a new DataFrame with the column names
        df_columns = pd.DataFrame(df_excel.columns, columns=['Nome da Coluna'])
        
        # Save the new DataFrame to a CSV file
        df_columns.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        
        print(f"A lista de colunas foi salva com sucesso no arquivo '{output_csv_path}'.")
        
    except FileNotFoundError:
        print(f"Erro: O arquivo '{excel_file_path}' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro ao processar o arquivo: {e}")

if __name__ == "__main__":
    save_hemoprod_columns_to_csv()