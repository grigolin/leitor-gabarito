"""Geometria da folha de gabarito. Fonte única da verdade.

O gerador da folha e o leitor importam deste módulo, portanto não podem
divergir. As posições são normalizadas (0..1) sobre o *retângulo canônico*,
que é delimitado pelos cantos EXTERNOS dos quatro marcadores ArUco — e não
pela borda do papel.
"""

A4_LARGURA_MM = 210.0
A4_ALTURA_MM = 297.0

MARGEM_MM = 15.0
MARCADOR_MM = 15.0

ARUCO_DICT_NOME = "DICT_4X4_50"
ARUCO_ID_SUP_ESQ = 0
ARUCO_ID_SUP_DIR = 1
ARUCO_ID_INF_DIR = 2
ARUCO_ID_INF_ESQ = 3
ARUCO_IDS = (ARUCO_ID_SUP_ESQ, ARUCO_ID_SUP_DIR, ARUCO_ID_INF_DIR, ARUCO_ID_INF_ESQ)

CANONICA_MM_LARGURA = A4_LARGURA_MM - 2 * MARGEM_MM
CANONICA_MM_ALTURA = A4_ALTURA_MM - 2 * MARGEM_MM
CANONICA_LARGURA = 1000
CANONICA_ALTURA = round(
    CANONICA_LARGURA * CANONICA_MM_ALTURA / CANONICA_MM_LARGURA
)

N_QUESTOES = 8
ALTERNATIVAS = ("A", "B", "C", "D")
N_ALTERNATIVAS = len(ALTERNATIVAS)

BOLINHA_RAIO = 18
BOLINHA_INSET = 0.80
ANEL_INTERNO = 1.35
ANEL_EXTERNO = 1.75

LIMIAR_VAZIA = 0.20
LIMIAR_MARCADA = 0.50
CONF_LIMIAR_VAZIA = 0.25
CONF_LIMIAR_MARCADA = 0.55

NOME_RECT = (0.10, 0.030, 0.90, 0.105)
TITULO_Y = 0.125
INSTRUCAO_Y = 0.160
QUESTOES_Y0 = 0.20
QUESTOES_Y1 = 0.90
ALTERNATIVA_X = (0.30, 0.45, 0.60, 0.75)
ROTULO_X = 0.18

TITULO = "GABARITO"
ROTULO_NOME = "Nome:"
INSTRUCAO = (
    "Preencha a bolinha por inteiro. "
    "Marcar mais de uma alternativa anula a questão."
)


def centro_bolinha(questao, alternativa, largura=CANONICA_LARGURA, altura=CANONICA_ALTURA):
    """Centro em px da bolinha (questao 0..7, alternativa 0..3)."""
    fracao_x = ALTERNATIVA_X[alternativa]
    passo = (QUESTOES_Y1 - QUESTOES_Y0) / N_QUESTOES
    fracao_y = QUESTOES_Y0 + (questao + 0.5) * passo
    return fracao_x * largura, fracao_y * altura


def retangulos_marcadores(largura=CANONICA_LARGURA, altura=CANONICA_ALTURA):
    """Retângulo (x0, y0, x1, y1) ocupado por cada marcador, em px."""
    lado = MARCADOR_MM * largura / CANONICA_MM_LARGURA
    return {
        ARUCO_ID_SUP_ESQ: (0.0, 0.0, lado, lado),
        ARUCO_ID_SUP_DIR: (largura - lado, 0.0, largura, lado),
        ARUCO_ID_INF_DIR: (largura - lado, altura - lado, largura, altura),
        ARUCO_ID_INF_ESQ: (0.0, altura - lado, lado, altura),
    }
