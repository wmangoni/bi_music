import pandas as pd

letras = ("w", "x", "y")
# Carregar os arquivos CSV em DataFrames separados
df1 = pd.read_csv(letras[0] + "_lyrics.csv", sep="\\", dtype=str, encoding='utf-8', low_memory=False)
df2 = pd.read_csv(letras[1] + "_lyrics.csv", sep="\\", dtype=str, encoding='utf-8', low_memory=False)
df3 = pd.read_csv(letras[2] + "_lyrics.csv", sep="\\", dtype=str, encoding='utf-8', low_memory=False)

# Unir os DataFrames em um único DataFrame
merged_df = pd.concat([df1, df2, df3], ignore_index=True)

merged_df.head(5)

# Salvar o DataFrame unido em um novo arquivo CSV
merged_df.to_csv(letras[0] + letras[1] + letras[2] + "_lyrics.csv", sep="\\", encoding='utf-8', index=False)
