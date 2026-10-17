# BI Music — correções da API e recomendador de músicas

Este documento descreve o que foi alterado na API e como funciona o novo endpoint `GET /recommendations`, que sugere músicas do acervo a partir de uma playlist do Spotify.

## Sumário

1. [Como rodar](#1-como-rodar)
2. [Correções na API existente](#2-correções-na-api-existente)
3. [Endpoints](#3-endpoints)
4. [Recomendador](#4-recomendador)
5. [Integração com o Spotify](#5-integração-com-o-spotify)
6. [Estrutura de arquivos](#6-estrutura-de-arquivos)
7. [Limitações conhecidas](#7-limitações-conhecidas)

---

## 1. Como rodar

### Pré-requisitos

- Python 3.12. O `numpy==1.25.0` original não tem suporte a 3.12; o `requirements.txt` agora usa `numpy==1.26.4`.
- Um app criado em [developer.spotify.com](https://developer.spotify.com/dashboard). Só é necessário para usar playlists do Spotify.

### Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Dados

O CSV fica dentro do zip e precisa ser extraído na pasta do projeto. O arquivo está no `.gitignore` e não deve ser commitado (82 MB):

```bash
unzip bi_music.zip
```

### Credenciais do Spotify

Crie um arquivo `.env` na pasta do projeto. Ele já está no `.gitignore`:

```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
# opcional, padrão http://127.0.0.1:8000/callback
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/callback
```

No app do Spotify, cadastre como **Redirect URI** exatamente `http://127.0.0.1:8000/callback`. O Spotify não aceita `localhost`. Marque a opção **Web API**.

### Subir o servidor

```bash
uvicorn main:app --reload --reload-exclude '.venv/*' --reload-exclude 'recomendador/cache/*'
```

- Os `--reload-exclude` evitam que o reloader trave ao instalar pacotes no `.venv` ou ao gravar o cache do modelo.
- Na **primeira** execução o modelo é treinado, o que leva de 35 a 45 s. Depois ele é carregado do cache em cerca de 0,1 s.
- `http://127.0.0.1:8000/` redireciona para a documentação interativa em `/docs`.

---

## 2. Correções na API existente

| Problema | Correção |
|---|---|
| `FileNotFoundError: bi_music/bi_music.csv`: o caminho era relativo à pasta de onde o comando era executado | O caminho agora é montado a partir da pasta do `main.py` |
| Os endpoints devolviam o JSON como **string** (`"[{\"Artist\"...}]"`), serializado duas vezes | Passaram a devolver `Response(..., media_type='application/json')` |
| O `paginateDf` paginava **antes** de filtrar: `/genre/X?page=1` só procurava nas 10 primeiras linhas do arquivo | Agora filtra primeiro e pagina depois |
| Nomes com `/` (`Gospel/Religioso`, `Hip Hop/Rap`) davam 404 | As rotas usam `{name:path}` |
| `GET /` devolvia 404 | Redireciona para `/docs` |

### Problema nos dados (ainda presente nas rotas antigas)

O CSV gerado pelo raspador está **desalinhado**: a mesma música aparece várias vezes, e em muitas linhas a letra (`Lyrics`) e a cifra (`Chords`) pertencem a músicas diferentes. Só cerca de 34% das linhas têm o título da letra igual ao título da cifra.

As rotas `/songs`, `/genre` e `/artist` continuam lendo o CSV original e por isso podem devolver a cifra de outra música. O recomendador **não** tem esse problema, porque monta um catálogo corrigido (ver 4.1).

---

## 3. Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/songs` | Lista paginada (sem letra e cifra) |
| GET | `/songs/{name}` | Busca por nome exato da música |
| GET | `/genre/{name}` | Busca por gênero exato |
| GET | `/artist/{name}` | Busca por artista exato |
| GET | `/recommendations` | **Novo.** Recomendações a partir de uma playlist ou de uma lista de músicas |
| GET | `/spotify/login` | **Novo.** Inicia o login no Spotify (abrir pela barra de endereços do navegador) |
| GET | `/callback` | **Novo.** Retorno do login do Spotify (chamado pelo próprio Spotify) |

Todas as rotas de busca aceitam `page` (padrão 1) e `per_page` (padrão 10).

### Campos devolvidos

| Campo | Origem |
|---|---|
| `Artist`, `Genre`, `Lyrics`, `Chords` | Colunas originais do CSV |
| `SongName` | Primeira linha da letra |
| `comprimento_letra` | Número de caracteres da letra |
| `ocorrencias_amor_love` | Ocorrências de "amor" ou "love". A contagem diferencia maiúsculas e conta pedaços de outras palavras, como "lovely" |

### `GET /recommendations`

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `playlist` | str | — | Link, URI ou ID de uma playlist do Spotify. Links com `?si=...` funcionam |
| `musicas` | list[str] | — | Alternativa sem Spotify: `Artista - Música`. Repita o parâmetro para várias músicas |
| `limit` | int | 10 | Quantidade de recomendações (1 a 100) |
| `peso_letra` | float | 0.35 | Peso do parâmetro 1 |
| `peso_palavra_acorde` | float | 0.20 | Peso do parâmetro 2 |
| `peso_ritmo` | float | 0.10 | Peso do parâmetro 3 |
| `peso_acordes` | float | 0.15 | Peso do parâmetro 4 |
| `peso_artista_genero` | float | 0.20 | Peso de mesmo artista / gênero |

É obrigatório informar `playlist` ou `musicas`. Um peso `0` desliga o parâmetro.

**Exemplo sem Spotify:**

```
GET /recommendations?musicas=Lulu Santos - Como Uma Onda&musicas=Legião Urbana - Tempo Perdido&limit=5
```

**Resposta (resumida):**

```json
{
  "entrada": {
    "faixas": 2,
    "encontradas_no_acervo": ["Lulu Santos - Como Uma Onda (Zen-Surfismo)", "Legião Urbana - Tempo Perdido"],
    "nao_encontradas": [],
    "artistas_no_acervo": ["Legião Urbana", "Lulu Santos"],
    "generos_mapeados": []
  },
  "pesos": {"letra": 0.35, "palavra_acorde": 0.2, "ritmo": 0.1, "acordes": 0.15, "artista_genero": 0.2},
  "recomendacoes": [
    {
      "Artist": "Lulu Santos",
      "Genre": "Pop Rock",
      "SongName": "Apenas Mais Uma de Amor",
      "score": 0.9888,
      "parametros": {"letra": 0.9959, "palavra_acorde": 0.997, "ritmo": 0.9586, "acordes": 0.9704, "artista_genero": 0.997}
    }
  ]
}
```

O campo `parametros` mostra o percentil de cada parâmetro, de 0 a 1. Músicas sem cifra não têm os parâmetros 2, 3 e 4.

**Códigos de erro:**

| Código | Quando |
|---|---|
| 400 | Faltou `playlist`/`musicas`, ou formato inválido em `musicas` |
| 401 | Não há login no Spotify, ou a sessão expirou: abra `/spotify/login` |
| 404 | Nenhuma música nem artista da entrada existe no acervo |
| 502 | Erro devolvido pelo Spotify, como uma playlist inacessível |

---

## 4. Recomendador

É uma recomendação **por similaridade de conteúdo**: as músicas da playlist formam um "perfil", e as músicas do acervo são ordenadas pela semelhança com esse perfil. Não há treino supervisionado, porque não existem dados de "acerto" para treinar.

### 4.1 Catálogo corrigido

Para contornar o desalinhamento do CSV, `montar_catalogo()` (`recomendador/modelo.py`) faz o seguinte:

1. Extrai as letras únicas por (artista, título), em que o título é a primeira linha da letra.
2. Extrai as cifras únicas por (artista, título), em que o título é o `<h1>` do HTML da cifra.
3. Junta os dois pelo par (artista, título normalizado). A normalização tira acentos e remove `(part. X)`, `[...]`, ` - Remix` e `feat.`.

O resultado tem **10.214 músicas**, das quais **6.039 com a cifra correta**.

### 4.2 Formato da cifra

A coluna `Chords` é HTML em texto monoespaçado. Os acordes ficam em `<b>` e são posicionados por espaços **acima** da palavra da letra:

```html
<b>Am</b>                      <b>F</b>
Early in the morning I still
```

As tablaturas ficam dentro de `<span class="tablatura">`, cerca de 23% das cifras têm tablatura, e cerca de 7 mil cifras marcam seções como `[Intro]` e `[Refrão]`.

### 4.3 Os parâmetros

| # | Parâmetro | Técnica | O que mede |
|---|---|---|---|
| 1 | `letra` | TF-IDF das letras (`min_df=2`, `max_df=0.5`, `sublinear_tf`) | Vocabulário e tema |
| 2 | `palavra_acorde` | TF-IDF de tokens `palavra@grau_tipo` | Quais palavras recebem quais acordes, por exemplo `amor@9_menor` (palavra "amor" sobre o vi menor) |
| 3 | `ritmo` | Média, desvio, mediana das distâncias entre acordes e trocas por caractere | **Ritmo harmônico**: se os acordes trocam a cada palavra ou a cada verso |
| 4 | `acordes` | Distribuição de tipos, complexidade e técnicas de tablatura | Vocabulário harmônico e dificuldade de execução |
| — | `artista_genero` | One-hot de gênero e artista (artista com peso 2) | Proximidade de catálogo |

**Parâmetro 2: tonalidade.** Para que a mesma música em Dó ou em Ré gere os mesmos tokens, os acordes são convertidos em **graus** (semitons a partir da tônica). O tom está escrito em só 29 cifras, então é **estimado** pelos próprios acordes (`estimar_tom()`): vence a tônica que deixa mais acordes diatônicos, com desempate pelo primeiro e pelo último acorde serem I ou vi.

**Parâmetro 3: tempo.** O acervo **não** traz BPM, compasso nem batida. A distância entre acordes, em caracteres da letra, é o substituto possível: mede a frequência das trocas harmônicas em relação ao texto.

**Parâmetro 4: detalhamento.**

- *Tipos de acorde* (notação brasileira): `maior`, `menor`, `dom7`, `maj7` (7M, 7+), `m7`, `dim` (°, º), `meio_dim` (m7(5-)), `aum` (+, 5+), `sus` (sus4, 4), `power` (5), `add` (9, 6, 11 sem sétima).
- *Complexidade dos acordes*: notas por acorde (tríade = 3, power chord = 2, cada sétima, sexta ou extensão soma uma), proporção de acordes com baixo invertido (`D/F#`) e quantidade de acordes distintos.
- *Técnicas de tablatura*, por 100 caracteres de tablatura: hammer-on (`h`), pull-off (`p`), bend (`b`), slide (`/`, `\`), vibrato (`~`), densidade de notas, casa média (região do braço) e proporção de notas simultâneas.

As técnicas são padronizadas **só entre as músicas que têm tablatura**. Assim, quem não tem tablatura não ganha um componente artificial em comum.

### 4.4 Cálculo da nota final

1. **Perfil:** para cada parâmetro, é a média dos vetores das sementes. Quando a playlist possui faixas encontradas no catálogo, elas são usadas como sementes principais nos parâmetros acústicos/líricos (`letra`, `palavra_acorde`, `ritmo` e `acordes`); as demais músicas dos mesmos artistas entram como sementes de apoio apenas em `artista_genero`, evitando que a discografia inteira do artista dilua as características musicais das faixas informadas. Se nenhuma faixa for encontrada no catálogo, as músicas dos artistas atuam como fallback.
2. **Similaridade:** cosseno de cada música do acervo com o perfil.
3. **Percentil:** similaridades estritamente positivas viram percentis de 0 a 1 entre as candidatas com afinidade real. Músicas com similaridade zero recebem nota zero, evitando empates com pontuações artificiais.
4. **Média ponderada por música:** só entram os parâmetros que a música tem. Uma música sem cifra é avaliada só por `letra` e `artista_genero`, sem ser zerada nos demais.
5. As músicas que já estão na playlist são excluídas, e as `limit` maiores notas são devolvidas.

### 4.5 Cache

O modelo treinado é salvo em `recomendador/cache/modelo_v{VERSAO}_{mtime_do_csv}.joblib` (atualmente versão 3 com matrizes esparsas e indexação O(1)), uma pasta ignorada pelo git. O cache é refeito sozinho quando o CSV muda. **Ao alterar a extração de características ou o `_treinar()`, incremente `VERSAO_CACHE`** em `recomendador/modelo.py`.

---

## 5. Integração com o Spotify

### Por que é preciso fazer login

Nas mudanças recentes da Web API do Spotify, ler as faixas de uma playlist passou a **exigir autenticação de usuário**. O login simples do app (Client Credentials) não basta: devolve 401/403. Por isso a API usa o fluxo **OAuth Authorization Code**.

### Fazer o login (uma vez)

1. Abra `http://127.0.0.1:8000/spotify/login` **pela barra de endereços** do navegador. O botão Execute do `/docs` não funciona aqui.
2. Entre na conta do Spotify e autorize. Os escopos pedidos são `playlist-read-private` e `playlist-read-collaborative`.
3. O Spotify redireciona para `/callback`. A API grava o token em `.spotify_token.json`, ignorado pelo git e com permissão 600, e volta para o `/docs`.
4. O token é renovado automaticamente com o `refresh_token`. Se aparecer um 401, basta repetir o login.

### Restrições atuais do Spotify

- **Playlists editoriais** do próprio Spotify (Today's Top Hits e afins, IDs começando com `37i9dQZF1`) são bloqueadas para apps novos (403). Use playlists criadas por usuários.
- O Spotify **não informa mais os gêneros** dos artistas. Por isso `generos_mapeados` vem vazio, e a ligação com o acervo é feita só por música e artista. O mapeamento de gêneros (`musicas_dos_generos()`) foi mantido para o caso de uma fonte de gêneros ser adicionada no futuro. Exemplos: "brazilian gospel" → "Gospel/Religioso", "funk carioca" → "Funk".
- Os endpoints de recomendações, características de áudio (BPM, energia) e artistas relacionados do Spotify foram desativados para apps novos, por isso a lógica de recomendação é inteiramente local.

---

## 6. Estrutura de arquivos

```
bi_music/
├── main.py                       # API FastAPI (rotas antigas + /recommendations + login Spotify)
├── recomendador/
│   ├── __init__.py
│   ├── caracteristicas.py        # leitura da cifra: acordes, tom, palavra↔acorde, ritmo, tablatura
│   ├── modelo.py                 # catálogo corrigido, vetorização, similaridade e cache
│   ├── spotify.py                # OAuth e leitura das faixas da playlist
│   └── cache/                    # modelo treinado (ignorado pelo git)
├── bi_music.zip                  # dados originais
├── bi_music.csv                  # extraído do zip (ignorado pelo git)
├── .env                          # credenciais do Spotify (ignorado pelo git)
├── .spotify_token.json           # token do usuário (ignorado pelo git)
└── requirements.txt              # + scikit-learn==1.5.2, numpy==1.26.4
```

---

## 7. Limitações conhecidas

- **A playlist precisa ter músicas ou artistas do acervo.** O Spotify não fornece letra nem cifra, então os parâmetros só funcionam para faixas e artistas que existem no CSV (527 artistas, 51 gêneros, acervo de um site de cifras brasileiro).
- **Músicas sem cifra** são avaliadas em menos parâmetros e podem ficar à frente de músicas com cifra na ordenação.
- **Perfil por média:** uma playlist muito variada, como pop internacional misturado com piseiro, gera um perfil "médio" que pode não representar bem nenhum dos estilos.
- **Artistas com muitas músicas** pesam mais no perfil.
- **O tom estimado é aproximado**, e o tom menor é tratado como o relativo maior.
- **Não há avaliação de qualidade:** os pesos padrão são um ponto de partida e devem ser ajustados testando.
- **A busca nas rotas antigas exige o texto exato**, e elas ainda usam o CSV desalinhado (ver seção 2).
- O `state` do login fica em memória: se o servidor reiniciar entre o `/spotify/login` e o `/callback`, repita o login.
