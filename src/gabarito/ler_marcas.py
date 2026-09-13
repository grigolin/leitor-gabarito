"""Mede o quanto cada bolinha está preenchida.

Não detecta bolinha nenhuma: depois do alinhamento elas estão em coordenadas
conhecidas. A medida primária é relativa ao papel ao redor da própria
bolinha, e por isso não depende da iluminação. A secundária, por limiar
adaptativo, serve só de conferência.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from . import layout as L


@dataclass(frozen=True)
class Leitura:
    preenchimento: float
    confirmacao: float
    marcada: bool
    ambigua: bool


def _mascaras(raio_janela):
    lado = 2 * raio_janela
    yy, xx = np.mgrid[0:lado, 0:lado]
    distancia = np.hypot(xx - raio_janela, yy - raio_janela)
    disco = distancia <= L.BOLINHA_RAIO * L.BOLINHA_INSET
    anel = (distancia >= L.BOLINHA_RAIO * L.ANEL_INTERNO) & (
        distancia <= L.BOLINHA_RAIO * L.ANEL_EXTERNO
    )
    return disco, anel


def _medir(cinza, binaria, cx, cy, disco, anel, raio_janela):
    x0 = int(round(cx)) - raio_janela
    y0 = int(round(cy)) - raio_janela
    lado = 2 * raio_janela
    janela = cinza[y0 : y0 + lado, x0 : x0 + lado].astype(np.float32)
    janela_binaria = binaria[y0 : y0 + lado, x0 : x0 + lado]

    # Percentil alto do anel = o branco do papel ali naquele ponto da página.
    # Percentil, e não média, para que tinta que vaze da bolinha não contamine
    # a referência de papel.
    fundo = float(np.percentile(janela[anel], 75))
    fundo = max(fundo, 1.0)

    preenchimento = float(np.clip(1.0 - float(janela[disco].mean()) / fundo, 0.0, 1.0))
    confirmacao = float((janela_binaria[disco] > 0).mean())

    acima = preenchimento > L.LIMIAR_MARCADA
    abaixo = preenchimento < L.LIMIAR_VAZIA
    discorda = (acima and confirmacao < L.CONF_LIMIAR_VAZIA) or (
        abaixo and confirmacao > L.CONF_LIMIAR_MARCADA
    )
    return Leitura(
        preenchimento=preenchimento,
        confirmacao=confirmacao,
        marcada=acima and not discorda,
        ambigua=(not acima and not abaixo) or discorda,
    )


def ler_marcas(canonica):
    """Imagem canônica -> matriz 8×4 de `Leitura`."""
    binaria = cv2.adaptiveThreshold(
        canonica,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        10,
    )
    raio_janela = int(np.ceil(L.BOLINHA_RAIO * L.ANEL_EXTERNO)) + 2
    disco, anel = _mascaras(raio_janela)

    return [
        [
            _medir(
                canonica,
                binaria,
                *L.centro_bolinha(questao, alternativa),
                disco,
                anel,
                raio_janela,
            )
            for alternativa in range(L.N_ALTERNATIVAS)
        ]
        for questao in range(L.N_QUESTOES)
    ]
