# Demonstração offline com CSV — opção de um único terminal

Esta opção apresenta amostras do CSV ao XGBoost existente e compara a previsão
real com o rótulo esperado. **Não gera tráfego e não bloqueia IPs.**
Não depende de Containerlab, serviço iperf ou detector rodando.

## Opção mais rápida no servidor: imagem Docker já construída

Copie/atualize o Makefile e `scripts/demo_csv.py` no servidor. Não precisa
reconstruir a imagem: o código atual é montado em modo somente leitura.
Em um único terminal, na raiz:

```bash
cd ~/xdp-flow-monitor
make demo-csv-docker
```

Esse comando usa a imagem local `chen-lab:local`, sem rede e sem privilégios
de monitoramento. Não cria o laboratório. Se a imagem não estiver disponível,
use um ambiente Python com as dependências pela opção abaixo.

Pressione **Enter** para iniciar e avançar cada amostra. **Ctrl+C** encerra.
O terminal mantém todas as amostras e resultados anteriores: role para cima
para comparar a sequência. A demonstração não limpa a tela entre amostras.
São dez amostras por padrão, alternando classes quando ambas estão disponíveis.
A seleção tem seed fixa e depende somente dos rótulos, nunca dos acertos.

```bash
make demo-csv-docker SAMPLES=6
```

## Opção sem Docker: Python com numpy e XGBoost

Use um ambiente Python existente com `numpy` e `xgboost` (a imagem usa
numpy 1.26.4 e XGBoost 2.1.4). O Makefile usa `.venv/bin/python` se existir;
caso contrário, `python3`. Você pode indicar o interpretador explicitamente:

```bash
make demo-csv-check CSV_PYTHON=/caminho/da/venv/bin/python
make demo-csv CSV_PYTHON=/caminho/da/venv/bin/python
```

Se o Python padrão já tem as dependências:

```bash
make demo-csv-check
make demo-csv
```

O check confere colunas, valores, nomes/ordem das features e executa a inferência
nas amostras selecionadas. Exibe o hash do modelo. Não altera nem retreina nada.
Os alvos sem Docker aceitam `CSV=/caminho/arquivo.csv` e
`MODEL=/caminho/modelo.ubj`; os arquivos precisam seguir o contrato do treinador
atual. O alvo Docker usa os arquivos padrão do repositório.

## O que dizer para os alunos

1. **“Cada linha descreve características de uma amostra de tráfego.”**
2. **“O CSV tem um rótulo esperado; o modelo recebe apenas as características.”**
3. **“Vamos comparar a previsão com esse rótulo, mostrando acertos e erros.”**
4. **“No sistema integrado, uma previsão de ataque solicita o bloqueio.
   Aqui mostramos somente essa decisão, sem aplicar bloqueio de rede.”**

A pontuação exibida é a saída do modelo, não uma garantia de confiança calibrada.
O limiar é o mesmo do daemon: maior que 0,5 significa ataque.

**Limites:** não foi comprovado que o CSV seja independente do treinamento.
O CSV sintético local contém inconsistências. A demonstração preserva a escala
original da duração, como o treinador atual (apenas renomeia a coluna).
Isso não corrige a incompatibilidade com duração em segundos na coleta ao vivo.
Acertos nesta apresentação não comprovam generalização ou detecção em rede real.

## Projetor

Projete só este terminal em tela cheia e aumente a fonte para 24–32 pontos,
ajustando para caberem cerca de 25 linhas e 65 colunas. Nada depende de cores.
Não é necessário manter outros terminais abertos.
