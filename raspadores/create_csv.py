import os
import csv
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Define the maximum number of concurrent threads
max_workers = 6

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=max_workers)


def extract_lyrics_and_metadata(folder, letra):
  """
  Extrai letras de músicas e metadados de uma pasta e salva em um arquivo CSV.

  Args:
    folder: Caminho da pasta a ser processada.
    letra: filtro para pegar apenas pastas que comecem com essa letra

  Returns:
    None
  """

  song = ""
  composition = ""
  lyrics = ""
  artist = ""
  genre = ""

  data = []

  print(folder)
  for filename in os.listdir(folder):
    
    if filename.endswith(".txt") and filename != "metadata.txt":

      print(filename)

      with open(os.path.join(folder, filename), "r", encoding="utf-8") as lyrics_file:
        song = lyrics_file.readline().strip()
        composition = lyrics_file.readlines()[-1].strip().replace("Essa informação está errada? Nos avise.", "")

      with open(os.path.join(folder, filename), 'r', encoding='utf-8') as f:
        lyrics = f.read().replace(composition, "")

      with open(os.path.join(folder, "metadata.txt"), "r", encoding="utf-8") as metadata_file:
        artist = metadata_file.readline().strip()
        genre = metadata_file.readline().strip()

      print(song)
      print(composition)
      print(artist)
      print(genre)

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
  df.to_csv(letra + "_lyrics.csv", index=False, encoding="utf-8")

# Caminho da pasta principal
root_dir = "conteudo_artistas/"

results = []

letras = ["u", "v", "x", "z", "y", "w"]

for letra in letras:
  for folder in os.listdir(root_dir):
    if folder.startswith(letra):
      #extract_lyrics_and_metadata(os.path.join(root_dir, folder))
      future = executor.submit(extract_lyrics_and_metadata, os.path.join(root_dir, folder), letra)
      results.append(future)
