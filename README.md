# Leitor de gabarito

Aplicação Streamlit que lê uma foto de um gabarito preenchido à mão com 8
questões e 4 alternativas por questão. Questões com mais de uma alternativa
marcada são anuladas.

## Instalação e execução

Instale as dependências com `uv` e inicie a interface:

```bash
uv sync
uv run streamlit run app.py
```

Abra <http://localhost:8501>. Sem `GEMINI_API_KEY`, a leitura das bolinhas
continua funcionando e o nome fica disponível para digitação manual. Para
ativar a transcrição opcional do nome:

```bash
GEMINI_API_KEY="sua-chave" uv run streamlit run app.py
```

Na barra lateral, escolha a chave de respostas e baixe a folha em PDF. Imprima
em A4 sem “ajustar à página”, preencha as bolinhas por inteiro e fotografe a
folha completa. A imagem pode ser enviada como arquivo ou capturada pela
webcam; os quatro marcadores ArUco dos cantos precisam estar visíveis.

Para tentar transcrever o nome manuscrito, defina `GEMINI_API_KEY` no
ambiente antes de iniciar o app. A transcrição é opcional: sem chave, sem rede,
com erro na API ou com resposta ilegível, o recorte continua visível e o nome
pode ser digitado no campo editável. O placar não depende da transcrição.

Se nenhuma fonte TrueType com acentuação estiver nos caminhos padrão, defina
`GABARITO_FONTE` apontando para um arquivo `.ttf` ou `.otf`. O gerador falha
explicitamente nesse caso para não produzir uma folha com texto corrompido.

Para demonstrar sem papel impresso, execute:

```bash
uv run python scripts/gerar_demos.py
```

Depois envie os arquivos `*_entrada.jpg` de `saida/demos/` para a interface. O
roteiro dos cinco cenários está em
[`docs/demos.md`](docs/demos.md).

## Funcionamento

O fluxo da aplicação é:

```text
foto → alinhamento por ArUco → leitura das 32 bolinhas → correção → anotação
                                  └→ recorte e transcrição opcional do nome
```

Os quatro marcadores identificam os cantos e permitem transformar a foto em
uma imagem canônica de 1000×1483 pixels, corrigindo perspectiva, rotação e
escala. Como as posições das bolinhas são conhecidas pelo módulo `layout`, o
leitor não precisa detectar círculos: mede o preenchimento relativo ao papel
ao redor de cada bolinha. A medida adaptativa é usada como conferência e pode
levar uma questão a `REVISAR`, mas não decide uma resposta sozinha.

A tela mostra a imagem de conferência, o recorte do nome, o placar `X/8` e uma
tabela com a situação de cada questão: `RESPONDIDA`, `ANULADA`, `EM BRANCO` ou
`REVISAR`. Se os quatro marcadores não forem encontrados, o app informa o erro
e não produz placar parcial.

## Testes e validação sintética

Execute a suíte completa com:

```bash
uv run pytest -q
```

Resultado atual: **286 testes passando**.

Para investigar uma parte específica:

```bash
uv run pytest tests/test_pipeline.py -q
uv run pytest tests/test_nome.py -q
```

Os testes geram folhas sintéticas a partir do mesmo layout usado na produção,
preenchem as respostas conhecidas e degradam as imagens como fotos de celular,
com perspectiva, rotação, escala, gradiente de iluminação, sombra, desfoque e
compressão JPEG. A integração verifica 200 folhas com respostas aleatórias,
além de folhas de cabeça para baixo, escalas diferentes, questões em branco,
marcações duplas, marcas ambíguas, iluminação difícil e fotos sem marcadores.

Essa validação é sintética: ela confirma o algoritmo contra uma verdade
conhecida, mas não substitui a demonstração com folhas impressas e fotos reais.

## Limitações conhecidas

- Ainda não há validação em papel real. Textura, reflexos, dobras, amassados,
  distorção de lente e desfoque de movimento podem se comportar de forma
  diferente das degradações simuladas.
- Os quatro marcadores precisam aparecer na foto. Um marcador cortado faz a
  leitura falhar corretamente, sem estimar um resultado parcial.
- A resolução prática observada é de aproximadamente 600 pixels no lado maior
  da folha; fotos muito distantes degradam a detecção.
- Um “X” ou “✓” em vez de uma bolinha preenchida pode ser lido como vazio. A
  folha instrui o preenchimento completo; marcas intermediárias tendem a virar
  `REVISAR`, mas não há garantia em todos os casos.
- A transcrição manuscrita não é verificada pelo software. O modelo pode errar,
  por isso o campo é editável e o recorte original permanece visível.

Detalhes do design e das decisões experimentais estão em
`docs/superpowers/specs/2026-09-13-leitor-gabarito-design.md`.
