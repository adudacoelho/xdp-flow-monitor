# IV-B — Coleta eBPF

Roteiro preliminar migrado do documento geral; validar no servidor antes da série.
Os comandos são executados nos containers, após preparar a VM correspondente.



### Throughput TCP

1. Target/serviço: `make serve SERVICE=iperf DURATION=600 RUN=fig5-server`.
2. Target/observação: `make observe MODE=baseline DURATION=70 RUN=fig5-base-r1`.
3. Depois de PRONTO, generator: `make traffic KIND=tcp DURATION=50 RUN=fig5-base-r1`.
4. Repita passos 2–3 com `MODE=tshark` e, separadamente, `MODE=collection-current`.
5. Para observar 200 s com intervalos de 50 s, use carga de 200 s e observação
   de 220 s; agregue os intervalos de 1 s do JSON iperf3 em quatro blocos de 50 s.

TShark é a variante sem GUI do comparador, com análise textual gravada em log;
não é uma medição da aplicação gráfica Wireshark do artigo. Seu custo de saída
e disco faz parte desta configuração e deve ser declarado. `collection-current`
executa o coletor existente sem daemon ML: há exportação por pacote e logging,
portanto ainda **não representa a coleta corrigida do artigo**.

### CPU e memória sob SYN flood

1. Mantenha o serviço iperf ativo na porta 80 da target.
2. Target: `make observe MODE=baseline DURATION=140 RUN=fig5-syn-base-r1`.
3. Generator: `make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-base-r1`.
4. Repita para `tshark` e `collection-current`, conservando duração e carga.
5. Calibre cargas maiores usando as taxas **observadas** no gerador e receptor.

O artigo informa aproximadamente **1,92 Gbps**, não uma opção de hping3 que
garanta essa taxa. Nosso PPS controla o intervalo solicitado ao hping3; seis
processos usam IPs de origem 192.168.157.101–106. O gerador pode não alcançar a
taxa pedida. Não declare 1,92 Gbps sem medi-la; informe também o tamanho dos
pacotes e a camada da contagem de bytes. Não substitua silenciosamente o teste
por UDP iperf3 ou suponha que `--flood` equivale à carga publicada.

### Latência TCP com Ethr

1. Encerre o serviço iperf (Ctrl+C): ambos usam a porta 80 para passar pelo
   filtro TCP do monitor atual.
2. Target/serviço: `make serve SERVICE=ethr DURATION=600 RUN=fig5-lat-server`.
3. Target: `make observe MODE=baseline DURATION=140 RUN=fig5-lat-base-r1`.
4. Generator: `make traffic KIND=latency DURATION=120 RUN=fig5-lat-base-r1`.
5. Repita observação/carga com `tshark` e `collection-current`. Guarde os logs
   Ethr; reporte média e percentis disponíveis. Não use ping ICMP como substituto.

