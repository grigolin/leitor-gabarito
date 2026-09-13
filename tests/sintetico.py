"""Gera folhas preenchidas e fotos falsas, com a verdade conhecida.

Não é um arquivo de teste: é a ferramenta que permite testar o pipeline em
volume sem papel. Os estilos de preenchimento imitam caneta de verdade —
marca irregular, descentrada e nem sempre preta — porque um disco preto
perfeito testaria um problema que não existe.
"""

import io

import cv2
import numpy as np
from PIL import Image, ImageDraw

from gabarito import gerar_folha, layout as L

ESTILOS = ("cheia", "boa", "parcial", "leve", "apagada")


def marcas_de_respostas(respostas, estilo="boa"):
    """['A', 'C', ...] -> {questao: [(alternativa, estilo)]}."""
    marcas = {}
    for questao, letra in enumerate(respostas):
        if letra is None:
            continue
        marcas[questao] = [(L.ALTERNATIVAS.index(letra), estilo)]
    return marcas


def _desenhar_marca(pincel, x, y, raio, estilo, rng):
    if estilo == "cheia":
        deslocamento = raio * 0.05
        tinta = int(rng.integers(10, 40))
        raio_marca = raio * 1.05
    elif estilo == "boa":
        deslocamento = raio * 0.15
        tinta = int(rng.integers(60, 110))
        raio_marca = raio * 0.90
    elif estilo == "parcial":
        deslocamento = raio * 0.10
        tinta = int(rng.integers(40, 90))
        raio_marca = raio * 0.85
    elif estilo == "apagada":
        deslocamento = raio * 0.10
        tinta = int(rng.integers(200, 225))
        raio_marca = raio * 0.80
    elif estilo == "leve":
        tinta = int(rng.integers(30, 80))
        braco = raio * 0.7
        largura = max(1, int(round(raio * 0.18)))
        for sinal in (1, -1):
            pincel.line(
                (x - braco, y - sinal * braco, x + braco, y + sinal * braco),
                fill=tinta,
                width=largura,
            )
        return
    else:
        raise ValueError(f"estilo desconhecido: {estilo}")

    cx = x + float(rng.uniform(-deslocamento, deslocamento))
    cy = y + float(rng.uniform(-deslocamento, deslocamento))
    caixa = (cx - raio_marca, cy - raio_marca, cx + raio_marca, cy + raio_marca)
    if estilo == "parcial":
        # metade da bolinha, com o corte num ângulo aleatório
        inicio = float(rng.uniform(0, 360))
        pincel.pieslice(caixa, inicio, inicio + 180, fill=tinta)
    else:
        pincel.ellipse(caixa, fill=tinta)


def folha_preenchida(marcas, nome="Ana Carolina de Souza", largura_px=2480, rng=None):
    """Página A4 com as marcas pedidas, sem nenhuma degradação."""
    rng = np.random.default_rng() if rng is None else rng
    pagina = Image.fromarray(gerar_folha.desenhar_a4(largura_px)).copy()
    pincel = ImageDraw.Draw(pagina)

    px_por_mm = largura_px / L.A4_LARGURA_MM
    largura_conteudo = L.CANONICA_MM_LARGURA * px_por_mm
    altura_conteudo = L.CANONICA_MM_ALTURA * px_por_mm
    deslocamento = L.MARGEM_MM * px_por_mm
    escala = largura_conteudo / L.CANONICA_LARGURA
    raio = L.BOLINHA_RAIO * escala

    x0, y0, x1, y1 = L.NOME_RECT
    pincel.text(
        (
            deslocamento + (x0 + 0.06) * largura_conteudo,
            deslocamento + (y0 + y1) / 2 * altura_conteudo,
        ),
        nome,
        font=gerar_folha.fonte(22 * escala),
        fill=int(rng.integers(20, 80)),
        anchor="lm",
    )

    for questao, alternativas in marcas.items():
        for alternativa, estilo in alternativas:
            x, y = L.centro_bolinha(questao, alternativa, largura_conteudo, altura_conteudo)
            _desenhar_marca(pincel, deslocamento + x, deslocamento + y, raio, estilo, rng)

    return np.asarray(pagina)


def _gradiente_e_sombra(imagem, rng, brilho_escuro, sombra):
    altura, largura = imagem.shape
    eixo_x = np.linspace(1.0, brilho_escuro, largura, dtype=np.float32)
    if rng.random() < 0.5:
        eixo_x = eixo_x[::-1]
    campo = np.tile(eixo_x, (altura, 1))
    if sombra:
        cx = float(rng.uniform(0, largura))
        cy = float(rng.uniform(0, altura))
        sigma = float(rng.uniform(0.25, 0.55)) * max(altura, largura)
        yy, xx = np.mgrid[0:altura, 0:largura].astype(np.float32)
        distancia = ((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2)
        campo = campo * (1.0 - float(rng.uniform(0.10, 0.30)) * np.exp(-distancia))
    return np.clip(imagem.astype(np.float32) * campo, 0, 255).astype(np.uint8)


def degradar(pagina, rng, lado_maior=1600, brilho_escuro=0.55, sombra=True, qualidade_jpeg=60):
    """Transforma a página perfeita numa foto plausível de celular."""
    altura, largura = pagina.shape

    # Tela 1,5x maior: sem essa folga a rotação joga um marcador para fora do
    # quadro e a "falha de detecção" é na verdade recorte. Aconteceu de verdade
    # durante o spike de viabilidade.
    margem_x, margem_y = int(largura * 0.25), int(altura * 0.25)
    tela = np.full((altura + 2 * margem_y, largura + 2 * margem_x), 235, np.uint8)
    tela[margem_y : margem_y + altura, margem_x : margem_x + largura] = pagina

    alvo_altura, alvo_largura = tela.shape
    origem = np.float32(
        [[margem_x, margem_y],
         [margem_x + largura, margem_y],
         [margem_x + largura, margem_y + altura],
         [margem_x, margem_y + altura]]
    )
    jitter = 0.08 * min(largura, altura)
    destino = origem + rng.uniform(-jitter, jitter, size=(4, 2)).astype(np.float32)
    transformada = cv2.getPerspectiveTransform(origem, destino)

    angulo = float(rng.uniform(-15, 15))
    rotacao = cv2.getRotationMatrix2D((alvo_largura / 2, alvo_altura / 2), angulo, 1.0)
    rotacao = np.vstack([rotacao, [0, 0, 1]]).astype(np.float32)

    imagem = cv2.warpPerspective(
        tela,
        rotacao @ transformada,
        (alvo_largura, alvo_altura),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=235,
    )

    fator = lado_maior / max(imagem.shape)
    imagem = cv2.resize(
        imagem, None, fx=fator, fy=fator, interpolation=cv2.INTER_AREA
    )

    imagem = _gradiente_e_sombra(imagem, rng, brilho_escuro, sombra)
    imagem = cv2.GaussianBlur(imagem, (3, 3), 0.8)

    buffer = io.BytesIO()
    Image.fromarray(imagem).save(buffer, "JPEG", quality=qualidade_jpeg)
    buffer.seek(0)
    return np.asarray(Image.open(buffer).convert("L"))


def foto(respostas, rng, estilo="boa", nome="Ana Carolina de Souza", **kwargs):
    """Atalho: respostas -> foto falsa pronta para o pipeline."""
    pagina = folha_preenchida(marcas_de_respostas(respostas, estilo), nome=nome, rng=rng)
    return degradar(pagina, rng, **kwargs)
