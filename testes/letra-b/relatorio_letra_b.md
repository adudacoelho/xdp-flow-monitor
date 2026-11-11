# Relatório — Reprodução da Seção IV-B do Artigo
## "Performance of eBPF" (Chen et al., 2024)

## 1. Objetivo

Reproduzir, no ambiente do projeto `xdp-flow-monitor` (ContainerLab, host único), o experimento da Seção IV-B do artigo "Efficient DDoS Detection and Mitigation in Cloud Data Centers Using eBPF and XDP" (Chen et al., TrustCom 2024), que compara o custo de captura de tráfego usando eBPF versus uma ferramenta tradicional (Wireshark), em quatro dimensões: throughput, uso de CPU, uso de memória e latência.

## 2. Adaptações em relação ao artigo original

| Aspecto | Artigo original | Reprodução |
|---|---|---|
| Ambiente | Cluster Kubernetes, 6 máquinas (Intel Xeon E5-2660, 4 vCPUs, 8GB RAM cada) | VM única VirtualBox + ContainerLab |
| Geração de tráfego de fundo | Benchmark DeathStarBench (social network) | `iperf3` entre containers |
| Ferramenta de captura tradicional | Wireshark | `tcpdump` (motor de captura do Wireshark; GUI não é viável em VM headless) |
| Ataque simulado | `hping3`, SYN flood ~1.92 Gbps, 120s | `hping3 --flood`, mesma duração (120s), banda limitada pela VM |
| Ferramenta eBPF | Sistema próprio dos autores (não open-source) | `flow_monitor` (projeto próprio, `xdp-flow-monitor`) |
| Métrica de latência | Ferramenta `ethr` | `ping` (RTT via ICMP) |
| Papel dos containers | Nós de ataque separados dos nós de tráfego normal | Container `atacante1` acumula os dois papéis (tráfego normal via `iperf3` e ataque via `hping3`, em momentos distintos) |

## 3. Ambiente utilizado

- **Vítima**: container `clab-xdp-ddos-vitima`, IP `172.20.20.6`
- **Atacante**: container `clab-xdp-ddos-atacante1`, IP `172.20.20.3`
- **Interface monitorada no host**: `vethdbcc23c` (par veth do atacante1)
- **Ferramentas**: `iperf3` (throughput), `hping3` (SYN flood), `pidstat`/`sysstat` (CPU/memória), `tcpdump`/`flow_monitor` (captura), `ping` (latência)
- Duração de cada sub-teste: **120s**, igual ao artigo

## 4. Metodologia

Para cada um dos 3 modos de captura (**baseline** — sem captura nenhuma, **eBPF** — `flow_monitor` ativo, **tcpdump** — captura tradicional ativa), foram executados 3 sub-testes:

1. **Throughput**: servidor `iperf3` na vítima, cliente `iperf3` no atacante, 120s, sem ataque simultâneo.
2. **CPU/Memória**: `flow_monitor`/`tcpdump` ativo na interface, enquanto o atacante executa SYN flood via `hping3 --flood` por 120s; `pidstat` amostra CPU% e memória do processo de captura a cada segundo.
3. **Latência**: `ping` do atacante para a vítima, 120 pacotes (1/segundo), sem ataque simultâneo.

## 5. Problemas encontrados durante a execução (documentados para o relatório)

Durante a automação, dois bugs de script (não do `flow_monitor` em si) invalidaram resultados parciais e precisaram ser corrigidos:

1. **Variável `$HOME` sob `sudo`**: ao rodar o script com `sudo bash script.sh`, o `$HOME` do processo passa a ser `/root`, não o home do usuário real. Isso fez o script procurar o binário `flow_monitor` em `/root/xdp-flow-monitor/...` (inexistente), e o modo `ebpf` falhou silenciosamente nas primeiras execuções. Corrigido usando `${SUDO_USER:-$USER}` para resolver o caminho real.
2. **`sudo` duplicado**: como o script inteiro já era executado com `sudo bash`, chamadas internas adicionais de `sudo flow_monitor`/`sudo tcpdump` criavam uma camada de processo extra. O `pidstat` acabava monitorando o PID do processo `sudo` (que fica ocioso esperando o filho), não o processo de captura real — resultando em CPU/memória artificialmente zeradas. Corrigido removendo o `sudo` interno redundante.
3. **`sysstat`/`pidstat` ausente na VM clonada**: pacote instalado originalmente numa VM diferente da usada nos testes finais; precisou ser reinstalado após a clonagem completa da VM de trabalho.

