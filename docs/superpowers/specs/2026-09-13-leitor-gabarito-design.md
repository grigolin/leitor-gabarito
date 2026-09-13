# Leitor de gabarito — design

Data: 2026-09-13

## 1. Objetivo

Ler a foto de um gabarito preenchido à mão e informar quantas das 8 questões
foram respondidas corretamente.

Requisitos do enunciado:

- 8 questões, 4 alternativas cada (A–D).
- Contar acertos.
- Mais de uma alternativa marcada anula a questão.
- A folha instrui o aluno a preencher a bolinha por inteiro.
- Ler o nome manuscrito, em letra cursiva ou de forma.
- Tolerar impressão torta e bolinhas de tamanhos diferentes.
- Entrega: demonstração ao vivo, relatando o que funcionou e o que não funcionou.
- O formato da folha é livre.

## 2. Decisões validadas por experimento

Três spikes descartáveis rodaram antes desta spec. Os números abaixo vêm deles.

### 2.1 Alinhamento por ArUco — aprovado

Quatro marcadores `DICT_4X4_50` (IDs 0=sup-esq, 1=sup-dir, 2=inf-dir, 3=inf-esq)
nos cantos da folha, 15 mm de lado, 15 mm para dentro da borda.

Com degradação simulando foto de celular (perspectiva com cantos deslocados até
8%, rotação ±15°, gradiente de iluminação até 0,55 de brilho, mancha de sombra,
desfoque, JPEG q60):

| lado maior da foto | 4 marcadores encontrados |
|---|---|
| 800 px | 100% |
| 1200 px | 100% |
| 1600 px | 100% |
| 2400 px | 100% |
| ~600 px | ~99% (limite prático) |
| < 450 px | degrada rápido |

Erro de reprojeção de um ponto conhecido para a imagem canônica: média 0,31–0,48 px,
máximo observado 1,27 px — contra um raio de bolinha de 18 px. Margem de ~14×.

Folha fotografada de cabeça para baixo é lida corretamente sem nenhum código de
orientação: o ArUco decodifica a identidade do marcador independentemente da
rotação, então os IDs bastam para saber qual canto é qual.

`DICT_5X5_50` e `DICT_6X6_250` foram comparados e não superam o 4×4 nas resoluções
que importam. Zero confusão de ID em ~1350 detecções.

### 2.2 Medida de preenchimento — aprovado com correção

Três métodos foram medidos em 4800 bolinhas sob iluminação desigual:

- **Otsu global: desqualificado.** Sob gradiente de iluminação, bolinhas vazias no
  lado escuro da página medem 1,000 (totalmente preenchidas). Falha sistemática.
- **`adaptiveThreshold` + fração de pixels escuros no disco interno:** separação
  ampla na iluminação nominal (vazia ≤ 0,091, preenchida ≥ 0,635), mas tem viés de
  iluminação real — a mesma marca lê 0,92 no lado claro e 0,81 no escuro. Com sombra
  pior que a nominal, o piso de uma marca boa cai para 0,394.
- **Medida relativa local** (intensidade média do disco interno normalizada contra o
  branco do papel no anel ao redor da própria bolinha): praticamente invariante à
  iluminação — marca boa lê 0,651 no lado claro e 0,647 no escuro. Sob sombra pior
  que a nominal, o piso permanece em 0,536.

**Decisão:** a medida relativa local é a primária. O `adaptiveThreshold` é calculado
em paralelo como conferência e só pode escalar uma questão para `REVISAR`; nunca
determina uma resposta sozinho.

### 2.3 Ambiente — aprovado

Python 3.13 tem wheels prontas para tudo (nada compila da fonte). O Python 3.14 do
sistema não é usado.

| pacote | versão |
|---|---|
| opencv-contrib-python | 5.0.0.93 (`cv2.__version__` = 5.0.0) |
| numpy | 2.5.3 |
| streamlit | 1.63.0 |
| google-genai | 2.23.0 |
| pytest | 9.1.1 |
| pillow | 12.3.0 |

O OpenCV 5.0 usa a API orientada a objeto do ArUco, não as funções soltas:

```python
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
corners, ids, rejected = detector.detectMarkers(image)
```

## 3. Layout da folha

