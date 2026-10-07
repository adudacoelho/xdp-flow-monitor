# 04 — Dois fluxos da mesma origem

**Objetivo:** mostrar a diferença entre fluxo (IPs, portas e protocolo) e origem
(IP). Faça duas rodadas limpas. O experimento observa a identidade dos registros;
a correção da contagem é avaliada separadamente no diagnóstico 01.

## Preparar os terminais

Siga primeiro o [README deste diagnóstico](README.md). Use sessões SSH separadas.

### TERMINAL 1 — NO SERVIDOR: entrar no TARGET

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 2 — NO SERVIDOR: entrar no GENERATOR

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=generator
```

O prompt deve mostrar `root@target` no terminal 1 e `root@generator` no 2.
Ambos abrem em `/workspace/testes/testes-chen/containers`. Se já estiver no
container correto, use `cd /workspace/testes/testes-chen/containers`.

### TERMINAL 1 — TARGET: iniciar observação limpa

```bash
make -s observe MODE=collection-current DURATION=60 RUN=diag-agregacao-r1
```

**Espere `PRONTO` e só então use o terminal 2.** O aviso de ML ausente é esperado.
Não há classificação nem bloqueio automático neste modo.

### TERMINAL 2 — GENERATOR: duas portas, mesmo IP

```bash
RUN=diag-agregacao-r1
OUT=/workspace/results/diagnostico-$RUN
mkdir "$OUT" || { echo 'Pasta já existe: use outro RUN.'; exit 1; }
uname -a > "$OUT/kernel.txt"
date -u +%s.%N > "$OUT/start-epoch.txt"
```

```bash
for rodada in 1 2; do
    for porta in 12345 23456; do
        timeout --foreground --kill-after=2 8 hping3 -I lab0 -S -p 80           -s "$porta" --keep -a 192.168.157.101 -c 1 192.168.157.20           > "$OUT/rodada-$rodada-porta-$porta.log" 2>&1
    done
    if [ "$rodada" = 1 ]; then sleep 6; fi
done
date -u +%s.%N > "$OUT/end-epoch.txt"
```

Esperado: duas cinco-tuplas no mapa, mas uma origem no monitor. O log atual não
identifica a porta e pode juntar os eventos em uma mesma janela. O último evento
pode ficar na janela seguinte sem fechamento; não use apenas a janela impressa
para contar todos os quatro pacotes.

### TERMINAL 3 — TARGET: inspecionar antes de terminar a observação

Abra outro shell target pelo comando da preparação. Use o caminho da rodada:

```bash
OBS=/workspace/results/PASTA_DA_OBSERVACAO
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" final
```

### Segunda rodada — repetir com dois IPs

Espere os 60 s e o retorno do terminal 1. Nele, execute:

```bash
make -s observe MODE=collection-current DURATION=60 RUN=diag-agregacao-ips-r1
```

No terminal 2, após `PRONTO`, crie uma pasta nova e envie:

```bash
OUT=/workspace/results/diagnostico-diag-agregacao-ips-r1
mkdir "$OUT" || { echo 'Pasta existente; use outra rodada.'; exit 1; }
date -u +%s.%N > "$OUT/start-epoch.txt"
for rodada in 1 2; do
    for origem in 192.168.157.101 192.168.157.102; do
        timeout --foreground --kill-after=2 8 hping3 -I lab0 -S -p 80           -s 12345 --keep -a "$origem" -c 1 192.168.157.20           > "$OUT/rodada-$rodada-$origem.log" 2>&1
    done
    if [ "$rodada" = 1 ]; then sleep 6; fi
done
date -u +%s.%N > "$OUT/end-epoch.txt"
```

## Interpretação

Na segunda rodada, espere duas origens no log e duas entradas no mapa. Na
primeira, duas entradas também existem, mas a saída agrupa pela mesma origem.
Agrupar por IP não é necessariamente errado: torna-se incorreto se o modelo e
a documentação pressupõem métricas por conexão. Antes da correção, escolha e
documente qual unidade deve ser usada. Depois, valide essa unidade explicitamente.
