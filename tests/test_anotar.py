import numpy as np

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.anotar import anotar
from gabarito.corrigir import corrigir
from gabarito.ler_marcas import ler_marcas

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def _pipeline(marcas, semente):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    canonica = A.alinhar(sintetico.degradar(pagina, rng))
    leituras = ler_marcas(canonica)
    return canonica, leituras, corrigir(leituras, CHAVE)


def test_saida_colorida_do_tamanho_certo():
    imagem = anotar(*_pipeline(sintetico.marcas_de_respostas(CHAVE), 0))
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA, 3)
    assert imagem.dtype == np.uint8


def test_acerto_desenha_verde_e_erro_desenha_vermelho():
    respostas = list(CHAVE)
    respostas[0] = "D"  # errada de propósito
    imagem = anotar(*_pipeline(sintetico.marcas_de_respostas(respostas), 1))
    azul, verde, vermelho = imagem[:, :, 0], imagem[:, :, 1], imagem[:, :, 2]
    assert (
        (verde.astype(int) - azul.astype(int) > 60)
        & (verde.astype(int) - vermelho.astype(int) > 60)
    ).sum() > 50
    assert (
        (vermelho.astype(int) - verde.astype(int) > 60)
        & (vermelho.astype(int) - azul.astype(int) > 60)
    ).sum() > 50


def test_nao_altera_a_canonica_recebida():
    canonica, leituras, resultado = _pipeline(sintetico.marcas_de_respostas(CHAVE), 2)
    antes = canonica.copy()
    anotar(canonica, leituras, resultado)
    assert np.array_equal(canonica, antes)
