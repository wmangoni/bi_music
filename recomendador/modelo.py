"""Recomendador por similaridade de conteúdo com 4 parâmetros + artista/gênero.

1) letra            TF-IDF das letras
2) palavra_acorde   TF-IDF dos pares "palavra@grau_tipo" (acorde que cai sobre cada palavra)
3) ritmo            distância entre trocas de acorde, em caracteres da letra (ritmo harmônico)
4) acordes          tipos de acorde + complexidade (notas por acorde) + técnicas de tablatura
"""
import html
import os
import re

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import rankdata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, normalize

from .caracteristicas import extrair, normalizar_palavra

VERSAO_CACHE = 3
PARAMETROS = ['letra', 'palavra_acorde', 'ritmo', 'acordes', 'artista_genero']
PESOS_PADRAO = {'letra': 0.35, 'palavra_acorde': 0.2, 'ritmo': 0.1, 'acordes': 0.15, 'artista_genero': 0.2}


def normalizar_titulo(t):
    t = normalizar_palavra(html.unescape(t or ''))
    t = re.sub(r'\(.*?\)|\[.*?\]| - .*$|feat\..*$|part\..*$', '', t)  # remove "(part. X)", " - Remix" etc.
    return re.sub(r'[^\w ]', '', t).strip()


def montar_catalogo(df_bruto):
    """Junta letra e cifra pelo par (artista, título), corrigindo o desalinhamento do CSV raspado."""
    def titulo_cifra(c):
        m = re.search(r'<h1>(.*?)</?h1>', c)
        return normalizar_titulo(m.group(1)) if m else None

    letras = df_bruto.dropna(subset=['Lyrics']).copy()
    letras['SongName'] = letras['Lyrics'].map(lambda l: l.split('\n')[0].strip())
    letras['chave'] = letras['SongName'].map(normalizar_titulo)
    letras = letras.drop_duplicates(['Artist', 'chave'])[['Artist', 'Genre', 'SongName', 'chave', 'Lyrics']]

    cifras = df_bruto.dropna(subset=['Chords']).copy()
    cifras['chave'] = cifras['Chords'].map(titulo_cifra)
    cifras = cifras.dropna(subset=['chave']).drop_duplicates(['Artist', 'chave'])[['Artist', 'chave', 'Chords']]

    cat = letras.merge(cifras, on=['Artist', 'chave'], how='left').reset_index(drop=True)
    cat['artista_chave'] = cat['Artist'].map(normalizar_titulo)
    return cat


