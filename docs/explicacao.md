# Leitor de gabarito — guia de apresentação

Este documento é um roteiro para entender, explicar e demonstrar o projeto
`leitor-gabarito`.

O sistema lê uma foto de uma folha com 8 questões e 4 alternativas por questão,
identifica as marcações, aplica uma chave de respostas e mostra o placar. Uma
questão com mais de uma alternativa marcada é anulada.

## 1. A ideia em uma frase

Quatro marcadores ArUco transformam qualquer foto da folha em uma imagem
canônica de tamanho fixo; depois disso, o sistema mede o preenchimento das 32
bolinhas em posições conhecidas e aplica regras simples de correção.

## 2. Como apresentar o problema

Uma foto de uma folha não é uma imagem perfeita:

- a folha pode estar inclinada ou girada;
- a câmera pode estar mais perto ou mais longe;
- a iluminação pode ser mais forte de um lado;
- pode existir sombra sobre parte da página;
- duas alternativas podem estar marcadas;
- uma marca pode ser fraca ou parcialmente apagada.

O projeto separa esses problemas em etapas. A geometria da foto é resolvida no
alinhamento; a leitura das bolinhas acontece somente depois que a folha foi
normalizada; e a correção da prova é uma lógica independente de imagens.

## 3. Fluxo completo

```text
foto
  ↓
detecção dos 4 ArUco
  ↓
homografia e imagem canônica 1000×1483
  ↓
medição das 32 bolinhas
  ↓
classificação de cada bolinha
  ↓
regras por questão
  ↓
placar, tabela e imagem de conferência
```

O nome do aluno é um fluxo separado e opcional:

```text
imagem canônica → recorte da faixa do nome → API de visão → texto editável
```

Se essa etapa falhar, o placar continua funcionando.

## 4. O que aparece na interface

Na barra lateral:

- oito seletores da chave de respostas, um por questão;
- botão para baixar a folha em branco em PDF;
- instruções para imprimir em A4 sem ajustar a escala e fotografar a folha inteira.

Na área principal:

- opção de enviar uma imagem ou usar a câmera;
- imagem de conferência com as marcações coloridas;
- recorte da faixa do nome;
- campo editável para o nome;
- placar `X/8`;
- tabela com resposta marcada, resposta correta e situação de cada questão.

Se os quatro marcadores não forem encontrados, o app mostra uma mensagem de
erro e não produz um resultado parcial.

## 5. A folha e a geometria

Toda a geometria vive em
[`src/gabarito/layout.py`](src/gabarito/layout.py). O gerador da folha e o
leitor importam o mesmo módulo; portanto, eles usam exatamente as mesmas
coordenadas.

### Dimensões

- folha física: A4, 210 × 297 mm;
- margem: 15 mm;
- região entre os marcadores: 180 × 267 mm;
- imagem canônica: 1000 × 1483 pixels;
- 8 questões;
- 4 alternativas por questão;
- 32 bolinhas no total;
- raio canônico da bolinha: 18 pixels.

A altura 1483 não foi escolhida arbitrariamente. Ela preserva a proporção de
180 × 267 mm nos dois eixos. Se a imagem canônica tivesse 1000 × 1400, por
exemplo, a homografia deformaria a folha e as bolinhas ficariam elípticas.

### Marcadores

Os IDs são fixos:

| ID | Posição |
|---:|---|
| 0 | superior esquerdo |
| 1 | superior direito |
| 2 | inferior direito |
| 3 | inferior esquerdo |

O dicionário usado é `DICT_4X4_50`. A implementação usa a API do OpenCV 5:

```python
dicionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
detector = cv2.aruco.ArucoDetector(
    dicionario,
    cv2.aruco.DetectorParameters(),
)
cantos, ids, rejeitados = detector.detectMarkers(imagem)
```

## 6. Alinhamento por homografia

O módulo [`src/gabarito/alinhar.py`](src/gabarito/alinhar.py) faz quatro coisas:

1. converte a foto colorida para tons de cinza, se necessário;
2. detecta os marcadores ArUco;
3. pega o canto externo de cada marcador;
4. calcula uma transformação de perspectiva para a região canônica.

A homografia corrige, de uma vez, perspectiva, rotação, escala e folha de
cabeça para baixo.

Se faltar qualquer ID, `alinhar()` levanta `FolhaNaoEncontrada`. Isso é
intencional: o sistema nunca tenta adivinhar a geometria e nunca emite um
placar parcial.

## 7. Como uma bolinha é lida

O módulo [`src/gabarito/ler_marcas.py`](src/gabarito/ler_marcas.py) não tenta
encontrar círculos na imagem. O centro de cada bolinha já é conhecido pelo
layout.

