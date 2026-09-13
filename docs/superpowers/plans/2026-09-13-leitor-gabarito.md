# Leitor de Gabarito — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ler a foto de um gabarito preenchido à mão (8 questões × 4 alternativas) e informar quantas questões foram respondidas corretamente, anulando as que tiverem mais de uma marcação.

**Architecture:** Quatro marcadores ArUco nos cantos da folha permitem uma homografia que converte qualquer foto numa imagem canônica fixa de 1000×1483 px. A partir daí as 32 bolinhas estão em coordenadas conhecidas e basta medir o quanto cada uma está escura — não é preciso detectar bolinha nenhuma. A medida é relativa ao papel ao redor da própria bolinha, o que a torna imune a iluminação desigual. Toda a geometria vive num único módulo (`layout.py`) importado tanto pelo gerador da folha quanto pelo leitor.

**Tech Stack:** Python 3.13, opencv-contrib-python 5.0 (API `ArucoDetector`), numpy, Pillow, Streamlit, SDK `google-genai`, pytest, ambiente gerido por `uv`.

**Spec:** `docs/superpowers/specs/2026-09-13-leitor-gabarito-design.md`

## Global Constraints

- Python **3.13** (o 3.14 do sistema não é usado; `uv` baixa o 3.13).
- OpenCV é `opencv-contrib-python` (o `aruco` não existe no `opencv-python` puro) e está na série **5.0**, que usa a API orientada a objeto: `cv2.aruco.getPredefinedDictionary(...)` + `cv2.aruco.ArucoDetector(dic, cv2.aruco.DetectorParameters())` + `detector.detectMarkers(img)`. As funções soltas do OpenCV ≤4.6 não existem.
- Dicionário ArUco: **`DICT_4X4_50`**, IDs 0=sup-esq, 1=sup-dir, 2=inf-dir, 3=inf-esq. Não trocar por 5×5/6×6 — foram medidos e não são melhores nas resoluções que importam.
- Imagem canônica: **1000 × 1483 px**, tons de cinza. A altura é 1483 (e não 1400) para preservar a proporção de 180×267 mm da região delimitada pelos marcadores; escalas diferentes por eixo deformariam as bolinhas.
- Medida de preenchimento primária é **relativa local** (disco interno normalizado contra o papel num anel ao redor da própria bolinha). Limiares: `< 0,20` vazia, `> 0,50` marcada. **Nunca usar limiar global tipo Otsu** — foi medido e falha: sob gradiente de iluminação, bolinha vazia no lado escuro lê 1,000.
- O `adaptiveThreshold` é medida **secundária**, só pode escalar para `REVISAR`; nunca define uma resposta sozinho. Seus limiares são outros: 0,25 / 0,55.
- Se os 4 marcadores não forem todos encontrados, levantar exceção. **Nunca** emitir placar parcial ou estimado.
- Nomes de módulos, funções e variáveis em português, como neste plano. Mensagens de erro e textos de interface em português.
- Todo texto desenhado na folha usa Pillow (`ImageDraw.text`), nunca `cv2.putText` — as fontes Hershey do OpenCV não têm acentuação e "questão" sairia corrompido.

---

## Estado da execução

**Última atualização: 2026-09-13. Tasks 1–10 concluídas.**

Trabalho concluído nas branches `implementacao` e `main`, ambas publicadas. A
`main` recebeu o fast-forward da `implementacao` no commit `732fc31`.

| Task | Estado | Commits |
|---|---|---|
| 1 — Projeto e geometria | ✅ concluída | `0a5fae3` |
| 2 — Gerar a folha em branco | ✅ concluída | `7b2deca`, `9dbb24f` |
| 3 — Gerador sintético de fotos | ✅ concluída | `fd575fa` |
| 4 — Alinhamento por ArUco | ✅ concluída | `1003c3c` |
| 5 — Medir o preenchimento | ✅ concluída | `f5ffb99` |
| 6 — Regras de correção | ✅ concluída | `460c4e5` |
| 7 — Integração do pipeline | ✅ concluída | `405c093` |
| 8 — Imagem de conferência | ✅ concluída | `ed0efa3` |
| 9 — Leitura do nome | ✅ concluída | `e1dfc89` |
| 10 — Interface Streamlit e README | ✅ concluída | `3a3b17f` |

Suíte atual: 286 testes passando (`uv run pytest -q`). A verificação manual do
Streamlit confirmou upload sintético, placar `6/8`, anulação, questão em branco,
download da folha e atualização do placar ao alterar a chave.

Depois da execução original, a Task 9 foi migrada de Anthropic para Gemini: o
projeto usa `google-genai`, `GEMINI_API_KEY` e o modelo `gemini-2.5-flash`. A
suíte continua com 286 testes passando e uma chamada manual real com uma folha
sintética retornou corretamente `Ana Carolina de Souza`.

### Para retomar

As Tasks 3–10 foram executadas. O `layout.py` e o `gerar_folha.py` já existem e
não devem ser reescritos a partir dos blocos de código deste plano.

Os checklists e blocos de código das Tasks 3–10 abaixo são o roteiro histórico
da execução. Para o estado final, prevalecem os arquivos no repositório, os
commits da tabela acima e os 286 testes passando.

### Divergências entre o plano e o código já escrito

Os blocos de código das Tasks 1 e 2 abaixo são o texto **original** do plano. O
código realmente em `src/` diverge dele em quatro pontos, todos decididos durante
a execução, todos deliberados. **O código é a verdade; os blocos abaixo ficam como
registro histórico.**

1. **`fonte()` não tem mais fallback silencioso.** O plano caía em
   `ImageFont.load_default()` quando nenhuma fonte do sistema era encontrada. Medimos
   e essa fonte colapsa `ã`, `õ` e `ç` no mesmo glifo de "ausente" — exatamente a
   corrupção que motivou usar Pillow em vez de `cv2.putText`. Agora levanta
   `RuntimeError` listando os caminhos tentados, e aceita a variável de ambiente
   `GABARITO_FONTE` como override de maior prioridade.
   **Consequência para as Tasks 3 e 8, que usam `fonte()`:** ela pode levantar
   exceção. Em máquina sem Arial nem DejaVu, defina `GABARITO_FONTE`.
2. **`_colar_marcadores` calcula `lado` uma única vez** e deriva as posições dos
   quatro cantos desse mesmo inteiro, em vez de pegar `x0`/`y0` dos floats de
   `L.retangulos_marcadores()`. Os dois arredondamentos podiam discordar em 1px nos
   marcadores da direita e de baixo, e o `paste` do PIL cortaria uma coluna em
   silêncio. `L.retangulos_marcadores()` continua existindo, usada pelos testes da
   Task 1.
3. **`test_as_32_bolinhas_estao_vazias` usa `raio = int(L.BOLINHA_RAIO * 0.5)`**, não
   `int(L.BOLINHA_RAIO * L.BOLINHA_INSET)`. Com meio-lado 14 os cantos do quadrado
   ficam a 19,8px do centro e cruzam o contorno impresso (raio 18), derrubando a média
   para ~245 — perto demais do limite de 240 do próprio teste.
4. **`test_os_quatro_marcadores_...` compara com `==`, não com `is`.** `cx` e `meio_x`
   vêm de `ndarray.mean()`, então a comparação devolve `numpy.bool_`, que nunca é
   idêntico a `True`/`False` do Python — o teste como estava no plano falharia sempre,
   mesmo com a geometria correta.

Fora isso, `gerar_pdf` salva a imagem em modo `L` direto (o plano convertia para RGB
sem necessidade, triplicando o raster embutido).

### Pendências menores, deferidas de propósito

- `import pytest` não usado em `tests/test_layout.py` (ruff F401).
- `pythonpath = ["tests"]` no pytest ini é redundante com o install editável.
- Em resoluções diferentes da padrão, as margens da página em `desenhar_a4` podem
  diferir 1px entre os lados opostos. Só estética; não afeta a geometria canônica.
- `_colar_marcadores` recria o dicionário ArUco e recarrega a fonte a cada chamada de
  `desenhar()`.

### Revisão visual da folha (feita, mas não automatizada)