`layout.py` é a fonte única da verdade da geometria. O gerador da folha e o leitor
importam dele, logo não podem divergir.

**Imagem canônica:** 1000×1483 px, definida como o retângulo delimitado pelos cantos
externos dos 4 marcadores. Em A4, com marcadores de 15 mm a 15 mm da borda, essa região
mede 180 × 267 mm. A altura canônica é 1483 e não 1400 justamente para preservar essa
proporção: 1 mm ≈ 5,556 px **nos dois eixos**. Se os eixos tivessem escalas diferentes, a
homografia deixaria as bolinhas elípticas e o disco de medição a 80% do raio não cobriria
a mesma fração nas duas direções.

Conteúdo, em coordenadas normalizadas do retângulo canônico:

- 4 marcadores ArUco nos cantos (IDs 0–3, 15 mm, a 15 mm da borda da página).
- Faixa do nome: retângulo no topo, altura ~8% da página, com a instrução de escrever
  o nome completo.
- 8 linhas de questões × 4 bolinhas (A–D). Raio da bolinha: 18 px canônicos
  (≈ 6,5 mm de diâmetro impresso), desenhadas como círculo de contorno fino.
- Instrução impressa: "Preencha a bolinha por inteiro. Marcar mais de uma alternativa
  anula a questão."

Trocar o número de questões ou de alternativas é editar esse arquivo.

## 4. Arquitetura

| Módulo | Entrada → saída |
|---|---|
| `layout.py` | constantes de geometria; sem lógica |
| `gerar_folha.py` | layout → PDF/PNG da folha em branco |
| `alinhar.py` | foto → imagem canônica 1000×1483, ou erro |
| `ler_marcas.py` | imagem canônica → 32 preenchimentos (0–1), por dois métodos |
| `corrigir.py` | preenchimentos + chave → estado por questão + placar |
| `nome.py` | imagem canônica → texto do nome, e sempre o recorte |
| `anotar.py` | imagem canônica + resultado → imagem de conferência |
| `app.py` | Streamlit; só amarra os demais |
| `sintetico.py` | layout + respostas → foto falsa degradada (testes) |

Fluxo: `foto → alinhar → ler_marcas → corrigir → anotar`, com `nome` pendurado na
imagem canônica.

`ler_marcas`, `corrigir` e `nome` nunca veem a foto original — apenas a imagem
canônica. Toda a bagunça física fica confinada em `alinhar.py`. `corrigir.py` não vê
imagem nenhuma, só números: as regras de anulação são lógica pura, testáveis sem foto.

**Erro:** se `alinhar` não encontrar os 4 marcadores, o pipeline para e o app pede
outra foto. Nunca se adivinha, nunca se emite placar parcial.

## 5. Leitura das marcas

Para cada uma das 32 bolinhas, em coordenadas fixas da imagem canônica:

- **Medida primária (relativa local):** intensidade média dentro de um disco a 80% do
  raio impresso — o recuo exclui o anel impresso — normalizada contra a intensidade do
  papel em um anel imediatamente ao redor da bolinha.
- **Medida de conferência:** `cv2.adaptiveThreshold` na imagem inteira, depois fração de
  pixels escuros no mesmo disco interno.

Classificação por bolinha, pela medida primária: `< 0,20` vazia · `> 0,50` marcada ·
entre as duas, **ambígua**.

Se as duas medidas discordarem quanto a uma bolinha estar marcada, ela é tratada como
ambígua.

Os limiares ficam em `layout.py` como constantes nomeadas, para recalibração quando
houver fotos reais.

## 6. Regras de correção

| Situação da questão | Estado | Pontua? |
|---|---|---|
| exatamente 1 marcada, nenhuma ambígua | `RESPONDIDA` | se igual à chave |
| 2 ou mais marcadas | `ANULADA` | não |
| nenhuma marcada nem ambígua | `EM_BRANCO` | não |
| qualquer uma ambígua | `REVISAR` | não |

`acertos = questões RESPONDIDAS cuja letra é igual à chave`.

O relatório mostra as 8 linhas com o estado de cada questão, não apenas o número final.

`REVISAR` não está no enunciado, mas cobre o que acontece no papel: rasura, marca
fraca, borracha mal apagada. Forçar esses casos para `RESPONDIDA` ou `EM_BRANCO` seria
inventar nota.

