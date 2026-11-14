# IV-B — Coleta eBPF

Compare throughput, CPU/memória e latência em três condições: `baseline`,
`tshark` e `collection-current`. Comece pelo **teste 1 — throughput TCP**.
O roteiro ainda precisa ser validado no servidor.

## Antes de começar — acessar o servidor e abrir os terminais

Conclua [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md), incluindo
`make clab-check` e `make clab-build`. Se o código mudou, atualize o repositório
e reconstrua o laboratório antes dos testes, conforme esse roteiro.

Abra um terminal no seu PC para cada função abaixo. Em cada um, execute primeiro
o SSH; espere aparecer o prompt do servidor antes de executar o bloco seguinte.
Se já estiver conectado ao servidor nesse terminal, pule somente o SSH.
Os comandos usam o acesso de Elisa; outras pessoas devem ajustar usuário,
endereço e chave. Ajuste também `~/xdp-flow-monitor` se necessário.

| Terminal | Container | Função |
| --- | --- | --- |
| 1 | `target` | Serviço que recebe conexões |
| 2 | `target` | Observação e coleta de métricas |
| 3 | `generator` | Geração de tráfego |

### TERMINAL 1 — Serviço que recebe conexões

**No PC**, conecte ao servidor:

```bash
ssh -i ~/.ssh/id_ed25519 elisa.jesus@10.50.1.91
```

**No servidor**, entre no repositório e abra o container `target`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 2 — Observação e coleta de métricas

**No PC**, conecte ao servidor:

```bash
ssh -i ~/.ssh/id_ed25519 elisa.jesus@10.50.1.91
```

**No servidor**, entre no repositório e abra o container `target`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 3 — Geração de tráfego

**No PC**, conecte ao servidor:

```bash
ssh -i ~/.ssh/id_ed25519 elisa.jesus@10.50.1.91
```

**No servidor**, entre no repositório e abra o container `generator`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=generator
```

O shell abre em `/workspace/testes/testes-chen/containers`. Confira o prompt:
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

## Se a rodada TShark não devolve o prompt

O terminal 3 (`generator`) termina a carga em aproximadamente 50 s; o terminal
2 (`target`, `observe`) observa por 70 s e depois encerra os processos. O serviço
no terminal 1 permanece ativo para as próximas rodadas. Não inicie outro servidor
iperf enquanto esse serviço estiver ativo.

O executor antigo usava uma espera sem limite no encerramento do TShark.
A versão corrigida mostra `Encerrando processos da observação`, concede até
5 s de tolerância e, se necessário, encerra o grupo TShark/dumpcap à força.
Isso não garante prazo em situações como bloqueio de I/O no kernel.
`shutdown.log` registra encerramento forçado; confira o log de captura antes de
validar a rodada. `status.txt` registra o código de saída (130 para Ctrl+C),
`end-epoch.txt` o fim das métricas e `cleanup-end-epoch.txt` o fim da limpeza.
Nenhum desses arquivos sozinho comprova uma rodada válida.

Atualizar apenas o Git no servidor não atualiza os containers: o código foi
copiado na construção da imagem. Com testes encerrados, atualize a elisa e
reconstrua pelo [roteiro do servidor](PREPARANDOSERVIDOR.md). Antes de começar,
confira no servidor se o código no container corresponde ao arquivo atualizado:

```bash
sha256sum containers/Makefile
sudo docker exec clab-chen-target sha256sum /workspace/testes/testes-chen/containers/Makefile
```

Execute esses dois comandos em `~/xdp-flow-monitor/testes/testes-chen`, fora
dos containers. Os hashes devem coincidir. Use `make -s observe ...` para
ocultar a impressão dos comandos e enxergar as mensagens de progresso.
Preserve tentativas interrompidas e repita com outro RUN nos dois terminais.

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
make -s serve SERVICE=iperf DURATION=1200 RUN=fig5-server
```

Mantenha esse terminal ocupado pelo serviço. Ele termina após 1200 segundos;
se encerrar antes de você concluir as rodadas, inicie-o novamente. Antes de cada
rodada, confira se continua ativo. Em caso de saída imediata, consulte o
`server.log` da execução em `/workspace/results/`.

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=baseline DURATION=70 RUN=fig5-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig5-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=tshark DURATION=70 RUN=fig5-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig5-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=collection-current DURATION=70 RUN=fig5-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=tcp DURATION=50 RUN=fig5-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Teste 2 — CPU e memória sob SYN flood

### TERMINAL 1 — TARGET: manter o serviço iperf3 ativo

Se o serviço do teste anterior ainda estiver rodando, mantenha-o. Caso tenha
terminado, execute:

```bash
make -s serve SERVICE=iperf DURATION=1200 RUN=fig5-syn-server
```

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=baseline DURATION=140 RUN=fig5-syn-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=tshark DURATION=140 RUN=fig5-syn-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=collection-current DURATION=140 RUN=fig5-syn-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Teste 3 — Latência TCP com Ethr

### TERMINAL 1 — TARGET: trocar iperf3 por Ethr

Encerre o iperf3 com **Ctrl+C no terminal 1** e aguarde o prompt retornar.
Ambos os serviços usam a porta 80, portanto não podem ficar ativos juntos.

```bash
make -s serve SERVICE=ethr DURATION=1200 RUN=fig5-lat-server
```

Se o serviço encerrar após 1200 segundos, reinicie-o antes da próxima rodada.

### Rodada 1 — baseline

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=baseline DURATION=140 RUN=fig5-lat-baseline-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=latency DURATION=120 RUN=fig5-lat-baseline-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 2 — tshark

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=tshark DURATION=140 RUN=fig5-lat-tshark-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=latency DURATION=120 RUN=fig5-lat-tshark-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.

### Rodada 3 — collection-current

#### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=collection-current DURATION=140 RUN=fig5-lat-collection-current-r1
```

**Aguarde aparecer `PRONTO: inicie a carga em generator`.** Só então execute
o próximo bloco no terminal 3 **imediatamente (procure iniciar em até 10 s)**.
Se houver erro, não inicie a carga.

#### TERMINAL 3 — GENERATOR: gerar o tráfego

```bash
make -s traffic KIND=latency DURATION=120 RUN=fig5-lat-collection-current-r1
```

Aguarde **os terminais 2 e 3 retornarem ao prompt** antes de iniciar outra rodada.


## Correções após a primeira execução

As rodadas antigas `collection-current` registraram falha de anexação XDP e
não medem o custo do eBPF. A topologia passou de MTU 9500 para 1500 nas duas
pontas; repita baseline, TShark e eBPF nessa configuração antes de compará-los.
Siga a atualização em [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md).

Se a porta 80 estiver ocupada, o serviço agora mostra o processo que a utiliza
e encerra com erro. Ao trocar iperf por Ethr, encerre o serviço anterior no
terminal 1. Não inicie a carga se o serviço falhar.

O cliente Ethr também recusa uma rodada com erro de handshake ou sem amostras.
Os percentis do JSON Ethr 1.0.0 observados nos primeiros resultados apresentaram
inconsistências; não os publique sem conferir a correspondência com o log textual.
Essa alteração não corrige o formato dos percentis do Ethr. A branch elisa agora
contém contagem por deltas e fechamento periódico das janelas; valide pelo
`make test-window` e pelos diagnósticos antes de repetir a série no servidor.

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
