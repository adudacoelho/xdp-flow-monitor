# Avaliação IV-C — filtragem XDP versus iptables

Gerado por `python3 scripts/resumir_4c.py`. Resultados brutos preservados.

## Comparação de 2026-11-16

Os percentuais de throughput usam a média dos baselines completos do mesmo dia, kernel e MTU. CPU e memória são do servidor inteiro, não exclusivas do filtro. Somente intervalos completos de 1 s dentro da carga entram nas médias. Sem inferência de significância com tão poucas repetições.

### Throughput TCP — sem ataque

Baseline: média de 2 rodadas = 8.359 Gbit/s. Os baselines individuais permanecem na tabela.

- xdp-static, 16 regras: 6.931 Gbit/s, variação de -17.08% frente ao baseline compatível.
- iptables, 16 regras: 7.525 Gbit/s, variação de -9.98% frente ao baseline compatível.

Com 16 regras, a média observada do XDP foi inferior à do iptables (-7.89%). Amostras pequenas não permitem generalizar; a causa da diferença não pode ser deduzida dessas médias.


| Observação (UTC) | Modo | Regras | Estado | Gbit/s recebidos | Δ baseline % | Retransmissões | CPU host % | Memória host MiB |
|---|---|---|---|---|---|---|---|---|
| 20261116T210232603044346-observe-fig6-tcp-baseline-r1 | baseline | 0 | completa | 8.37 | 0.15 | 0 | 5.00 | 1044.20 |
| 20261116T210432431429000-observe-fig6-tcp-baseline-r2 | baseline | 0 | completa | 8.35 | -0.15 | 0 | 4.98 | 1017.72 |
| 20261116T210606820931726-observe-fig6-tcp-xdp-16-r1 | xdp-static | 16 | completa | 6.93 | -17.08 | 0 | 5.28 | 1021.11 |
| 20261116T210738470534906-observe-fig6-tcp-iptables-16-r1 | iptables | 16 | completa | 7.52 | -9.98 | 0 | 5.12 | 1020.87 |

### CPU e memória sob SYN

| Modo | Regras | Estado | pps enviados | rxpck/s em lab0 | CPU host % | Memória host MiB | DROP iptables | Amostras CPU |
|---|---|---|---|---|---|---|---|---|
| baseline | 0 | completa | 4929.52 | 4905.47 | 0.27 | 1041.50 | — | 119 |
| xdp-static | 16 | completa | 4941.69 | 4943.50 | 0.24 | 1049.04 | — | 119 |
| iptables | 16 | completa | 4939.00 | 4940.18 | 0.25 | 1056.31 | 592805 | 119 |

### Verificação dos filtros

| RUN | Regras conferidas | Modo XDP (valor registrado) | Observações |
|---|---|---|---|
| fig6-tcp-xdp-16-r1 | 16 | 1 | — |
| fig6-tcp-iptables-16-r1 | 16 | — | — |
| fig6-syn-xdp-16-r1 | 16 | 1 | sem contador XDP_DROP; bloqueio ainda não comprovado por contagem |
| fig6-syn-iptables-16-r1 | 16 | — | — |

## Todas as tentativas, incluindo históricas

| Observação (UTC) | Estado | Gerador associado | Observações |
|---|---|---|---|
| 20261114T145519248253644-observe-fig6-tcp-xdp-16-r1 | completa | 20261114T145524051654909-traffic-fig6-tcp-xdp-16-r1 | — |
| 20261114T151147757095542-observe-fig6-tcp-baseline-r1 | completa | 20261114T151152939513624-traffic-fig6-tcp-baseline-r1 | — |
| 20261114T152245940522136-observe-fig6-tcp-xdp-16-r1 | completa | 20261114T152253904330397-traffic-fig6-tcp-xdp-16-r1 | — |
| 20261114T152454291851135-observe-fig6-tcp-iptables-16-r1 | revisar | — | associação ausente/ambígua (2 cargas) |
| 20261114T152606464140883-observe-fig6-tcp-iptables-16-r1 | revisar | — | associação ausente/ambígua (0 cargas) |
| 20261116T210232603044346-observe-fig6-tcp-baseline-r1 | completa | 20261116T210244181029112-traffic-fig6-tcp-baseline-r1 | — |
| 20261116T210432431429000-observe-fig6-tcp-baseline-r2 | completa | 20261116T210441997509753-traffic-fig6-tcp-baseline-r2 | — |
| 20261116T210606820931726-observe-fig6-tcp-xdp-16-r1 | completa | 20261116T210613982807493-traffic-fig6-tcp-xdp-16-r1 | — |
| 20261116T210738470534906-observe-fig6-tcp-iptables-16-r1 | completa | 20261116T210744674412225-traffic-fig6-tcp-iptables-16-r1 | — |
| 20261116T210858783396724-observe-fig6-syn-baseline-r1 | completa | 20261116T210904185952022-traffic-fig6-syn-baseline-r1 | — |
| 20261116T211126992785865-observe-fig6-syn-xdp-16-r1 | completa | 20261116T211133923941751-traffic-fig6-syn-xdp-16-r1 | sem contador XDP_DROP; bloqueio ainda não comprovado por contagem |
| 20261116T211420126028719-observe-fig6-syn-iptables-16-r1 | completa | 20261116T211425678102048-traffic-fig6-syn-iptables-16-r1 | — |

## Como interpretar

- Este experimento usa xdp_min, filtro estático isolado. Não avalia o coletor nem o XGBoost do detector completo.
- Completa significa que arquivos, duração, associação e regras passaram nas verificações do script. Não certifica a reprodução do artigo nem o bloqueio XDP.
- A associação exige mesmo RUN e início da carga dentro da observação. Cargas sem par estão no CSV separado; não escolhemos uma tentativa arbitrariamente.
- CPU = 100 − %idle médio das linhas all; inclui espera de I/O. Memória = kbmemused médio / 1024. Memória inclui estado do host e não permite atribuir diferenças ao filtro.
- PPS enviados = soma dos seis hping / duração externa da carga. rxpck/s é a estatística da interface, não um contador de decisões XDP; não permite deduzir descartes XDP.
- iptables: conferimos as regras e seus contadores DROP. XDP: conferimos chaves /32, programa anexado e quantidade de regras; faltam contadores PASS/DROP para confrontar envio e descarte.
- O KIND do parameters.txt da observação usa um padrão tcp mesmo sob SYN. O script usa o nome RUN e confere KIND no gerador, que identifica a carga efetiva.
- MTU e kernel estão em rodadas.csv. Commit, afinidade de CPU e carga concorrente não estão identificados por rodada; são limites da comparação.
- Para avaliar escalabilidade até 512 regras ainda são necessárias outras quantidades, repetições equilibradas, ordem alternada e carga observada calibrada. Resultados de 16 regras não descrevem toda a curva.
- 12 observações catalogadas; 2 cargas sem par. Campos ausentes podem resultar de tentativas interrompidas ou download incompleto.
