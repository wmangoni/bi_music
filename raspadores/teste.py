import pandas as pd
import os

# Caminho para a pasta da artista
artist_folder = "conteudo_artistas/avrillavigne/"

# Lista para armazenar os dados temporariamente
data = [] 

# Percorre todos os arquivos de letra de música na pasta
for lyrics_filename in os.listdir(artist_folder):
		if lyrics_filename.endswith(".txt") and lyrics_filename != "metadata.txt":
				lyrics_filepath = os.path.join(artist_folder, lyrics_filename)
				metadata_filepath = os.path.join(artist_folder, "metadata.txt")

				if os.stat(lyrics_filepath).st_size == 0:
						continue

				with open(lyrics_filepath, "r", encoding="utf-8") as lyrics_file:
						song = lyrics_file.readline().strip()
						composition = lyrics_file.readlines()[-1].strip().replace("Essa informação está errada? Nos avise.", "")

				with open(lyrics_filepath, 'r', encoding='utf-8') as f:
						lyrics = f.read()

				# Abre o arquivo de metadados para leitura
				with open(metadata_filepath, "r", encoding="utf-8") as metadata_file:
						artist = metadata_file.readline().strip()
						genre = metadata_file.readline().strip()  

				# Adiciona os dados à lista temporária  
				data.append({
								"Lyrics": lyrics,
								"Song": song,
								"Artist": artist,
								"Genre": genre,
								"Composition": composition
				})

# Cria o DataFrame a partir da lista de dados
df = pd.DataFrame(data)

# Salva o DataFrame em um arquivo CSV
df.to_csv("avril_teste_lyrics.csv", index=False, encoding="utf-8")
