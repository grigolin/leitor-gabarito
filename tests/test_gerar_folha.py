import cv2
import numpy as np
import pytest

from gabarito import gerar_folha, layout as L


@pytest.fixture(scope="module")
def canonica():
    return gerar_folha.desenhar()


def test_dimensoes_e_tipo(canonica):
    assert canonica.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
    assert canonica.dtype == np.uint8


def test_os_quatro_marcadores_sao_detectaveis_nos_cantos_certos():
    pagina = gerar_folha.desenhar_a4()
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())
    cantos, ids, _ = detector.detectMarkers(pagina)

    assert ids is not None
    achados = {int(i): c[0] for i, c in zip(ids.flatten(), cantos)}
    assert set(achados) == set(L.ARUCO_IDS)

    altura, largura = pagina.shape
    meio_x, meio_y = largura / 2, altura / 2
    esperado = {
        L.ARUCO_ID_SUP_ESQ: (True, True),
        L.ARUCO_ID_SUP_DIR: (False, True),
        L.ARUCO_ID_INF_DIR: (False, False),
        L.ARUCO_ID_INF_ESQ: (True, False),
    }
    for identificador, (esquerda, cima) in esperado.items():
        cx, cy = achados[identificador].mean(axis=0)
        assert (cx < meio_x) == esquerda
        assert (cy < meio_y) == cima


def test_as_32_bolinhas_estao_vazias(canonica):
    for q in range(L.N_QUESTOES):
        for a in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(q, a)
            raio = int(L.BOLINHA_RAIO * 0.5)
            recorte = canonica[
                int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio
            ]
            assert recorte.mean() > 240, f"bolinha {q},{a} não está vazia"


def test_as_bolinhas_tem_contorno_visivel(canonica):
    x, y = L.centro_bolinha(0, 0)
    raio = L.BOLINHA_RAIO
    recorte = canonica[int(y) - raio - 3 : int(y) + raio + 3, int(x) - raio - 3 : int(x) + raio + 3]
    assert recorte.min() < 128


def test_gera_pdf(tmp_path):
    destino = tmp_path / "folha.pdf"
    gerar_folha.gerar_pdf(destino)
    assert destino.exists()
    assert destino.stat().st_size > 5_000
