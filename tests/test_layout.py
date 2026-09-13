import math

import pytest

from gabarito import layout as L


def test_proporcao_canonica_bate_com_os_milimetros():
    proporcao_mm = L.CANONICA_MM_ALTURA / L.CANONICA_MM_LARGURA
    proporcao_px = L.CANONICA_ALTURA / L.CANONICA_LARGURA
    assert math.isclose(proporcao_px, proporcao_mm, rel_tol=1e-3)


def test_altura_canonica_esperada():
    assert L.CANONICA_LARGURA == 1000
    assert L.CANONICA_ALTURA == 1483


def test_existem_32_bolinhas_distintas():
    centros = [
        L.centro_bolinha(q, a)
        for q in range(L.N_QUESTOES)
        for a in range(L.N_ALTERNATIVAS)
    ]
    assert len(centros) == 32
    assert len(set(centros)) == 32


def test_bolinhas_nao_se_sobrepoem():
    centros = [
        L.centro_bolinha(q, a)
        for q in range(L.N_QUESTOES)
        for a in range(L.N_ALTERNATIVAS)
    ]
    folga = 2 * L.BOLINHA_RAIO * L.ANEL_EXTERNO
    for i, (x1, y1) in enumerate(centros):
        for x2, y2 in centros[i + 1 :]:
            assert math.hypot(x1 - x2, y1 - y2) > folga


def test_aneis_de_fundo_cabem_na_imagem():
    raio = L.BOLINHA_RAIO * L.ANEL_EXTERNO
    for q in range(L.N_QUESTOES):
        for a in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(q, a)
            assert raio < x < L.CANONICA_LARGURA - raio
            assert raio < y < L.CANONICA_ALTURA - raio


def test_nada_invade_a_area_dos_marcadores():
    marcadores = L.retangulos_marcadores()
    assert set(marcadores) == set(L.ARUCO_IDS)

    def sobrepoe(a, b):
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1

    caixas = []
    for q in range(L.N_QUESTOES):
        for a in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(q, a)
            r = L.BOLINHA_RAIO * L.ANEL_EXTERNO
            caixas.append((x - r, y - r, x + r, y + r))
    nx0, ny0, nx1, ny1 = L.NOME_RECT
    caixas.append(
        (
            nx0 * L.CANONICA_LARGURA,
            ny0 * L.CANONICA_ALTURA,
            nx1 * L.CANONICA_LARGURA,
            ny1 * L.CANONICA_ALTURA,
        )
    )
    for caixa in caixas:
        for marcador in marcadores.values():
            assert not sobrepoe(caixa, marcador)


def test_chave_de_limiares_coerente():
    assert 0.0 < L.LIMIAR_VAZIA < L.LIMIAR_MARCADA < 1.0
    assert 0.0 < L.CONF_LIMIAR_VAZIA < L.CONF_LIMIAR_MARCADA < 1.0
    assert 0.0 < L.BOLINHA_INSET < 1.0 < L.ANEL_INTERNO < L.ANEL_EXTERNO
