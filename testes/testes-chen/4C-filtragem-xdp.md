# IV-C — Filtragem XDP

**ESTADO: procedimento experimental ainda pendente.**

Objetivo: Comparar throughput, CPU e memória entre XDP e iptables, variando o número de regras (Figura 6).

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

O filtro BPF adicional foi removido. **`MODE=xdp` não existe no Makefile atual.**
O comparador `MODE=iptables` está disponível, mas ainda precisamos definir o
procedimento de comparação usando a implementação do projeto, com quantidades
de regras e cargas equivalentes. O detector completo não equivale a um filtro
estático isolado.

Ainda não há uma sequência completa de comandos para este experimento.
