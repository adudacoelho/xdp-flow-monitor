# Reprodução de Chen et al. (2024)

Diagnóstico inicial em 2026-09-08. Fonte: PDF fornecido pelo usuário,
“Efficient DDoS Detection and Mitigation in Cloud Data Centers Using eBPF and XDP”,
pp. 1869–1874, DOI 10.1109/TrustCom63139.2024.00258.
Os números abaixo são referências publicadas, não resultados deste repositório.

## Matriz de experimentos

| Experimento | Protocolo descrito no artigo | Medições necessárias |
| --- | --- | --- |
| IV-B / Fig. 5: coleta | Baseline sem captura, eBPF e Wireshark; throughput medido a cada 50 s; SYN flood com hping3 a aproximadamente 1,92 Gbps por 120 s para CPU; memória em configuração semelhante; latência com ethr | Throughput TCP, CPU, memória e latência TCP |
| IV-C / Fig. 6: filtragem | XDP versus iptables, variando quantidade de regras até 512; iperf3 para throughput; SYN flood a aproximadamente 1,92 Gbps com seis IPs falsificados | Throughput, CPU e memória por quantidade de regras |
| IV-D / Fig. 7: classificação | Comparação de modelos com CIC-DDoS2019 estendido com tráfego normal e ataques de aplicação | Acurácia, precisão, recall, F1, matriz de confusão, detecção de normais e ataques |
| IV-E / Tabela II: processamento | tcpreplay a 180.163 pacotes/s | Tempo de coleta, inferência e filtragem, separadamente |
| IV-E / Fig. 8: sistema integrado | Sistema versus Snort sob UDP flood gerado com hping3 em diferentes intensidades; médias durante 120 s | CPU, memória e throughput |

A Tabela II informa 12,68 µs para eBPF, 11,96 µs para XGBoost e 5,72 µs
para XDP. Não somar esses valores como latência observada de bloqueio: o
fechamento da janela e a comunicação também influenciam essa latência.

O ambiente publicado usa seis máquinas, cada uma com Intel Xeon E5-2660 0
@ 2,20 GHz, 4 vCPUs, 8 GB RAM, Ubuntu 22.04, kernel 5.15.0-33-lowlatency e
Kubernetes 1.23.4. A aplicação é o social network do DeathStarBench.
Há dois containers atacantes no Host 1, um no Host 2 e monitoramento no Host 3.
Uma VM com containers deve ser apresentada como reprodução adaptada.

## Problemas encontrados no código

1. **Contagem cumulativa duplicada.** `flow_monitor.bpf.c` envia o estado
   acumulado de cada fluxo a cada pacote; `window.c` soma os estados recebidos.
   Verificação local com a implementação em `xdp-flow-monitor-main/window.c`:
   três snapshots com 1, 2 e 3 pacotes, nos instantes 0, 3 e 6 s, produziram
   6 pacotes e 6 SYN, embora o fluxo tivesse somente 3 de cada.
2. **Agregação diferente do artigo.** A janela está no userspace e agrupa
   por IP de origem. O artigo descreve agregação por cinco-tupla em janelas
   no kernel, reduzindo a comunicação kernel/userspace.
3. **Ciclo de vida dos fluxos.** Os 1.024 slots userspace nunca são liberados;
   o hash de 10.000 fluxos no kernel também não tem expiração. Janelas só
   fecham quando chega um evento; fluxos inativos podem ficar sem classificação.
4. **Duas árvores divergentes.** A raiz não contém `common.h`; a subpasta
   contém esse arquivo e correções diferentes. O script `compile_us.sh`
   não inclui `window.c` na linkedição.
5. **Protocolo ML frágil.** A raiz procura `"attack":true`, mas o daemon
   serializa `"attack": true`. A subpasta depende da presença desse espaço.
   Ambos assumem que uma leitura do socket contém uma mensagem completa.
6. **Unidades de duração sem contrato.** O treino renomeia `Flow Duration`
   para `duration_sec` sem converter unidades. É necessário conferir as
   unidades da fonte e padronizar treino e inferência antes de treinar novamente.
7. **Procedência do modelo não comprovada.** Existe um CSV sintético na
   subpasta; não foram encontrados CSVs reais ou PCAPs no repositório.
   O README gera dados sintéticos, mas também afirma treino real e 100% de
   acurácia sem relatório versionado que sustente essa afirmação.
8. **Cobertura de captura divergente.** A subpasta aceita TCP com origem
   **ou** destino na porta 80; a raiz não aplica esse filtro. Um monitor
   apenas na veth de um atacante não observa automaticamente os demais.
9. **Falta instrumentação experimental.** Não há executor de benchmarks,
   séries temporais, configurações dos comparadores nem resultados brutos.

## Ordem de implementação e critérios de aceitação

1. Consolidar uma árvore de código e um comando de build reproduzível.
2. Corrigir contagem, identidade de fluxo, concorrência, expiração e exportação
   por janela; testar contagens conhecidas, vários fluxos de um IP, perdas de
   eventos e preenchimento dos mapas. Nenhuma taxa pode depender de somar
   snapshots cumulativos.
3. Definir nomes, ordem, unidades e tamanho de pacote das features em um
   contrato único; corrigir comunicação com o classificador e registrar erros.
4. Validar funcionalmente em topologia isolada: tráfego normal passa,
   tráfego classificado é bloqueado, outros emissores continuam alcançáveis.
5. Separar modos de coleta, filtragem estática e sistema completo. Na Fig. 5,
   classificação/bloqueio não podem interromper a carga e enviesar a comparação.
6. Automatizar cada linha da matriz e salvar dados brutos antes de gerar gráficos.
7. Treinar com dados reais identificados, registrar partições e prevenção de
   vazamento entre treino/teste; manter dados sintéticos como teste funcional.

Para cada execução, guardar commit, comando, versões, hardware, topologia,
interface e modo XDP, seed, quantidade e ordem das regras, intensidade
solicitada e observada, duração, amostras de CPU/memória e resultado do gerador.
Definir explicitamente CPU de processo versus host, normalização por núcleo,
RSS versus memória do sistema e se throughput significa carga oferecida ou
tráfego útil recebido. Registrar perdas do coletor e falhas de atualização de mapas.

Como escolha metodológica da reprodução, usar pelo menos cinco repetições
independentes, aquecimento documentado e ordem alternada entre comparadores;
reportar dispersão além da média. Isso não é um protocolo declarado pelos autores.

## Limitações da reprodução exata

O artigo não fornece no texto todos os parâmetros de treinamento, partições,
conteúdo da extensão do dataset, comandos completos, metodologia detalhada
dos tempos por pacote ou repetições. As curvas precisam de inspeção visual
para transcrever os pontos de carga e de regras antes da configuração final.
A definição textual de taxas de detecção na seção IV-D menciona amostras
“undetected”, gerando ambiguidade: publicar explicitamente TN/(TN+FP) para
normais e TP/(TP+FN) para ataques, identificando a interpretação adotada.

## Estado desta sessão

PDF e fontes inspecionados; erro de contagem reproduzido com compilação local
de `window.c` e entradas controladas, sem carregar BPF. Kernel local observado:
7.0.0-31-generic. clang, bpftool e Docker estão no PATH; disponibilidade
operacional ainda não validada. iperf3, ethr, hping3, tcpreplay e Snort não
foram encontrados no PATH. Nenhum benchmark de rede foi executado.

Pendente de informação do usuário: máquina/VM/cluster de execução e localização
dos dados reais/PCAPs. Essas informações definem a topologia executável e quais
comparações serão reproduções adaptadas.
