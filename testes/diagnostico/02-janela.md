# 02 — Janela sem novos eventos

**Objetivo:** verificar se a janela fecha após cinco segundos mesmo sem novos
pacotes. Observação: **60 segundos**. Carga: dois SYNs do mesmo fluxo.

**Resultado já observado:** durante a pausa, nenhuma janela foi apresentada.
Após o segundo envio, o log final mostrou uma janela com `SYN:3`, apesar de dois
envios reportados. Isso evidencia a dependência de novos eventos e reforça o
erro de soma dos contadores acumulados. Veja a seção 16 do
[relatório](../../docs/testes-chen/RELATORIO-4B-2026-10-06.md).

## 1. Prepare os TRÊS terminais antes de começar

Siga os pré-requisitos do [README](README.md). Não mantenha outras cargas nem
o daemon ML ativos. Abra três sessões SSH no servidor.

### TERMINAL 1 — SERVIDOR: entrar no TARGET para observar

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 2 — SERVIDOR: entrar no GENERATOR para enviar

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=generator
```

### TERMINAL 3 — SERVIDOR: entrar no TARGET para inspecionar

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

**Confira os prompts:** terminais 1 e 3 devem mostrar `root@target`; terminal 2,
`root@generator`. Os comandos seguintes são executados dentro dos containers.

## 2. TERMINAL 2 — GENERATOR: reservar uma rodada nova

Execute uma vez. O identificador automático evita reutilizar pastas anteriores.
Copie sempre os blocos completos, incluindo os parênteses. Eles protegem seu
shell: um erro encerra apenas o bloco.

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = generator
    RUN=diag-janela-$(date -u +%Y%m%dT%H%M%S%N)
    OUT=/workspace/results/diagnostico-$RUN
    mkdir "$OUT"
    printf '%s\n' "$OUT" > /tmp/chen-diag-janela-out
    printf '\nCOPIE ESTE COMANDO NO TERMINAL 1:\n'
    printf 'make -s observe MODE=collection-current DURATION=60 RUN=%s\n' "$RUN"
)
```

## 3. TERMINAL 1 — TARGET: iniciar a observação

**Execute o comando completo que o terminal 2 acabou de mostrar.** Ele já tem
o identificador correto. Aguarde `PRONTO` e execute imediatamente o próximo
bloco no terminal 2. Não espere a observação terminar.

## 4. TERMINAL 2 — GENERATOR: enviar, pausar e aguardar sua confirmação

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = generator
    OUT=$(cat /tmp/chen-diag-janela-out)
    test -d "$OUT"
    test ! -e "$OUT/primeiro-epoch.txt" || {
        echo 'Envio já tentado. Recomece na etapa 2 com uma nova observação.'
        exit 1
    }
    enviar() {
        nome=$1
        date -u +%s.%N > "$OUT/$nome-epoch.txt"
        rc=0
        LC_ALL=C timeout --foreground --kill-after=1 2 \
          hping3 -I lab0 -S -p 80 \
          -s 12345 --keep -a 192.168.157.101 \
          -c 1 192.168.157.20 > "$OUT/$nome.log" 2>&1 || rc=$?
        printf '%s\n' "$rc" > "$OUT/$nome.status"
        case "$rc" in
            0|1|124) ;;
            *) cat "$OUT/$nome.log"; exit 1 ;;
        esac
        grep -Eq '^1 packets? transmitted,' "$OUT/$nome.log" || {
            cat "$OUT/$nome.log"
            echo 'Envio não confirmado; rodada incompleta.'
            exit 1
        }
    }
    uname -a > "$OUT/kernel.txt"
    date -u +%s.%N > "$OUT/start-epoch.txt"
    enviar primeiro
    sleep 8
    echo 'AGORA: execute a etapa 5 no TERMINAL 3.'
    read -r -t 25 -p 'Após salvar a inspeção, pressione Enter aqui: ' || {
        echo 'Tempo excedido; rodada incompleta. Recomece na etapa 2.'
        exit 1
    }
    enviar segundo
    date -u +%s.%N > "$OUT/end-epoch.txt"
    echo "Segundo envio reportado. Evidências: $OUT"
)
```

A ausência de resposta ao IP simulado não significa automaticamente ausência
de envio. Por isso o bloco confere também a estatística de um pacote transmitido.
Isso não substitui uma confirmação de recepção no destino.

## 5. TERMINAL 3 — TARGET: salvar o log DURANTE A PAUSA

Execute quando o gerador pedir. O bloco seleciona a observação de janela mais
recente: mantenha apenas uma rodada deste diagnóstico em andamento. Ele recusa
observação encerrada e não sobrescreve uma inspeção anterior.

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = target
    OBS=$(ls -dt /workspace/results/*-observe-diag-janela-* 2>/dev/null | head -n 1)
    test -n "$OBS" || { echo 'Nenhuma observação encontrada.'; exit 1; }
    test ! -e "$OBS/end-epoch.txt" || {
        echo 'Observação encerrada. Recomece a rodada na etapa 2.'; exit 1;
    }
    test ! -e "$OBS/monitor-durante-pausa.log" || {
        echo 'Inspeção já salva; não será sobrescrita.'; exit 1;
    }
    cp "$OBS/monitor.log" "$OBS/monitor-durante-pausa.log"
    date -u +%s.%N > "$OBS/inspecao-pausa-epoch.txt"
    printf '%s\n' "$OBS" > /tmp/chen-diag-janela-obs
    echo "Observação: $OBS"
    cat "$OBS/monitor-durante-pausa.log"
    echo 'Inspeção salva. Volte ao TERMINAL 2 e pressione Enter.'
)
```