A folha gerada foi inspecionada: os 4 marcadores estão nos cantos, a acentuação de
"questão" sai correta, a caixa do nome não encosta nos marcadores e as 8 linhas
A–D estão alinhadas. Sugestões cosméticas ainda não aplicadas, à espera de decisão:
o título "GABARITO" está abaixo da caixa de nome em vez de acima; as letras A/B/C/D
se repetem em todas as linhas em vez de aparecerem uma vez como cabeçalho.

**Nada disso foi validado em papel impresso.** Ver seção 10 da spec.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `pyproject.toml` | dependências, versão do Python, config do pytest |
| `src/gabarito/layout.py` | geometria e limiares; sem lógica, sem I/O |
| `src/gabarito/gerar_folha.py` | desenha a folha em branco (canônica e A4) e exporta PDF |
| `src/gabarito/alinhar.py` | foto → imagem canônica, via ArUco + homografia |
| `src/gabarito/ler_marcas.py` | imagem canônica → 32 medidas de preenchimento |
| `src/gabarito/corrigir.py` | medidas + chave → estado por questão e placar; lógica pura |
| `src/gabarito/anotar.py` | imagem canônica + resultado → imagem de conferência |
| `src/gabarito/nome.py` | recorta a faixa do nome e transcreve via API |
| `app.py` | interface Streamlit; só amarra os módulos |
| `tests/sintetico.py` | gera folhas preenchidas e fotos falsas degradadas (auxiliar, não é teste) |
| `tests/test_*.py` | um arquivo por módulo, mais `test_pipeline.py` de integração |

---

## Task 1: Projeto e geometria

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/gabarito/__init__.py`, `src/gabarito/layout.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: nada.
- Produces: o módulo `gabarito.layout` (importado como `L` em todo o resto), com as constantes listadas abaixo e as funções `centro_bolinha(questao, alternativa, largura=..., altura=...) -> tuple[float, float]` e `retangulos_marcadores(largura=..., altura=...) -> dict[int, tuple[float, float, float, float]]`.

- [x] **Step 1: Criar o projeto e o ambiente**

```bash
cd /Users/grigolin/Programming/visao
cat > pyproject.toml <<'EOF'
[project]
name = "leitor-gabarito"
version = "0.1.0"
description = "Leitor de gabaritos de prova por visão computacional"
requires-python = ">=3.13"
dependencies = [
    "opencv-contrib-python>=5.0.0.93",
    "numpy>=2.5.3",
    "pillow>=12.3.0",
    "streamlit>=1.63.0",
    "google-genai>=1.0.0",
]

[dependency-groups]
dev = ["pytest>=9.1.1"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gabarito"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
EOF

cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.pyc
.pytest_cache/
saida/
EOF

mkdir -p src/gabarito tests
touch src/gabarito/__init__.py
uv venv --python 3.13
uv sync
```

Expected: `uv sync` resolve tudo com wheels prontas, nada compila da fonte.

- [x] **Step 2: Escrever o teste que falha**

Estes testes existem porque um erro de geometria aqui é silencioso: a folha continua bonita, mas o leitor mede o lugar errado. O teste de sobreposição com os marcadores já pegou um bug real durante o design (a faixa do nome invadia o marcador do canto).

```python
# tests/test_layout.py
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
```

- [x] **Step 3: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_layout.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.layout'`

- [x] **Step 4: Escrever `layout.py`**

```python
# src/gabarito/layout.py
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
```

- [x] **Step 5: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_layout.py -v`
Expected: PASS, 8 testes.

- [x] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore uv.lock src/ tests/
git commit -m "feat: projeto e geometria da folha"
```

---

## Task 2: Gerar a folha em branco

**Files:**
- Create: `src/gabarito/gerar_folha.py`
- Test: `tests/test_gerar_folha.py`

**Interfaces:**
- Consumes: `gabarito.layout` (Task 1).
- Produces:
  - `desenhar(largura=L.CANONICA_LARGURA, altura=L.CANONICA_ALTURA) -> np.ndarray` — imagem uint8 em tons de cinza do retângulo canônico, com os 4 marcadores nos cantos, a faixa do nome, a instrução e as 32 bolinhas vazias.
  - `desenhar_a4(largura_px=2480) -> np.ndarray` — página A4 inteira, com a margem de 15 mm em branco ao redor do conteúdo canônico. É o que vira PDF e o que o gerador sintético usa como base.
  - `gerar_pdf(caminho) -> None` — salva a página A4 em 300 DPI.
  - `fonte(tamanho_px) -> PIL.ImageFont.FreeTypeFont` — usada também pelo `sintetico.py` e pelo `anotar.py`.

- [x] **Step 1: Escrever o teste que falha**

O teste importante não é "desenhou alguma coisa", é **o próprio detector ArUco encontrar os 4 marcadores na folha que acabamos de desenhar, com os IDs nos cantos certos**. Isso fecha o ciclo gerador↔leitor.

```python
# tests/test_gerar_folha.py
import cv2
import numpy as np
import pytest

from gabarito import gerar_folha, layout as L


@pytest.fixture(scope="module")
def canonica():
    return gerar_folha.desenhar()


def test_dimensoes_e_tipo(canonica):
    assert canonica.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
    assert canonica.dtype == np.uint8


def test_os_quatro_marcadores_sao_detectaveis_nos_cantos_certos():
    pagina = gerar_folha.desenhar_a4()
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())
    cantos, ids, _ = detector.detectMarkers(pagina)

    assert ids is not None
    achados = {int(i): c[0] for i, c in zip(ids.flatten(), cantos)}
    assert set(achados) == set(L.ARUCO_IDS)

    altura, largura = pagina.shape
    meio_x, meio_y = largura / 2, altura / 2
    esperado = {
        L.ARUCO_ID_SUP_ESQ: (True, True),
        L.ARUCO_ID_SUP_DIR: (False, True),
        L.ARUCO_ID_INF_DIR: (False, False),
        L.ARUCO_ID_INF_ESQ: (True, False),
    }
    for identificador, (esquerda, cima) in esperado.items():
        cx, cy = achados[identificador].mean(axis=0)
        assert (cx < meio_x) is esquerda
        assert (cy < meio_y) is cima


def test_as_32_bolinhas_estao_vazias(canonica):
    for q in range(L.N_QUESTOES):
        for a in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(q, a)
            raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
            recorte = canonica[
                int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio
            ]
            assert recorte.mean() > 240, f"bolinha {q},{a} não está vazia"


def test_as_bolinhas_tem_contorno_visivel(canonica):
    x, y = L.centro_bolinha(0, 0)
    raio = L.BOLINHA_RAIO
    recorte = canonica[int(y) - raio - 3 : int(y) + raio + 3, int(x) - raio - 3 : int(x) + raio + 3]
    assert recorte.min() < 128


def test_gera_pdf(tmp_path):
    destino = tmp_path / "folha.pdf"
    gerar_folha.gerar_pdf(destino)
    assert destino.exists()
    assert destino.stat().st_size > 5_000
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_gerar_folha.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.gerar_folha'`

- [x] **Step 3: Escrever `gerar_folha.py`**

```python
# src/gabarito/gerar_folha.py
"""Desenha a folha de gabarito em branco.

Tudo é desenhado a partir de `layout`, em qualquer resolução, para que a
versão de tela (canônica, 1000×1483) e a versão de impressão (A4 a 300 DPI)
sejam literalmente o mesmo desenho em escalas diferentes.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import layout as L

_CAMINHOS_DE_FONTE = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def fonte(tamanho_px):
    """Fonte escalável com acentuação. Pillow ≥10.1 para o fallback."""
    tamanho = max(8, int(round(tamanho_px)))
    for caminho in _CAMINHOS_DE_FONTE:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def _colar_marcadores(imagem, largura, altura):
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    for identificador, (x0, y0, _, _) in L.retangulos_marcadores(largura, altura).items():
        lado = int(round(L.MARCADOR_MM * largura / L.CANONICA_MM_LARGURA))
        marcador = cv2.aruco.generateImageMarker(dicionario, identificador, lado)
        imagem.paste(Image.fromarray(marcador), (int(round(x0)), int(round(y0))))


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
    Image.fromarray(desenhar_a4(2480)).convert("RGB").save(
        caminho, "PDF", resolution=300.0
    )
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_gerar_folha.py -v`
Expected: PASS, 5 testes.

