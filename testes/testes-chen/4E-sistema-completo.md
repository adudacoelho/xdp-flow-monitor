# IV-E — Sistema completo

Roteiro preliminar migrado do documento geral; validar no servidor antes da série.
Os comandos são executados nos containers, após preparar a VM correspondente.

## 7. Tabela II — replay e tempos por etapa (seção IV-E)

1. Obtenha um PCAP real, selecione somente o sentido atacante → vítima e
   preserve o original. Não transforme o tráfego de retorno em ataque.
2. Na generator, converta a cópia selecionada em PCAP clássico Ethernet/IPv4
   (sem VLAN), e reescreva endereços/MACs para o laboratório:

```bash
editcap -F pcap /workspace/dataset/attack-only.pcapng /workspace/results/attack-only.pcap
tcprewrite --infile=/workspace/results/attack-only.pcap --outfile=/workspace/results/lab.pcap \
  --srcipmap=0.0.0.0/0:192.168.157.101/32 \
  --dstipmap=0.0.0.0/0:192.168.157.20/32 \
  --enet-smac=52:54:00:ce:02:10 --enet-dmac=52:54:00:ce:02:20 --fixcsum
```

3. Target: `make observe MODE=collection-current DURATION=140 RUN=table2-r1`.
4. Generator:

```bash
make traffic KIND=replay PCAP=results/lab.pcap PPS=180163 DURATION=120 RUN=table2-r1
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

## 8. Fig. 8 — sistema completo versus Snort (seção IV-E)

1. Target/serviço: inicie iperf como antes.
2. Target: `make observe MODE=snort DURATION=150 RUN=fig8-snort-5000-r1`.
3. Generator/carga: `make traffic KIND=udp PPS=5000 DURATION=120 RUN=fig8-snort-5000-r1`.
4. Em outro terminal generator, durante a mesma carga, execute
   `make traffic KIND=tcp DURATION=110 RUN=fig8-snort-5000-tcp-r1`.
5. Repita usando `MODE=baseline` e `MODE=detector-current`.
6. Repita para **5.000, 10.000, 50.000, 100.000 e 150.000 pps** (Fig. 8),
   sempre registrando a taxa realmente alcançada, e faça as cinco repetições.

Para permitir tráfego TCP legítimo simultâneo ao UDP, cada tipo de carga usa um
lock próprio. As janelas de medição são diferentes: CPU/memória durante os 120 s
de ataque e throughput durante os 110 s sobrepostos. Isso é uma adaptação explícita;
sincronização automática de 120 s para todas as métricas ainda não foi implementada.

O Makefile gera `snort.conf` na pasta da execução usando a regra de UDP da Tabela III com limiar de 100 eventos em 10 s
por origem, SID 1000003. `EXTERNAL_NET` foi definido como a vítima para a regra
disparar neste laboratório. A ação é **alert**, não bloqueio. `snort -T` valida
a configuração antes de observar. O pacote instalado é Snort 2, não Snort 3.

`detector-current` inicia o daemon e o monitor sem mudar seu código ou modelo.
Os bugs de contagem e procedência do modelo impedem usar essa rodada como
reprodução válida da detecção. Após as correções, valide bloqueio, falsos positivos,
continuidade do tráfego legítimo e latência até bloquear, antes da série completa.

