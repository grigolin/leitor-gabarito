"""Interface de demonstração do leitor de gabarito."""

import io

import cv2
import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError

from gabarito import alinhar as A, gerar_folha, layout as L, nome as N
from gabarito.anotar import anotar
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import ler_marcas


CHAVE_PADRAO = ["A", "B", "C", "D", "A", "B", "C", "D"]


@st.cache_data(show_spinner=False)
def _pdf_folha():
    """Gera o PDF da folha sem deixar uma falha de fonte derrubar a página.

    A folha em branco não depende de nenhuma entrada do usuário, então o
    desenho A4 é reaproveitado entre os reruns disparados pela chave de
    respostas.
    """
    buffer = io.BytesIO()
    Image.fromarray(gerar_folha.desenhar_a4(2480)).convert("RGB").save(
        buffer, "PDF", resolution=300.0
    )
    return buffer.getvalue()


def _tabela_resultado(resultado):
    icone = {
        Estado.RESPONDIDA: "",
        Estado.ANULADA: "🚫",
        Estado.EM_BRANCO: "—",
        Estado.REVISAR: "⚠️",
    }
    return [
        {
            "Questão": questao.numero,
            "Marcou": questao.marcada or icone[questao.estado],
            "Correta": questao.correta,
            "Situação": (
                ("✅ certa" if questao.acertou else "❌ errada")
                if questao.estado is Estado.RESPONDIDA
                else questao.estado.value.replace("_", " ").capitalize()
            ),
        }
        for questao in resultado.questoes
    ]


st.set_page_config(page_title="Leitor de gabarito", layout="wide")
st.title("Leitor de gabarito")

with st.sidebar:
    st.header("Chave de respostas")
    chave = [
        st.selectbox(
            f"Questão {numero + 1}",
            L.ALTERNATIVAS,
            index=L.ALTERNATIVAS.index(CHAVE_PADRAO[numero]),
            key=f"chave_{numero}",
        )
        for numero in range(L.N_QUESTOES)
    ]

    st.divider()
    st.header("Folha em branco")
    try:
        pdf = _pdf_folha()
    except RuntimeError as erro:
        st.error(f"Não foi possível gerar a folha: {erro}")
        st.caption(
            "Instale uma fonte TrueType com acentuação ou defina "
            "GABARITO_FONTE apontando para um arquivo .ttf/.otf."
        )
    else:
        st.download_button(
            "Baixar folha para imprimir (PDF)",
            data=pdf,
            file_name="folha-gabarito.pdf",
            mime="application/pdf",
        )
    st.caption(
        "Imprima em A4, sem 'ajustar à página'. Fotografe a folha inteira, "
        "com os quatro marcadores dos cantos visíveis."
    )

origem = st.radio("Imagem", ["Enviar arquivo", "Usar a câmera"], horizontal=True)
enviado = (
    st.file_uploader("Foto do gabarito", type=["jpg", "jpeg", "png"])
    if origem == "Enviar arquivo"
    else st.camera_input("Fotografe o gabarito")
)

if enviado is None:
    st.info("Envie uma foto do gabarito preenchido para começar.")
    st.stop()

try:
    foto = np.asarray(Image.open(enviado).convert("L"))
except (UnidentifiedImageError, OSError) as erro:
    st.error(f"Não foi possível abrir a imagem: {erro}")
    st.stop()

try:
    canonica = A.alinhar(foto)
except A.FolhaNaoEncontrada as erro:
    st.error(str(erro))
    st.image(foto, caption="Foto recebida", clamp=True)
    st.stop()

leituras = ler_marcas(canonica)
resultado = corrigir(leituras, chave)

esquerda, direita = st.columns([3, 2])

with esquerda:
    st.subheader("Conferência")
    try:
        anotada = anotar(canonica, leituras, resultado)
    except RuntimeError as erro:
        st.warning(
            "Não foi possível desenhar os rótulos da conferência por causa da "
            f"fonte: {erro}"
        )
        st.image(canonica, caption="Folha alinhada (sem anotações)", clamp=True)
    else:
        st.image(
            cv2.cvtColor(anotada, cv2.COLOR_BGR2RGB),
            caption="Verde: certa · vermelho: errada · amarelo: revisar · cinza: anulada",
            width="stretch",
        )

with direita:
    st.subheader("Nome")
    recorte = N.recortar_nome(canonica)
    st.image(recorte, caption="Recorte do nome", clamp=True, width="stretch")
    transcrito = N.transcrever(recorte)
    if transcrito is None:
        st.caption(
            "Não foi possível transcrever automaticamente (sem "
            "GEMINI_API_KEY, sem rede ou nome ilegível). Digite o nome abaixo."
        )
    st.text_input("Nome do aluno", value=transcrito or "")

    st.subheader("Resultado")
    st.metric("Acertos", f"{resultado.acertos} / {resultado.total}")
    st.table(_tabela_resultado(resultado))