- [x] **Step 5: Gerar a folha e olhar com os próprios olhos**

```bash
uv run python -c "from gabarito import gerar_folha; gerar_folha.gerar_pdf('saida/folha.pdf'); print('ok')"
open saida/folha.pdf
```

Confira visualmente: 4 marcadores nos cantos, caixa do nome sem encostar nos marcadores, 8 linhas numeradas com A/B/C/D, instrução legível e acentuada ("questão", não "quest?o").

- [x] **Step 6: Commit**

```bash
git add src/gabarito/gerar_folha.py tests/test_gerar_folha.py
git commit -m "feat: gerador da folha em branco (canônica, A4 e PDF)"
```

---

## Task 3: Gerador sintético de fotos

**Files:**
- Create: `tests/sintetico.py`
- Test: `tests/test_sintetico.py`

**Interfaces:**
- Consumes: `gabarito.layout`, `gabarito.gerar_folha` (Tasks 1–2).
- Produces:
  - `ESTILOS` — tupla `("cheia", "boa", "parcial", "leve", "apagada")`.
  - `marcas_de_respostas(respostas, estilo="boa") -> dict[int, list[tuple[int, str]]]` — converte `["A", "C", ...]` na estrutura de marcas.
  - `folha_preenchida(marcas, nome="Ana Carolina de Souza", largura_px=2480, rng=None) -> np.ndarray` — página A4 preenchida, sem degradação.
  - `degradar(pagina, rng, lado_maior=1600, brilho_escuro=0.55, sombra=True, qualidade_jpeg=60) -> np.ndarray` — foto falsa.
  - `foto(respostas, rng, **kwargs) -> np.ndarray` — atalho que encadeia os três.

- [x] **Step 1: Escrever o teste que falha**

```python
# tests/test_sintetico.py
import cv2
import numpy as np
import pytest

import sintetico
from gabarito import layout as L


def test_bolinha_marcada_fica_escura_e_o_resto_nao():
    marcas = sintetico.marcas_de_respostas(["A"] * L.N_QUESTOES, estilo="cheia")
    pagina = sintetico.folha_preenchida(
        marcas, rng=np.random.default_rng(0), largura_px=2480
    )
    assert pagina.dtype == np.uint8
    assert pagina.ndim == 2

    px_por_mm = 2480 / L.A4_LARGURA_MM
    largura_conteudo = L.CANONICA_MM_LARGURA * px_por_mm
    altura_conteudo = L.CANONICA_MM_ALTURA * px_por_mm
    deslocamento = L.MARGEM_MM * px_por_mm
    escala = largura_conteudo / L.CANONICA_LARGURA
    raio = int(L.BOLINHA_RAIO * escala * L.BOLINHA_INSET)

    def media(questao, alternativa):
        x, y = L.centro_bolinha(questao, alternativa, largura_conteudo, altura_conteudo)
        x, y = int(deslocamento + x), int(deslocamento + y)
        return pagina[y - raio : y + raio, x - raio : x + raio].mean()

    for questao in range(L.N_QUESTOES):
        assert media(questao, 0) < 80, f"q{questao} A deveria estar preenchida"
        for alternativa in range(1, L.N_ALTERNATIVAS):
            assert media(questao, alternativa) > 240, f"q{questao} alt{alternativa} deveria estar vazia"


def test_degradar_preserva_a_detectabilidade_dos_marcadores():
    rng = np.random.default_rng(1)
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())
    for semente in range(10):
        imagem = sintetico.foto(
            ["A", "B", "C", "D", "A", "B", "C", "D"],
            rng=np.random.default_rng(semente),
        )
        _, ids, _ = detector.detectMarkers(imagem)
        assert ids is not None, f"semente {semente}: nenhum marcador"
        assert set(int(i) for i in ids.flatten()) >= set(L.ARUCO_IDS)


def test_degradar_muda_a_imagem_e_o_tamanho():
    rng = np.random.default_rng(2)
    pagina = sintetico.folha_preenchida(
        sintetico.marcas_de_respostas(["B"] * L.N_QUESTOES), rng=rng
    )
    imagem = sintetico.degradar(pagina, rng, lado_maior=1200)
    assert max(imagem.shape) == 1200
    assert imagem.shape != pagina.shape


@pytest.mark.parametrize("estilo", sintetico.ESTILOS)
def test_todos_os_estilos_desenham_algo(estilo):
    rng = np.random.default_rng(3)
    marcas = {0: [(0, estilo)]}
    pagina = sintetico.folha_preenchida(marcas, rng=rng, largura_px=1240)
    limpa = sintetico.folha_preenchida({}, rng=np.random.default_rng(3), largura_px=1240)
    assert pagina.astype(int).sum() < limpa.astype(int).sum()
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_sintetico.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sintetico'`

- [x] **Step 3: Escrever `tests/sintetico.py`**

```python
# tests/sintetico.py
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
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_sintetico.py -v`
Expected: PASS, 8 testes (3 diretos + 5 parametrizados por estilo).

- [x] **Step 5: Olhar uma foto sintética**

```bash
uv run python -c "
import numpy as np, cv2, sys; sys.path.insert(0, 'tests')
import sintetico
img = sintetico.foto(['A','B','C','D','A','B','C','D'], np.random.default_rng(7))
cv2.imwrite('saida/foto_sintetica.png', img); print(img.shape)
"
open saida/foto_sintetica.png
```

Deve parecer uma foto torta e mal iluminada de uma folha — não uma digitalização limpa. Se parecer limpa demais, a suíte inteira está testando fácil demais.

- [x] **Step 6: Commit**

```bash
git add tests/sintetico.py tests/test_sintetico.py
git commit -m "test: gerador sintético de folhas preenchidas e fotos degradadas"
```

---

## Task 4: Alinhamento por ArUco

**Files:**
- Create: `src/gabarito/alinhar.py`
- Test: `tests/test_alinhar.py`

**Interfaces:**
- Consumes: `gabarito.layout` (Task 1), `sintetico` (Task 3, só nos testes).
- Produces:
  - `class FolhaNaoEncontrada(Exception)`.
  - `alinhar(foto) -> np.ndarray` — recebe imagem BGR ou em tons de cinza, devolve a canônica 1000×1483 em tons de cinza. Levanta `FolhaNaoEncontrada` se qualquer um dos 4 IDs faltar.

- [x] **Step 1: Escrever o teste que falha**

O teste decisivo é o de **precisão**: depois de alinhar, o centro de uma bolinha marcada tem que cair onde o `layout` diz que ela está. É isso que todo o resto assume.

```python
# tests/test_alinhar.py
import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L


def _canonica(respostas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    return A.alinhar(sintetico.foto(respostas, rng, **kwargs))


def test_dimensoes_da_canonica():
    imagem = _canonica(["A"] * L.N_QUESTOES, 0)
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
    assert imagem.dtype == np.uint8


def test_a_marca_cai_onde_o_layout_diz():
    respostas = ["A", "B", "C", "D", "D", "C", "B", "A"]
    imagem = _canonica(respostas, 1, estilo="cheia")
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    for questao, letra in enumerate(respostas):
        for alternativa in range(L.N_ALTERNATIVAS):
            x, y = L.centro_bolinha(questao, alternativa)
            recorte = imagem[
                int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio
            ]
            marcada = L.ALTERNATIVAS[alternativa] == letra
            if marcada:
                assert recorte.mean() < 120, f"q{questao} {letra} deveria estar escura"
            else:
                assert recorte.mean() > 150, f"q{questao}{alternativa} deveria estar clara"


@pytest.mark.parametrize("semente", range(10))
def test_alinha_em_varias_degradacoes(semente):
    imagem = _canonica(["A"] * L.N_QUESTOES, semente)
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)


def test_folha_de_cabeca_para_baixo():
    rng = np.random.default_rng(4)
    foto = sintetico.foto(["C"] * L.N_QUESTOES, rng, estilo="cheia")
    de_ponta_cabeca = np.rot90(foto, 2).copy()
    imagem = A.alinhar(de_ponta_cabeca)
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    x, y = L.centro_bolinha(0, L.ALTERNATIVAS.index("C"))
    recorte = imagem[int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio]
    assert recorte.mean() < 120


@pytest.mark.parametrize("lado_maior", [800, 1200, 2000])
def test_varias_escalas(lado_maior):
    imagem = _canonica(["B"] * L.N_QUESTOES, 5, lado_maior=lado_maior, estilo="cheia")
    raio = int(L.BOLINHA_RAIO * L.BOLINHA_INSET)
    x, y = L.centro_bolinha(3, 1)
    recorte = imagem[int(y) - raio : int(y) + raio, int(x) - raio : int(x) + raio]
    assert recorte.mean() < 120


def test_sem_marcadores_levanta_excecao():
    branco = np.full((1200, 900), 255, np.uint8)
    with pytest.raises(A.FolhaNaoEncontrada):
        A.alinhar(branco)


def test_um_marcador_cortado_levanta_excecao():
    rng = np.random.default_rng(6)
    foto = sintetico.foto(["A"] * L.N_QUESTOES, rng)
    cortada = foto[:, foto.shape[1] // 4 :].copy()
    with pytest.raises(A.FolhaNaoEncontrada) as erro:
        A.alinhar(cortada)
    assert "marcador" in str(erro.value).lower()


def test_aceita_imagem_colorida():
    import cv2

    rng = np.random.default_rng(7)
    foto = sintetico.foto(["A"] * L.N_QUESTOES, rng)
    colorida = cv2.cvtColor(foto, cv2.COLOR_GRAY2BGR)
    assert A.alinhar(colorida).shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA)
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_alinhar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.alinhar'`