**Agora volte ao terminal 2 e pressione Enter.** Se houver erro na inspeção,
não confirme o segundo envio. Aguarde os comandos terminarem e inicie uma nova
rodada pela etapa 2. Não é necessário reconstruir os containers para repetir.

## 6. Após terminar: ler as evidências

### TERMINAL 3 — TARGET: comparar pausa e resultado final

Espere o terminal 1 voltar ao prompt antes deste bloco.

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = target
    OBS=$(cat /tmp/chen-diag-janela-obs)
    test -f "$OBS/end-epoch.txt" || { echo 'Observação ainda ativa.'; exit 1; }
    echo '=== DURANTE A PAUSA ==='
    cat "$OBS/monitor-durante-pausa.log"
    echo '=== LOG FINAL ==='
    cat "$OBS/monitor.log"
    echo '=== INÍCIO, INSPEÇÃO E FIM ==='
    cat "$OBS/start-epoch.txt" "$OBS/inspecao-pausa-epoch.txt" "$OBS/end-epoch.txt"
)
```

### TERMINAL 2 — GENERATOR: conferir os dois envios

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = generator
    OUT=$(cat /tmp/chen-diag-janela-out)
    echo '=== PRIMEIRO E SEGUNDO ENVIO ==='
    cat "$OUT/primeiro-epoch.txt" "$OUT/segundo-epoch.txt"
    echo '=== ESTATÍSTICAS DOS ENVIOS ==='
    cat "$OUT/primeiro.log" "$OUT/segundo.log"
)
```

## O que o resultado significa

Confira que cada chamada reportou um pacote, que a inspeção ocorreu entre os
envios e que ambos ocorreram dentro da observação. Os registros de tempo servem
para validar essa sequência; não é necessário transcrevê-los no relatório.

Na rodada analisada, a pausa ultrapassou cinco segundos sem apresentar janela.
O log final apresentou uma janela após o segundo envio. Isso sustenta o problema
identificado no código: o tempo só é verificado quando chega um novo evento.
O teste não mede o instante exato do fechamento. O aviso de ML ausente é esperado.

`SYN:3` para dois envios é compatível com somar os snapshots acumulados `1 + 2`.
As taxas exatas variam com a pausa e não são critérios de aprovação.

Após corrigir o fechamento, a janela deve ser exportada perto do prazo previsto
sem esperar outro pacote. Após corrigir também a contagem, o total nas janelas
relevantes deve corresponder aos dois pacotes efetivamente recebidos. Preserve
os logs antes e depois da correção e obtenha-os pelo
[roteiro de resultados](../testes-chen/OBTENDORESULTADOS.md).
