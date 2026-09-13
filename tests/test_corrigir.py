import pytest

from gabarito import layout as L
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import Leitura

VAZIA = Leitura(preenchimento=0.02, confirmacao=0.00, marcada=False, ambigua=False)
MARCADA = Leitura(preenchimento=0.88, confirmacao=0.91, marcada=True, ambigua=False)
AMBIGUA = Leitura(preenchimento=0.37, confirmacao=0.51, marcada=False, ambigua=True)

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def linha(**posicoes):
    """linha(0=MARCADA) -> [MARCADA, VAZIA, VAZIA, VAZIA]"""
    celulas = [VAZIA] * L.N_ALTERNATIVAS
    for indice, valor in posicoes.items():
        celulas[int(indice)] = valor
    return celulas


def matriz(*linhas):
    assert len(linhas) == L.N_QUESTOES
    return list(linhas)


def todas_em_branco():
    return matriz(*[linha() for _ in range(L.N_QUESTOES)])


def test_gabarito_todo_certo():
    leituras = matriz(
        *[linha(**{str(L.ALTERNATIVAS.index(letra)): MARCADA}) for letra in CHAVE]
    )
    resultado = corrigir(leituras, CHAVE)
    assert resultado.acertos == 8
    assert resultado.total == 8
    assert all(q.estado is Estado.RESPONDIDA for q in resultado.questoes)
    assert all(q.acertou for q in resultado.questoes)


def test_resposta_errada_nao_pontua():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"1": MARCADA})  # marcou B, chave é A
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.RESPONDIDA
    assert resultado.questoes[0].marcada == "B"
    assert resultado.questoes[0].acertou is False
    assert resultado.acertos == 0


def test_duas_marcacoes_anulam_a_questao():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "2": MARCADA})
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.questoes[0].marcada is None
    assert resultado.questoes[0].acertou is False


def test_anulada_mesmo_quando_uma_das_marcadas_e_a_certa():
    """A regra é anular, não dar o benefício da dúvida."""
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "3": MARCADA})  # A é a correta
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.acertos == 0


def test_quatro_marcacoes_anulam():
    leituras = todas_em_branco()
    leituras[0] = [MARCADA] * L.N_ALTERNATIVAS
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.ANULADA


def test_questao_em_branco():
    resultado = corrigir(todas_em_branco(), CHAVE)
    assert all(q.estado is Estado.EM_BRANCO for q in resultado.questoes)
    assert resultado.acertos == 0


def test_ambigua_vira_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": AMBIGUA})
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.REVISAR
    assert resultado.questoes[0].acertou is False


def test_marcada_com_outra_ambigua_vira_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "1": AMBIGUA})
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.REVISAR


def test_anulada_tem_prioridade_sobre_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "1": MARCADA, "2": AMBIGUA})
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.ANULADA


def test_placar_misto():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA})                  # certa
    leituras[1] = linha(**{"0": MARCADA})                  # errada
    leituras[2] = linha(**{"0": MARCADA, "1": MARCADA})    # anulada
    leituras[3] = linha(**{"3": AMBIGUA})                  # revisar
    leituras[4] = linha(**{"0": MARCADA})                  # certa
    resultado = corrigir(leituras, CHAVE)
    assert resultado.acertos == 2
    estados = [q.estado for q in resultado.questoes]
    assert estados[:5] == [
        Estado.RESPONDIDA,
        Estado.RESPONDIDA,
        Estado.ANULADA,
        Estado.REVISAR,
        Estado.RESPONDIDA,
    ]
    assert [q.numero for q in resultado.questoes] == list(range(1, 9))


def test_chave_de_tamanho_errado():
    with pytest.raises(ValueError, match="8"):
        corrigir(todas_em_branco(), ["A", "B"])


def test_chave_com_letra_invalida():
    with pytest.raises(ValueError, match="E"):
        corrigir(todas_em_branco(), ["E"] + CHAVE[1:])
