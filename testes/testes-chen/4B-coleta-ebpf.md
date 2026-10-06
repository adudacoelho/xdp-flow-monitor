# IV-B — Coleta eBPF

Compare throughput, CPU/memória e latência em três condições: `baseline`,
`tshark` e `collection-current`. Comece pelo **teste 1 — throughput TCP**.
O roteiro ainda precisa ser validado no servidor.

## Antes de começar — abrir os terminais

Conclua [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md), incluindo a compilação
com `make clab-build`. Abra **uma sessão SSH no servidor para cada terminal**
abaixo. Ajuste `~/xdp-flow-monitor` se o projeto estiver em outro caminho.

| Terminal | Container | Função |
| --- | --- | --- |
| 1 | `target` | Serviço que recebe conexões |
| 2 | `target` | Observação e coleta de métricas |
| 3 | `generator` | Geração de tráfego |

### TERMINAL 1 — NO SERVIDOR: entrar em TARGET

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```


### TERMINAL 2 — NO SERVIDOR: entrar em TARGET

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```


### TERMINAL 3 — NO SERVIDOR: entrar em GENERATOR

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=generator
```

O shell já abre em `/workspace/testes/testes-chen/containers`.
Confira o prompt: **`root@target` nos terminais 1 e 2** e
**`root@generator` nos terminais de geração**.
Se já estiver no container correto, basta entrar na pasta:

```bash
cd /workspace/testes/testes-chen/containers
```

**Execute cada bloco somente no terminal indicado.** Os comandos de serviço,
observação e tráfego ocupam o terminal até terminarem. Não cole todos os blocos
em um único shell. Para sair de um container, use `exit 0`.

## ATENÇÃO — prepare a carga antes de iniciar a observação

Deixe o comando do terminal 3 digitado, **sem pressionar Enter**. Inicie a
observação no terminal 2 e, assim que aparecer `PRONTO`, execute a carga no
terminal 3. **Procure iniciar em até 10 segundos.**

Mantemos o encerramento automático para evitar uma coleta esquecida e padronizar
as durações das rodadas. Os 70 s de observação para 50 s de carga (e 140 s para
120 s) são escolhas deste roteiro, não uma exigência de Chen. A margem total é
20 s, incluindo atraso de início e encerramento; ela não é tempo de espera sugerido.

O objetivo é evitar comparações distorcidas por períodos diferentes com e sem
tráfego. **O limite de tempo sozinho não garante carga constante nem médias
comparáveis:** use os horários registrados e analise o período efetivo da carga.
Se a observação não cobrir toda a transferência, marque a rodada como incompleta
e repita com outro `RUN`, preservando os arquivos anteriores.

Manter tráfego legítimo contínuo e ligar/desligar um ataque é outro cenário,
adequado para estudar o impacto do ataque sobre esse tráfego. Exige períodos
bem definidos antes/durante/depois e não substitui automaticamente as condições
de coleta deste roteiro. Aqui mantemos as cargas com duração limitada.

## Teste 1 — Throughput TCP

### TERMINAL 1 — TARGET: iniciar o serviço iperf3

```bash
make serve SERVICE=iperf DURATION=1200 RUN=fig5-server
```

Mantenha esse terminal ocupado pelo serviço. Ele termina após 1200 segundos;
se encerrar antes de você concluir as rodadas, inicie-o novamente. Antes de cada
rodada, confira se continua ativo. Em caso de saída imediata, consulte o
`server.log` da execução em `/workspace/results/`.

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=baseline DURATION=70 RUN=fig5-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=tcp DURATION=50 RUN=fig5-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=tshark DURATION=70 RUN=fig5-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=tcp DURATION=50 RUN=fig5-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=collection-current DURATION=70 RUN=fig5-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=tcp DURATION=50 RUN=fig5-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Teste 2 — CPU e memória sob SYN flood

### TERMINAL 1 — TARGET: manter o serviço iperf3 ativo

Se o serviço do teste anterior ainda estiver rodando, mantenha-o. Caso tenha
terminado, execute:

```bash
make serve SERVICE=iperf DURATION=1200 RUN=fig5-syn-server
```

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=baseline DURATION=140 RUN=fig5-syn-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=tshark DURATION=140 RUN=fig5-syn-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=collection-current DURATION=140 RUN=fig5-syn-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Teste 3 — Latência TCP com Ethr

### TERMINAL 1 — TARGET: trocar iperf3 por Ethr

Encerre o iperf3 com **Ctrl+C no terminal 1** e aguarde o prompt retornar.
Ambos os serviços usam a porta 80, portanto não podem ficar ativos juntos.

```bash
make serve SERVICE=ethr DURATION=1200 RUN=fig5-lat-server
```

Se o serviço encerrar após 1200 segundos, reinicie-o antes da próxima rodada.

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=baseline DURATION=140 RUN=fig5-lat-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=latency DURATION=120 RUN=fig5-lat-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=tshark DURATION=140 RUN=fig5-lat-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=latency DURATION=120 RUN=fig5-lat-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make observe MODE=collection-current DURATION=140 RUN=fig5-lat-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make traffic KIND=latency DURATION=120 RUN=fig5-lat-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Resultados e interpretação

Os arquivos ficam em `/workspace/results/` no respectivo container. No servidor,
eles aparecem em `testes/testes-chen/results-servidor/target/` e `generator/`.
Associe os arquivos pelo identificador `RUN` igual nos dois terminais.

| Medição | Arquivo | Container |
| --- | --- | --- |
| Throughput TCP | `iperf.json` | `generator` |
| CPU | `cpu.txt` | `target` |
| Memória | `memory.txt` | `target` |
| Rede | `network.txt` | `target` |
| Latência | `ethr.json` e `ethr.log` | `generator` |
| Coletor eBPF | `monitor.log` | `target` |

CPU e memória refletem o **servidor compartilhado**. A observação inclui tempo
antes e depois da carga; use os registros de início/fim para identificar o período
sob tráfego. Guarde os logs Ethr e reporte média e percentis disponíveis.
Não substitua a medição de latência TCP por ping ICMP.

Para baixar os arquivos, siga [OBTENDORESULTADOS.md](OBTENDORESULTADOS.md).
Para novas repetições, troque `r1` por `r2`, etc., nos dois comandos da rodada.

## Protocolo e limitações

- Para throughput durante 200 s com intervalos de 50 s, use carga de 200 s e
  observação de 220 s; agregue os intervalos de 1 s do JSON iperf3 em quatro blocos.
- TShark é o comparador sem GUI, com análise textual gravada em log. O custo de
  saída e disco faz parte desta configuração; não é a aplicação gráfica Wireshark.
- `collection-current` executa o coletor sem daemon ML, com exportação por pacote
  e logging. Ainda **não representa a coleta corrigida do artigo**.
- No SYN flood, `PPS=5000` é a taxa total solicitada, distribuída entre seis
  processos com origens 192.168.157.101–106. Registre as taxas realmente observadas.
- O artigo informa aproximadamente **1,92 Gbps**. Não declare essa taxa sem medi-la,
  nem suponha que `--flood` a garante. Registre tamanho dos pacotes e camada de
  contagem dos bytes. Calibre cargas maiores antes da série experimental.
