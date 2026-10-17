"""Extração de características musicais a partir da coluna Chords (HTML do site de cifras).

Formato da cifra: texto monoespaçado dentro de <pre>, com acordes em <b>..</b> posicionados
por espaços acima da linha da letra, e tablaturas dentro de <span class="tablatura">.
"""
import html
import re
import unicodedata

import numpy as np

NOTAS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

# Classes de acorde (parâmetro 4: tipos de acorde)
CLASSES_ACORDE = ['maior', 'menor', 'dom7', 'maj7', 'm7', 'dim', 'meio_dim', 'aum', 'sus', 'power', 'add']

# Tríades diatônicas da escala maior: grau (semitons a partir da tônica) -> qualidade
DIATONICO = {0: 'maior', 2: 'menor', 4: 'menor', 5: 'maior', 7: 'maior', 9: 'menor', 11: 'dim'}

RE_ACORDE = re.compile(r'^([A-G])([#b]?)(.*?)(?:/([A-G][#b]?))?$')
RE_TAG = re.compile(r'<[^>]+>')
RE_B = re.compile(r'<b>(.*?)</b>')
RE_TAB = re.compile(r'<span class="tablatura">(.*?)(?:</span>\s*)+', re.S)
RE_LINHA_TAB = re.compile(r'^\s*[eBGDAE]\|')
RE_PALAVRA = re.compile(r"[\wÀ-ÿ']+")


def _classe_nota(letra, acidente):
    pc = NOTAS[letra]
    if acidente == '#':
        pc += 1
    elif acidente == 'b':
        pc -= 1
    return pc % 12


def analisar_acorde(simbolo):
    """Retorna (fundamental 0-11, classe, quantidade de notas, tem_baixo) ou None se não for acorde."""
    m = RE_ACORDE.match(simbolo.strip())
    if not m:
        return None
    letra, acidente, resto, baixo = m.groups()
    raiz = _classe_nota(letra, acidente)
    r = resto.replace('º', '°').replace('(', '').replace(')', '')

    menor = r.startswith('m') and not r.startswith('maj')
    if menor:
        r = r[1:]

    if '°' in r or 'dim' in r:
        classe = 'dim'
    elif menor and ('5-' in r or 'b5' in r):
        classe = 'meio_dim'
    elif r.startswith('+') or r.startswith('5+') or 'aug' in r:
        classe = 'aum'
    elif r == '5':
        classe = 'power'
    elif '7M' in r or 'maj7' in r or '7+' in r:
        classe = 'maj7'
    elif '7' in r:
        classe = 'm7' if menor else 'dom7'
    elif 'sus' in r or re.match(r'^4', r):
        classe = 'sus'
    elif menor:
        classe = 'menor'
    elif re.search(r'\d', r):
        classe = 'add'  # C9, A6, D11 sem sétima
    else:
        classe = 'maior'

    # Complexidade: tríade = 3 notas, power chord = 2, cada sétima/sexta/extensão soma uma nota
    notas = 2 if classe == 'power' else 3
    if classe in ('dom7', 'maj7', 'm7', 'meio_dim') or re.search(r'(?<!\d)6', r):
        notas += 1
    notas += len(re.findall(r'9|11|13', r))
    tem_baixo = baixo is not None and _classe_nota(baixo[0], baixo[1:]) != raiz
    if tem_baixo:
        notas += 1
    return raiz, classe, notas, tem_baixo


def _qualidade_triade(classe):
    if classe in ('menor', 'm7'):
        return 'menor'
    if classe in ('dim', 'meio_dim'):
        return 'dim'
    return 'maior'


def estimar_tom(acordes):
    """Estima a tônica (escala maior relativa) pela tônica que mais encaixa os acordes como diatônicos."""
    if not acordes:
        return 0
    melhor, melhor_pontos = 0, -1.0
    for tonica in range(12):
        pontos = 0.0
        for raiz, classe, _, _ in acordes:
            grau = (raiz - tonica) % 12
            if DIATONICO.get(grau) == _qualidade_triade(classe):
                pontos += 1
        # Desempate: primeiro e último acorde costumam ser I ou vi
        for raiz, _, _, _ in (acordes[0], acordes[-1]):
            if (raiz - tonica) % 12 in (0, 9):
                pontos += 0.5
        if pontos > melhor_pontos:
            melhor, melhor_pontos = tonica, pontos
    return melhor


def normalizar_palavra(p):
    p = unicodedata.normalize('NFKD', p.lower())
    return ''.join(c for c in p if not unicodedata.combining(c))


def _acordes_da_linha(linha_html):
    """Se a linha só contém acordes, devolve [(coluna, símbolo)]; senão None."""
    if '<b>' not in linha_html:
        return None
    resto = RE_B.sub('', linha_html)
    resto = RE_TAG.sub('', resto)
    if re.sub(r'[\s\[\]()|x\d:.-]|intro|refr[aã]o|parte|solo|final|ponte|riff', '', html.unescape(resto), flags=re.I):
        return None  # tem letra misturada
    acordes, visivel = [], 0
    pos = 0
    for m in RE_B.finditer(linha_html):
        visivel += len(html.unescape(RE_TAG.sub('', linha_html[pos:m.start()])))
        acordes.append((visivel, m.group(1)))
        visivel += len(m.group(1))
        pos = m.end()
    return acordes