class Recomendador:
    def __init__(self, caminho_csv, pasta_cache=None, df_bruto=None):
        pasta_cache = pasta_cache or os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(pasta_cache, exist_ok=True)
        cache = os.path.join(pasta_cache, f'modelo_v{VERSAO_CACHE}_{int(os.path.getmtime(caminho_csv))}.joblib')
        if os.path.exists(cache):
            self.__dict__.update(joblib.load(cache))
            if not hasattr(self, '_mapa_indices'):
                self._criar_mapa_indices()
        else:
            if df_bruto is None:
                df_bruto = pd.read_csv(caminho_csv, encoding='utf-8')
            self._treinar(df_bruto)
            joblib.dump(self.__dict__, cache)

    def _criar_mapa_indices(self):
        self._mapa_indices = {
            (a, t): i
            for i, (a, t) in enumerate(zip(self.catalogo['artista_chave'], self.catalogo['chave']))
        }

    def _treinar(self, df_bruto):
        cat = montar_catalogo(df_bruto)
        tem_cifra = cat['Chords'].notna().to_numpy()
        feats = [extrair(c) if isinstance(c, str) else None for c in cat['Chords']]

        m = {}
        m['letra'] = TfidfVectorizer(min_df=2, max_df=0.5, sublinear_tf=True, max_features=50000) \
            .fit_transform(cat['Lyrics'])
        m['palavra_acorde'] = TfidfVectorizer(min_df=2, sublinear_tf=True, token_pattern=r'\S+') \
            .fit_transform([f['tokens_palavra_acorde'] if f else '' for f in feats])

        def densa(chave, mascara):
            primeiro = next((f[chave] for f in feats if f), None)
            largura = len(primeiro) if primeiro is not None else 0
            x = np.array([f[chave] if f else np.zeros(largura) for f in feats])
            if mascara.any():
                x[mascara] = StandardScaler().fit_transform(x[mascara])
            x[~mascara] = 0
            return x

        tem_tab = np.array([bool(f and f['tecnicas'][0]) for f in feats])
        m['ritmo'] = densa('ritmo', tem_cifra)
        # tipos de acorde (todas as cifras) + técnicas (só quem tem tablatura, senão vira um componente comum)
        m['acordes'] = np.hstack([densa('tipos', tem_cifra), densa('tecnicas', tem_tab)[:, 1:]])

        # Matriz esparsa de artista e gênero para otimizar uso de memória e disco (~47MB -> ~0.5MB)
        generos = sparse.csr_matrix(pd.get_dummies(cat['Genre'], dtype=float).values)
        artistas = sparse.csr_matrix(pd.get_dummies(cat['Artist'], dtype=float).values)
        m['artista_genero'] = sparse.hstack([generos, artistas * 2], format='csr')

        self.matrizes = {k: normalize(v) for k, v in m.items()}
        self.catalogo = cat.drop(columns=['Lyrics', 'Chords'])
        self.tem_cifra = tem_cifra
        self._criar_mapa_indices()

    # ---------- busca ----------

    def localizar(self, musicas):
        """musicas: [(artista, título)] -> índices encontrados no catálogo e lista dos não encontrados."""
        idx, nao_encontradas = [], []
        for artista, titulo in musicas:
            chave = (normalizar_titulo(artista), normalizar_titulo(titulo))
            i = self._mapa_indices.get(chave)
            if i is not None:
                idx.append(i)
            else:
                nao_encontradas.append(f'{artista} - {titulo}')
        return idx, nao_encontradas

    def musicas_dos_artistas(self, artistas):
        a = {normalizar_titulo(x) for x in artistas}
        return list(np.flatnonzero(self.catalogo['artista_chave'].isin(a).to_numpy()))

    def musicas_dos_generos(self, generos_spotify):
        """Mapeia gêneros do Spotify ("brazilian gospel") para os do acervo ("Gospel/Religioso") por palavra em comum."""
        ignorar = {'brazilian', 'classic', 'modern', 'new', 'alternative', 'contemporary', 'and', 'roll', 'music',
                   'brasileiro', 'brasileira', 'de', 'da', 'do', 'e'}
        palavras = lambda g: set(re.findall(r'[a-z0-9]+', normalizar_palavra(g))) - ignorar
        sp = set().union(*[palavras(g) for g in generos_spotify]) if generos_spotify else set()
        acervo = [g for g in self.catalogo['Genre'].dropna().unique() if palavras(g) & sp]
        return list(np.flatnonzero(self.catalogo['Genre'].isin(acervo).to_numpy())), acervo

    def recomendar(self, sementes, excluir=None, sementes_fracas=(), pesos=None, limite=10):
        """sementes: índices que formam o perfil nos 5 parâmetros.
        excluir: índices que não podem ser recomendados (as músicas que já estão na playlist).
        sementes_fracas: índices de apoio (ex: outros faixas dos artistas e gêneros, contam apenas no artista_genero)."""
        excluir = list(sementes if excluir is None else excluir)
        pesos = {**PESOS_PADRAO, **(pesos or {})}
        n = len(self.catalogo)
        score = np.zeros(n)
        soma_pesos = np.zeros(n)  # por candidata: só conta o peso dos parâmetros que ela tem
        detalhe = {}
        for k in PARAMETROS:
            if not pesos[k]:
                continue
            base = list(sementes) + (list(sementes_fracas) if k == 'artista_genero' else [])
            if k in ('palavra_acorde', 'ritmo', 'acordes'):
                base = [i for i in base if self.tem_cifra[i]]
            if not base:
                continue
            x = self.matrizes[k]
            perfil = np.asarray(x[base].mean(axis=0)).ravel()
            perfil /= np.linalg.norm(perfil) or 1
            s = np.asarray(x @ perfil).ravel()
            # Percentil (0-1) calculado sobre similaridades positivas para evitar notas artificiais em empates nulos
            validos = self.tem_cifra if k in ('palavra_acorde', 'ritmo', 'acordes') else np.ones(n, bool)
            pos = validos & (s > 0)
            p = np.zeros(n)
            if pos.any():
                p[pos] = rankdata(s[pos]) / pos.sum()
            detalhe[k] = np.where(validos, p, np.nan)
            score += pesos[k] * p
            soma_pesos += pesos[k] * validos

        # Média ponderada: músicas sem cifra (ou sementes sem cifra) não são penalizadas pelos parâmetros de acordes
        score = np.divide(score, soma_pesos, out=np.zeros(n), where=soma_pesos > 0)
        score[excluir] = -np.inf
        top = np.argsort(-score)[:limite]
        out = []
        for i in top:
            if not np.isfinite(score[i]) or score[i] <= 0:
                break
            linha = self.catalogo.iloc[i]
            out.append({
                'Artist': linha['Artist'], 'Genre': linha['Genre'], 'SongName': linha['SongName'],
                'score': round(float(score[i]), 4),
                'parametros': {k: round(float(v[i]), 4) for k, v in detalhe.items() if not np.isnan(v[i])},
            })
        return out
