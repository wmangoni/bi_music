# Como Iniciar a API Localmente
Este guia passo a passo te ensinará como clonar o repositório, instalar as dependências e executar a API localmente.

### Pré-requisitos:

Ter o Python 3.6 ou superior instalado:
Verifique a versão do Python: python3 --version
Se necessário, instale o Python: https://www.python.org/downloads/
Ter o pip instalado:
Verifique se o pip está instalado: pip --version
Se necessário, instale o pip: https://pip.pypa.io/en/stable/installation/
Ter um editor de código de sua preferência:
Opções populares: Visual Studio Code, PyCharm, Sublime Text
Passos:

## 1. Clonando o Repositório:

Abra um terminal ou prompt de comando.
Navegue até o diretório onde você deseja clonar o repositório.
Clone o repositório usando o seguinte comando:

```Bash
git clone https://github.com/wmangoni/bi_music.git
```

Use o código com cuidado.
Substitua SEU_NOME_DE_USUARIO pelo seu nome de usuário no GitHub e SEU_NOME_DO_REPOSITÓRIO pelo nome do repositório.

## 2. Instalando as Dependências:

Acesse o diretório do projeto clonado:

```
Bash
cd SEU_NOME_DO_REPOSITÓRIO
```

Instale as dependências com o seguinte comando:

```
Bash
pip install -r requirements.txt
```

## 3. Executando a API:

Ative um ambiente virtual (recomendado):
Crie um ambiente virtual (opcional): python3 -m venv .venv
Ative o ambiente virtual: source .venv/bin/activate
Inicie a API com o seguinte comando:

```
Bash
uvicorn main:app --reload
```

Isso iniciará o servidor Uvicorn e executará a API. Você poderá acessá-la em http://localhost:8000.
A opção --reload garante que o servidor reinicie automaticamente quando você fizer alterações no código.
Observações:

Certifique-se de substituir SEU_NOME_DE_USUARIO e SEU_NOME_DO_REPOSITÓRIO pelos valores corretos nos comandos.
Se você encontrar erros durante a instalação ou execução, revise os logs e procure por soluções online.
Este guia assume que você possui conhecimento básico de Git, Python e uso de terminal.
Dicas:

Utilize um editor de código com suporte a Python para melhor experiência de desenvolvimento.
Configure um IDE com o interpretador Python correto e as bibliotecas instaladas.
Explore a documentação do FastAPI e Uvicorn para se familiarizar com suas funcionalidades.