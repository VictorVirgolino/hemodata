import pandas as pd
import os
import glob

def load_data():
    # Adjust path as script is in src/
    parquet_path = "dados_processados/base_nacional.parquet"
    
    if os.path.exists(parquet_path):
        try:
            df = pd.read_parquet(parquet_path, engine="pyarrow")
            print(f"Loaded from Parquet: {parquet_path}")
            return df
        except Exception as e:
            print(f"Error loading Parquet: {e}")

    print("Parquet not found or error, trying Excel...")
    path = "."
    # Adjust paths for script running in src/
    brutos_files = glob.glob(os.path.join(path, "dados_brutos", "Hemoprod_*.xlsx"))
    processados_files = glob.glob(os.path.join(path, "dados_processados", "hemoprod_*.xlsx"))
    all_files = brutos_files + processados_files

    if not all_files:
        print("No files found.")
        return pd.DataFrame()

    df_list = []
    for file in all_files:
        try:
            df_list.append(pd.read_excel(file))
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not df_list:
        return pd.DataFrame()

    return pd.concat(df_list, ignore_index=True)

df = load_data()


with open("states_output.txt", "w", encoding="utf-8") as f:
    if not df.empty:
        f.write("--- Columns ---\n")
        f.write(str(df.columns.tolist()) + "\n")
        
        if "estado" in df.columns:
            f.write("\n--- Unique values in 'estado' ---\n")
            unique_estados = sorted(df["estado"].dropna().astype(str).unique())
            for val in unique_estados:
                 f.write(f"'{val}'\n")
            
        if "uf" in df.columns:
            f.write("\n--- Unique values in 'uf' ---\n")
            unique_ufs = sorted(df["uf"].dropna().astype(str).unique())
            for val in unique_ufs:
                 f.write(f"'{val}'\n")
    else:
        f.write("DataFrame is empty.\n")

