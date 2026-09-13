# Kit de demonstração sem papel

Para gerar ou recriar os materiais visuais:

```bash
UV_CACHE_DIR=/private/tmp/visao-uv-cache uv run python scripts/gerar_demos.py
```

Os arquivos são criados em `saida/demos/`, que é uma pasta local de saída e
fica fora do Git. Cada cenário produz quatro arquivos:

- `*_entrada.jpg`: imagem para enviar ao Streamlit;
- `*.pdf`: folha sintética preenchida, útil para mostrar o formato A4;
- `*_alinhada.png`: resultado depois da homografia dos ArUco;
- `*_conferencia.png`: resultado final com círculos e estados coloridos.

| Cenário | Entrada | Resultado esperado |
|---|---|---|
| Tudo correto | `01_tudo_certo_entrada.jpg` | `8/8` |
| Anulada e em branco | `02_anulada_branco_entrada.jpg` | `6/8`, questão 3 anulada e questão 5 em branco |
| Erro e revisão | `03_erro_revisar_entrada.jpg` | `5/8`, questões 2 e 5 erradas e questão 6 para revisar |
| Iluminação difícil | `04_luz_dificil_entrada.jpg` | `8/8` mesmo com sombra e gradiente |
| Cabeça para baixo | `05_cabeca_baixo_entrada.jpg` | `8/8` mesmo com rotação de 180° |

Para uma apresentação rápida, envie `02_anulada_branco_entrada.jpg` primeiro:
ela mostra simultaneamente acertos, anulação e questão em branco. Depois envie
`03_erro_revisar_entrada.jpg` para mostrar vermelho e amarelo na imagem de
conferência.

Os resultados em `resultados.json` são escritos pelo gerador e servem como
referência do que a demonstração deve produzir.

O arquivo `painel_resumo.png` reúne as cinco imagens de conferência em uma
única composição, útil para mostrar o conjunto em um slide.
