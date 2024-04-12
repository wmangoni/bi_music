import requests
from bs4 import BeautifulSoup
import os
from unidecode import unidecode
import re


def remover_caracteres_especiais(palavra):
    # Substituir todos os caracteres que não são letras ou números por uma string vazia
    palavra_sem_especiais = re.sub(r'[^a-zA-Z0-9]', '', palavra)
    return palavra_sem_especiais


def scrape_letras_musicais(url_base):
    # Faz uma solicitação GET para a URL base
    response = requests.get(url_base + "/letra/A/")
    
    # Verifica se a solicitação foi bem-sucedida (código de status 200)
    if response.status_code == 200:
        # Parseia o HTML da página usando BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontra todas as tags <a> dentro das <li>
        links_artistas = artistas = soup.find('ul', class_='homeRecommendedArtists-artists').find_all('a')
        
        # Cria um diretório para salvar os arquivos se não existir
        if not os.path.exists('conteudo_artistas'):
            os.makedirs('conteudo_artistas')
        
        # Itera sobre os links dos artistas
        for link_artista in links_artistas:
            # Extrai o atributo href de cada tag <a>
            href = link_artista['href']
            href_formated = unidecode(remover_caracteres_especiais(href.replace("/", "")))

            response_artista = requests.get(url_base + href)
            if response_artista.status_code == 200:

                soup_artista = BeautifulSoup(response_artista.text, 'html.parser')

                songs = soup_artista.find('ol', class_='artist-songList-content').find_all('a')

                print(songs[0])

                for song in songs:
                    print(song.encode('utf-8'))

                    resp_song = requests.get(url_base + song['href'])

                    soup_song = BeautifulSoup(resp_song.text, 'html.parser')

                    lyric = soup_song.find('div', class_='lyric-original')
                    print(lyric.text.strip().encode('utf-8'))

                    #Se não existir o diretório, temos que criar um
                    if not os.path.exists(f'conteudo_artistas/{href_formated}'):
                        os.makedirs(f'conteudo_artistas/{href_formated}')

                    # Salva o conteúdo em um arquivo separado
                    s = song['title'].replace("/", "_")
                    s_formated = unidecode(remover_caracteres_especiais(s.replace(" ", "_")))
                    nome_arquivo = f'conteudo_artistas/{href_formated}/{s_formated}.txt'

                    with open(nome_arquivo, 'w', encoding='utf-8') as file:
                        file.write(lyric.text.strip())

                    print(f"Conteúdo do artista {href.encode('utf-8')} salvo com sucesso em {nome_arquivo.encode('utf-8')}.")
            else:
                print(f"Erro ao fazer a requisição HTTP para {url_completa}.")
    else:
        print("Erro ao fazer a requisição HTTP para a URL base.")

# URL base da página
url_base = 'https://www.letras.mus.br'

# Chama a função de scraping
scrape_letras_musicais(url_base)
