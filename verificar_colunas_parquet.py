import pandas as pd

df = pd.read_parquet('dados_processados/hemoprod_nacional.parquet')
print(df.columns.tolist())