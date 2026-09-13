"""Converte a foto numa imagem canônica de tamanho fixo.

Todo o caos físico — perspectiva, rotação, escala, folha de cabeça para
baixo — fica confinado aqui. Os módulos seguintes só veem a canônica.
"""

import cv2
import numpy as np

from . import layout as L


class FolhaNaoEncontrada(Exception):
    """Os quatro marcadores não foram todos localizados na foto."""


# `detectMarkers` devolve os 4 cantos no referencial do próprio marcador
# (sup-esq, sup-dir, inf-dir, inf-esq), e a identidade do marcador independe
# de como ele está girado na foto. Logo, para cada marcador basta pegar o
# canto que aponta para fora da folha: é ele que define o retângulo canônico.
_CANTO_EXTERNO = {
    L.ARUCO_ID_SUP_ESQ: 0,
    L.ARUCO_ID_SUP_DIR: 1,
    L.ARUCO_ID_INF_DIR: 2,
    L.ARUCO_ID_INF_ESQ: 3,
}

_DESTINO = {
    L.ARUCO_ID_SUP_ESQ: (0.0, 0.0),
    L.ARUCO_ID_SUP_DIR: (float(L.CANONICA_LARGURA), 0.0),
    L.ARUCO_ID_INF_DIR: (float(L.CANONICA_LARGURA), float(L.CANONICA_ALTURA)),
    L.ARUCO_ID_INF_ESQ: (0.0, float(L.CANONICA_ALTURA)),
}


def _detector():
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    return cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())


def alinhar(foto):
    """Foto (BGR ou cinza) -> canônica 1000×1483 em tons de cinza."""
    cinza = foto if foto.ndim == 2 else cv2.cvtColor(foto, cv2.COLOR_BGR2GRAY)

    cantos, ids, _ = _detector().detectMarkers(cinza)
    achados = {} if ids is None else {int(i): c[0] for i, c in zip(ids.flatten(), cantos)}
    faltando = [i for i in L.ARUCO_IDS if i not in achados]
    if faltando:
        raise FolhaNaoEncontrada(
            f"Não encontrei {len(faltando)} dos 4 marcadores (faltaram os IDs "
            f"{faltando}). Enquadre a folha inteira, com os quatro cantos visíveis."
        )

    origem = np.array(
        [achados[i][_CANTO_EXTERNO[i]] for i in L.ARUCO_IDS], dtype=np.float32
    )
    destino = np.array([_DESTINO[i] for i in L.ARUCO_IDS], dtype=np.float32)
    transformada = cv2.getPerspectiveTransform(origem, destino)
    return cv2.warpPerspective(
        cinza,
        transformada,
        (L.CANONICA_LARGURA, L.CANONICA_ALTURA),
        flags=cv2.INTER_CUBIC,
    )