- [x] **Step 3: Escrever `alinhar.py`**

```python
# src/gabarito/alinhar.py
"""Converte a foto numa imagem canônica de tamanho fixo.

Todo o caos físico — perspectiva, rotação, escala, folha de cabeça para
baixo — fica confinado aqui. Os módulos seguintes só veem a canônica.
"""

import cv2
import numpy as np

from . import layout as L


class FolhaNaoEncontrada(Exception):
    """Os quatro marcadores não foram todos localizados na foto."""


# `detectMarkers` devolve os 4 cantos no referencial do próprio marcador
# (sup-esq, sup-dir, inf-dir, inf-esq), e a identidade do marcador independe
# de como ele está girado na foto. Logo, para cada marcador basta pegar o
# canto que aponta para fora da folha: é ele que define o retângulo canônico.
_CANTO_EXTERNO = {
    L.ARUCO_ID_SUP_ESQ: 0,
    L.ARUCO_ID_SUP_DIR: 1,
    L.ARUCO_ID_INF_DIR: 2,
    L.ARUCO_ID_INF_ESQ: 3,
}

_DESTINO = {
    L.ARUCO_ID_SUP_ESQ: (0.0, 0.0),
    L.ARUCO_ID_SUP_DIR: (float(L.CANONICA_LARGURA), 0.0),
    L.ARUCO_ID_INF_DIR: (float(L.CANONICA_LARGURA), float(L.CANONICA_ALTURA)),
    L.ARUCO_ID_INF_ESQ: (0.0, float(L.CANONICA_ALTURA)),
}


def _detector():
    dicionario = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, L.ARUCO_DICT_NOME)
    )
    return cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())


def alinhar(foto):
    """Foto (BGR ou cinza) -> canônica 1000×1483 em tons de cinza."""
    cinza = foto if foto.ndim == 2 else cv2.cvtColor(foto, cv2.COLOR_BGR2GRAY)

    cantos, ids, _ = _detector().detectMarkers(cinza)
    achados = {} if ids is None else {int(i): c[0] for i, c in zip(ids.flatten(), cantos)}
    faltando = [i for i in L.ARUCO_IDS if i not in achados]
    if faltando:
        raise FolhaNaoEncontrada(
            f"Não encontrei {len(faltando)} dos 4 marcadores (faltaram os IDs "
            f"{faltando}). Enquadre a folha inteira, com os quatro cantos visíveis."
        )

    origem = np.array(
        [achados[i][_CANTO_EXTERNO[i]] for i in L.ARUCO_IDS], dtype=np.float32
    )
    destino = np.array([_DESTINO[i] for i in L.ARUCO_IDS], dtype=np.float32)
    transformada = cv2.getPerspectiveTransform(origem, destino)
    return cv2.warpPerspective(
        cinza,
        transformada,
        (L.CANONICA_LARGURA, L.CANONICA_ALTURA),
        flags=cv2.INTER_CUBIC,
    )
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_alinhar.py -v`
Expected: PASS, 19 testes.

- [x] **Step 5: Commit**

```bash
git add src/gabarito/alinhar.py tests/test_alinhar.py
git commit -m "feat: alinhamento da foto por marcadores ArUco"
```

---

## Task 5: Medir o preenchimento das bolinhas

**Files:**
- Create: `src/gabarito/ler_marcas.py`
- Test: `tests/test_ler_marcas.py`

**Interfaces:**
- Consumes: `gabarito.layout` (Task 1).
- Produces:
  - `@dataclass(frozen=True) class Leitura` com os campos `preenchimento: float`, `confirmacao: float`, `marcada: bool`, `ambigua: bool`.
  - `ler_marcas(canonica) -> list[list[Leitura]]` — matriz 8×4, indexada `[questao][alternativa]`.

- [x] **Step 1: Escrever o teste que falha**

O teste que justifica este módulo é o da **iluminação**: a mesma marca, no lado claro e no lado escuro da página, tem que medir quase igual. É exatamente onde o método global descartado falhava.

```python
# tests/test_ler_marcas.py
import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.ler_marcas import ler_marcas


def _ler(marcas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    return ler_marcas(A.alinhar(sintetico.degradar(pagina, rng, **kwargs)))


def test_formato_da_matriz():
    leituras = _ler({}, 0)
    assert len(leituras) == L.N_QUESTOES
    assert all(len(linha) == L.N_ALTERNATIVAS for linha in leituras)


def test_folha_em_branco_nao_tem_nenhuma_marcada():
    for linha in _ler({}, 1):
        for leitura in linha:
            assert not leitura.marcada
            assert not leitura.ambigua
            assert leitura.preenchimento < L.LIMIAR_VAZIA


@pytest.mark.parametrize("estilo", ["cheia", "boa"])
def test_marca_boa_e_lida_como_marcada(estilo):
    marcas = {q: [(q % L.N_ALTERNATIVAS, estilo)] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 2)
    for questao in range(L.N_QUESTOES):
        esperada = questao % L.N_ALTERNATIVAS
        for alternativa in range(L.N_ALTERNATIVAS):
            leitura = leituras[questao][alternativa]
            assert leitura.marcada is (alternativa == esperada), (
                f"q{questao} alt{alternativa}: preenchimento={leitura.preenchimento:.3f}"
            )


def test_marca_parcial_fica_ambigua():
    marcas = {q: [(1, "parcial")] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 3)
    ambiguas = sum(1 for q in range(L.N_QUESTOES) if leituras[q][1].ambigua)
    assert ambiguas >= 7, "marca de ~50% deveria cair na faixa ambígua"


def test_borracha_mal_apagada_nao_vira_marcacao():
    marcas = {q: [(2, "apagada")] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 4)
    for questao in range(L.N_QUESTOES):
        assert not leituras[questao][2].marcada


def test_a_medida_e_invariante_a_iluminacao():
    """A mesma marca no lado claro e no escuro tem que medir quase igual.

    É este teste que proíbe a volta ao limiar global: com Otsu, a bolinha
    VAZIA do lado escuro media 1,000.
    """
    marcas = {q: [(a, "boa") for a in range(L.N_ALTERNATIVAS)] for q in range(L.N_QUESTOES)}
    leituras = _ler(marcas, 5, brilho_escuro=0.35)
    valores = [
        leituras[q][a].preenchimento
        for q in range(L.N_QUESTOES)
        for a in range(L.N_ALTERNATIVAS)
    ]
    assert min(valores) > L.LIMIAR_MARCADA
    assert max(valores) - min(valores) < 0.30


def test_iluminacao_ruim_nao_inventa_marcacao():
    leituras = _ler({}, 6, brilho_escuro=0.30)
    for linha in leituras:
        for leitura in linha:
            assert not leitura.marcada


def test_duas_marcas_na_mesma_questao_sao_ambas_lidas():
    leituras = _ler({0: [(0, "cheia"), (2, "cheia")]}, 7)
    assert leituras[0][0].marcada
    assert leituras[0][2].marcada
    assert not leituras[0][1].marcada
    assert not leituras[0][3].marcada
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_ler_marcas.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.ler_marcas'`

