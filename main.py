import os
from typing import Union

from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, Response

import pandas as pd

app = FastAPI()

# Caminho para o arquivo CSV
caminho_arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bi_music.csv')

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

    df_filtrado = df[df[colunm] == name]

    df_page = df_filtrado.iloc[start_index:end_index]
    return Response(content=df_page.to_json(orient='records'), media_type='application/json')


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/songs")
def get_all(page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):

    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    df_page = df.iloc[start_index:end_index]

    df_paginado_filtrado = df_page.iloc[:, [0, 1, 4, 5, 6]]

    return Response(content=df_paginado_filtrado.to_json(orient='records'), media_type='application/json')


@app.get("/songs/{name:path}")
def get_songs(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "SongName", name)

@app.get("/genre/{name:path}")
def get_genre(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "Genre", name)

@app.get("/artist/{name:path}")
def read_item(name: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=10, gt=0)):
    return paginateDf(page, per_page, "Artist", name)