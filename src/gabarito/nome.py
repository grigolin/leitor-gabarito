"""Recorta a faixa do nome e transcreve o manuscrito.

Este é o único módulo do leitor que depende de rede. Por isso a transcrição
falha de forma segura: qualquer problema devolve ``None`` e não interrompe a
correção da folha.
"""

import base64
import io
import os

import numpy as np
from PIL import Image

from . import layout as L

MODELO = "claude-sonnet-5"
LADO_MAIOR_MAXIMO = 2576
INSTRUCAO = (
    "Você transcreve nomes manuscritos de folhas de prova. "
    "O nome pode estar em letra cursiva ou de forma. "
    "Responda APENAS com o nome transcrito, sem comentários. "
    "Se não conseguir ler, responda exatamente: ILEGÍVEL"
)


def recortar_nome(canonica):
    """Devolve a faixa ``NOME_RECT`` da imagem canônica em tons de cinza."""
    imagem = Image.fromarray(np.asarray(canonica)).convert("L")
    x0, y0, x1, y1 = L.NOME_RECT
    return np.asarray(
        imagem.crop(
            (
                int(round(x0 * L.CANONICA_LARGURA)),
                int(round(y0 * L.CANONICA_ALTURA)),
                int(round(x1 * L.CANONICA_LARGURA)),
                int(round(y1 * L.CANONICA_ALTURA)),
            )
        )
    )


def _para_base64(recorte):
    buffer = io.BytesIO()
    Image.fromarray(np.asarray(recorte)).convert("L").save(buffer, "PNG")
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def _chamar_api(recorte):
    """Envia o recorte para a API Anthropic e devolve o texto bruto."""
    import anthropic

    cliente = anthropic.Anthropic()
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=256,
        system=INSTRUCAO,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": _para_base64(recorte),
                        },
                    },
                    {"type": "text", "text": "Transcreva o nome manuscrito."},
                ],
            }
        ],
    )
    return resposta.content[0].text


def transcrever(recorte):
    """Devolve o nome transcrito, ou ``None`` se não for possível.

    A função é deliberadamente tolerante: ausência de chave, falha de
    importação, erro de rede/API, resposta vazia e ``ILEGÍVEL`` não propagam
    exceções para o restante do pipeline.
    """
    try:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None
        texto = (_chamar_api(recorte) or "").strip()
        if not texto or texto.upper() == "ILEGÍVEL":
            return None
        return texto
    except Exception:
        return None