- [x] **Step 3: Escrever `ler_marcas.py`**

```python
# src/gabarito/ler_marcas.py
"""Mede o quanto cada bolinha está preenchida.

Não detecta bolinha nenhuma: depois do alinhamento elas estão em coordenadas
conhecidas. A medida primária é relativa ao papel ao redor da própria
bolinha, e por isso não depende da iluminação. A secundária, por limiar
adaptativo, serve só de conferência.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from . import layout as L


@dataclass(frozen=True)
class Leitura:
    preenchimento: float
    confirmacao: float
    marcada: bool
    ambigua: bool


def _mascaras(raio_janela):
    lado = 2 * raio_janela
    yy, xx = np.mgrid[0:lado, 0:lado]
    distancia = np.hypot(xx - raio_janela, yy - raio_janela)
    disco = distancia <= L.BOLINHA_RAIO * L.BOLINHA_INSET
    anel = (distancia >= L.BOLINHA_RAIO * L.ANEL_INTERNO) & (
        distancia <= L.BOLINHA_RAIO * L.ANEL_EXTERNO
    )
    return disco, anel


def _medir(cinza, binaria, cx, cy, disco, anel, raio_janela):
    x0 = int(round(cx)) - raio_janela
    y0 = int(round(cy)) - raio_janela
    lado = 2 * raio_janela
    janela = cinza[y0 : y0 + lado, x0 : x0 + lado].astype(np.float32)
    janela_binaria = binaria[y0 : y0 + lado, x0 : x0 + lado]

    # Percentil alto do anel = o branco do papel ali naquele ponto da página.
    # Percentil, e não média, para que tinta que vaze da bolinha não contamine
    # a referência de papel.
    fundo = float(np.percentile(janela[anel], 75))
    fundo = max(fundo, 1.0)

    preenchimento = float(np.clip(1.0 - float(janela[disco].mean()) / fundo, 0.0, 1.0))
    confirmacao = float((janela_binaria[disco] > 0).mean())

    acima = preenchimento > L.LIMIAR_MARCADA
    abaixo = preenchimento < L.LIMIAR_VAZIA
    discorda = (acima and confirmacao < L.CONF_LIMIAR_VAZIA) or (
        abaixo and confirmacao > L.CONF_LIMIAR_MARCADA
    )
    return Leitura(
        preenchimento=preenchimento,
        confirmacao=confirmacao,
        marcada=acima and not discorda,
        ambigua=(not acima and not abaixo) or discorda,
    )


def ler_marcas(canonica):
    """Imagem canônica -> matriz 8×4 de `Leitura`."""
    binaria = cv2.adaptiveThreshold(
        canonica,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        10,
    )
    raio_janela = int(np.ceil(L.BOLINHA_RAIO * L.ANEL_EXTERNO)) + 2
    disco, anel = _mascaras(raio_janela)

    return [
        [
            _medir(
                canonica,
                binaria,
                *L.centro_bolinha(questao, alternativa),
                disco,
                anel,
                raio_janela,
            )
            for alternativa in range(L.N_ALTERNATIVAS)
        ]
        for questao in range(L.N_QUESTOES)
    ]
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_ler_marcas.py -v`
Expected: PASS, 9 testes.

Se `test_marca_parcial_fica_ambigua` falhar, ajuste `L.LIMIAR_VAZIA` / `L.LIMIAR_MARCADA` — e só eles, nunca o método de medição. Imprima os valores com `pytest -s` antes de mexer.

- [x] **Step 5: Commit**

```bash
git add src/gabarito/ler_marcas.py tests/test_ler_marcas.py
git commit -m "feat: medida de preenchimento relativa local das bolinhas"
```

---

## Task 6: Regras de correção

**Files:**
- Create: `src/gabarito/corrigir.py`
- Test: `tests/test_corrigir.py`

**Interfaces:**
- Consumes: `gabarito.layout` (Task 1), `gabarito.ler_marcas.Leitura` (Task 5).
- Produces:
  - `class Estado(str, Enum)` com `RESPONDIDA`, `ANULADA`, `EM_BRANCO`, `REVISAR`.
  - `@dataclass(frozen=True) class ResultadoQuestao`: `numero: int` (1-based), `estado: Estado`, `marcada: str | None`, `correta: str`, `acertou: bool`.
  - `@dataclass(frozen=True) class Resultado`: `questoes: list[ResultadoQuestao]`, `acertos: int`, `total: int`.
  - `corrigir(leituras, chave) -> Resultado`. `chave` é uma sequência de 8 letras de `L.ALTERNATIVAS`; qualquer outra coisa levanta `ValueError`.

- [x] **Step 1: Escrever o teste que falha**

Este módulo não vê imagem nenhuma, então os testes constroem `Leitura` na mão. É de propósito: as regras de anulação são a parte do sistema que mais importa acertar e a que menos precisa de foto.

```python
# tests/test_corrigir.py
import pytest

from gabarito import layout as L
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import Leitura

VAZIA = Leitura(preenchimento=0.02, confirmacao=0.00, marcada=False, ambigua=False)
MARCADA = Leitura(preenchimento=0.88, confirmacao=0.91, marcada=True, ambigua=False)
AMBIGUA = Leitura(preenchimento=0.37, confirmacao=0.51, marcada=False, ambigua=True)

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def linha(**posicoes):
    """linha(0=MARCADA) -> [MARCADA, VAZIA, VAZIA, VAZIA]"""
    celulas = [VAZIA] * L.N_ALTERNATIVAS
    for indice, valor in posicoes.items():
        celulas[int(indice)] = valor
    return celulas


def matriz(*linhas):
    assert len(linhas) == L.N_QUESTOES
    return list(linhas)


def todas_em_branco():
    return matriz(*[linha() for _ in range(L.N_QUESTOES)])


def test_gabarito_todo_certo():
    leituras = matriz(
        *[linha(**{str(L.ALTERNATIVAS.index(letra)): MARCADA}) for letra in CHAVE]
    )
    resultado = corrigir(leituras, CHAVE)
    assert resultado.acertos == 8
    assert resultado.total == 8
    assert all(q.estado is Estado.RESPONDIDA for q in resultado.questoes)
    assert all(q.acertou for q in resultado.questoes)


def test_resposta_errada_nao_pontua():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"1": MARCADA})  # marcou B, chave é A
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.RESPONDIDA
    assert resultado.questoes[0].marcada == "B"
    assert resultado.questoes[0].acertou is False
    assert resultado.acertos == 0


def test_duas_marcacoes_anulam_a_questao():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "2": MARCADA})
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.questoes[0].marcada is None
    assert resultado.questoes[0].acertou is False


def test_anulada_mesmo_quando_uma_das_marcadas_e_a_certa():
    """A regra é anular, não dar o benefício da dúvida."""
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "3": MARCADA})  # A é a correta
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.acertos == 0


def test_quatro_marcacoes_anulam():
    leituras = todas_em_branco()
    leituras[0] = [MARCADA] * L.N_ALTERNATIVAS
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.ANULADA


def test_questao_em_branco():
    resultado = corrigir(todas_em_branco(), CHAVE)
    assert all(q.estado is Estado.EM_BRANCO for q in resultado.questoes)
    assert resultado.acertos == 0


def test_ambigua_vira_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": AMBIGUA})
    resultado = corrigir(leituras, CHAVE)
    assert resultado.questoes[0].estado is Estado.REVISAR
    assert resultado.questoes[0].acertou is False


def test_marcada_com_outra_ambigua_vira_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "1": AMBIGUA})
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.REVISAR


def test_anulada_tem_prioridade_sobre_revisar():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA, "1": MARCADA, "2": AMBIGUA})
    assert corrigir(leituras, CHAVE).questoes[0].estado is Estado.ANULADA


def test_placar_misto():
    leituras = todas_em_branco()
    leituras[0] = linha(**{"0": MARCADA})                  # certa
    leituras[1] = linha(**{"0": MARCADA})                  # errada
    leituras[2] = linha(**{"0": MARCADA, "1": MARCADA})    # anulada
    leituras[3] = linha(**{"3": AMBIGUA})                  # revisar
    leituras[4] = linha(**{"0": MARCADA})                  # certa
    resultado = corrigir(leituras, CHAVE)
    assert resultado.acertos == 2
    estados = [q.estado for q in resultado.questoes]
    assert estados[:5] == [
        Estado.RESPONDIDA,
        Estado.RESPONDIDA,
        Estado.ANULADA,
        Estado.REVISAR,
        Estado.RESPONDIDA,
    ]
    assert [q.numero for q in resultado.questoes] == list(range(1, 9))


def test_chave_de_tamanho_errado():
    with pytest.raises(ValueError, match="8"):
        corrigir(todas_em_branco(), ["A", "B"])


def test_chave_com_letra_invalida():
    with pytest.raises(ValueError, match="E"):
        corrigir(todas_em_branco(), ["E"] + CHAVE[1:])
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_corrigir.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.corrigir'`

