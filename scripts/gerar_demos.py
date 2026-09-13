"""Gera materiais visuais para demonstrar o leitor sem papel impresso.

Os arquivos de entrada podem ser enviados diretamente para o Streamlit. Para
cada cenário também são salvos o PDF da folha preenchida, a folha alinhada e a
imagem de conferência produzida pelo pipeline.

Execute na raiz do projeto com:

    uv run python scripts/gerar_demos.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests"))

import sintetico  # noqa: E402
from gabarito import alinhar, anotar, corrigir, gerar_folha, layout  # noqa: E402
from gabarito.ler_marcas import ler_marcas  # noqa: E402


CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]
DESTINO = RAIZ / "saida" / "demos"


def _marcas_personalizadas(especificacao):
    """Converte uma lista de respostas/estados em marcas sintéticas."""
    marcas = {}
    for questao, valor in enumerate(especificacao):
        if valor is None:
            continue
        if isinstance(valor, str):
            marcas[questao] = [
                (layout.ALTERNATIVAS.index(valor), "boa")
            ]
        else:
            marcas[questao] = [
                (layout.ALTERNATIVAS.index(letra), estilo)
                for letra, estilo in valor
            ]
    return marcas


CASOS = [
    {
        "id": "01_tudo_certo",
        "titulo": "Tudo correto",
        "descricao": "Oito respostas preenchidas corretamente.",
        "marcas": CHAVE,
        "semente": 101,
        "degradacao": {},
        "rotacionar": False,
    },
    {
        "id": "02_anulada_branco",
        "titulo": "Anulada e em branco",
        "descricao": "A questão 3 tem duas marcas e a questão 5 está vazia.",
        "marcas": [
            "A",
            "B",
            [("A", "cheia"), ("D", "cheia")],
            "D",
            None,
            "B",
            "C",
            "D",
        ],
        "semente": 102,
        "degradacao": {},
        "rotacionar": False,
    },
    {
        "id": "03_erro_revisar",
        "titulo": "Erro e revisão",
        "descricao": "Há respostas erradas e uma marca parcial que pede revisão.",
        "marcas": [
            "A",
            "A",
            "C",
            "D",
            "B",
            [("B", "parcial")],
            "C",
            "D",
        ],
        "semente": 103,
        "degradacao": {},
        "rotacionar": False,
    },
    {
        "id": "04_luz_dificil",
        "titulo": "Iluminação difícil",
        "descricao": "A folha correta passa por sombra e gradiente forte.",
        "marcas": CHAVE,
        "semente": 104,
        "degradacao": {
            "brilho_escuro": 0.30,
            "sombra": True,
            "qualidade_jpeg": 45,
        },
        "rotacionar": False,
    },
    {
        "id": "05_cabeca_baixo",
        "titulo": "Foto de cabeça para baixo",
        "descricao": "A imagem é girada 180 graus antes do alinhamento.",
        "marcas": CHAVE,
        "semente": 105,
        "degradacao": {},
        "rotacionar": True,
    },
]


def _salvar_pdf(pagina, caminho):
    Image.fromarray(pagina).save(caminho, "PDF", resolution=300.0)


def _estados(resultado):
    return [questao.estado.value for questao in resultado.questoes]


def gerar_caso(caso):
    rng = np.random.default_rng(caso["semente"])
    marcas = _marcas_personalizadas(caso["marcas"])
    pagina = sintetico.folha_preenchida(
        marcas,
        nome="Ana Carolina de Souza",
        rng=rng,
    )
    foto = sintetico.degradar(pagina, rng, **caso["degradacao"])
    if caso["rotacionar"]:
        foto = np.rot90(foto, 2).copy()

    canonica = alinhar.alinhar(foto)
    leituras = ler_marcas(canonica)
    resultado = corrigir.corrigir(leituras, CHAVE)
    conferencia = anotar.anotar(canonica, leituras, resultado)

    prefixo = DESTINO / caso["id"]
    _salvar_pdf(pagina, prefixo.with_suffix(".pdf"))
    cv2.imwrite(str(prefixo.with_name(prefixo.name + "_entrada.jpg")), foto)
    cv2.imwrite(str(prefixo.with_name(prefixo.name + "_alinhada.png")), canonica)
    cv2.imwrite(
        str(prefixo.with_name(prefixo.name + "_conferencia.png")), conferencia
    )

    return {
        "id": caso["id"],
        "titulo": caso["titulo"],
        "descricao": caso["descricao"],
        "acertos": resultado.acertos,
        "total": resultado.total,
        "estados": _estados(resultado),
        "entrada": prefixo.name + "_entrada.jpg",
        "pdf": prefixo.name + ".pdf",
        "alinhada": prefixo.name + "_alinhada.png",
        "conferencia": prefixo.name + "_conferencia.png",
    }


def _gerar_painel(resultados):
    """Monta uma imagem única com as cinco conferências."""
    largura_miniatura = 420
    altura_miniatura = 622
    margem = 28
    cabecalho = 82
    colunas = 2
    linhas = (len(resultados) + colunas - 1) // colunas
    painel = Image.new(
        "RGB",
        (
            colunas * largura_miniatura + (colunas + 1) * margem,
            linhas * (altura_miniatura + cabecalho) + (linhas + 1) * margem,
        ),
        "white",
    )
    pincel = ImageDraw.Draw(painel)
    fonte_titulo = gerar_folha.fonte(26)
    fonte_resultado = gerar_folha.fonte(22)

    for indice, resultado in enumerate(resultados):
        coluna = indice % colunas
        linha = indice // colunas
        x = margem + coluna * largura_miniatura
        y = margem + linha * (altura_miniatura + cabecalho)
        pincel.text(
            (x, y),
            resultado["titulo"],
            fill="black",
            font=fonte_titulo,
        )
        pincel.text(
            (x, y + 34),
            f"Resultado: {resultado['acertos']}/{resultado['total']}",
            fill="#008800",
            font=fonte_resultado,
        )
        imagem = Image.open(DESTINO / resultado["conferencia"]).convert("RGB")
        miniatura = ImageOps.contain(
            imagem,
            (largura_miniatura, altura_miniatura),
            method=Image.Resampling.LANCZOS,
        )
        painel.paste(miniatura, (x, y + cabecalho))

    painel.save(DESTINO / "painel_resumo.png")


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    resultados = [gerar_caso(caso) for caso in CASOS]
    _gerar_painel(resultados)
    (DESTINO / "resultados.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for resultado in resultados:
        print(
            f"{resultado['id']}: "
            f"{resultado['acertos']}/{resultado['total']} — "
            f"{', '.join(resultado['estados'])}"
        )


if __name__ == "__main__":
    main()
