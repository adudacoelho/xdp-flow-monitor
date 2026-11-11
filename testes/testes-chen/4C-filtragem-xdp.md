# IV-C — Filtragem XDP versus iptables

A integração usa `xdp_min.c` da branch de IV-C como filtro estático isolado,
sem coletor ou ML. Não mede o custo do detector completo. Os scripts antigos
em `testes/letra-c*` e seus resultados permanecem como histórico: usam outra
topologia e não devem ser executados diretamente no laboratório `chen`.

Atualize o laboratório conforme [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md),
incluindo reconstrução da imagem e `make clab-build`. Valide primeiro uma rodada
curta. A integração ainda precisa ser executada no servidor.

Abra três sessões SSH e entre em `testes/testes-chen` no servidor:

- Terminal 1: `make clab-shell NODE=target` (serviço).
- Terminal 2: `make clab-shell NODE=target` (observação).
- Terminal 3: `make clab-shell NODE=generator` (carga).

Os shells abrem em `/workspace/testes/testes-chen/containers`.

## Throughput sem ataque

Terminal 1:

```bash
make serve SERVICE=iperf DURATION=1200 RUN=fig6-server
```

Terminal 2:

```bash
make observe MODE=xdp-static RULES=16 DURATION=70 RUN=fig6-tcp-xdp-16-r1
```

Após `PRONTO`, imediatamente no terminal 3:

```bash
make traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-16-r1
```

Espere ambos terminarem. Repita com `MODE=iptables` e identificação
`fig6-tcp-iptables-16-r1`. Faça também baseline, sem filtro, com `MODE=baseline`.

## CPU e memória sob SYN

Terminal 2:

```bash
make observe MODE=xdp-static RULES=16 DURATION=140 RUN=fig6-syn-xdp-16-r1
```

Após `PRONTO`, imediatamente no terminal 3:

```bash
make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-16-r1
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