- [x] **Step 3: Escrever `corrigir.py`**

```python
# src/gabarito/corrigir.py
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
    if len(chave) != L.N_QUESTOES:
        raise ValueError(
            f"A chave precisa ter {L.N_QUESTOES} respostas, recebi {len(chave)}."
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
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_corrigir.py -v`
Expected: PASS, 12 testes.

- [x] **Step 5: Commit**

```bash
git add src/gabarito/corrigir.py tests/test_corrigir.py
git commit -m "feat: regras de correção, anulação e placar"
```

---

## Task 7: Testes de integração do pipeline

**Files:**
- Create: `tests/test_pipeline.py`
- Modify: nenhum módulo de produção, a menos que um teste revele um defeito real.

**Interfaces:**
- Consumes: tudo das Tasks 1–6.
- Produces: nenhuma API nova. Produz a evidência de que o sistema funciona ponta a ponta, que é o que será mostrado na entrega.

- [x] **Step 1: Escrever os testes de integração**

```python
# tests/test_pipeline.py
"""Foto sintética -> placar. É aqui que o sistema é julgado."""

import numpy as np
import pytest

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import ler_marcas

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def _corrigir_foto(marcas, semente, **kwargs):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    return corrigir(ler_marcas(A.alinhar(sintetico.degradar(pagina, rng, **kwargs))), CHAVE)


def _marcas_de(respostas, estilo="boa"):
    return sintetico.marcas_de_respostas(respostas, estilo)


@pytest.mark.parametrize("semente", range(200))
def test_propriedade_200_folhas_aleatorias(semente):
    """Respostas sorteadas, degradação sorteada, leitura tem que bater sempre."""
    rng = np.random.default_rng(10_000 + semente)
    respostas = [L.ALTERNATIVAS[int(i)] for i in rng.integers(0, 4, L.N_QUESTOES)]
    esperado = sum(1 for dada, certa in zip(respostas, CHAVE) if dada == certa)

    pagina = sintetico.folha_preenchida(_marcas_de(respostas), rng=rng)
    resultado = corrigir(
        ler_marcas(A.alinhar(sintetico.degradar(pagina, rng))), CHAVE
    )

    lidas = [q.marcada for q in resultado.questoes]
    assert lidas == respostas, f"semente {semente}: lido {lidas}, esperado {respostas}"
    assert resultado.acertos == esperado


def test_duas_marcacoes_anulam_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    marcas[0] = [(0, "cheia"), (2, "cheia")]
    resultado = _corrigir_foto(marcas, 1)
    assert resultado.questoes[0].estado is Estado.ANULADA
    assert resultado.acertos == 7


def test_questao_em_branco_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    del marcas[3]
    resultado = _corrigir_foto(marcas, 2)
    assert resultado.questoes[3].estado is Estado.EM_BRANCO
    assert resultado.acertos == 7


def test_marca_pela_metade_vira_revisar_ponta_a_ponta():
    marcas = _marcas_de(CHAVE)
    marcas[5] = [(L.ALTERNATIVAS.index(CHAVE[5]), "parcial")]
    resultado = _corrigir_foto(marcas, 3)
    assert resultado.questoes[5].estado is Estado.REVISAR
    assert resultado.acertos == 7


def test_folha_de_cabeca_para_baixo():
    rng = np.random.default_rng(4)
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng)
    foto = np.rot90(sintetico.degradar(pagina, rng), 2).copy()
    resultado = corrigir(ler_marcas(A.alinhar(foto)), CHAVE)
    assert resultado.acertos == 8


@pytest.mark.parametrize("escala", [0.85, 1.0, 1.15])
def test_impressao_maior_e_menor(escala):
    """Impressão fora de escala: os marcadores carregam a escala junto."""
    rng = np.random.default_rng(5)
    largura = int(round(2480 * escala))
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng, largura_px=largura)
    resultado = corrigir(ler_marcas(A.alinhar(sintetico.degradar(pagina, rng))), CHAVE)
    assert resultado.acertos == 8


@pytest.mark.parametrize("lado_maior", [800, 1200, 1600, 2400])
def test_varias_distancias_de_foto(lado_maior):
    resultado = _corrigir_foto(_marcas_de(CHAVE), 6, lado_maior=lado_maior)
    assert resultado.acertos == 8


def test_iluminacao_pior_que_a_nominal():
    """O lado escuro a 0,30 é onde o limiar global falhava. Não pode voltar."""
    resultado = _corrigir_foto(_marcas_de(CHAVE), 7, brilho_escuro=0.30)
    assert resultado.acertos == 8


def test_foto_sem_marcadores_nunca_produz_placar():
    rng = np.random.default_rng(8)
    pagina = sintetico.folha_preenchida(_marcas_de(CHAVE), rng=rng)
    foto = sintetico.degradar(pagina, rng)
    cortada = foto[foto.shape[0] // 3 :, :].copy()
    with pytest.raises(A.FolhaNaoEncontrada):
        A.alinhar(cortada)
```

- [x] **Step 2: Rodar o pipeline completo**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS. São 213 casos e leva ~1–3 minutos — a maior parte é o teste de propriedade.

Se o teste de propriedade falhar em poucas sementes, **não afrouxe o teste**. Isole a semente, salve a canônica daquele caso (`cv2.imwrite`) e olhe. Os limiares em `layout.py` são o único lugar legítimo para ajustar.

- [x] **Step 3: Rodar a suíte inteira**

Run: `uv run pytest -q`
Expected: PASS, tudo.

- [x] **Step 4: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: integração ponta a ponta, 200 folhas aleatórias e casos-limite"
```

---

## Task 8: Imagem de conferência

**Files:**
- Create: `src/gabarito/anotar.py`
- Test: `tests/test_anotar.py`

**Interfaces:**
- Consumes: `gabarito.layout`, `gabarito.gerar_folha.fonte`, `gabarito.corrigir.Estado`/`Resultado`, `gabarito.ler_marcas.Leitura`.
- Produces: `anotar(canonica, leituras, resultado) -> np.ndarray` — imagem **BGR** (uint8, 3 canais) pronta para exibir.

Cores (BGR): verde `(0, 170, 0)` marcada e certa · vermelho `(0, 0, 220)` marcada e errada · amarelo `(0, 190, 220)` ambígua · cinza `(130, 130, 130)` contorno das bolinhas de questão anulada.

- [x] **Step 1: Escrever o teste que falha**

```python
# tests/test_anotar.py
import numpy as np

import sintetico
from gabarito import alinhar as A, layout as L
from gabarito.anotar import anotar
from gabarito.corrigir import corrigir
from gabarito.ler_marcas import ler_marcas

CHAVE = ["A", "B", "C", "D", "A", "B", "C", "D"]


def _pipeline(marcas, semente):
    rng = np.random.default_rng(semente)
    pagina = sintetico.folha_preenchida(marcas, rng=rng)
    canonica = A.alinhar(sintetico.degradar(pagina, rng))
    leituras = ler_marcas(canonica)
    return canonica, leituras, corrigir(leituras, CHAVE)