Para cada centro, são criadas duas regiões:

```text
        anel de papel
      ┌───────────────┐
      │    bolinha    │
      │   disco 80%   │
      └───────────────┘
```

- o disco interno usa 80% do raio e evita o contorno impresso;
- o anel externo mede o branco do papel perto daquela bolinha;
- a intensidade do disco é comparada com a intensidade do anel.

A medida principal é aproximadamente:

```text
preenchimento = 1 - média_do_disco / branco_local_do_papel
```

O resultado é limitado entre 0 e 1.

Isso é melhor que comparar a bolinha com um valor global. Uma bolinha vazia em
uma região escura ainda é comparada com o papel escuro que está ao redor dela.

### Limiares principais

| Preenchimento | Interpretação |
|---:|---|
| `< 0,20` | vazia |
| `> 0,50` | marcada |
| entre os dois | ambígua |

Em paralelo, o sistema calcula uma confirmação com `adaptiveThreshold`. Ela
usa limiares próprios, `0,25` e `0,55`, e não substitui a medida relativa
local. Se os métodos discordarem de forma relevante, a bolinha fica ambígua.

## 8. Regras de correção

O módulo [`src/gabarito/corrigir.py`](src/gabarito/corrigir.py) não recebe
imagem; recebe somente a matriz de leituras.

As regras são:

| Situação | Estado | Pontua? |
|---|---|---|
| uma marcada, nenhuma ambígua | `RESPONDIDA` | se igual à chave |
| duas ou mais marcadas | `ANULADA` | não |
| nenhuma marcada nem ambígua | `EM_BRANCO` | não |
| qualquer ambiguidade | `REVISAR` | não |

`ANULADA` tem prioridade sobre `REVISAR`: se duas alternativas estão
definitivamente marcadas, a questão é anulada mesmo que exista uma terceira
marca ambígua.

## 9. Imagem de conferência

O módulo [`src/gabarito/anotar.py`](src/gabarito/anotar.py) recebe a imagem
canônica, as leituras e o resultado da correção. Ele devolve uma imagem BGR
colorida sem alterar a imagem original.

As cores usadas são:

- verde: marcada e correta;
- vermelho: marcada e errada;
- amarelo: ambígua;
- cinza: questão anulada.

Essa imagem é importante na apresentação porque torna o funcionamento visível.
Não aparece somente um número; é possível ver quais bolinhas o sistema
interpretou e por quê.

## 10. Leitura do nome

O módulo [`src/gabarito/nome.py`](src/gabarito/nome.py) recorta a região
`NOME_RECT` da imagem canônica e, se houver `GEMINI_API_KEY`, envia o recorte
para o modelo configurado (`gemini-2.5-flash`).

Características importantes:

- sem chave de API, retorna `None`;
- erro de rede ou da API retorna `None`;
- resposta vazia ou `ILEGÍVEL` retorna `None`;
- nenhum desses casos interrompe o placar;
- o recorte continua visível para conferência humana;
- o campo do nome pode ser editado na UI.

Nos testes automatizados, a API é substituída por dublês para não depender de
rede nem consumir quota. Além disso, foi feita uma chamada manual real com uma
folha sintética; o Gemini retornou `Ana Carolina de Souza` para o nome impresso.

## 11. Por que escolhemos esses métodos

### ArUco em vez de tentar detectar a borda da folha

Detectar a borda da folha é mais frágil quando existe fundo parecido, sombra,
recorte ou perspectiva. Os ArUco têm identidade própria e informam diretamente
qual canto da folha foi encontrado.

Além disso, os marcadores permitem saber a orientação sem precisar de uma seta
ou código adicional.

### `DICT_4X4_50`

Foram comparados dicionários ArUco 4×4, 5×5 e 6×6. Nas resoluções relevantes,
o 4×4 foi suficiente e não foi superado pelos maiores. Usar um dicionário
maior também não resolveria os problemas de enquadramento ou iluminação.

### Medida local em vez de Otsu global

Otsu global foi descartado. Nos experimentos, sob um gradiente de iluminação,
uma bolinha vazia no lado escuro chegou a ser interpretada como preenchimento
com valor 1,000.

A medida local compara cada bolinha com o próprio papel ao redor e por isso é
mais estável.

### `adaptiveThreshold` apenas como conferência

O threshold adaptativo separa bem algumas marcas, mas ainda apresenta viés de
iluminação. Uma marca igual pode assumir valores diferentes em regiões claras
e escuras, e sob sombra forte uma marca boa pode ficar abaixo do limite.

Por isso ele não decide sozinho. A medida relativa local é a autoridade; o
threshold adaptativo pode apenas aumentar a cautela e produzir `REVISAR`.

