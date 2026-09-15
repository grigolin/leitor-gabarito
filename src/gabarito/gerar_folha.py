"""Desenha a folha de gabarito em branco.

Tudo é desenhado a partir de `layout`, em qualquer resolução, para que a
versão de tela (canônica, 1000×1483) e a versão de impressão (A4 a 300 DPI)
sejam literalmente o mesmo desenho em escalas diferentes.
"""

import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import layout as L

# Cada distribuição guarda as mesmas fontes em um lugar diferente, então a
# lista cobre os dois layouts comuns: Debian/Ubuntu aninham por família sob
# `truetype/`, Arch/Manjaro e Fedora usam `TTF/` ou a família na raiz.
_CAMINHOS_DE_FONTE = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
)


def fonte(tamanho_px):
    """Fonte TrueType/OpenType escalável, com acentuação.

    Não há fallback silencioso para `ImageFont.load_default()`: essa fonte
    embutida do Pillow não tem glifos acentuados — "ã", "õ" e "ç" caem todos
    na mesma caixa de "glifo ausente" — que é exatamente a corrupção que
    motivou desenhar com Pillow em vez de `cv2.putText`. Se nenhum caminho
    candidato existir, falha alto com `RuntimeError` em vez de desenhar texto
    quebrado silenciosamente.

    A variável de ambiente `GABARITO_FONTE`, se definida, tem prioridade
    sobre os caminhos padrão — deve apontar para um arquivo de fonte
    existente.
    """
    tamanho = max(8, int(round(tamanho_px)))

    candidatos = []
    caminho_env = os.environ.get("GABARITO_FONTE")
    if caminho_env:
        if not Path(caminho_env).exists():
            raise RuntimeError(
                f"GABARITO_FONTE aponta para um arquivo inexistente: "
                f"{caminho_env!r}. Corrija a variável de ambiente ou remova-a "
                "para usar os caminhos padrão."
            )
        candidatos.append(caminho_env)
    candidatos.extend(_CAMINHOS_DE_FONTE)

    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)

    raise RuntimeError(
        "Nenhuma fonte TrueType com acentuação foi encontrada. Caminhos "
        "tentados: " + ", ".join(candidatos) + ". Instale uma dessas fontes "
        "ou defina a variável de ambiente GABARITO_FONTE apontando para um "
        "arquivo .ttf/.otf válido."
    )


def _colar_marcadores(imagem, largura, altura):
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    lado = int(round(L.MARCADOR_MM * largura / L.CANONICA_MM_LARGURA))
    posicoes = {
        L.ARUCO_ID_SUP_ESQ: (0, 0),
        L.ARUCO_ID_SUP_DIR: (largura - lado, 0),
        L.ARUCO_ID_INF_DIR: (largura - lado, altura - lado),
        L.ARUCO_ID_INF_ESQ: (0, altura - lado),
    }
    for identificador, posicao in posicoes.items():
        marcador = cv2.aruco.generateImageMarker(dicionario, identificador, lado)
        imagem.paste(Image.fromarray(marcador), posicao)


def desenhar(largura=L.CANONICA_LARGURA, altura=L.CANONICA_ALTURA):
    """Retângulo canônico da folha, em tons de cinza."""
    escala = largura / L.CANONICA_LARGURA
    imagem = Image.new("L", (largura, altura), 255)
    pincel = ImageDraw.Draw(imagem)

    _colar_marcadores(imagem, largura, altura)

    pincel.text(
        (largura / 2, L.TITULO_Y * altura),
        L.TITULO,
        font=fonte(30 * escala),
        fill=0,
        anchor="mm",
    )

    x0, y0, x1, y1 = L.NOME_RECT
    caixa = (x0 * largura, y0 * altura, x1 * largura, y1 * altura)
    pincel.rectangle(caixa, outline=0, width=max(1, int(2 * escala)))
    pincel.text(
        (caixa[0] + 10 * escala, caixa[1] + 8 * escala),
        L.ROTULO_NOME,
        font=fonte(18 * escala),
        fill=0,
    )

    pincel.text(
        (largura / 2, L.INSTRUCAO_Y * altura),
        L.INSTRUCAO,
        font=fonte(17 * escala),
        fill=0,
        anchor="mm",
    )

    raio = L.BOLINHA_RAIO * escala
    fonte_rotulo = fonte(20 * escala)
    fonte_letra = fonte(15 * escala)
    for questao in range(L.N_QUESTOES):
        _, y = L.centro_bolinha(questao, 0, largura, altura)
        pincel.text(
            (L.ROTULO_X * largura, y),
            f"{questao + 1}",
            font=fonte_rotulo,
            fill=0,
            anchor="mm",
        )
        for alternativa in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(questao, alternativa, largura, altura)
            pincel.ellipse(
                (x - raio, y - raio, x + raio, y + raio),
                outline=0,
                width=max(1, int(round(2 * escala))),
            )
            pincel.text(
                (x, y - raio - 12 * escala),
                L.ALTERNATIVAS[alternativa],
                font=fonte_letra,
                fill=0,
                anchor="mm",
            )

    return np.asarray(imagem)


def desenhar_a4(largura_px=2480):
    """Página A4 inteira, com a margem em branco onde o conteúdo não entra."""
    altura_px = int(round(largura_px * L.A4_ALTURA_MM / L.A4_LARGURA_MM))
    px_por_mm = largura_px / L.A4_LARGURA_MM
    pagina = Image.new("L", (largura_px, altura_px), 255)
    conteudo = desenhar(
        int(round(L.CANONICA_MM_LARGURA * px_por_mm)),
        int(round(L.CANONICA_MM_ALTURA * px_por_mm)),
    )
    deslocamento = int(round(L.MARGEM_MM * px_por_mm))
    pagina.paste(Image.fromarray(conteudo), (deslocamento, deslocamento))
    return np.asarray(pagina)


def gerar_pdf(caminho):
    """Salva a folha em A4 a 300 DPI, pronta para imprimir."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(desenhar_a4(2480)).save(caminho, "PDF", resolution=300.0)
