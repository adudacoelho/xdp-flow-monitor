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

## Iniciar o serviço — TERMINAL 1, TARGET

```bash
make -s serve SERVICE=iperf DURATION=1200 RUN=fig6-server
```

Mantenha esse terminal ocupado. Se o iperf já estiver ativo na porta 80,
use o serviço existente; não inicie outro. Se o serviço encerrar após 1200 s,
reinicie-o com o comando acima antes da próxima rodada.

## Validação inicial — 16 regras, primeira repetição

Os seis cenários abaixo já têm todos os parâmetros preenchidos. Execute um
cenário por vez. Prepare o comando do terminal 3 antes de iniciar o terminal 2;
após `PRONTO`, inicie a carga imediatamente, de preferência em até 10 s.
Espere **os terminais 2 e 3** voltarem ao prompt antes do próximo cenário.
Se houver erro antes de `PRONTO`, não inicie a carga.

Esta sequência é uma validação funcional, não a campanha final de desempenho.
Não inicie cinco repetições antes de conferir os resultados desta primeira passagem.

### Throughput TCP sem ataque: baseline

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=baseline DURATION=70 RUN=fig6-tcp-baseline-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-baseline-r1
```

### Throughput TCP sem ataque: XDP estático — 16 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=16 DURATION=70 RUN=fig6-tcp-xdp-16-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-16-r1
```

### Throughput TCP sem ataque: iptables — 16 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=16 DURATION=70 RUN=fig6-tcp-iptables-16-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-16-r1
```

### CPU e memória sob SYN: baseline

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=baseline DURATION=140 RUN=fig6-syn-baseline-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-baseline-r1
```

### CPU e memória sob SYN: XDP estático — 16 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=16 DURATION=140 RUN=fig6-syn-xdp-16-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-16-r1
```

### CPU e memória sob SYN: iptables — 16 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=16 DURATION=140 RUN=fig6-syn-iptables-16-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-16-r1
```

## Outras quantidades de regras — executar após validar os seis cenários

Abaixo estão os comandos da primeira repetição para as demais quantidades,
sem precisar adaptar o exemplo de 16 regras. Cada seção contém quatro cenários;
abra somente a quantidade que pretende medir. O baseline correspondente está
na seção anterior. Não reutilize uma medição baseline de outra configuração
ou campanha sem verificar sua equivalência.

<details>
<summary>6 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 6 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=6 DURATION=70 RUN=fig6-tcp-xdp-6-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-6-r1
```

### Throughput TCP: iptables, 6 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=6 DURATION=70 RUN=fig6-tcp-iptables-6-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-6-r1
```

### CPU e memória sob SYN: XDP estático, 6 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=6 DURATION=140 RUN=fig6-syn-xdp-6-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-6-r1
```

### CPU e memória sob SYN: iptables, 6 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=6 DURATION=140 RUN=fig6-syn-iptables-6-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-6-r1
```

</details>

<details>
<summary>32 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 32 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=32 DURATION=70 RUN=fig6-tcp-xdp-32-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-32-r1
```

### Throughput TCP: iptables, 32 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=32 DURATION=70 RUN=fig6-tcp-iptables-32-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-32-r1
```

### CPU e memória sob SYN: XDP estático, 32 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=32 DURATION=140 RUN=fig6-syn-xdp-32-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-32-r1
```

### CPU e memória sob SYN: iptables, 32 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=32 DURATION=140 RUN=fig6-syn-iptables-32-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-32-r1
```

</details>

<details>
<summary>64 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 64 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=64 DURATION=70 RUN=fig6-tcp-xdp-64-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-64-r1
```

### Throughput TCP: iptables, 64 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=64 DURATION=70 RUN=fig6-tcp-iptables-64-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-64-r1
```

### CPU e memória sob SYN: XDP estático, 64 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=64 DURATION=140 RUN=fig6-syn-xdp-64-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-64-r1
```

### CPU e memória sob SYN: iptables, 64 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=64 DURATION=140 RUN=fig6-syn-iptables-64-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-64-r1
```

</details>

<details>
<summary>128 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 128 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=128 DURATION=70 RUN=fig6-tcp-xdp-128-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-128-r1
```

### Throughput TCP: iptables, 128 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=128 DURATION=70 RUN=fig6-tcp-iptables-128-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-128-r1
```

### CPU e memória sob SYN: XDP estático, 128 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=128 DURATION=140 RUN=fig6-syn-xdp-128-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-128-r1
```

### CPU e memória sob SYN: iptables, 128 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=128 DURATION=140 RUN=fig6-syn-iptables-128-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-128-r1
```

</details>

<details>
<summary>256 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 256 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=256 DURATION=70 RUN=fig6-tcp-xdp-256-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-256-r1
```

### Throughput TCP: iptables, 256 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=256 DURATION=70 RUN=fig6-tcp-iptables-256-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-256-r1
```

### CPU e memória sob SYN: XDP estático, 256 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=256 DURATION=140 RUN=fig6-syn-xdp-256-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-256-r1
```

### CPU e memória sob SYN: iptables, 256 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=256 DURATION=140 RUN=fig6-syn-iptables-256-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-256-r1
```

</details>

<details>
<summary>512 regras — comandos prontos (r1)</summary>

### Throughput TCP: XDP estático, 512 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=512 DURATION=70 RUN=fig6-tcp-xdp-512-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-xdp-512-r1
```

### Throughput TCP: iptables, 512 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=512 DURATION=70 RUN=fig6-tcp-iptables-512-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig6-tcp-iptables-512-r1
```

### CPU e memória sob SYN: XDP estático, 512 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=xdp-static RULES=512 DURATION=140 RUN=fig6-syn-xdp-512-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-xdp-512-r1
```

### CPU e memória sob SYN: iptables, 512 regras

**TERMINAL 2 — TARGET: observar**

```bash
make -s observe MODE=iptables RULES=512 DURATION=140 RUN=fig6-syn-iptables-512-r1
```

**TERMINAL 3 — GENERATOR: executar assim que aparecer `PRONTO`**

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-iptables-512-r1
```

</details>

## Interpretação e campanha final

Esta adaptação começa em seis regras: ambos os filtros incluem as seis origens
simuladas .101–.106. As demais regras usam os mesmos IPs de preenchimento
198.18.x.x, antes das seis regras que casam com o SYN. O TCP legítimo vem de .10
e não casa com essas regras.

Os blocos acima são todos `r1`. Tentativas interrompidas devem ser preservadas
e identificadas separadamente antes de repetir. A numeração automática continua
adiada até validar os testes, conforme combinado. Para a campanha final, serão
necessárias pelo menos cinco repetições por condição e ordem alternada entre
comparadores; esta passagem inicial não fornece essa evidência estatística.

Confira `xdp-rules.json`, `xdp-program.json`, `xdp-attached.json` no modo XDP
e `iptables-counters.txt` no modo iptables. Antes de uma campanha, confirme a
quantidade de regras e o bloqueio das seis origens; anexação sozinha não prova
que o tráfego foi descartado. O XDP usa LPM trie, enquanto iptables percorre
regras sequencialmente: a estrutura e a posição das regras fazem parte da análise.

Os dados ficam em `results-servidor/target` e `generator`, associados por RUN.
CPU/memória são do host compartilhado; selecione somente o intervalo da carga.
5.000 pps é carga inicial solicitada, não os 1,92 Gbps do artigo. Registre a taxa
real e calibre antes de aumentar. Não misture resultados históricos com os novos.
