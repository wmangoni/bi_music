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

  return data;

# Caminho da pasta principal
root_dir = "conteudo_artistas/"

results = []

def percorre_letra(letra):

  d = []

  for folder in os.listdir(root_dir):
    if folder.startswith(letra):
      print(f"folder >> : {folder}")
      d = d + extract_lyrics_and_metadata(os.path.join(root_dir, folder), letra)

  # Cria o DataFrame a partir da lista de dados
  df = pd.DataFrame(d)

  delimitador="\\"

  # Salva o DataFrame em um arquivo CSV
  df.to_csv(letra + "_lyrics.csv", index=False, encoding="utf-8", sep=delimitador)
      

# percorre_letra("a")
# results.append(executor.submit(percorre_letra, "a"))
# results.append(executor.submit(percorre_letra, "b"))
# results.append(executor.submit(percorre_letra, "c"))
# results.append(executor.submit(percorre_letra, "d"))
# results.append(executor.submit(percorre_letra, "e"))
# results.append(executor.submit(percorre_letra, "f"))

# results.append(executor.submit(percorre_letra, "g"))
# results.append(executor.submit(percorre_letra, "h"))
# results.append(executor.submit(percorre_letra, "i"))
# results.append(executor.submit(percorre_letra, "j"))
# results.append(executor.submit(percorre_letra, "k"))
# results.append(executor.submit(percorre_letra, "l"))

# results.append(executor.submit(percorre_letra, "m"))
# results.append(executor.submit(percorre_letra, "n"))
# results.append(executor.submit(percorre_letra, "o"))
# results.append(executor.submit(percorre_letra, "p"))
# results.append(executor.submit(percorre_letra, "q"))
# results.append(executor.submit(percorre_letra, "r"))

results.append(executor.submit(percorre_letra, "s"))
results.append(executor.submit(percorre_letra, "t"))
results.append(executor.submit(percorre_letra, "u"))
results.append(executor.submit(percorre_letra, "v"))
results.append(executor.submit(percorre_letra, "x"))
results.append(executor.submit(percorre_letra, "y"))
results.append(executor.submit(percorre_letra, "w"))
results.append(executor.submit(percorre_letra, "z"))