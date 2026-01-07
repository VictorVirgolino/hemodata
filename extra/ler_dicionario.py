import pandas as pd

df = pd.read_excel('dicionario_colunas.xlsx')
print(df.to_string())