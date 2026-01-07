"""
Script para analisar transfusões até dezembro de 2024
"""
import pandas as pd
import os

# Carregar dados
parquet_path = "dados_processados/base_nacional.parquet"

if os.path.exists(parquet_path):
    df = pd.read_parquet(parquet_path, engine="pyarrow")
    print(f"✓ Dados carregados: {len(df)} registros")
else:
    print("❌ Arquivo não encontrado:", parquet_path)
    exit(1)

# Filtrar até dezembro de 2024
if "ano_referencia" in df.columns:
    df_filtrado = df[df["ano_referencia"] <= 2024].copy()
    print(f"✓ Registros até 2024: {len(df_filtrado)}")
else:
    print("⚠ Coluna 'ano_referencia' não encontrada")
    df_filtrado = df.copy()

# Definir todas as categorias de transfusões
transfusoes_categorias = {
    "Sangue Total": "tranfusoes_sangue_total_total",
    "Plasma Fresco Congelado": "tranfusoes_plasma_fresco_congelado_total",
    "Plasma Comum": "tranfusoes_plasma_comum_total",
    "Concentrado de Hemácias": "tranfusoes_concentrado_de_hemacias_total",
    "Concentrado de Hemácias sem Buffy Coat": "tranfusoes_concentrado_de_hemacias_sem_buffy_coat_total",
    "Concentrado de Plaquetas": "tranfusoes_concentrado_de_plaquetas_total",
    "Concentrado de Plaquetas de Aférese": "tranfusoes_concentrado_de_plaquetas_de_aferese_total",
    "Concentrado de Leucócitos": "tranfusoes_concentrado_de_leucocitos_total",
    "Crioprecipitado": "tranfusoes_crioprecipitado_total",
    "Concentrado de Plaquetas sem Buffy Coat": "tranfusoes_concentrado_de_plaquetas_sem_buffy_coat_total",
}

print("\n" + "="*80)
print("TRANSFUSÕES REALIZADAS ATÉ DEZEMBRO DE 2024")
print("="*80 + "\n")

# Calcular totais
total_geral = 0
resultados = []

for nome_categoria, coluna in transfusoes_categorias.items():
    if coluna in df_filtrado.columns:
        total = df_filtrado[coluna].sum()
        total_geral += total
        resultados.append({
            "Categoria": nome_categoria,
            "Total": int(total)
        })
        print(f"{nome_categoria:50s}: {int(total):>15,}")
    else:
        print(f"{nome_categoria:50s}: Coluna não encontrada")

print("\n" + "-"*80)
print(f"{'TOTAL GERAL':50s}: {int(total_geral):>15,}")
print("="*80 + "\n")

# Análise por ambiente (ambulatorial vs hospitalar)
print("\nANÁLISE POR AMBIENTE (Ambulatorial vs Hospitalar)")
print("="*80 + "\n")

for nome_categoria, coluna_total in transfusoes_categorias.items():
    # Obter nome base da coluna (sem o _total)
    nome_base = coluna_total.replace("_total", "")
    
    col_ambulatorial = f"{nome_base}_ambulatorial"
    col_hospitalar = f"{nome_base}_hospitalar"
    
    if col_ambulatorial in df_filtrado.columns and col_hospitalar in df_filtrado.columns:
        amb = int(df_filtrado[col_ambulatorial].sum())
        hosp = int(df_filtrado[col_hospitalar].sum())
        total = amb + hosp
        
        if total > 0:
            pct_amb = (amb / total) * 100
            pct_hosp = (hosp / total) * 100
            
            print(f"\n{nome_categoria}:")
            print(f"  Ambulatorial: {amb:>12,} ({pct_amb:>5.1f}%)")
            print(f"  Hospitalar:   {hosp:>12,} ({pct_hosp:>5.1f}%)")
            print(f"  Total:        {total:>12,}")

# Análise por ano
print("\n\n" + "="*80)
print("TRANSFUSÕES POR ANO")
print("="*80 + "\n")

if "ano_referencia" in df_filtrado.columns:
    anos = sorted(df_filtrado["ano_referencia"].dropna().unique())
    
    for ano in anos:
        df_ano = df_filtrado[df_filtrado["ano_referencia"] == ano]
        total_ano = 0
        
        print(f"\nANO {int(ano)}:")
        print("-" * 80)
        
        for nome_categoria, coluna in transfusoes_categorias.items():
            if coluna in df_ano.columns:
                total = df_ano[coluna].sum()
                total_ano += total
                if total > 0:
                    print(f"  {nome_categoria:48s}: {int(total):>12,}")
        
        print(f"\n  {'TOTAL DO ANO':48s}: {int(total_ano):>12,}")

print("\n" + "="*80)
print("✓ Análise concluída!")
print("="*80)

# Salvar resultados em CSV
df_resultados = pd.DataFrame(resultados)
output_file = "dados_processados/transfusoes_ate_dez_2024.csv"
df_resultados.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"\n💾 Resultados salvos em: {output_file}")