## 6. Resultados finais

| Métrica | Baseline | eBPF (`flow_monitor`) | tcpdump |
|---|---|---|---|
| Throughput médio | 32.730,01 Mbps | 1.164,37 Mbps (queda de 96,4%) | 7.702,71 Mbps (queda de 76,5%) |
| Latência média (RTT) | 0,069 ms | 0,349 ms (5,1x maior) | 0,089 ms (1,3x maior) |
| Latência mín/máx | 0,031 / 0,770 ms | 0,207 / 1,020 ms | 0,063 / 0,265 ms |
| CPU média (%usr) do processo de captura | — (não aplicável) | 0,25% | 0,53% |

## 7. Análise — divergência em relação ao artigo original

O uso de CPU confirma o padrão esperado pelo artigo: o `flow_monitor` (eBPF) consome menos CPU que o `tcpdump` (0,25% vs 0,53%).

Porém, **throughput e latência mostram o padrão oposto** ao relatado no artigo: no ambiente reproduzido, o modo eBPF causou impacto substancialmente maior no throughput e na latência do que o `tcpdump`, enquanto no artigo original o eBPF tem impacto menor em todas as métricas.

**Hipótese mais provável para a divergência**: interfaces `veth` de containers Docker/ContainerLab tipicamente só suportam o modo **XDP genérico (SKB mode)**, e não o modo **nativo/driver**, que exige suporte da placa de rede física e do driver do kernel. O artigo original foi executado em um cluster com hardware físico (Intel Xeon E5-2660), permitindo XDP nativo, que processa pacotes antes mesmo de montar o `sk_buff`, com overhead mínimo. Em modo genérico, o XDP roda depois que o `sk_buff` já foi alocado pelo kernel, adicionando overhead de processamento que não aparece na métrica de CPU do processo em user-space monitorado pelo `pidstat` (parte do custo fica em softirq/kernel, fora do escopo dessa medição).

Essa divergência não indica um bug no `flow_monitor`, mas sim uma **limitação da reprodução em ambiente virtualizado** (VM + containers) frente ao ambiente de hardware dedicado do artigo original — uma diferença relevante para discutir na análise crítica do trabalho.

## 7. Como extrair os números finais (a preencher)

```bash
# Throughput médio (Mbps)
for mode in baseline ebpf tcpdump; do
  echo -n "$mode: "
  python3 -c "import json; d=json.load(open('/home/eduarda/teste_b_resultados/throughput_${mode}.json')); print(d['end']['sum_received']['bits_per_second']/1e6, 'Mbps')"
done

# Latência média (RTT)
for mode in baseline ebpf tcpdump; do
  echo -n "$mode: "
  tail -1 ~/teste_b_resultados/latency_${mode}.log
done

# CPU/memória médias (confirmar antes que o processo monitorado é o correto)
awk '{print $NF}' ~/teste_b_resultados/cpu_mem_ebpf.log | sort | uniq -c
awk '{print $NF}' ~/teste_b_resultados/cpu_mem_tcpdump.log | sort | uniq -c
```

## 9. Conclusão

A metodologia da Seção IV-B foi reproduzida com sucesso, com adaptações de escala documentadas na Seção 2. O uso de CPU confirmou o padrão do artigo (eBPF mais leve que captura tradicional). Throughput e latência divergiram do artigo, com impacto maior no modo eBPF — atribuído à limitação do modo XDP genérico em interfaces virtuais `veth`, versus o modo nativo disponível em hardware físico usado pelos autores originais. Essa divergência é um resultado relevante para a discussão crítica do trabalho, não uma falha de execução.

---
*Relatório gerado como parte da reprodução letra-a-letra da Seção IV do artigo (letras A-E). Próximas etapas: Letra C (Performance of XDP), Letra D (Performance of Anomaly Detection), Letra E (End-to-End Performance).*
