# IV-C — Filtragem XDP versus iptables

A integração usa `xdp_min.c` da branch de IV-C como filtro estático isolado,
sem coletor ou ML. Não mede o custo do detector completo. Os scripts antigos
em `testes/letra-c*` e seus resultados permanecem como histórico: usam outra
topologia e não devem ser executados diretamente no laboratório `chen`.

Atualize o laboratório conforme [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md),
incluindo reconstrução da imagem e `make clab-build`. Valide primeiro uma rodada
curta. A integração ainda precisa ser executada no servidor.

## Antes de começar — já dentro do servidor

Conclua [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md), incluindo
`make clab-check` e `make clab-build`. Se o código mudou, atualize o repositório
e reconstrua o laboratório antes dos testes, conforme esse roteiro.

**Já dentro do servidor**, use um terminal separado para cada função abaixo.
Ajuste `~/xdp-flow-monitor` se o projeto estiver em outro caminho.

| Terminal | Container | Função |
| --- | --- | --- |
| 1 | `target` | Serviço que recebe conexões |
| 2 | `target` | Observação e coleta de métricas |
| 3 | `generator` | Geração de tráfego |

### TERMINAL 1 — Serviço que recebe conexões

**Já dentro do servidor**, entre no repositório e abra o container `target`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 2 — Observação e coleta de métricas

**Já dentro do servidor**, entre no repositório e abra o container `target`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 3 — Geração de tráfego

**Já dentro do servidor**, entre no repositório e abra o container `generator`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=generator
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

## Throughput sem ataque

Terminal 1:

```bash
make -s serve SERVICE=iperf DURATION=1200 RUN=fig6-server
```

Terminal 2:

```bash
make -s observe MODE=xdp-static RULES=16 DURATION=70 RUN=fig6-tcp-xdp-16-r1
```

Após `PRONTO`, imediatamente no terminal 3:

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-16-r1
```

Espere ambos terminarem. Repita com `MODE=iptables` e identificação
`fig6-tcp-iptables-16-r1`. Faça também baseline, sem filtro, com `MODE=baseline`.

## CPU e memória sob SYN

Terminal 2:

```bash
make -s observe MODE=xdp-static RULES=16 DURATION=140 RUN=fig6-syn-xdp-16-r1
```

Após `PRONTO`, imediatamente no terminal 3:

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-16-r1
```

Repita com `MODE=iptables`, alterando também o RUN nos dois terminais, e baseline.
Faça cinco repetições e alterne a ordem dos modos. Use inicialmente 6, 16, 32,
64, 128, 256 e 512 regras. Esta adaptação começa em seis, pois ambos os filtros
sempre incluem as seis origens simuladas .101–.106. As demais regras são os
mesmos IPs de preenchimento 198.18.x.x nos dois filtros, antes das seis regras
que casam com o SYN. O TCP legítimo vem de .10 e não casa com essas regras.

Confira `xdp-rules.json`, `xdp-program.json`, `xdp-attached.json` no modo XDP
e `iptables-counters.txt` no modo iptables. Antes de uma campanha, confirme a
quantidade de regras e o bloqueio das seis origens; anexação sozinha não prova
que o tráfego foi descartado. O XDP usa LPM trie, enquanto iptables percorre
regras sequencialmente: a estrutura e a posição das regras fazem parte da análise.

Os dados ficam em `results-servidor/target` e `generator`, associados por RUN.
CPU/memória são do host compartilhado; selecione somente o intervalo da carga.
5.000 pps é carga inicial solicitada, não os 1,92 Gbps do artigo. Registre a taxa
real e calibre antes de aumentar. Não misture resultados históricos com os novos.
