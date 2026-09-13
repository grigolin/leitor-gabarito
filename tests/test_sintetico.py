import cv2
import numpy as np
import pytest

import sintetico
from gabarito import layout as L


def test_bolinha_marcada_fica_escura_e_o_resto_nao():
    marcas = sintetico.marcas_de_respostas(["A"] * L.N_QUESTOES, estilo="cheia")
    pagina = sintetico.folha_preenchida(
        marcas, rng=np.random.default_rng(0), largura_px=2480
    )
    assert pagina.dtype == np.uint8
    assert pagina.ndim == 2

    px_por_mm = 2480 / L.A4_LARGURA_MM
    largura_conteudo = L.CANONICA_MM_LARGURA * px_por_mm
    altura_conteudo = L.CANONICA_MM_ALTURA * px_por_mm
    deslocamento = L.MARGEM_MM * px_por_mm
    escala = largura_conteudo / L.CANONICA_LARGURA
    raio = int(L.BOLINHA_RAIO * escala * L.BOLINHA_INSET)
    yy, xx = np.ogrid[-raio:raio, -raio:raio]
    disco = xx * xx + yy * yy <= raio * raio

    def media(questao, alternativa):
        x, y = L.centro_bolinha(questao, alternativa, largura_conteudo, altura_conteudo)
        x, y = int(deslocamento + x), int(deslocamento + y)
        recorte = pagina[y - raio : y + raio, x - raio : x + raio]
        return recorte[disco].mean()

    for questao in range(L.N_QUESTOES):
        assert media(questao, 0) < 80, f"q{questao} A deveria estar preenchida"
        for alternativa in range(1, L.N_ALTERNATIVAS):
            assert media(questao, alternativa) > 240, f"q{questao} alt{alternativa} deveria estar vazia"


def test_degradar_preserva_a_detectabilidade_dos_marcadores():
    rng = np.random.default_rng(1)
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())
    for semente in range(10):
        imagem = sintetico.foto(
            ["A", "B", "C", "D", "A", "B", "C", "D"],
            rng=np.random.default_rng(semente),
        )
        _, ids, _ = detector.detectMarkers(imagem)
        assert ids is not None, f"semente {semente}: nenhum marcador"
        assert set(int(i) for i in ids.flatten()) >= set(L.ARUCO_IDS)


def test_degradar_muda_a_imagem_e_o_tamanho():
    rng = np.random.default_rng(2)
    pagina = sintetico.folha_preenchida(
        sintetico.marcas_de_respostas(["B"] * L.N_QUESTOES), rng=rng
    )
    imagem = sintetico.degradar(pagina, rng, lado_maior=1200)
    assert max(imagem.shape) == 1200
    assert imagem.shape != pagina.shape


@pytest.mark.parametrize("estilo", sintetico.ESTILOS)
def test_todos_os_estilos_desenham_algo(estilo):
    rng = np.random.default_rng(3)
    marcas = {0: [(0, estilo)]}
    pagina = sintetico.folha_preenchida(marcas, rng=rng, largura_px=1240)
    limpa = sintetico.folha_preenchida({}, rng=np.random.default_rng(3), largura_px=1240)
    assert pagina.astype(int).sum() < limpa.astype(int).sum()