### Pillow em vez de `cv2.putText`

O texto da folha inclui acentos, como em “questão”. As fontes Hershey do
OpenCV não são adequadas para isso. O projeto usa `ImageDraw.text` do Pillow.

Também não existe fallback silencioso para a fonte padrão do Pillow: em alguns
ambientes ela transforma acentos em glifos incorretos. Se o sistema não tiver
Arial ou DejaVu Sans, `fonte()` informa o problema e aceita o caminho definido
por `GABARITO_FONTE`.

## 12. O que foi testado

A suíte atual tem 286 testes:

| Arquivo | Quantidade | O que verifica |
|---|---:|---|
| `test_layout.py` | 7 | proporções, centros, sobreposição e limites |
| `test_gerar_folha.py` | 7 | folha, marcadores, bolinhas, PDF e fontes |
| `test_sintetico.py` | 8 | marcas e degradações sintéticas |
| `test_alinhar.py` | 19 | homografia, escalas, rotação e erros |
| `test_ler_marcas.py` | 9 | preenchimento e iluminação |
| `test_corrigir.py` | 12 | estados, anulação e placar |
| `test_pipeline.py` | 213 | integração e 200 folhas aleatórias |
| `test_anotar.py` | 3 | cores, dimensões e imutabilidade |
| `test_nome.py` | 8 | recorte e falhas da API |

Comando:

```bash
uv run pytest -q
```

Resultado validado:

```text
286 passed
```

### Gerador sintético

[`tests/sintetico.py`](tests/sintetico.py) cria uma folha com respostas
conhecidas e depois simula uma foto:

- perspectiva com deslocamento dos cantos;
- rotação de até aproximadamente ±15°;
- diferentes escalas;
- gradiente de iluminação;
- sombra;
- desfoque;
- compressão JPEG.

As marcas sintéticas têm cinco estilos:

- `cheia`: preenchimento escuro e quase completo;
- `boa`: preenchimento irregular, representando uma marca normal;
- `parcial`: aproximadamente meia marca;
- `leve`: traço em X;
- `apagada`: marca clara, parecida com uma borracha mal apagada.

## 13. Casos específicos testados ponta a ponta

O pipeline completo foi testado com:

- 200 folhas aleatórias, comparando cada resposta lida com a resposta esperada;
- duas alternativas marcadas, resultando em `ANULADA`;
- questão sem marca, resultando em `EM_BRANCO`;
- marca parcial, resultando em `REVISAR`;
- folha fotografada de cabeça para baixo;
- impressão 15% menor e 15% maior;
- fotos com lado maior de 800, 1200, 1600 e 2400 pixels;
- iluminação pior que a nominal, com lado escuro a 0,30;
- foto sem marcadores, que deve levantar erro e nunca produzir placar.

## 14. O que deu certo

Até agora, nos testes sintéticos:

- os quatro ArUco são encontrados nas degradações testadas;
- a marca volta para a posição correta depois da homografia;
- a folha de cabeça para baixo é alinhada corretamente;
- o leitor mantém as marcas boas sob iluminação difícil;
- marcas parciais não são forçadas para certa ou errada;
- duas marcações são anuladas;
- o placar bate com a verdade conhecida nas 200 folhas aleatórias;
- a interface mostra a explicação visual do resultado;
- o nome não bloqueia a correção quando a API está ausente.

## 15. O que não deu certo ou não está validado

### Métodos descartados

- Otsu global falhou sob iluminação desigual.
- Threshold adaptativo sozinho apresentou viés e não virou a decisão principal.
- Fallback silencioso do Pillow corrompia acentos.
- `cv2.putText` não foi usado porque suas fontes não atendem aos textos
  acentuados da folha.

### Ainda não validado

Ainda não foi feito o teste com uma folha realmente impressa. Os testes usam
imagens sintéticas e não reproduzem perfeitamente:

- textura e absorção reais do papel;
- reflexo de luz direta;
- dobra ou amassado;
- distorção de lente;
- desfoque de movimento;
- variações de impressora;
- diferentes tipos de caneta;
- enquadramentos reais de celular.

Foi feita uma chamada real de validação ao Gemini com uma chave fornecida para o
teste, usando um nome sintético renderizado na folha. Isso confirma a integração
de rede e o envio da imagem, mas não substitui o teste com nome manuscrito em
papel real. A integração também é coberta por testes simulados e o fallback é
seguro.

## 16. Limitações para mencionar na apresentação

- Os quatro marcadores precisam aparecer na foto.
- A resolução prática observada é aproximadamente 600 pixels no lado maior da
  folha; abaixo disso a detecção tende a degradar.
- Um “X” ou “✓” pode ser interpretado como vazio ou como uma marca ambígua; a
  folha instrui o aluno a preencher a bolinha inteira.
