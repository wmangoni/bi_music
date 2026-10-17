import os
from typing import Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, Response

import pandas as pd

from recomendador import spotify
from recomendador.modelo import PESOS_PADRAO, Recomendador

app = FastAPI()

# Caminho para o arquivo CSV
pasta_projeto = os.path.dirname(os.path.abspath(__file__))
caminho_arquivo = os.path.join(pasta_projeto, 'bi_music.csv')

load_dotenv(os.path.join(pasta_projeto, '.env'))

if not os.path.exists(caminho_arquivo):
    zip_path = os.path.join(pasta_projeto, 'bi_music.zip')
    msg_extra = " Extraia-o executando: unzip bi_music.zip" if os.path.exists(zip_path) else ""
    raise FileNotFoundError(f"Arquivo '{caminho_arquivo}' não encontrado.{msg_extra}")

# Ler o arquivo CSV usando o pandas
df = pd.read_csv(caminho_arquivo, encoding='utf-8')

df = df.drop_duplicates(subset='Lyrics')
df = df.dropna()
df = df.reset_index(drop=True)

# Modelo de recomendação (treina na 1ª execução, ~40s, depois carrega do cache em recomendador/cache/)
recomendador = Recomendador(caminho_arquivo, df_bruto=df)

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


@app.get("/spotify/login", include_in_schema=False)
def spotify_login():
    try:
        return RedirectResponse(spotify.url_login())
    except spotify.ErroSpotify as e:
        raise HTTPException(500, str(e))


@app.get("/callback", include_in_schema=False)
def spotify_callback(code: str = None, state: str = None, error: str = None):
    if error or not code:
        raise HTTPException(400, f'Login no Spotify cancelado ou negado: {error}')
    try:
        spotify.concluir_login(code, state)
    except spotify.ErroSpotify as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(url="/docs#/default/get_recommendations_recommendations_get")


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


@app.get("/recommendations")
def get_recommendations(
    playlist: Union[str, None] = Query(default=None, description="Link, URI ou ID de uma playlist pública do Spotify"),
    musicas: Union[list[str], None] = Query(default=None, description='Sem Spotify: "Artista - Música" (repita o parâmetro para várias)'),
    limit: int = Query(default=10, gt=0, le=100),
    peso_letra: float = Query(default=PESOS_PADRAO['letra'], ge=0, description="1) semelhança das letras"),
    peso_palavra_acorde: float = Query(default=PESOS_PADRAO['palavra_acorde'], ge=0, description="2) palavras associadas aos mesmos acordes (em graus)"),
    peso_ritmo: float = Query(default=PESOS_PADRAO['ritmo'], ge=0, description="3) distância entre acordes em caracteres (ritmo harmônico)"),
    peso_acordes: float = Query(default=PESOS_PADRAO['acordes'], ge=0, description="4) tipos de acorde, complexidade e técnicas de tablatura"),
    peso_artista_genero: float = Query(default=PESOS_PADRAO['artista_genero'], ge=0, description="mesmo artista / gênero"),
):
    if not playlist and not musicas:
        raise HTTPException(400, 'Informe "playlist" (Spotify) ou ao menos um "musicas" ("Artista - Música")')

    faixas = []  # [([artistas], título)]
    generos_spotify = set()  # o Spotify não fornece mais gêneros dos artistas; mantido para outras fontes
    if playlist:
        try:
            faixas_sp = spotify.faixas_da_playlist(playlist)
        except spotify.LoginNecessario as e:
            raise HTTPException(401, str(e))
        except spotify.ErroSpotify as e:
            raise HTTPException(502, str(e))
        faixas += [(f['artistas'], f['nome']) for f in faixas_sp]
    for m in musicas or []:
        artista, sep, titulo = m.partition(' - ')
        if not sep or not artista.strip() or not titulo.strip():
            raise HTTPException(400, f'Formato inválido em "{m}": use "Artista - Música"')
        faixas.append(([artista.strip()], titulo.strip()))

    encontradas, nao_encontradas = [], []
    for artistas, titulo in faixas:
        idx = next((i for a in artistas for i in recomendador.localizar([(a, titulo)])[0]), None)
        (encontradas.append(idx) if idx is not None else nao_encontradas.append(f"{', '.join(artistas)} - {titulo}"))
    encontradas = list(dict.fromkeys(encontradas))
    dos_artistas = recomendador.musicas_dos_artistas([a for artistas, _ in faixas for a in artistas])
    dos_generos, generos_mapeados = recomendador.musicas_dos_generos(generos_spotify)

    if not encontradas and not dos_artistas and not dos_generos:
        raise HTTPException(404, 'Nenhuma música, artista ou gênero da playlist existe no acervo')

    pesos = {'letra': peso_letra, 'palavra_acorde': peso_palavra_acorde, 'ritmo': peso_ritmo,
             'acordes': peso_acordes, 'artista_genero': peso_artista_genero}
    if sum(pesos.values()) <= 0:
        raise HTTPException(400, 'Ao menos um peso de parâmetro deve ser maior que zero')

    # Se faixas foram encontradas no acervo, usamos elas como sementes principais
    # para letra, ritmo e acordes. As demais músicas dos mesmos artistas entram como
    # sementes fracas (apenas no componente artista_genero), evitando diluir o perfil
    # musical da faixa solicitada pela discografia inteira do artista.
    # Se nenhuma faixa foi encontrada, usamos as músicas dos artistas como fallback.
    if encontradas:
        sementes_principais = encontradas
        fracas = list(dict.fromkeys(dos_artistas + dos_generos))
    else:
        sementes_principais = dos_artistas
        fracas = dos_generos

    recomendacoes = recomendador.recomendar(
        sementes=sementes_principais,
        excluir=encontradas,
        sementes_fracas=fracas,
        pesos=pesos,
        limite=limit,
    )

    cat = recomendador.catalogo
    return {
        'entrada': {
            'faixas': len(faixas),
            'encontradas_no_acervo': [f"{cat['Artist'].iloc[i]} - {cat['SongName'].iloc[i]}" for i in encontradas],
            'nao_encontradas': nao_encontradas,
            'artistas_no_acervo': sorted(cat['Artist'].iloc[dos_artistas].unique().tolist()) if dos_artistas else [],
            'generos_mapeados': generos_mapeados,
        },
        'pesos': pesos,
        'recomendacoes': recomendacoes,
    }
