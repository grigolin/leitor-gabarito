"""Recorta a faixa do nome e transcreve o manuscrito.

Este é o único módulo do leitor que depende de rede. Por isso a transcrição
falha de forma segura: qualquer problema devolve ``None`` e não interrompe a
correção da folha.
"""

import io
import os

import numpy as np
from PIL import Image

from . import layout as L

MODELO = "gemini-2.5-flash"
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


def _para_png(recorte):
    buffer = io.BytesIO()
    Image.fromarray(np.asarray(recorte)).convert("L").save(buffer, "PNG")
    return buffer.getvalue()


def _chamar_api(recorte):
    """Envia o recorte para a API Gemini e devolve o texto bruto."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resposta = cliente.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(data=_para_png(recorte), mime_type="image/png"),
            f"{INSTRUCAO} Transcreva o nome manuscrito.",
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=256,
        ),
    )
    return resposta.text or ""


def transcrever(recorte):
    """Devolve o nome transcrito, ou ``None`` se não for possível.

    A função é deliberadamente tolerante: ausência de chave, falha de
    importação, erro de rede/API, resposta vazia e ``ILEGÍVEL`` não propagam
    exceções para o restante do pipeline.
    """
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            return None
        texto = (_chamar_api(recorte) or "").strip()
        if not texto or texto.upper() == "ILEGÍVEL":
            return None
        return texto
    except Exception:
        return None
