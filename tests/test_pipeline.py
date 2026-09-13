"""Foto sintética -> placar. É aqui que o sistema é julgado."""

import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import ler_marcas

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def _corrigir_foto(marcas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    return corrigir(ler_marcas(A.alinhar(sintetico.degradar(pagina, rng, **kwargs))), CHAVE)


def _marcas_de(respostas, estilo="boa"):
    return sintetico.marcas_de_respostas(respostas, estilo)


@pytest.mark.parametrize("semente", range(200))
def test_propriedade_200_folhas_aleatorias(semente):
    """Respostas sorteadas, degradação sorteada, leitura tem que bater sempre."""
    rng = np.random.default_rng(10_000 + semente)
    respostas = [L.ALTERNATIVAS[int(i)] for i in rng.integers(0, 4, L.N_QUESTOES)]
    esperado = sum(1 for dada, certa in zip(respostas, CHAVE) if dada == certa)

    pagina = sintetico.folha_preenchida(_marcas_de(respostas), rng=rng)
    resultado = corrigir(
        ler_marcas(A.alinhar(sintetico.degradar(pagina, rng))), CHAVE
    )

    lidas = [q.marcada for q in resultado.questoes]
    assert lidas == respostas, f"semente {semente}: lido {lidas}, esperado {respostas}"
    assert resultado.acertos == esperado


def test_duas_marcacoes_anulam_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    marcas[0] = [(0, "cheia"), (2, "cheia")]
    resultado = _corrigir_foto(marcas, 1)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.acertos == 7


def test_questao_em_branco_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    del marcas[3]
    resultado = _corrigir_foto(marcas, 2)
    assert resultado.questoes[3].estado is Estado.EM_BRANCO
    assert resultado.acertos == 7


def test_marca_pela_metade_vira_revisar_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    marcas[5] = [(L.ALTERNATIVAS.index(CHAVE[5]), "parcial")]
    resultado = _corrigir_foto(marcas, 3)
    assert resultado.questoes[5].estado is Estado.REVISAR
    assert resultado.acertos == 7


def test_folha_de_cabeca_para_baixo():
    rng = np.random.default_rng(4)
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng)
    foto = np.rot90(sintetico.degradar(pagina, rng), 2).copy()
    resultado = corrigir(ler_marcas(A.alinhar(foto)), CHAVE)
    assert resultado.acertos == 8


@pytest.mark.parametrize("escala", [0.85, 1.0, 1.15])
def test_impressao_maior_e_menor(escala):
    """Impressão fora de escala: os marcadores carregam a escala junto."""
    rng = np.random.default_rng(5)
    largura = int(round(2480 * escala))
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng, largura_px=largura)
    resultado = corrigir(ler_marcas(A.alinhar(sintetico.degradar(pagina, rng))), CHAVE)
    assert resultado.acertos == 8


@pytest.mark.parametrize("lado_maior", [800, 1200, 1600, 2400])
def test_varias_distancias_de_foto(lado_maior):
    resultado = _corrigir_foto(_marcas_de(CHAVE), 6, lado_maior=lado_maior)
    assert resultado.acertos == 8


def test_iluminacao_pior_que_a_nominal():
    """O lado escuro a 0,30 é onde o limiar global falhava. Não pode voltar."""
    resultado = _corrigir_foto(_marcas_de(CHAVE), 7, brilho_escuro=0.30)
    assert resultado.acertos == 8


def test_foto_sem_marcadores_nunca_produz_placar():
    rng = np.random.default_rng(8)
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng)
    foto = sintetico.degradar(pagina, rng)
    cortada = foto[foto.shape[0] // 3 :, :].copy()
    with pytest.raises(A.FolhaNaoEncontrada):
        A.alinhar(cortada)
