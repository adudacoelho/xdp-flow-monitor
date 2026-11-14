# Comparação IV-B

Gerado por `python3 scripts/resumir_4b.py`. Todos os dados originais foram preservados.

CPU e memória são do servidor compartilhado, selecionadas somente em intervalos completos de 1 s dentro da carga. Não representam consumo exclusivo do coletor. O CSV inclui todas as datas e caminhos para auditoria.

Cada associação exige mesmo RUN e início da carga dentro da observação. Tentativas sem correspondência única são separadas. A categoria completa verifica arquivos e duração; não certifica a correção do coletor ou independência experimental.

Não agrupamos dias, kernels, MTUs ou versões diferentes. Não há comparação percentual contra baseline de outro dia. Falta identificação de commit por rodada para assegurar equivalência de versão. Arquivos antigos arquivados em resultados-antigos não são duplicados nesta análise.

## Dia mais recente: 20261113

Neste recorte, a ausência de algum cenário significa que ele precisa ser medido ou baixado; não substituímos por uma rodada antiga.

Todas as tentativas desse dia aparecem abaixo, inclusive as que precisam de revisão. Os horários nos nomes das pastas são UTC.

### Throughput TCP

| Observação (UTC) | Modo | Estado | Gbit/s recebidos | CPU host % | Memória host MiB | pps enviados | Latência Avg µs | Amostras CPU | Observações |
|---|---|---|---|---|---|---|---|---|---|
| 20261113T133015405265441-observe-fig5-tshark-r1 | tshark | completa | 4.59 | 12.20 | 2246.53 | — | — | 49 | — |
| 20261113T133615138425260-observe-fig5-tshark-r1 | tshark | revisar | 4.63 | 12.18 | 2324.19 | — | — | 49 | captura encerrada à força; revisar log |
| 20261113T133741819279225-observe-fig5-collection-current-r1 | collection-current | completa | 4.61 | 6.36 | 1328.68 | — | — | 49 | — |
| 20261113T135328730030596-observe-fig5-collection-current-r1 | collection-current | completa | 4.59 | 6.10 | 1167.63 | — | — | 49 | — |
| 20261113T170310749811107-observe-fig5-collection-current-r1 | collection-current | completa | 4.27 | 6.11 | 1136.14 | — | — | 49 | — |

Baseline TCP ausente nesse dia: não é possível calcular a queda relativa com equivalência temporal.

### SYN: CPU e memória

| Observação (UTC) | Modo | Estado | Gbit/s recebidos | CPU host % | Memória host MiB | pps enviados | Latência Avg µs | Amostras CPU | Observações |
|---|---|---|---|---|---|---|---|---|---|
| 20261113T170437748906297-observe-fig5-syn-baseline-r1 | baseline | completa | — | 0.26 | 1158.11 | 4928.71 | — | 119 | — |
| 20261113T170710175969078-observe-fig5-syn-tshark-r1 | tshark | completa | — | 0.44 | 1672.10 | 4927.07 | — | 119 | — |
| 20261113T170937016458463-observe-fig5-syn-collection-current-r1 | collection-current | completa | — | 0.31 | 1176.04 | 4923.33 | — | 119 | — |

### Latência TCP

| Observação (UTC) | Modo | Estado | Gbit/s recebidos | CPU host % | Memória host MiB | pps enviados | Latência Avg µs | Amostras CPU | Observações |
|---|---|---|---|---|---|---|---|---|---|
| 20261113T171339593320077-observe-fig5-lat-baseline-r1 | baseline | completa* | — | 0.19 | 1192.57 | — | 25.54 | 121 | percentis Ethr inconsistentes; Avg provisório |
| 20261113T171716961920193-observe-fig5-lat-tshark-r1 | tshark | completa* | — | 0.25 | 1346.24 | — | 26.20 | 121 | percentis Ethr inconsistentes; Avg provisório |
| 20261113T171942999030681-observe-fig5-lat-collection-current-r1 | collection-current | completa* | — | 0.23 | 1195.77 | — | 29.03 | 120 | percentis Ethr inconsistentes; Avg provisório |

## Limites e próximos passos

- Latência: média aritmética dos Avg de cada registro, não média de todas as medições individuais. Percentis inconsistentes não são publicados; Avg permanece provisório.
- PPS: soma dos transmitidos pelo hping dividida pela duração externa da carga; não comprova recepção pelo kernel.
- MTU e kernel estão no CSV; conferir antes de comparar. Repetições com mesmo RUN não são fundidas.
- Arquivos ausentes podem indicar download incompleto. Preserve a tentativa até verificar no servidor.
- Logs TShark/monitor de vários GB não foram varridos; perdas da captura e erros internos exigem análise adicional desses logs.
- 43 observações catalogadas; 2 cargas sem associação única listadas em cargas-sem-par.csv.
