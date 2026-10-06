# IV-D — Classificação

**ESTADO: procedimento experimental ainda pendente.**

Objetivo: Comparar acurácia, precisão, recall, F1 e taxas de detecção de normais e ataques (Figura 7).

## Antes de começar — entrar no container TARGET

Prepare o ambiente seguindo [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md).
Em uma sessão SSH **no servidor**, execute:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

O prompt deve mostrar `root@target`, na pasta
`/workspace/testes/testes-chen/containers`. Se já estiver nesse container:

```bash
cd /workspace/testes/testes-chen/containers
```

## O que falta para executar a comparação

Precisamos definir os dados reais, as partições de treino/teste e o contrato de
features antes de apresentar resultados como reprodução do artigo.
A comparação entre todos os modelos ainda não está implementada.

## TERMINAL TARGET — treinamento isolado disponível

**Execute somente depois de preparar os CSVs em `/workspace/dataset`.**
Este comando treina apenas o XGBoost existente; não executa a comparação completa.

```bash
make ml
```

O treinamento salva o modelo e `training.log` em `/workspace/build/ml`.
Essa pasta é interna ao container e não é o diretório de resultados montado;
preserve os artefatos antes de remover o laboratório. O daemon ainda carrega
`xdp-flow-monitor-main/ddos_model.ubj`: esse treinamento não substitui
automaticamente o modelo usado pelo detector.