**Chave de respostas:** 8 seletores A/B/C/D na barra lateral do Streamlit, com um valor
padrão pré-preenchido. Alterável ao vivo durante a demonstração.

## 7. Leitura do nome

O retângulo do nome é recortado da imagem canônica (no máximo 1000 px de lado maior,
bem abaixo do limite de 2576 px da API — não precisa redimensionar) e enviado ao
`gemini-2.5-flash` para transcrição, usando a variável `GEMINI_API_KEY`.

Sem chave de API, sem internet, ou erro na chamada: o app exibe o recorte e deixa o
campo editável. O restante do fluxo continua funcionando. **O placar nunca depende do
nome.**

## 8. Interface

Página única em Streamlit:

- upload da foto (ou captura pela webcam);
- imagem de conferência: folha alinhada com cada bolinha circulada — verde = marcada e
  certa, vermelho = marcada e errada, amarelo = ambígua, contorno cinza = questão
  anulada, letra da chave ao lado;
- nome lido, em campo editável;
- placar `X/8` e a tabela das 8 questões com seus estados;
- barra lateral com a chave de respostas e um botão para baixar a folha em branco.

A imagem de conferência serve simultaneamente de demonstração e de depuração.

## 9. Testes

O gerador sintético é a base: recebe as respostas desejadas por questão, desenha a
folha a partir do mesmo `layout.py`, preenche as bolinhas com discos irregulares de
opacidade variável, escreve um nome, e degrada — homografia aleatória, rotação, escala,
gradiente de iluminação, sombra, desfoque, ruído JPEG. Isso dá verdade conhecida em
volume.

- **Teste de propriedade:** 200 folhas com respostas sorteadas, leitura correta em 100%.
- Duas alternativas marcadas → `ANULADA`.
- Questão em branco → `EM_BRANCO`.
- Marca com ~50% de cobertura → `REVISAR`.
- Folha fotografada de cabeça para baixo → lida corretamente.
- Folha impressa 15% menor e 15% maior → mesma leitura.
- Foto sem os marcadores → erro claro, nunca um placar.
- Iluminação pior que a nominal (lado escuro a 0,30 de brilho) → marcas boas continuam
  `RESPONDIDA`. Este teste existe porque é exatamente onde o método descartado falhava.
- `corrigir.py` testado diretamente com listas de números, sem imagem.

**Ordem de implementação (TDD):** `layout.py` → `gerar_folha.py` → `sintetico.py` com
os testes falhando → `alinhar.py` → `ler_marcas.py` → `corrigir.py` → `anotar.py` →
`app.py` → `nome.py` por último, por ser o único que depende de rede.

## 10. Limitações conhecidas

A serem declaradas na entrega.

- **Não há validação em papel real.** Os testes usam fotos sintéticas. Elas não
  reproduzem textura de papel, reflexo de luz direta, dobra, amassado, distorção de
  lente nem desfoque de movimento. "100% em 200 folhas sintéticas" mede o algoritmo,
  não o mundo. O gerador da folha fica pronto cedo justamente para permitir validação
  real assim que houver impressão.
- **Os 4 cantos precisam estar na foto.** Se o enquadramento cortar um marcador, a
  leitura falha — corretamente, mas falha. Mitigação: instrução na interface; uma
  conferência de enquadramento ao vivo na captura seria a evolução natural.
- **Resolução mínima ~600 px** no lado maior da folha. Qualquer celular atual passa
  folgado, mas fotos muito distantes não.
- **Um "X" ou "✓" em vez de preenchimento** pode ser lido como bolinha vazia. A folha
  instrui a preencher por inteiro; o caso de ~20% de cobertura cai majoritariamente em
  `REVISAR`, mas com uma cauda que lê como vazia.
- **A transcrição do nome não é verificada.** O modelo pode errar um nome manuscrito e
  não há como o software saber. Por isso o campo é editável e o recorte fica visível.

## 11. Fora de escopo

- Banco de dados, histórico de alunos, autenticação.
- Processamento em lote de uma pasta (o núcleo suporta, mas a interface não).
- Folha-mestre preenchida pelo professor como fonte da chave.
- Fallback de alinhamento sem marcadores (detecção da moldura da folha).
- Correção de distorção de lente.
