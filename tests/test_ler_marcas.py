import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.ler_marcas import ler_marcas


def _ler(marcas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    return ler_marcas(A.alinhar(sintetico.degradar(pagina, rng, **kwargs)))


def test_formato_da_matriz():
    leituras = _ler({}, 0)
    assert len(leituras) == L.N_QUESTOES
    assert all(len(linha) == L.N_ALTERNATIVAS for linha in leituras)


def test_folha_em_branco_nao_tem_nenhuma_marcada():
    for linha in _ler({}, 1):
        for leitura in linha:
            assert not leitura.marcada
            assert not leitura.ambigua
            assert leitura.preenchimento < L.LIMIAR_VAZIA


@pytest.mark.parametrize("estilo", ["cheia", "boa"])
def test_marca_boa_e_lida_como_marcada(estilo):
    marcas = {q: [(q % L.N_ALTERNATIVAS, estilo)] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 2)
    for questao in range(L.N_QUESTOES):
        esperada = questao % L.N_ALTERNATIVAS
        for alternativa in range(L.N_ALTERNATIVAS):
            leitura = leituras[questao][alternativa]
            assert leitura.marcada is (alternativa == esperada), (
                f"q{questao} alt{alternativa}: preenchimento={leitura.preenchimento:.3f}"
            )


def test_marca_parcial_fica_ambigua():
    marcas = {q: [(1, "parcial")] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 3)
    ambiguas = sum(1 for q in range(L.N_QUESTOES) if leituras[q][1].ambigua)
    assert ambiguas >= 7, "marca de ~50% deveria cair na faixa ambígua"


def test_borracha_mal_apagada_nao_vira_marcacao():
    marcas = {q: [(2, "apagada")] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 4)
    for questao in range(L.N_QUESTOES):
        assert not leituras[questao][2].marcada


def test_a_medida_e_invariante_a_iluminacao():
    """A mesma marca no lado claro e no escuro tem que medir quase igual.

    É este teste que proíbe a volta ao limiar global: com Otsu, a bolinha
    VAZIA do lado escuro media 1,000.
    """
    marcas = {
        q: [(a, "boa") for a in range(L.N_ALTERNATIVAS)]
        for q in range(L.N_QUESTOES)
    }
    leituras = _ler(marcas, 5, brilho_escuro=0.35)
    valores = [
        leituras[q][a].preenchimento
        for q in range(L.N_QUESTOES)
        for a in range(L.N_ALTERNATIVAS)
    ]
    assert min(valores) > L.LIMIAR_MARCADA
    assert max(valores) - min(valores) < 0.30


def test_iluminacao_ruim_nao_inventa_marcacao():
    leituras = _ler({}, 6, brilho_escuro=0.30)
    for linha in leituras:
        for leitura in linha:
            assert not leitura.marcada


def test_duas_marcas_na_mesma_questao_sao_ambas_lidas():
    leituras = _ler({0: [(0, "cheia"), (2, "cheia")]}, 7)
    assert leituras[0][0].marcada
    assert leituras[0][2].marcada
    assert not leituras[0][1].marcada
    assert not leituras[0][3].marcada
