"""Leitura de playlists do Spotify.

Desde as mudanças da Web API, ler as faixas de uma playlist exige login do usuário (OAuth Authorization Code).
Fluxo: abrir /spotify/login -> autorizar no Spotify -> /callback salva o token (renovado automaticamente).
Variáveis no .env: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET e, opcionalmente, SPOTIFY_REDIRECT_URI.
"""
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode

import requests

API = 'https://api.spotify.com/v1'
CONTAS = 'https://accounts.spotify.com'
ESCOPOS = 'playlist-read-private playlist-read-collaborative'
ARQUIVO_TOKEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.spotify_token.json')

_estados = {}  # estado -> timestamp


class ErroSpotify(Exception):
    pass


class LoginNecessario(ErroSpotify):
    pass


def _credenciais():
    cid, segredo = os.getenv('SPOTIFY_CLIENT_ID'), os.getenv('SPOTIFY_CLIENT_SECRET')
    if not cid or not segredo:
        raise ErroSpotify('Defina SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET no arquivo .env')
    return cid, segredo


def redirect_uri():
    return os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8000/callback')


# ---------- OAuth ----------

def url_login():
    cid, _ = _credenciais()
    # Limpa estados expirados (mais de 10 minutos)
    agora = time.time()
    expirados = [k for k, v in _estados.items() if agora - v > 600]
    for k in expirados:
        _estados.pop(k, None)

    estado = secrets.token_urlsafe(16)
    _estados[estado] = agora
    return f'{CONTAS}/authorize?' + urlencode({
        'client_id': cid, 'response_type': 'code', 'redirect_uri': redirect_uri(),
        'scope': ESCOPOS, 'state': estado,
    })


def _pedir_token(dados):
    r = requests.post(f'{CONTAS}/api/token', data=dados, auth=_credenciais(), timeout=15)
    if r.status_code != 200:
        raise ErroSpotify(f'Falha ao obter token do Spotify ({r.status_code}): {r.text[:200]}')
    token = r.json()
    token['expira'] = time.time() + token['expires_in']
    return token


def _salvar(token):
    with open(ARQUIVO_TOKEN, 'w') as f:
        json.dump(token, f)
    os.chmod(ARQUIVO_TOKEN, 0o600)


def concluir_login(code, estado):
    agora = time.time()
    criado = _estados.pop(estado, None)
    if criado is None or (agora - criado > 600):
        raise ErroSpotify('Login inválido ou expirado: abra /spotify/login novamente')
    _salvar(_pedir_token({'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri()}))


def _token_usuario():
    if not os.path.exists(ARQUIVO_TOKEN):
        raise LoginNecessario('Faça login no Spotify abrindo /spotify/login')
    try:
        with open(ARQUIVO_TOKEN) as f:
            token = json.load(f)
        if 'expira' not in token or 'access_token' not in token or 'refresh_token' not in token:
            raise LoginNecessario('Token do Spotify incompleto: abra /spotify/login novamente')
    except (json.JSONDecodeError, OSError):
        raise LoginNecessario('Token do Spotify corrompido: abra /spotify/login novamente')

    if time.time() > token['expira'] - 60:
        novo = _pedir_token({'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']})
        novo.setdefault('refresh_token', token['refresh_token'])  # o Spotify nem sempre devolve um novo
        _salvar(novo)
        token = novo
    return token['access_token']


def _get(url, **params):
    r = requests.get(url, params=params, headers={'Authorization': f'Bearer {_token_usuario()}'}, timeout=15)
    if r.status_code == 401:
        raise LoginNecessario('Sessão do Spotify expirada: abra /spotify/login novamente')
    if r.status_code != 200:
        raise ErroSpotify(f'Spotify respondeu {r.status_code} em {url}: {r.text[:200]}')
    return r.json()


# ---------- Playlists ----------

def id_playlist(playlist):
    """Aceita link (open.spotify.com/playlist/ID), URI (spotify:playlist:ID) ou o próprio ID."""
    m = re.search(r'playlist[/:]([A-Za-z0-9]{22})', playlist)
    if m:
        return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9]{22}', playlist):
        return playlist
    raise ErroSpotify('Playlist inválida: use o link, a URI ou o ID da playlist')


def faixas_da_playlist(playlist, max_faixas=500):
    """Retorna [{'nome': str, 'artistas': [str]}] de faixas da playlist (até max_faixas)."""
    url = f'{API}/playlists/{id_playlist(playlist)}/items'
    params = {'limit': 50}
    faixas = []
    while url and len(faixas) < max_faixas:
        dados = _get(url, **params)
        for registro in dados.get('items', []):
            t = registro.get('item') or registro.get('track')  # a API renomeou "track" para "item"
            if t and t.get('name') and t.get('type', 'track') == 'track':
                faixas.append({'nome': t['name'], 'artistas': [a['name'] for a in t.get('artists', [])]})
                if len(faixas) >= max_faixas:
                    return faixas
        url, params = dados.get('next'), {}
    return faixas
