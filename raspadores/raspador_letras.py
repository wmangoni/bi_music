import requests
from bs4 import BeautifulSoup
import os
from unidecode import unidecode
import re
import string
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
import time

# Define the maximum number of concurrent threads
max_workers = 6

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=max_workers)

MODO_TESTE = False
DIRRETORIO_PRINCIPAL = 'conteudo_artistas'
#CLASSE_LINK_ARTISTAS_OLD = ('ul', 'homeRecommendedArtists-artists')
CLASSE_LINK_ARTISTAS = ('ul', 'cnt-list cnt-list--col3')
CLASSE_CONTEUDO = ('ol', 'artist-songList-content')
CLASSE_CONTEUDO_COMPLETO = ('ul', 'songList-table-content')
CLASSE_TITLE = ('h1', 'head-title')
CLASSE_LYRIC = ('div', 'lyric-original')
CLASSE_LYRIC_INFO = ('div', 'lyric-info')
CLASSE_LYRIC_COMPOSITION = ('div', 'lyric-info-composition')


def proccess_chords_url(href_cifra, song, href_formated, title_song):
    # print("cifra >>>>>>>" + self.href_cifra)
    try:
        resp_song_cifra = requests.get(
            href_cifra)  # EXEMPLO: https://www.cifraclub.com.br/king-king/you-stopped-the-rain/
        handle_cifra(resp_song_cifra, song, href_formated, title_song)
    except Exception as e:
        print(e);


def remover_caracteres_especiais(palavra):
    # Substituir todos os caracteres que não são letras ou números por uma string vazia
    palavra_sem_especiais = re.sub(r'[^a-zA-Z0-9]', '', palavra)
    return palavra_sem_especiais


def extrair_nome_arquivo(song_title, href_formated):
    # Formata o nome do arquivo removendo caracteres especiais e substituindo espaços por underscores
    s_formated = unidecode(remover_caracteres_especiais(song_title.replace(" ", "_")))
    return f'{DIRRETORIO_PRINCIPAL}/{href_formated}/{s_formated}.txt'


def salvar_cifra(nome_arquivo, cifra, title_song):
    # Salva o conteúdo da cifra em um arquivo
    with open(nome_arquivo.replace('.txt', '_cifra.html'), 'w', encoding='utf-8') as file:
        html = f'<html><h1>{title_song.get_text() + "<h1><div>" + str(cifra.pre)}</div></html>'
        file.write(html)


def salvar_lyric(nome_arquivo, lyric_content, title_song, composition):
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(nome_arquivo), exist_ok=True)

    # Salva o conteúdo da letra em um arquivo
    with open(nome_arquivo, 'w', encoding='utf-8') as file:
        for l in lyric_content:
            if MODO_TESTE is not None and MODO_TESTE:
                print(str(l.contents))
                print(composition.get_text())

            composicao = "Composição: não enconrtada!"
            if composition is not None:
                composicao = composition.get_text()

            all_content = title_song.get_text() + "\n \n" + str(l.contents) \
                .replace("]", "\n") \
                .replace("['", "") \
                .replace("[\"", "") \
                .replace(" ,", "") \
                .replace("\",", "") \
                .replace("',", " ") \
                .replace(" '", " ") \
                .replace("\"'", "") \
                .replace("\"", "") \
                .replace(" <br/>, ", "\n")
            file.write(all_content.replace("'\n", "\n"))

        file.write("\n\n" + composicao)


def scrape_letras_musicais(base_url):
    # Cria um array com todas as letras do alfabeto
    #letras_alfabeto = list(string.ascii_uppercase)

    # se quiser executar apenas algumas letras pode fazer assim:
    letras_alfabeto = ['Q', 'R', 'S', 'T', 'U']

    for letra in letras_alfabeto:

        response = requests.get(
            base_url + "/letra/" + letra.upper() + "/artists_ajax.html")  # EXEMPLO: https://www.letras.mus.br/letra/K/artists_ajax.html
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links_artistas = soup.find(CLASSE_LINK_ARTISTAS[0], class_=CLASSE_LINK_ARTISTAS[1]).find_all('a')

            # Garante que o diretório existe
            os.makedirs(DIRRETORIO_PRINCIPAL, exist_ok=True)

            results = []

            for link_artista in links_artistas:
                href = link_artista['href']
                href_formated = unidecode(remover_caracteres_especiais(href.replace("/", "")))
                #img = link_artista.find('img')
                #img_src = img['data-original']
                #print(img_src)

                music_classification = link_artista.find('small')
                if music_classification is None:
                    music_classification = ""
                else:
                    music_classification = music_classification.get_text()

                #scrape_musica_artista(base_url + href, href_formated, music_classification, "")
                future = executor.submit(scrape_musica_artista, base_url + href, href_formated, music_classification, "")
                results.append(future)

                if MODO_TESTE:
                    break
        else:
            print("Erro ao fazer a requisição HTTP para a URL base.")

        if MODO_TESTE:
            break


