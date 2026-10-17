import os
import unittest
import numpy as np
import pandas as pd

from recomendador import spotify
from recomendador.caracteristicas import (
    analisar_acorde,
    estimar_tom,
    RE_TAB,
)
from recomendador.modelo import (
    Recomendador,
    montar_catalogo,
    normalizar_titulo,
)


class TestCaracteristicas(unittest.TestCase):
    def test_analisar_acorde(self):
        # C maior: fundamental 0, classe 'maior', 3 notas, sem baixo invertido
        c = analisar_acorde('C')
        self.assertIsNotNone(c)
        self.assertEqual(c[0], 0)
        self.assertEqual(c[1], 'maior')
        self.assertFalse(c[3])

        # Am: fundamental 9, classe 'menor'
        am = analisar_acorde('Am')
        self.assertIsNotNone(am)
        self.assertEqual(am[0], 9)
        self.assertEqual(am[1], 'menor')

        # D/F#: fundamental 2, classe 'maior', baixo invertido F#
        df = analisar_acorde('D/F#')
        self.assertIsNotNone(df)
        self.assertEqual(df[0], 2)
        self.assertTrue(df[3])

        # Não acorde
        self.assertIsNone(analisar_acorde('Solo'))

    def test_estimar_tom(self):
        # C, G, Am, F -> Tom C (0)
        acordes = [analisar_acorde(x) for x in ['C', 'G', 'Am', 'F']]
        self.assertEqual(estimar_tom(acordes), 0)

    def test_re_tab_single_and_double_span(self):
        html_tab1 = '<span class="tablatura">e|--0--\nB|--1--</span></span>'
        html_tab2 = '<span class="tablatura">e|--3--\nB|--0--</span>'
        self.assertEqual(len(RE_TAB.findall(html_tab1)), 1)
        self.assertEqual(len(RE_TAB.findall(html_tab2)), 1)