def test_saida_colorida_do_tamanho_certo():
    imagem = anotar(*_pipeline(sintetico.marcas_de_respostas(CHAVE), 0))
    assert imagem.shape == (L.CANONICA_ALTURA, L.CANONICA_LARGURA, 3)
    assert imagem.dtype == np.uint8


def test_acerto_desenha_verde_e_erro_desenha_vermelho():
    respostas = list(CHAVE)
    respostas[0] = "D"  # errada de propósito
    imagem = anotar(*_pipeline(sintetico.marcas_de_respostas(respostas), 1))
    azul, verde, vermelho = imagem[:, :, 0], imagem[:, :, 1], imagem[:, :, 2]
    assert (
        (verde.astype(int) - azul.astype(int) > 60)
        & (verde.astype(int) - vermelho.astype(int) > 60)
    ).sum() > 50
    assert (
        (vermelho.astype(int) - verde.astype(int) > 60)
        & (vermelho.astype(int) - azul.astype(int) > 60)
    ).sum() > 50


def test_nao_altera_a_canonica_recebida():
    canonica, leituras, resultado = _pipeline(sintetico.marcas_de_respostas(CHAVE), 2)
    antes = canonica.copy()
    anotar(canonica, leituras, resultado)
    assert np.array_equal(canonica, antes)
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_anotar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.anotar'`

- [x] **Step 3: Escrever `anotar.py`**

```python
# src/gabarito/anotar.py
"""Desenha o resultado sobre a folha alinhada.

Serve de demonstração e de depuração ao mesmo tempo: se o software errar,
o erro fica visível na imagem em vez de escondido num número.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import layout as L
from .corrigir import Estado
from .gerar_folha import fonte

VERDE = (0, 170, 0)
VERMELHO = (0, 0, 220)
AMARELO = (0, 190, 220)
CINZA = (130, 130, 130)


def _cor_da_bolinha(leitura, questao_resultado):
    if leitura.ambigua:
        return AMARELO
    if not leitura.marcada:
        return None
    if questao_resultado.estado is Estado.ANULADA:
        return CINZA
    return VERDE if questao_resultado.acertou else VERMELHO


def anotar(canonica, leituras, resultado):
    """Canônica em cinza + leituras + resultado -> imagem BGR anotada."""
    base = cv2.cvtColor(canonica, cv2.COLOR_GRAY2BGR)
    imagem = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB))
    pincel = ImageDraw.Draw(imagem)
    fonte_estado = fonte(16)
    raio = L.BOLINHA_RAIO + 6

    for questao in range(L.N_QUESTOES):
        questao_resultado = resultado.questoes[questao]
        for alternativa in range(L.N_ALTERNATIVAS):
            leitura = leituras[questao][alternativa]
            cor = _cor_da_bolinha(leitura, questao_resultado)
            if cor is None:
                continue
            x, y = L.centro_bolinha(questao, alternativa)
            pincel.ellipse(
                (x - raio, y - raio, x + raio, y + raio),
                outline=(cor[2], cor[1], cor[0]),
                width=4,
            )

        if questao_resultado.estado is Estado.ANULADA:
            x0, _ = L.centro_bolinha(questao, 0)
            x1, y = L.centro_bolinha(questao, L.N_ALTERNATIVAS - 1)
            pincel.line(
                (x0 - raio, y, x1 + raio, y),
                fill=(CINZA[2], CINZA[1], CINZA[0]),
                width=3,
            )

        _, y = L.centro_bolinha(questao, L.N_ALTERNATIVAS - 1)
        rotulo = {
            Estado.RESPONDIDA: f"{questao_resultado.marcada}  (certa: {questao_resultado.correta})",
            Estado.ANULADA: "ANULADA",
            Estado.EM_BRANCO: "EM BRANCO",
            Estado.REVISAR: "REVISAR",
        }[questao_resultado.estado]
        cor_rotulo = VERDE if questao_resultado.acertou else (
            AMARELO if questao_resultado.estado is Estado.REVISAR else VERMELHO
        )
        # A 789 px, com fonte 16, o rótulo mais longo termina por volta de
        # 884 px — dentro dos 1000 px da folha. Rótulos maiores seriam cortados.
        pincel.text(
            (L.ALTERNATIVA_X[-1] * L.CANONICA_LARGURA + raio + 14, y),
            rotulo,
            font=fonte_estado,
            fill=(cor_rotulo[2], cor_rotulo[1], cor_rotulo[0]),
            anchor="lm",
        )

    return cv2.cvtColor(np.asarray(imagem), cv2.COLOR_RGB2BGR)
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_anotar.py -v`
Expected: PASS, 3 testes.

- [x] **Step 5: Olhar a imagem anotada**

```bash
uv run python -c "
import sys; sys.path.insert(0, 'tests')
import numpy as np, cv2, sintetico
from gabarito import alinhar as A
from gabarito.ler_marcas import ler_marcas
from gabarito.corrigir import corrigir
from gabarito.anotar import anotar
chave = ['A','B','C','D','A','B','C','D']
rng = np.random.default_rng(0)
marcas = sintetico.marcas_de_respostas(['A','B','C','A','A','B','C','D'])
marcas[6] = [(0,'cheia'), (2,'cheia')]
marcas[7] = [(3,'parcial')]
del marcas[4]
pagina = sintetico.folha_preenchida(marcas, rng=rng)
canonica = A.alinhar(sintetico.degradar(pagina, rng))
leituras = ler_marcas(canonica)
resultado = corrigir(leituras, chave)
cv2.imwrite('saida/conferencia.png', anotar(canonica, leituras, resultado))
print(f'{resultado.acertos}/{resultado.total}')
for q in resultado.questoes: print(q.numero, q.estado.value, q.marcada, q.correta, q.acertou)
"
open saida/conferencia.png
```

Esta é a imagem que vai na apresentação. Confira que os rótulos não saem da folha e que as cores batem com os estados impressos no terminal.

- [x] **Step 6: Commit**

```bash
git add src/gabarito/anotar.py tests/test_anotar.py
git commit -m "feat: imagem de conferência com o resultado sobreposto"
```

---

## Task 9: Leitura do nome

**Files:**
- Create: `src/gabarito/nome.py`
- Test: `tests/test_nome.py`

**Interfaces:**
- Consumes: `gabarito.layout` (Task 1).
- Produces:
  - `recortar_nome(canonica) -> np.ndarray` — recorte em tons de cinza da faixa do nome.
  - `transcrever(recorte) -> str | None` — texto transcrito, ou `None` se não houver chave de API, não houver rede, ou a chamada falhar. **Nunca levanta exceção.**

Motivo do `None` em vez de exceção: o nome é o único ponto do sistema que depende de rede, e o placar não pode depender dele. Um erro aqui degrada a experiência, não quebra a correção.

- [x] **Step 1: Escrever o teste que falha**

A chamada de rede é substituída por um dublê. Não fazemos chamada real em teste.

```python
# tests/test_nome.py
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


def test_resposta_vazia_vira_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(N, "_chamar_api", lambda _: "   ")
    assert N.transcrever(N.recortar_nome(_canonica())) is None
```

- [x] **Step 2: Rodar para confirmar que falha**

Run: `uv run pytest tests/test_nome.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'gabarito.nome'`

- [x] **Step 3: Escrever `nome.py`**

```python
# src/gabarito/nome.py
"""Recorta a faixa do nome e transcreve o manuscrito.

Único módulo que depende de rede. Por isso nunca levanta exceção: devolve
`None` e o sistema continua, mostrando o recorte para conferência humana.
"""

import io
import os

import numpy as np
from PIL import Image

from . import layout as L

MODELO = "gemini-2.5-flash"
LADO_MAIOR_MAXIMO = 2576  # limite de resolução da API de visão
INSTRUCAO = (
    "Você transcreve nomes manuscritos de folhas de prova. "
    "O nome pode estar em letra cursiva ou de forma. "
    "Responda APENAS com o nome transcrito, sem comentários. "
    "Se não conseguir ler, responda exatamente: ILEGÍVEL"
)


def recortar_nome(canonica):
    """Faixa do nome, em tons de cinza."""
    x0, y0, x1, y1 = L.NOME_RECT
    return canonica[
        int(round(y0 * L.CANONICA_ALTURA)) : int(round(y1 * L.CANONICA_ALTURA)),
        int(round(x0 * L.CANONICA_LARGURA)) : int(round(x1 * L.CANONICA_LARGURA)),
    ]


def _para_png(recorte):
    buffer = io.BytesIO()
    Image.fromarray(recorte).convert("L").save(buffer, "PNG")
    return buffer.getvalue()


def _chamar_api(recorte):
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
    """Texto do nome, ou None se não for possível. Nunca levanta exceção."""
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    try:
        texto = (_chamar_api(recorte) or "").strip()
    except Exception:
        return None
    if not texto or texto.upper() == "ILEGÍVEL":
        return None
    return texto
```