def _palavra_na_coluna(linha, coluna):
    palavras = [(m.start(), m.end(), m.group()) for m in RE_PALAVRA.finditer(linha)]
    if not palavras:
        return None
    for ini, fim, p in palavras:
        if ini <= coluna < fim:
            return p
    for ini, _, p in palavras:
        if ini > coluna:
            return p
    return palavras[-1][2]


def _tecnicas_tablatura(cifra):
    """Parâmetro 4 (técnicas + complexidade da tablatura)."""
    linhas = []
    for bloco in RE_TAB.findall(cifra):
        texto = html.unescape(RE_TAG.sub('', bloco))
        linhas += [l for l in texto.split('\n') if RE_LINHA_TAB.match(l)]
    if not linhas:
        return np.zeros(9)
    corpo = [l.split('|', 1)[1] for l in linhas]
    total = sum(len(l) for l in corpo) or 1
    notas = [int(n) for l in corpo for n in re.findall(r'\d+', l)]
    # Notas simultâneas: agrupa linhas em blocos de 6 cordas e conta colunas com mais de uma nota
    simult, colunas_com_nota = 0, 0
    for i in range(0, len(corpo) - 5, 6):
        bloco = corpo[i:i + 6]
        largura = min(len(l) for l in bloco)
        for c in range(largura):
            n = sum(l[c].isdigit() for l in bloco)
            if n:
                colunas_com_nota += 1
                simult += n > 1
    return np.array([
        1.0,                                                   # tem tablatura
        sum(l.count('h') for l in corpo) / total * 100,        # hammer-on
        sum(l.count('p') for l in corpo) / total * 100,        # pull-off
        sum(l.count('b') for l in corpo) / total * 100,        # bend
        sum(l.count('/') + l.count('\\') for l in corpo) / total * 100,  # slide
        sum(l.count('~') for l in corpo) / total * 100,        # vibrato
        len(notas) / total * 100,                              # densidade de notas
        float(np.mean(notas)) if notas else 0.0,               # casa média (região do braço)
        simult / colunas_com_nota if colunas_com_nota else 0.0,  # proporção de notas simultâneas
    ])


def extrair(cifra):
    """Extrai todas as características de uma cifra.

    Retorna dict com:
      tokens_palavra_acorde: str  (parâmetro 2, tokens "palavra@grau_classe")
      ritmo: np.array            (parâmetro 3, distâncias entre acordes em caracteres)
      tipos: np.array            (parâmetro 4, distribuição de tipos de acorde + complexidade)
      tecnicas: np.array         (parâmetro 4, técnicas e complexidade da tablatura)
    """
    cifra = cifra or ''
    sem_tab = re.sub(r'^.*?<pre>', '', RE_TAB.sub('', cifra), count=1, flags=re.S)  # remove o título <h1>
    linhas = sem_tab.split('\n')

    # 1ª passada: todos os acordes, para estimar o tom
    todos = []
    for l in linhas:
        for _, s in _acordes_da_linha(l) or []:
            a = analisar_acorde(s)
            if a:
                todos.append(a)
    tonica = estimar_tom(todos)

    pares, distancias, trocas_por_char = [], [], []
    for i, l in enumerate(linhas):
        acordes = _acordes_da_linha(l)
        if not acordes or i + 1 >= len(linhas):
            continue
        letra = html.unescape(RE_TAG.sub('', linhas[i + 1]))
        if not letra.strip() or _acordes_da_linha(linhas[i + 1]) or RE_LINHA_TAB.match(letra):
            continue
        cols = []
        for col, s in acordes:
            a = analisar_acorde(s)
            if not a:
                continue
            palavra = _palavra_na_coluna(letra, col)
            if palavra:
                grau = (a[0] - tonica) % 12
                pares.append(f'{normalizar_palavra(palavra)}@{grau}_{a[1]}')
            cols.append(col)
        distancias += list(np.diff(cols))
        if cols:
            trocas_por_char.append(len(cols) / max(len(letra.strip()), 1))

    if distancias:
        d = np.array(distancias, dtype=float)
        ritmo = np.array([d.mean(), d.std(), np.median(d), np.mean(trocas_por_char) * 100])
    elif trocas_por_char:
        ritmo = np.array([0.0, 0.0, 0.0, np.mean(trocas_por_char) * 100])
    else:
        ritmo = np.zeros(4)

    hist = np.zeros(len(CLASSES_ACORDE))
    for _, classe, _, _ in todos:
        hist[CLASSES_ACORDE.index(classe)] += 1
    if todos:
        hist /= len(todos)
        complexidade = np.array([
            np.mean([a[2] for a in todos]),               # notas por acorde
            np.mean([a[3] for a in todos]),               # proporção com baixo invertido
            len({(a[0], a[1]) for a in todos}),           # acordes distintos
        ])
    else:
        complexidade = np.zeros(3)

    return {
        'tokens_palavra_acorde': ' '.join(pares),
        'ritmo': ritmo,
        'tipos': np.concatenate([hist, complexidade]),
        'tecnicas': _tecnicas_tablatura(cifra),
    }
