import requests
from bs4 import BeautifulSoup
import os
from unidecode import unidecode
import re
import string

def remover_caracteres_especiais(palavra):
    # Substituir todos os caracteres que não são letras ou números por uma string vazia
    palavra_sem_especiais = re.sub(r'[^a-zA-Z0-9]', '', palavra)
    return palavra_sem_especiais

def extrair_nome_arquivo(song_title, href_formated):
    # Formata o nome do arquivo removendo caracteres especiais e substituindo espaços por underscores
    s_formated = unidecode(remover_caracteres_especiais(song_title.replace(" ", "_")))
    return f'conteudo_artistas/{href_formated}/{s_formated}.txt'

def salvar_lyric(nome_arquivo, lyric_content):
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(nome_arquivo), exist_ok=True)

    # Salva o conteúdo da letra em um arquivo
    with open(nome_arquivo, 'w', encoding='utf-8') as file:
        for l in lyric_content:
            #print(str(l.contents))
            file.write(str(l.contents).replace("<br/>", "\n").replace("]", "").replace("[", "").replace(", ", "").replace("'", "").replace("\"", ""))

def scrape_letras_musicais(url_base):

    # Cria um array com todas as letras do alfabeto
    letras_alfabeto = list(string.ascii_uppercase)

    for letra in letras_alfabeto:

        response = requests.get(url_base + "/letra/" + letra.upper() + "/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links_artistas = soup.find('ul', class_='homeRecommendedArtists-artists').find_all('a')

            # Garante que o diretório existe
            os.makedirs('conteudo_artistas', exist_ok=True)

            for link_artista in links_artistas:
                href = link_artista['href']
                href_formated = unidecode(remover_caracteres_especiais(href.replace("/", "")))
                scrape_musica_artista(url_base + href, href_formated)
        else:
            print("Erro ao fazer a requisição HTTP para a URL base.")

def scrape_musica_artista(url_artista, href_formated):
    response_artista = requests.get(url_artista)
    if response_artista.status_code == 200:
        soup_artista = BeautifulSoup(response_artista.text, 'html.parser')
        songs = soup_artista.find('ol', class_='artist-songList-content').find_all('a')
        for song in songs:
            print(song['href'].encode('utf-8'))
            resp_song = requests.get(url_base + song['href'])
            if resp_song.status_code == 200:
                soup_song = BeautifulSoup(resp_song.text, 'html.parser')
                lyric = soup_song.find('div', class_='lyric-original').find_all("p")
                if lyric:
                    nome_arquivo = extrair_nome_arquivo(song['title'], href_formated)
                    salvar_lyric(nome_arquivo, lyric)
                else:
                    print(f"Letra não encontrada para a música: {song['title']}")
            else:
                print(f"Erro ao fazer a requisição HTTP para {url_base + song['href']}.")
    else:
        print(f"Erro ao fazer a requisição HTTP para {url_artista}.")

# URL base da página
url_base = 'https://www.letras.mus.br'

# Chama a função de scraping
scrape_letras_musicais(url_base)
