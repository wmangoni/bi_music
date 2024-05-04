import os
import pandas as pd


# Função para ler o arquivo metadata.txt e obter o nome do artista e o gênero musical
def ler_metadata(metadata_file):
    with open(metadata_file, 'r', encoding='utf-8') as f:
        artist_name = f.readline().strip()
        genre = f.readline().strip()
        img = f.readline().strip()
    return artist_name, genre, img

# Função para ler o conteúdo do arquivo .txt (letra da música)
def ler_letra(letra_file):
    with open(letra_file, 'r', encoding='utf-8') as f:
        letra = f.read()
    return letra

# Função para ler o conteúdo do arquivo .html (cifra da música)
def ler_cifra(cifra_file):
    with open(cifra_file, 'r', encoding='utf-8') as f:
        cifra = f.read()
    return cifra

# Lista para armazenar os dados de cada música
data = []
# Percorrer recursivamente as pastas de artistas
for root, dirs, files in os.walk('conteudo_artistas/'):

    # if '.config' in dirs:
    #     dirs.remove('.config')
    # if '.ipynb_checkpoints' in dirs:
    #     dirs.remove('.ipynb_checkpoints')
    # if 'sample_data' in dirs:
    #     dirs.remove('sample_data')

    artist_name, genre, letra, cifra = ["", "", "", ""]

    if os.path.exists(os.path.join(root,'metadata.txt')):
        artist_name, genre, img = ler_metadata(os.path.join(root,'metadata.txt'))

    for file in files:
        m_file = os.path.join(root, file)

        if '.html' in file:
            cifra = ler_cifra(m_file)
        else:
            letra = ler_letra(m_file)

        data.append({'Artist': artist_name, 'Img': img, 'Genre': genre, 'Lyrics': letra, 'Chords': cifra})

# Criar um DataFrame com os dados coletados
df = pd.DataFrame(data)

df.head(10)

df.to_csv('bi_music_a_i.csv')