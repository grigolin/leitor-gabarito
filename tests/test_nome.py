import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L, nome as N


def _canonica(texto="Ana Carolina de Souza"):
    rng = np.random.default_rng(0)
    pagina = sintetico.folha_preenchida({}, nome=texto, rng=rng)
    return A.alinhar(sintetico.degradar(pagina, rng))


def test_recorte_tem_o_tamanho_da_faixa_do_nome():
    recorte = N.recortar_nome(_canonica())
    x0, y0, x1, y1 = L.NOME_RECT
    assert recorte.shape[0] == pytest.approx(
        (y1 - y0) * L.CANONICA_ALTURA, abs=2
    )
    assert recorte.shape[1] == pytest.approx(
        (x1 - x0) * L.CANONICA_LARGURA, abs=2
    )
    assert recorte.ndim == 2


def test_o_recorte_contem_tinta():
    assert N.recortar_nome(_canonica()).min() < 150


def test_recorte_cabe_no_limite_da_api():
    assert max(N.recortar_nome(_canonica()).shape) <= N.LADO_MAIOR_MAXIMO


def test_sem_chave_de_api_devolve_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert N.transcrever(N.recortar_nome(_canonica())) is None


def test_erro_na_api_devolve_none_sem_levantar(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")

    def explodir(*_, **__):
        raise RuntimeError("rede caiu")

    monkeypatch.setattr(N, "_chamar_api", explodir)
    assert N.transcrever(N.recortar_nome(_canonica())) is None


def test_transcricao_bem_sucedida(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(N, "_chamar_api", lambda _: "  Ana Carolina de Souza\n")
    assert N.transcrever(N.recortar_nome(_canonica())) == "Ana Carolina de Souza"


def test_resposta_vazia_ou_ilegivel_vira_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(N, "_chamar_api", lambda _: "   ")
    assert N.transcrever(N.recortar_nome(_canonica())) is None
    monkeypatch.setattr(N, "_chamar_api", lambda _: " ILEGÍVEL ")
    assert N.transcrever(N.recortar_nome(_canonica())) is None


def test_falha_de_importacao_da_api_vira_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(N, "_chamar_api", lambda _: (_ for _ in ()).throw(ImportError()))
    assert N.transcrever(N.recortar_nome(_canonica())) is None
