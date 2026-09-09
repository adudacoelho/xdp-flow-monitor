# IV-C — Filtragem XDP

Objetivo: comparar throughput, CPU e memória entre XDP e iptables, variando
o número de regras (Figura 6).

Passo a passo pendente. O filtro BPF adicional foi removido; `MODE=xdp` não é
um modo disponível no Makefile atual. A comparação deve ser organizada usando
a implementação do projeto, sem presumir que o detector equivale a um filtro
estático isolado. O comparador `MODE=iptables` continua disponível.
