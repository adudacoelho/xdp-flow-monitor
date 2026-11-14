# IV-E — Sistema completo

**Roteiro preliminar: ainda há pendências de instrumentação e de validação do
detector.** Os comandos abaixo não produzem, sozinhos, uma reprodução válida
dos tempos por etapa ou da detecção do artigo.

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
| 4 | `generator` | Tráfego TCP simultâneo ao ataque |

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

### TERMINAL 4 — Tráfego TCP simultâneo ao ataque

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

## Experimento 1 — Replay e tempos por etapa (Tabela II)

1. Obtenha um PCAP real, selecione somente o sentido atacante → vítima e
   preserve o original. Não transforme o tráfego de retorno em ataque.
### TERMINAL 3 — GENERATOR: preparar o PCAP

Converta a cópia selecionada em PCAP clássico Ethernet/IPv4
   (sem VLAN), e reescreva endereços/MACs para o laboratório:

```bash
editcap -F pcap /workspace/dataset/attack-only.pcapng /workspace/results/attack-only.pcap
tcprewrite --infile=/workspace/results/attack-only.pcap --outfile=/workspace/results/lab.pcap \
  --srcipmap=0.0.0.0/0:192.168.157.101/32 \
  --dstipmap=0.0.0.0/0:192.168.157.20/32 \
  --enet-smac=52:54:00:ce:02:10 --enet-dmac=52:54:00:ce:02:20 --fixcsum
```

### TERMINAL 2 — TARGET: iniciar a observação

```bash
make -s observe MODE=collection-current DURATION=140 RUN=table2-r1
```

**Aguarde `PRONTO` antes de iniciar o replay.**

### TERMINAL 3 — GENERATOR: executar o replay

```bash
make -s traffic KIND=replay PCAP=results/lab.pcap PPS=180163 DURATION=120 RUN=table2-r1
```

O executor valida os endereços antes de enviar; guarde estatísticas do tcpreplay
e checksum do PCAP original e reescrito. A cópia converte origens para um IP e
altera a diversidade de fluxos: declare essa adaptação; não use seu resultado
como avaliação da diversidade original. Repita com as etapas relevantes após
corrigir/instrumentar o sistema.

**Pendente:** replay pronto não mede tempos individuais. Para reproduzir a
Tabela II ainda precisamos instrumentar coleta, inferência e filtragem,
definir início/fim de cada medição, medir overhead e salvar amostras. Inferência
por janela não é tempo por pacote. Não dividir 120 s pelo número de pacotes
nem tratar o inverso de 180.163 pps como latência de processamento. Referências
publicadas: 12,68 µs (eBPF), 11,96 µs (XGBoost), 5,72 µs (XDP).

## Experimento 2 — Sistema completo versus Snort (Figura 8)

### TERMINAL 1 — TARGET: iniciar o serviço

```bash
make -s serve SERVICE=iperf DURATION=600 RUN=fig8-server
```

Mantenha-o ativo. Se encerrar após 600 segundos, reinicie antes da próxima rodada.

### TERMINAL 2 — TARGET: observar com Snort

```bash
make -s observe MODE=snort DURATION=150 RUN=fig8-snort-5000-r1
```

**Aguarde `PRONTO`.** Em seguida, inicie a carga no terminal 3 e, logo depois,
o tráfego TCP no terminal 4, enquanto a carga ainda estiver rodando.

### TERMINAL 3 — GENERATOR: iniciar a carga UDP

```bash
make -s traffic KIND=udp PPS=5000 DURATION=120 RUN=fig8-snort-5000-r1
```

### TERMINAL 4 — GENERATOR: iniciar o TCP simultâneo

```bash
make -s traffic KIND=tcp DURATION=110 RUN=fig8-snort-5000-tcp-r1
```

### Próximas rodadas

Aguarde os terminais 2, 3 e 4 retornarem ao prompt antes de cada nova rodada.
Repita a sequência com `MODE=baseline` e `MODE=detector-current` no terminal 2.
Atualize também `snort` no nome `RUN` dos três comandos para identificar o modo.

Repita para **5.000, 10.000, 50.000, 100.000 e 150.000 pps**, alterando `PPS`
no terminal 3 e a identificação da taxa nos nomes `RUN`. Registre a taxa
realmente alcançada e faça cinco repetições, identificadas por `r1` a `r5`.

## Interpretação e pendências

Para permitir tráfego TCP legítimo simultâneo ao UDP, cada tipo de carga usa um
lock próprio. As janelas de medição são diferentes: CPU/memória durante os 120 s
de ataque e throughput durante os 110 s sobrepostos. Isso é uma adaptação explícita;
sincronização automática de 120 s para todas as métricas ainda não foi implementada.

O Makefile gera `snort.conf` na pasta da execução usando a regra de UDP da Tabela III com limiar de 100 eventos em 10 s
por origem, SID 1000003. `EXTERNAL_NET` foi definido como a vítima para a regra
disparar neste laboratório. A ação é **alert**, não bloqueio. `snort -T` valida
a configuração antes de observar. O pacote instalado é Snort 2, não Snort 3.

`detector-current` inicia o daemon e o monitor sem mudar seu código ou modelo.
A contagem por deltas e o fechamento periódico foram integrados; ainda precisam
de validação no servidor. A procedência e a escala do modelo versionado continuam
pendentes e impedem tratar a rodada como reprodução validada da detecção. Após as correções, valide bloqueio, falsos positivos,
continuidade do tráfego legítimo e latência até bloquear, antes da série completa.