- O modelo pode transcrever o nome incorretamente; por isso o campo é editável.
- A validação sintética não equivale a uma garantia no mundo real.
- O título está abaixo da caixa de nome e as letras A/B/C/D aparecem em cada
  linha. Essas são decisões cosméticas mantidas como estão; não afetam a leitura.

## 17. Roteiro de demonstração

### Preparação

```bash
uv sync
uv run streamlit run app.py
```

Abra <http://localhost:8501>.

Para preparar uma demonstração completa sem papel, gere o kit de cenários:

```bash
uv run python scripts/gerar_demos.py
```

Os arquivos ficam em `saida/demos/`. Envie os arquivos `*_entrada.jpg` para a
interface; as imagens `*_conferencia.png` já mostram visualmente o resultado
esperado. A tabela e os detalhes estão em [`docs/demos.md`](docs/demos.md).

Se quiser testar sem papel, gere uma foto sintética:

```bash
uv run python -c "
import sys, cv2, numpy as np
sys.path.insert(0, 'tests')
import sintetico

chave = ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
marcas = sintetico.marcas_de_respostas(chave)
marcas[2] = [(0, 'cheia'), (3, 'cheia')]
del marcas[5]
rng = np.random.default_rng(42)
pagina = sintetico.folha_preenchida(marcas, rng=rng)
foto = sintetico.degradar(pagina, rng)
cv2.imwrite('saida/demo.jpg', foto)
"
```

Na apresentação:

1. mostre a chave na barra lateral;
2. mostre o botão de PDF;
3. envie a foto sintética ou uma foto real;
4. destaque a imagem de conferência;
5. mostre a questão anulada e a questão em branco;
6. altere a chave de uma questão e mostre o placar mudando;
7. explique que o nome é opcional e não interfere na nota.

### Demonstração com papel real

1. baixe o PDF pela própria interface;
2. imprima em A4, sem “ajustar à página”;
3. preencha uma alternativa por questão;
4. faça também uma questão em branco e uma com duas marcações;
5. fotografe a folha inteira, incluindo os quatro marcadores;
6. envie a foto;
7. compare a leitura automática com o papel.

Esse é o próximo experimento mais importante, porque valida a ponte entre o
algoritmo sintético e o comportamento físico do sistema.

## 18. Perguntas prováveis

### “Por que não usar um threshold global?”

Porque a iluminação não é uniforme. Um valor global pode confundir papel
escuro com tinta. A comparação com o anel local acompanha a iluminação de cada
região.

### “Por que não detectar todas as bolinhas com círculos?”

Porque as bolinhas já foram desenhadas pelo próprio sistema em posições fixas.
Detectá-las novamente adicionaria uma fonte de erro desnecessária.

### “E se a foto estiver de cabeça para baixo?”

Os IDs dos ArUco identificam os quatro cantos, então a homografia reorganiza a
folha corretamente.

### “Por que uma marca duvidosa não recebe uma nota?”

Porque seria inventar uma resposta. O sistema prefere mostrar `REVISAR` para que
uma pessoa decida.

### “O que acontece se faltar um marcador?”

O sistema falha de forma explícita e pede outra foto. Ele não calcula um
resultado estimado.

### “O nome é necessário para corrigir?”

Não. O nome é apenas uma informação auxiliar e seu processamento depende de uma
API externa.

### “Os 286 testes provam que funciona no mundo real?”

Não. Eles demonstram que o algoritmo funciona contra uma verdade conhecida em
imagens sintéticas. O teste com papel real ainda é necessário.

## 19. Arquivos importantes

| Arquivo | Função |
|---|---|
| `app.py` | interface Streamlit |
| `src/gabarito/layout.py` | geometria única da folha |
| `src/gabarito/gerar_folha.py` | folha canônica, A4 e PDF |
| `src/gabarito/alinhar.py` | ArUco e homografia |
| `src/gabarito/ler_marcas.py` | medição das bolinhas |
| `src/gabarito/corrigir.py` | estados e placar |
| `src/gabarito/anotar.py` | imagem de conferência |
| `src/gabarito/nome.py` | recorte e OCR opcional |
| `tests/sintetico.py` | gerador de folhas/fotos sintéticas |
| `tests/test_pipeline.py` | validação ponta a ponta |
| `scripts/gerar_demos.py` | gera o kit visual para demonstração sem papel |
| `README.md` | instruções curtas de uso |

## 20. Estado final

O código está testado, a UI está disponível localmente e o kit de demonstração
sem papel pode ser recriado com `scripts/gerar_demos.py`. A próxima etapa de
validação do mundo físico é imprimir uma folha e testar com uma foto real.