class TestModelo(unittest.TestCase):
    def setUp(self):
        # Dataset sintético pequeno para testes rápidos
        self.dados = pd.DataFrame([
            {
                'Artist': 'Legião Urbana',
                'Genre': 'Rock',
                'Lyrics': 'Tempo Perdido\nTodos os dias quando acordo\nNão tenho mais o tempo que passou',
                'Chords': '<html><h1>Tempo Perdido</h1><div><pre><b>C</b>\nTodos os dias\n<b>Am</b>\nquando acordo</pre></div></html>',
            },
            {
                'Artist': 'Legião Urbana',
                'Genre': 'Rock',
                'Lyrics': 'Pais e Filhos\nÉ preciso amar as pessoas como se não houvesse amanhã',
                'Chords': '<html><h1>Pais e Filhos<h1><div><pre><b>C</b>\nÉ preciso amar\n<b>G</b>\nas pessoas</pre></div></html>',
            },
            {
                'Artist': 'Lulu Santos',
                'Genre': 'Pop',
                'Lyrics': 'Como Uma Onda\nNada do que foi será de novo do jeito que já foi um dia',
                'Chords': '<html><h1>Como Uma Onda (Zen-Surfismo)</h1><div><pre><b>C</b>\nNada do que foi\n<b>F</b>\nserá de novo</pre></div></html>',
            },
            {
                'Artist': 'Lulu Santos',
                'Genre': 'Pop',
                'Lyrics': 'Apenas Mais Uma de Amor\nEu gosto tanto de você que até prefiro esconder',
                'Chords': '<html><h1>Apenas Mais Uma de Amor</h1><div><pre><b>Am</b>\nEu gosto tanto\n<b>Em</b>\nde você</pre></div></html>',
            },
            {
                'Artist': 'Chitãozinho & Xororó',
                'Genre': 'Sertanejo',
                'Lyrics': 'Evidências\nQuando eu digo que deixei de te amar é porque eu te amo',
                'Chords': None,  # Música sem cifra
            },
        ])

    def test_normalizar_titulo(self):
        self.assertEqual(normalizar_titulo('Como Uma Onda (Zen-Surfismo)'), 'como uma onda')
        self.assertEqual(normalizar_titulo('Tempo Perdido [Remastered]'), 'tempo perdido')
        self.assertEqual(normalizar_titulo('Música feat. Convidado'), 'musica')
        self.assertEqual(normalizar_titulo('Pais e Filhos - Ao Vivo'), 'pais e filhos')

    def test_montar_catalogo(self):
        cat = montar_catalogo(self.dados)
        self.assertEqual(len(cat), 5)
        # Verifica que o título com fechamento h1 malformado (<h1>...<h1>) e com fechamento correto foram pareados
        tp = cat[(cat['Artist'] == 'Legião Urbana') & (cat['chave'] == 'tempo perdido')]
        self.assertEqual(len(tp), 1)
        self.assertTrue(pd.notna(tp['Chords'].iloc[0]))

        pf = cat[(cat['Artist'] == 'Legião Urbana') & (cat['chave'] == 'pais e filhos')]
        self.assertEqual(len(pf), 1)
        self.assertTrue(pd.notna(pf['Chords'].iloc[0]))

    def test_localizar_com_indice_o1(self):
        rec = object.__new__(Recomendador)
        rec.catalogo = montar_catalogo(self.dados)
        rec._criar_mapa_indices()

        idx, nao_encontradas = rec.localizar([
            ('Legião Urbana', 'Tempo Perdido'),
            ('Lulu Santos', 'Como Uma Onda'),
            ('Artista Inexistente', 'Musica Inexistente'),
        ])
        self.assertEqual(len(idx), 2)
        self.assertEqual(len(nao_encontradas), 1)
        self.assertEqual(nao_encontradas[0], 'Artista Inexistente - Musica Inexistente')

    def test_recomendar_percentil_positivo_e_sementes_fracas(self):
        # Instancia e treina recomendador sobre dataset sintético
        rec = object.__new__(Recomendador)
        rec._treinar(self.dados)

        # Localiza Tempo Perdido (Legião)
        idx_tp, _ = rec.localizar([('Legião Urbana', 'Tempo Perdido')])
        idx_pf, _ = rec.localizar([('Legião Urbana', 'Pais e Filhos')])
        self.assertTrue(len(idx_tp) > 0)

        # Recomenda passando Tempo Perdido como semente principal e Pais e Filhos como semente fraca
        recs = rec.recomendar(
            sementes=idx_tp,
            excluir=idx_tp,
            sementes_fracas=idx_pf,
            pesos={'letra': 0.5, 'palavra_acorde': 0.0, 'ritmo': 0.0, 'acordes': 0.0, 'artista_genero': 0.5},
            limite=3,
        )

        # Tempo Perdido não deve constar nas recomendações (excluído)
        nomes_rec = [r['SongName'] for r in recs]
        self.assertNotIn('Tempo Perdido', nomes_rec)

        # Músicas recomendadas devem ter score > 0 e parâmetros com scores válidos
        for r in recs:
            self.assertGreater(r['score'], 0.0)
            self.assertIn('Artist', r)
            self.assertIn('parametros', r)


class TestSpotify(unittest.TestCase):
    def test_id_playlist(self):
        pid = '37i9dQZF1DXcBWIGoYBM5M'
        self.assertEqual(spotify.id_playlist(pid), pid)
        self.assertEqual(spotify.id_playlist(f'https://open.spotify.com/playlist/{pid}'), pid)
        self.assertEqual(spotify.id_playlist(f'https://open.spotify.com/playlist/{pid}?si=12345'), pid)
        self.assertEqual(spotify.id_playlist(f'spotify:playlist:{pid}'), pid)
        with self.assertRaises(spotify.ErroSpotify):
            spotify.id_playlist('url_invalida')

    def test_token_usuario_sem_refresh_token(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write('{"access_token": "abc", "expira": 0}')  # falta refresh_token
            caminho_temp = f.name

        original_token_path = spotify.ARQUIVO_TOKEN
        try:
            spotify.ARQUIVO_TOKEN = caminho_temp
            with self.assertRaises(spotify.LoginNecessario):
                spotify._token_usuario()
        finally:
            spotify.ARQUIVO_TOKEN = original_token_path
            os.remove(caminho_temp)

    def test_concluir_login_expirado(self):
        # Estado que nunca foi registrado ou expirado
        with self.assertRaises(spotify.ErroSpotify):
            spotify.concluir_login('code_fake', 'estado_inexistente')


if __name__ == '__main__':
    unittest.main()
