import os


root_dir = "conteudo_artistas/"
artistas = 0
musicas = 0

for folder in os.listdir(root_dir):
	artistas = artistas + 1
	for filename in os.listdir(os.path.join(root_dir, folder)):
		musicas = musicas + 1

print(f"artistas: {artistas}")
print(f"musicas: {musicas}")