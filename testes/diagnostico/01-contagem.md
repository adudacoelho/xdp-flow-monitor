# 01 — Contagem conhecida de pacotes

**Objetivo:** demonstrar ou descartar a soma duplicada de contadores com uma
entrada pequena. Carga: três SYNs de mesma origem e porta, separados por pausas.
A observação dura 60 s; a sequência de envio inclui duas pausas de 3 s, além do tempo de cada chamada.

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
make -s observe MODE=collection-current DURATION=60 RUN=diag-contagem-r5
```

**Espere `PRONTO` e só então use o terminal 2.** O aviso de ML ausente é esperado.
Não há classificação nem bloqueio automático neste modo.

### TERMINAL 2 — GENERATOR: preparar e enviar em um único bloco

Copie o bloco inteiro, incluindo os parênteses. Eles isolam a execução: um erro
encerra somente este bloco, sem fechar o container nem o SSH. `r5` separa esta repetição das tentativas anteriores. Se já existir, escolha
um identificador novo nos dois terminais antes de iniciar.

O IP .101 é simulado, portanto não esperamos respostas no gerador. Cada chamada
fica limitada a dois segundos e deve reportar exatamente um pacote transmitido.
O código de retorno é salvo: 124 indica o limite de espera, não prova ausência
de envio. Outros erros só são tolerados nos casos explicitamente abaixo e com
a estatística de envio presente. Isso não comprova a recepção no target.

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = generator || {
        echo 'Execute no container GENERATOR.'; exit 1;
    }
    RUN=diag-contagem-r5
    OUT=/workspace/results/diagnostico-$RUN
    mkdir "$OUT" || { echo 'Não foi possível criar a pasta; confira o erro e use outro RUN se ela já existir.'; exit 1; }
    uname -a > "$OUT/kernel.txt"
    date -u +%s.%N > "$OUT/start-epoch.txt"
    for n in 1 2 3; do
        date -u +%s.%N >> "$OUT/envios-epoch.txt"
        rc=0
        LC_ALL=C timeout --foreground --kill-after=1 2 hping3 -I lab0 -S -p 80 \
          -s 12345 --keep -a 192.168.157.101 -c 1 192.168.157.20 \
          > "$OUT/pacote-$n.log" 2>&1 || rc=$?
        printf '%s\n' "$rc" > "$OUT/pacote-$n.status"
        case "$rc" in
            0|1|124) ;;
            *) cat "$OUT/pacote-$n.log"; echo 'Erro inesperado; rodada incompleta.'; exit 1 ;;
        esac
        if ! grep -Eq '^1 packets? transmitted,' "$OUT/pacote-$n.log"; then
            cat "$OUT/pacote-$n.log"
            echo 'Não foi confirmado exatamente um pacote enviado; rodada incompleta.'
            exit 1
        fi
        echo "Pacote $n: um envio reportado (retorno $rc)."
        if [ "$n" != 3 ]; then sleep 3; fi
    done
    date -u +%s.%N > "$OUT/end-epoch.txt"
    echo "Sequência concluída. Evidências: $OUT"
)
```

As duas pausas de três segundos garantem que o terceiro envio seja iniciado
mais de seis segundos depois do primeiro, independentemente de o hping3 retornar
antes do timeout. Os horários reais precisam ser conferidos: se o segundo pacote
já chegar após cinco segundos, o fechamento pode ocorrer nele e o terceiro ficar
na janela seguinte. Não presuma sempre SYN=6 sem conferir os eventos e os tempos.

## Ler o resultado — TARGET, após a observação terminar

O bloco abaixo abre a observação `diag-contagem-r5`. Se houver mais de uma
com esse identificador, ele para para evitar misturar rodadas. Preserve o log
completo, inclusive os avisos.

```bash
(
    set -eu
    test "$(cat /etc/xdp-chen-lab)" = target
    shopt -s nullglob
    pastas=(/workspace/results/*-observe-diag-contagem-r5)
    if [ "${#pastas[@]}" -ne 1 ]; then
        echo 'É necessária exatamente uma observação r5; confira as pastas desta rodada.'
        printf '%s\n' "${pastas[@]}"
        exit 1
    fi
    OBS=${pastas[0]}
    test -f "$OBS/end-epoch.txt" || { echo 'Aguarde a observação terminar.'; exit 1; }
    cat "$OBS/monitor.log"
    echo '=== INÍCIO E FIM DA OBSERVAÇÃO ==='
    cat "$OBS/start-epoch.txt" "$OBS/end-epoch.txt"
)
```

### TERMINAL 2 — GENERATOR: ler as evidências da nova rodada

```bash
cat /workspace/results/diagnostico-diag-contagem-r5/envios-epoch.txt
cat /workspace/results/diagnostico-diag-contagem-r5/pacote-*.log
cat /workspace/results/diagnostico-diag-contagem-r5/pacote-*.status
```

No target, leia também início/fim da pasta EXATA anunciada por `PRONTO`.
Confirme que todos os envios ficaram dentro da observação. Não escolha apenas
pelo `RUN` se houver mais de uma pasta com esse rótulo.

## Resultado já observado

O diagnóstico reproduziu uma janela com `SYN:6` para a sequência de três SYNs.
Isso é compatível com a soma incorreta dos snapshots acumulados `1 + 2 + 3`.
Não é necessário repetir apenas para confirmar novamente o defeito; preserve
os dados para comparar com a implementação corrigida.

A [seção 15 do relatório](../../docs/testes-chen/RELATORIO-4B-2026-10-06.md#15-diagnóstico-01--contagem-conhecida-de-pacotes)
explica o que foi demonstrado e o critério de validação após a correção.

## O que procurar

| Situação | Interpretação |
| --- | --- |
| Uma janela com SYN=6 após o terceiro pacote | Compatível com snapshots acumulados 1+2+3 somados novamente. |
| Nenhuma janela | Verificar anexação, envio e timestamps antes de interpretar. |
| Contagens diferentes | Guardar a evidência; conferir duração real, fluxos extras e perdas. |

Se o segundo evento ocorrer antes de cinco segundos e o terceiro depois desse
limite em relação ao primeiro, o terceiro dispara o fechamento no algoritmo atual. Os três SYNs representam três pacotes, mas as
fotografias acumuladas são 1, 2 e 3. **O total esperado de entrada é 3, não 6.**
Não use a taxa interna do monitor como confirmação independente da contagem.

Após corrigir o fechamento por tempo, os três pacotes podem cair em duas
janelas diferentes. Nesse caso, avalie a soma das janelas, incluindo a final:
o total continua sendo três. O critério não exige preservar o comportamento
errado de incluir o terceiro pacote na janela anterior.
