"""Desenha o resultado sobre a folha alinhada.

Serve de demonstração e de depuração ao mesmo tempo: se o software errar,
o erro fica visível na imagem em vez de escondido num número.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import layout as L
from .corrigir import Estado
from .gerar_folha import fonte

VERDE = (0, 170, 0)
VERMELHO = (0, 0, 220)
AMARELO = (0, 190, 220)
CINZA = (130, 130, 130)


def _cor_da_bolinha(leitura, questao_resultado):
    if leitura.ambigua:
        return AMARELO
    if not leitura.marcada:
        return None
    if questao_resultado.estado is Estado.ANULADA:
        return CINZA
    return VERDE if questao_resultado.acertou else VERMELHO


def anotar(canonica, leituras, resultado):
    """Canônica em cinza + leituras + resultado -> imagem BGR anotada."""
    base = cv2.cvtColor(canonica, cv2.COLOR_GRAY2BGR)
    imagem = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB))
    pincel = ImageDraw.Draw(imagem)
    fonte_estado = fonte(16)
    raio = L.BOLINHA_RAIO + 6

    for questao in range(L.N_QUESTOES):
        questao_resultado = resultado.questoes[questao]
        for alternativa in range(L.N_ALTERNATIVAS):
            leitura = leituras[questao][alternativa]
            cor = _cor_da_bolinha(leitura, questao_resultado)
            if cor is None:
                continue
            x, y = L.centro_bolinha(questao, alternativa)
            pincel.ellipse(
                (x - raio, y - raio, x + raio, y + raio),
                outline=(cor[2], cor[1], cor[0]),
                width=4,
            )

        if questao_resultado.estado is Estado.ANULADA:
            x0, _ = L.centro_bolinha(questao, 0)
            x1, y = L.centro_bolinha(questao, L.N_ALTERNATIVAS - 1)
            pincel.line(
                (x0 - raio, y, x1 + raio, y),
                fill=(CINZA[2], CINZA[1], CINZA[0]),
                width=3,
            )

        _, y = L.centro_bolinha(questao, L.N_ALTERNATIVAS - 1)
        rotulo = {
            Estado.RESPONDIDA: f"{questao_resultado.marcada}  (certa: {questao_resultado.correta})",
            Estado.ANULADA: "ANULADA",
            Estado.EM_BRANCO: "EM BRANCO",
            Estado.REVISAR: "REVISAR",
        }[questao_resultado.estado]
        cor_rotulo = VERDE if questao_resultado.acertou else (
            AMARELO if questao_resultado.estado is Estado.REVISAR else VERMELHO
        )
        # A 789 px, com fonte 16, o rótulo mais longo termina por volta de
        # 884 px — dentro dos 1000 px da folha. Rótulos maiores seriam cortados.
        pincel.text(
            (L.ALTERNATIVA_X[-1] * L.CANONICA_LARGURA + raio + 14, y),
            rotulo,
            font=fonte_estado,
            fill=(cor_rotulo[2], cor_rotulo[1], cor_rotulo[0]),
            anchor="lm",
        )

    return cv2.cvtColor(np.asarray(imagem), cv2.COLOR_RGB2BGR)
