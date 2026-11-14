# IV-D — Classificação

A branch `teste-letra-d` foi integrada: `evaluate_models.py` compara Logistic
Regression, Naive Bayes, KNN, SVM RBF, Decision Tree, Random Forest, MLP e
XGBoost. Salva métricas, matriz de confusão em colunas TN/FP/FN/TP, tempos de
lote e gráficos. Isso é uma reprodução adaptada; os hiperparâmetros e modelos
implementados precisam ser confrontados com o protocolo desejado.

## Preparação

Atualize o laboratório por [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md).
Reconstrua a imagem: matplotlib foi acrescentado às dependências fixadas.
No servidor, coloque o CSV real em `dataset/Syn.csv` antes de criar o laboratório.
Essa pasta é montada somente para leitura nos containers. Escolha explicitamente
os arquivos; apontar para uma pasta mistura todos os CSVs dela.

## Antes de começar — já dentro do servidor

Conclua [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md), incluindo
`make clab-check` e `make clab-build`. Se o código mudou, atualize o repositório
e reconstrua o laboratório antes dos testes, conforme esse roteiro.

**Já dentro do servidor**, use um terminal separado para cada função abaixo.
Ajuste `~/xdp-flow-monitor` se o projeto estiver em outro caminho.

| Terminal | Container | Função |
| --- | --- | --- |
| 1 | `target` | Classificação e avaliação dos modelos |

### TERMINAL 1 — Classificação e avaliação dos modelos

**Já dentro do servidor**, entre no repositório e abra o container `target`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

O shell abre em `/workspace/testes/testes-chen/containers` com o prompt em
verde automaticamente pelo comando `make clab-shell`. Confira o prompt:
`root@target` nos terminais de serviço/observação/classificação e
`root@generator` nos terminais de carga. Se já estiver no container correto:

```bash
cd /workspace/testes/testes-chen/containers
```

Execute os comandos de cada teste somente no terminal indicado. Os serviços e
as coletas ocupam seus terminais até terminar; não cole todos os blocos em um
único shell. Para sair do container e voltar ao servidor, use `exit 0`.
Os comandos abaixo usam `make -s` para ocultar a listagem interna do Makefile;
as mensagens do teste e os erros continuam aparecendo.

## Validar janelas

Dentro de target, na pasta aberta pelo shell:

```bash
make -s test-window
```

Esse teste C não depende de tráfego ou carregamento BPF.

## Avaliar modelos

```bash
make -s ml-evaluate DATA=/workspace/dataset/Syn.csv DURATION_UNIT=us MAX_ROWS=20000 CV=0 JOBS=2 RUN=fig7-real-r1
```

Comece sem validação cruzada. SVM e KNN podem demorar; `MAX_ROWS` limita a amostra
estratificada. Após conferir a execução, se necessário use `CV=5`. Não rode o
benchmark de CPU/rede ao mesmo tempo que o treinamento. Este comando termina
quando os modelos concluem; `DURATION` não limita o treinamento.

Os artefatos ficam em `/workspace/results/<timestamp>-ml-evaluate-<RUN>/`,
persistidos no servidor em `results-servidor/target/`. Incluem CSV/Markdown,
`fig7a_metrics.png`, `fig7b_detect_rates.png`, log, parâmetros e hashes de dados
e código. Consulte [OBTENDORESULTADOS.md](OBTENDORESULTADOS.md) para baixar.

O split é aleatório estratificado por linha, seed 42. Ele não previne vazamento
entre capturas relacionadas. Resultados científicos exigem identificar os dados,
verificar duplicatas e definir partições independentes por captura/dia/origem.
As taxas são TN/(TN+FP) para normais e TP/(TP+FN) para ataques. O tempo de
inferência em lote não equivale ao tempo por pacote da Tabela II.

## Treinar apenas XGBoost

```bash
make -s ml DATA=/workspace/dataset/Syn.csv DURATION_UNIT=us RUN=xgb-real-r1
```

O modelo é salvo no volume de resultados junto com o log e hashes. A duração
é convertida de microssegundos para segundos por `features.py`; para outras
fontes, informe `DURATION_UNIT=ms` ou `s` conforme a unidade real.
O modelo versionado e o daemon não são substituídos automaticamente. Um modelo
antigo treinado na escala anterior precisa ser retreinado antes de uso ao vivo.

## Ensaio sem dados reais

Em outro terminal conectado ao servidor, **fora dos containers**, gere um arquivo
separado usando um ambiente Python com numpy e pandas. Entre primeiro na raiz
do repositório (esse comando não usa a pasta `testes/testes-chen`):

```bash
cd ~/xdp-flow-monitor
python3 xdp-flow-monitor-main/gen_dataset.py --n 2000 --out dataset/ensaio-sintetico.csv
```

Depois use `DATA=/workspace/dataset/ensaio-sintetico.csv` e um RUN identificado
como sintético. Não substitua o CSV versionado ou misture esse arquivo com dados
reais. O gerador é uma ferramenta de ensaio e não reproduz CIC-DDoS2019.