- [x] **Step 4: Rodar para confirmar que passa**

Run: `uv run pytest tests/test_nome.py -v`
Expected: PASS, 8 testes.

- [x] **Step 5: Commit**

```bash
git add src/gabarito/nome.py tests/test_nome.py
git commit -m "feat: recorte e transcrição do nome manuscrito"
```

---

## Task 10: Interface Streamlit e README

**Files:**
- Create: `app.py`, `README.md`
- Test: manual (Step 4). Não há teste automatizado de interface: o valor estaria em testar o Streamlit, não o nosso código, e toda a lógica já está coberta.

**Interfaces:**
- Consumes: todos os módulos anteriores.
- Produces: aplicação executável com `uv run streamlit run app.py`.

- [x] **Step 1: Escrever `app.py`**

```python
# app.py
"""Interface de demonstração do leitor de gabarito."""

import io

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from gabarito import alinhar as A, gerar_folha, layout as L, nome as N
from gabarito.anotar import anotar
from gabarito.corrigir import Estado, corrigir
from gabarito.ler_marcas import ler_marcas

CHAVE_PADRAO = ["A", "B", "C", "D", "A", "B", "C", "D"]

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
    buffer = io.BytesIO()
    Image.fromarray(gerar_folha.desenhar_a4(2480)).convert("RGB").save(
        buffer, "PDF", resolution=300.0
    )
    st.download_button(
        "Baixar folha para imprimir (PDF)",
        data=buffer.getvalue(),
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

foto = np.asarray(Image.open(enviado).convert("L"))

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
    st.image(
        cv2.cvtColor(anotar(canonica, leituras, resultado), cv2.COLOR_BGR2RGB),
        width="stretch",
    )

with direita:
    st.subheader("Nome")
    recorte = N.recortar_nome(canonica)
    st.image(recorte, clamp=True, width="stretch")
    transcrito = N.transcrever(recorte)
    if transcrito is None:
        st.caption(
            "Não foi possível transcrever automaticamente "
            "(sem GEMINI_API_KEY ou sem rede). Digite o nome abaixo."
        )
    st.text_input("Nome do aluno", value=transcrito or "")

    st.subheader("Resultado")
    st.metric("Acertos", f"{resultado.acertos} / {resultado.total}")

    icone = {
        Estado.RESPONDIDA: "",
        Estado.ANULADA: "🚫",
        Estado.EM_BRANCO: "—",
        Estado.REVISAR: "⚠️",
    }
    st.table(
        [
            {
                "Questão": q.numero,
                "Marcou": q.marcada or icone[q.estado],
                "Correta": q.correta,
                "Situação": ("✅ certa" if q.acertou else "❌ errada")
                if q.estado is Estado.RESPONDIDA
                else q.estado.value.replace("_", " ").capitalize(),
            }
            for q in resultado.questoes
        ]
    )
```

- [x] **Step 2: Escrever o `README.md`**

```markdown
# Leitor de gabarito

Lê a foto de um gabarito preenchido à mão (8 questões × 4 alternativas) e conta
os acertos. Questões com mais de uma alternativa marcada são anuladas.

## Como funciona

Quatro marcadores ArUco nos cantos da folha permitem corrigir perspectiva,
rotação e escala de uma só vez: qualquer foto vira a mesma imagem canônica de
1000×1483 px. A partir daí as 32 bolinhas estão em coordenadas conhecidas e o
software apenas mede o quanto cada uma está escura, comparando com o papel ao
redor dela — o que torna a leitura imune a iluminação desigual.

## Uso

```bash
uv sync
uv run streamlit run app.py
```

Na barra lateral, baixe a folha em PDF, imprima em A4 (sem "ajustar à página"),
preencha e fotografe com os quatro cantos visíveis.

Para transcrever o nome manuscrito, defina `GEMINI_API_KEY`. Sem ela, o
software mostra o recorte do nome e deixa o campo para digitação — a correção
funciona normalmente.

## Testes

```bash
uv run pytest -q
```

A suíte gera folhas sintéticas preenchidas, degrada-as como fotos de celular
(perspectiva, rotação, sombra, ruído) e verifica a leitura contra a verdade
conhecida, incluindo 200 folhas com respostas sorteadas.

## Limitações conhecidas

Ver `docs/superpowers/specs/2026-09-13-leitor-gabarito-design.md`, seção 10.
Em resumo: a validação é toda sintética até haver folhas impressas de verdade;
os quatro cantos precisam estar enquadrados na foto; um "X" em vez de
preenchimento pode ser lido como bolinha vazia; e a transcrição do nome não tem
como ser verificada pelo software.
```

- [x] **Step 3: Rodar a suíte inteira antes de olhar a interface**

Run: `uv run pytest -q`
Expected: PASS, tudo.

- [x] **Step 4: Verificação manual da interface**

```bash
uv run python -c "
import sys; sys.path.insert(0, 'tests')
import numpy as np, cv2, sintetico
chave = ['A','B','C','D','A','B','C','D']
marcas = sintetico.marcas_de_respostas(chave)
marcas[2] = [(0,'cheia'), (3,'cheia')]
del marcas[5]
rng = np.random.default_rng(42)
cv2.imwrite('saida/demo.jpg', sintetico.degradar(sintetico.folha_preenchida(marcas, rng=rng), rng))
print('saida/demo.jpg')
"
uv run streamlit run app.py
```

Abra `http://localhost:8501`, envie `saida/demo.jpg` e confirme:
- placar mostra 6/8;
- questão 3 aparece como Anulada, questão 6 como Em branco;
- a imagem de conferência mostra as duas bolinhas cinzas na questão 3;
- mudar a chave na barra lateral muda o placar na hora;
- o botão de download entrega um PDF que abre.

Encerre com `Ctrl+C`.

- [x] **Step 5: Commit**

```bash
git add app.py README.md
git commit -m "feat: interface Streamlit e README"
git push
```

---

## Cobertura da spec

| Requisito da spec | Onde é implementado | Onde é testado |
|---|---|---|
| 8 questões × 4 alternativas | `layout.py` (Task 1) | `test_layout.py` |
| Contar acertos | `corrigir.py` (Task 6) | `test_corrigir.py`, `test_pipeline.py` |
| Mais de uma marcação anula | `corrigir.py` (Task 6) | `test_corrigir.py`, `test_pipeline.py` |
| Instrução de preencher por inteiro | `layout.INSTRUCAO` (Task 1), desenhada na Task 2 | `test_gerar_folha.py` (inspeção visual no Step 5) |
| Ler nome cursivo ou de forma | `nome.py` (Task 9) | `test_nome.py` |
| Impressão torta / escalas diferentes | `alinhar.py` (Task 4) | `test_alinhar.py`, `test_pipeline.py::test_impressao_maior_e_menor` |
| Medida imune a iluminação | `ler_marcas.py` (Task 5) | `test_ler_marcas.py::test_a_medida_e_invariante_a_iluminacao` |
| Nunca emitir placar sem os 4 marcadores | `alinhar.py` (Task 4) | `test_pipeline.py::test_foto_sem_marcadores_nunca_produz_placar` |
| Estado `REVISAR` para marcas duvidosas | `corrigir.py` (Task 6) | `test_corrigir.py`, `test_pipeline.py` |
| Demonstração ao vivo | `app.py` (Task 10) | verificação manual, Task 10 Step 4 |
| Folha em PDF para imprimir | `gerar_folha.py` (Task 2) | `test_gerar_folha.py::test_gera_pdf` |
| Imagem de conferência | `anotar.py` (Task 8) | `test_anotar.py` |
| Limitações declaradas na entrega | `README.md` (Task 10) + spec §10 | — |
