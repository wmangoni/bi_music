from typing import Union

from fastapi import FastAPI, Query

import pandas as pd

app = FastAPI()

# Caminho para o arquivo CSV
caminho_arquivo = 'bi_music/bi_music.csv'

# Ler o arquivo CSV usando o pandas
df = pd.read_csv(caminho_arquivo, encoding='utf-8')

df = df.drop_duplicates(subset='Lyrics')
df = df.dropna()
df = df.reset_index(drop=True)

def extract_song_name(lyrics_text):
  if lyrics_text:
      return lyrics_text.split("\n")[0]  # Retorna o nome da música se 'Lyrics' não for vazia
  else:                                   
      return "Música sem nome"            # Valor padrão se 'Lyrics' for vazia

df["SongName"] = df["Lyrics"].apply(extract_song_name) 
df['comprimento_letra'] = df['Lyrics'].str.len()
df['ocorrencias_amor_love'] = df['Lyrics'].str.count('amor|love')

# Visualizar as primeiras linhas do DataFrame para garantir que os dados foram carregados corretamente

def paginateDf(page, per_page, colunm, name):
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    df_page = df.iloc[start_index:end_index]

    df_filtrado = df_page[df[colunm] == name]
    return df_filtrado.to_json(orient='records')


@app.get("/songs")
def get_all(page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):

    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    df_page = df.iloc[start_index:end_index]

    df_paginado_filtrado = df_page.iloc[:, [0, 1, 4, 5, 6]]

    return df_paginado_filtrado.to_json(orient='records')


@app.get("/songs/{name}")
def get_songs(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "SongName", name)

@app.get("/genre/{name}")
def get_genre(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "Genre", name)

@app.get("/artist/{name}")
def read_item(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "Artist", name)