def scrape_musica_artista(url_artista, href_formated, music_classification, img_src):
    response_artista = requests.get(
        url_artista + "mais_acessadas.html")  # EXEMPLO: https://www.letras.mus.br/king-king/mais_acessadas.html
    print("url_artista " + url_artista)

    if response_artista.status_code == 200:

        soup_artista = BeautifulSoup(response_artista.text, 'html.parser')

        name_artistic = soup_artista.find(CLASSE_TITLE[0], class_=CLASSE_TITLE[1])

        file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(name_artistic.get_text() + "\n" + music_classification + "\n" + img_src)


        # Esse return serve pra só coletar o metadado e cair fora sem pegar as musicas
        # return;

        if soup_artista is None:
            return;

        songs = soup_artista.find(CLASSE_CONTEUDO_COMPLETO[0], class_=CLASSE_CONTEUDO_COMPLETO[1]).find_all('a')

        for song in songs:

            print(song['href'].encode('utf-8'))
            resp_song = requests.get(
                url_base + song['href'])  # EXEMPLO: https://www.letras.mus.br/king-king/you-stopped-the-rain/

            title = song.find('span').get_text()

            if resp_song.status_code == 200:

                soup_song = BeautifulSoup(resp_song.text, 'html.parser')
                title_song = soup_song.find(CLASSE_TITLE[0], class_=CLASSE_TITLE[1])

                os.system('clear')

                if soup_song is not None:

                    composition = soup_song.find(CLASSE_LYRIC_COMPOSITION[0], class_=CLASSE_LYRIC_COMPOSITION[1])

                    """
                    lm = soup_song.find('div', class_='lyric-menu')

                    if lm is None:
                        continue

                    menu_list = soup_song.find('div', class_='lyric-menu').find_all('a')
                    
                    results = []

                    for i in menu_list:
                        if 'data-action' in str(i):
                            if i['data-action'] == 'Nav Cifra':
                                href_cifra = i['href']

                                # ===== PROCESSO ANTIGO SEM THREADS =======
                                # print("cifra >>>>>>>" + href_cifra)
                                # resp_song_cifra = requests.get(href_cifra, timeout=1) ### EXEMPLO: https://www.cifraclub.com.br/king-king/you-stopped-the-rain/
                                # handle_cifra(resp_song_cifra, song, href_formated, title_song)

                                # ===== PROCESSO NOVO COM THREADS =======
                                future = executor.submit(proccess_chords_url, href_cifra, song, href_formated,
                                                         title_song)
                                results.append(future)
                    """

                    lyric = soup_song.find(CLASSE_LYRIC[0], class_=CLASSE_LYRIC[1]).find_all("p")

                    if lyric:
                        nome_arquivo = extrair_nome_arquivo(title, href_formated)
                        salvar_lyric(nome_arquivo, lyric, title_song, composition)
                    else:
                        print(f"Letra não encontrada para a música: {title}")
                        file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'
                        with open(file_name, 'a', encoding='utf-8') as file:
                            file.write("\n" + f"Letra não encontrada para a música: {title}")

                else:
                    print(f"Erro ao fazer a requisição HTTP para {url_base + song['href']}.")
                    file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'
                    with open(file_name, 'a', encoding='utf-8') as file:
                        file.write("\n" + f"Erro ao fazer a requisição HTTP para {url_base + song['href']}.")
            else:
                print(f"Erro ao fazer a requisição HTTP para {url_base + song['href']}.")
                file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'
                with open(file_name, 'a', encoding='utf-8') as file:
                    file.write("\n" + f"Erro ao fazer a requisição HTTP para {url_base + song['href']}.")

            if MODO_TESTE:
                break
    else:
        print(f"Erro ao fazer a requisição HTTP para {url_artista}.")


def handle_cifra(resp_song_cifra, song, href_formated, title_song):
    if resp_song_cifra.status_code == 200:

        resp_song_cifra = BeautifulSoup(resp_song_cifra.text, 'html.parser')

        cifra = resp_song_cifra.find('div', class_='cifra_cnt g-fix cifra-mono')

        title = song.find('span').get_text()

        if cifra:
            nome_arquivo = extrair_nome_arquivo(title, href_formated)
            salvar_cifra(nome_arquivo, cifra, title_song)
        else:
            print(f"Cifra não encontrada para a música: {title}")
            file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'
            with open(file_name, 'a', encoding='utf-8') as file:
                file.write("\n" + f"Cifra não encontrada para a música: {title}")
    else:
        print(f"Erro ao fazer a requisição HTTP para {url_base_cifra + song['href']}.")
        file_name = f'{DIRRETORIO_PRINCIPAL}/{href_formated}/metadata.txt'
        with open(file_name, 'a', encoding='utf-8') as file:
            file.write("\n" + f"Erro ao fazer a requisição HTTP para {url_base_cifra + song['href']}.")


# URL base da página
url_base = 'https://www.letras.mus.br'
url_base_cifra = 'https://www.cifraclub.com.br'


inicio = time.time()
# Chama a função de scraping
scrape_letras_musicais(url_base)
fim = time.time()
 
tempo_execucao = fim - inicio  # Calcula o tempo de execução em segundos
print(f"Tempo de execução: {tempo_execucao:.2f} segundos")

# aqui pe pra rodar só um artista
# scrape_musica_artista('https://www.letras.mus.br/legiao-urbana/', 'legiao-urbana', 'Pop Rock')

# Ideia de raspagem futura: https://www.palcomp3.com.br/mp3/A/todos.htm
