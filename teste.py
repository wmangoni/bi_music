from colorama import init, Fore, Style
import os

# Inicializa o colorama
init()

bar = "="
resto = "                                                                                                   "

for i in range(100):
	os.system('clear')
	print(Fore.GREEN + "============== INICIO ==============")
	bar = bar + "="
	print(Fore.RED + "[" + bar + ">" + resto[:-i] +  "]")
	print(str(i) + " %")

# Limpa o console antes de imprimir novas informações
print(Fore.RESET + Style.RESET_ALL)

# Imprime novas informações no console limpo
print(Fore.GREEN + "=============== FIM ================")