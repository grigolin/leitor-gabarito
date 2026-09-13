import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L


def _canonica(respostas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    return A.alinhar(sintetico.foto(respostas, rng, **kwargs))


def test_dimensoes_da_canonica():
    imagem = _canonica(["A"] * L.N_QUESTOES, 0)
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
    assert imagem.dtype == np.uint8


def test_a_marca_cai_onde_o_layout_diz():
    respostas = ["A", "B", "C", "D", "D", "C", "B", "A"]
    imagem = _canonica(respostas, 1, estilo="cheia")
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    for questao, letra in enumerate(respostas):
        medias = []
        for alternativa in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(questao, alternativa)
            recorte = imagem[
                int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio
            ]
            medias.append(recorte.mean())

        marcada = L.ALTERNATIVAS.index(letra)
        assert medias[marcada] < 120, f"q{questao} {letra} deveria estar escura"
        for alternativa, media in enumerate(medias):
            if alternativa != marcada:
                # A degradação padrão aplica um gradiente até 55% de brilho;
                # por isso a separação precisa ser local, não um valor absoluto.
                assert media > medias[marcada] + 80, (
                    f"q{questao}{alternativa} deveria estar mais clara "
                    f"que a marca em {letra}"
                )


@pytest.mark.parametrize("semente", range(10))
def test_alinha_em_varias_degradacoes(semente):
    imagem = _canonica(["A"] * L.N_QUESTOES, semente)
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)


def test_folha_de_cabeca_para_baixo():
    rng = np.random.default_rng(4)
    foto = sintetico.foto(["C"] * L.N_QUESTOES, rng, estilo="cheia")
    de_ponta_cabeca = np.rot90(foto, 2).copy()
    imagem = A.alinhar(de_ponta_cabeca)
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    x, y = L.centro_bolinha(0, L.ALTERNATIVAS.index("C"))
    recorte = imagem[int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio]
    assert recorte.mean() < 120


@pytest.mark.parametrize("lado_maior", [800, 1200, 2000])
def test_varias_escalas(lado_maior):
    imagem = _canonica(["B"] * L.N_QUESTOES, 5, lado_maior=lado_maior, estilo="cheia")
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    x, y = L.centro_bolinha(3, 1)
    recorte = imagem[int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio]
    assert recorte.mean() < 120


def test_sem_marcadores_levanta_excecao():
    branco = np.full((1200, 900), 255, np.uint8)
    with pytest.raises(A.FolhaNaoEncontrada):
        A.alinhar(branco)


def test_um_marcador_cortado_levanta_excecao():
    rng = np.random.default_rng(6)
    foto = sintetico.foto(["A"] * L.N_QUESTOES, rng)
    cortada = foto[:, foto.shape[1] // 4 :].copy()
    with pytest.raises(A.FolhaNaoEncontrada) as erro:
        A.alinhar(cortada)
    assert "marcador" in str(erro.value).lower()


def test_aceita_imagem_colorida():
    import cv2

    rng = np.random.default_rng(7)
    foto = sintetico.foto(["A"] * L.N_QUESTOES, rng)
    colorida = cv2.cvtColor(foto, cv2.COLOR_GRAY2BGR)
    assert A.alinhar(colorida).shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
