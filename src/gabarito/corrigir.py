"""Aplica as regras da prova. Lógica pura: nenhuma imagem entra aqui."""

from dataclasses import dataclass
from enum import Enum

from . import layout as L


class Estado(str, Enum):
    RESPONDIDA = "RESPONDIDA"
    ANULADA = "ANULADA"
    EM_BRANCO = "EM_BRANCO"
    REVISAR = "REVISAR"


@dataclass(frozen=True)
class ResultadoQuestao:
    numero: int
    estado: Estado
    marcada: str | None
    correta: str
    acertou: bool


@dataclass(frozen=True)
class Resultado:
    questoes: list[ResultadoQuestao]
    acertos: int
    total: int


def _validar_chave(chave):
    try:
        tamanho = len(chave)
    except TypeError as erro:
        raise ValueError(
            f"A chave precisa ter {L.N_QUESTOES} respostas."
        ) from erro

    if tamanho != L.N_QUESTOES:
        raise ValueError(
            f"A chave precisa ter {L.N_QUESTOES} respostas, recebi {tamanho}."
        )

    invalidas = sorted({letra for letra in chave if letra not in L.ALTERNATIVAS})
    if invalidas:
        raise ValueError(
            f"Letras inválidas na chave: {', '.join(invalidas)}. "
            f"Use apenas {', '.join(L.ALTERNATIVAS)}."
        )


def corrigir(leituras, chave):
    """Matriz 8×4 de `Leitura` + chave de respostas -> `Resultado`."""
    _validar_chave(chave)

    questoes = []
    for indice, (linha, correta) in enumerate(zip(leituras, chave)):
        marcadas = [i for i, leitura in enumerate(linha) if leitura.marcada]
        tem_ambigua = any(leitura.ambigua for leitura in linha)

        if len(marcadas) >= 2:
            # Anular tem prioridade: duas marcas cheias são um fato, não uma dúvida.
            estado, letra = Estado.ANULADA, None
        elif tem_ambigua:
            estado, letra = Estado.REVISAR, None
        elif marcadas:
            estado, letra = Estado.RESPONDIDA, L.ALTERNATIVAS[marcadas[0]]
        else:
            estado, letra = Estado.EM_BRANCO, None

        questoes.append(
            ResultadoQuestao(
                numero=indice + 1,
                estado=estado,
                marcada=letra,
                correta=correta,
                acertou=estado is Estado.RESPONDIDA and letra == correta,
            )
        )

    return Resultado(
        questoes=questoes,
        acertos=sum(1 for q in questoes if q.acertou),
        total=L.N_QUESTOES,
    )
