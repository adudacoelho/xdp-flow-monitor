# 03 — Ocupação do mapa e recuperação após saturação

**Objetivo:** comparar muitos pacotes de um único fluxo com muitos fluxos e
verificar se entradas antigas são removidas. A inspeção confirma ocupação do
mapa; sem contadores adicionais, não mede todas as falhas de inserção.

Carga limitada: 1.000 pacotes com porta fixa e 11.000 com portas variáveis,
solicitados a cerca de 2.000 pacotes/s. Não use `--flood`.

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
make -s observe MODE=collection-current DURATION=60 RUN=diag-mapa-r1
```

**Espere `PRONTO` e só então use o terminal 2.** O aviso de ML ausente é esperado.
Não há classificação nem bloqueio automático neste modo.

Prepare os três terminais antes de iniciar. A observação encerra em 60 s:
execute as etapas em sequência. Deixe os comandos e o caminho `OBS` preparados.
Os limites das chamadas e a pausa somam cerca de 34 s no pior caso; o restante
é a margem para trocar de terminal e salvar os mapas. Se não couber, não conclua
que o mapa se recuperou ou perdeu dados a partir de uma execução incompleta. Se esse prazo acabar antes da última inspeção,
não misture mapas de outro processo; registre a tentativa como incompleta.
Os dumps devem ocorrer com o gerador parado para evitar uma contagem que muda
durante a leitura.

### TERMINAL 3 — NO SERVIDOR: abrir outro shell TARGET

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
make clab-shell NODE=target
```

### TERMINAL 3 — TARGET: selecionar a observação e salvar o mapa vazio

Copie o caminho exato mostrado após `PRONTO`. O script usa o ID do programa
nessa execução e procura seu próprio `flow_map`; não escolhe um mapa pelo nome
entre todos os programas do servidor. Somente lê e grava uma cópia nos resultados.

```bash
OBS=/workspace/results/PASTA_DA_OBSERVACAO
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" antes
sha256sum /workspace/build/flow_monitor /workspace/build/flow_monitor.bpf.o > "$OBS/binarios.sha256"
```

Esperado: zero entradas antes da carga, se não houver outro tráfego relevante.
Se não encontrar o programa/mapa, pare: a observação pode ter terminado.

### TERMINAL 2 — GENERATOR: preparar pasta e enviar porta fixa

```bash
RUN=diag-mapa-r1
OUT=/workspace/results/diagnostico-$RUN
mkdir "$OUT" || { echo 'Pasta já existe: use outro RUN.'; exit 1; }
uname -a > "$OUT/kernel.txt"
date -u +%s.%N > "$OUT/start-epoch.txt"
```

```bash
timeout --foreground --kill-after=1 10 hping3 -I lab0 -S -p 80   -s 12345 --keep -a 192.168.157.101 -c 1000 -i u500 192.168.157.20   > "$OUT/fixa.log" 2>&1
```

Confira `fixa.log`: deve registrar 1.000 transmitidos. Confira a estatística de transmissão, mesmo se o retorno indicar ausência de
resposta ou timeout: o IP é simulado. Se foram enviados menos pacotes, registre
a rodada como incompleta. Não execute estes blocos com `set -e` no shell.

### TERMINAL 3 — TARGET: depois da carga fixa

```bash
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" fixa
```

Esperado no código atual: aproximadamente uma entrada para o fluxo enviado,
apesar dos 1.000 pacotes. Outras entradas exigem investigação do tráfego extra.

### TERMINAL 2 — GENERATOR: enviar portas variáveis

O bloco abaixo omite `--keep`: hping3 incrementa a porta de origem a partir de
20000. São 11.000 portas, abaixo do ponto de retorno a zero do campo de 16 bits.

```bash
timeout --foreground --kill-after=1 10 hping3 -I lab0 -S -p 80   -s 20000 -a 192.168.157.101 -c 11000 -i u500 192.168.157.20   > "$OUT/variavel.log" 2>&1
```

Antes de continuar, confira `variavel.log`: devem constar 11.000 pacotes
transmitidos. A taxa solicitada não é garantida; se o limite de dez segundos
interromper a carga antes dessa quantidade, a tentativa ficou incompleta.

### TERMINAL 3 — TARGET: medir ocupação, esperar e medir novamente

```bash
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" cheio
sleep 10
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" espera
```

Esperado no código atual: se pelo menos 10.000 fluxos distintos chegaram,
o mapa atinge sua capacidade e não esvazia durante a pausa.

### TERMINAL 2 — GENERATOR: tentar registrar uma nova origem

```bash
timeout --foreground --kill-after=1 2 hping3 -I lab0 -S -p 80   -s 45000 --keep -a 192.168.157.102 -c 1 192.168.157.20   > "$OUT/nova-origem.log" 2>&1
date -u +%s.%N > "$OUT/end-epoch.txt"
```

### TERMINAL 3 — TARGET: salvar o estado final

```bash
python3 /workspace/testes/diagnostico/snapshot_mapa.py "$OBS" novo
```

## Como interpretar

Compare os arquivos `mapa-*.json`, particularmente `quantidade`, `max_entries`
e as chaves nas `entradas`. Uma ocupação constante de 10.000 não prova sozinha
que a nova origem foi recusada: confirme se sua chave apareceu. O formato das
chaves depende do BTF/bpftool; preserve o JSON para análise, sem adivinhar offsets.

A combinação “mapa cheio + entradas antigas preservadas + nova origem ausente”
é compatível com recusa de novos fluxos. Ainda falta confirmar a chegada do
pacote à função e o erro de inserção com contadores específicos. Não atribua
a ausência automaticamente ao mapa sem essa evidência adicional.

Para verificar recuperação por reinício, espere a observação terminar, abra uma
nova com `RUN=diag-mapa-reinicio-r1`, salve o mapa `antes` e repita SOMENTE a
carga de um pacote da nova origem, em uma nova pasta do gerador. Salve o mapa
`novo` e compare. Não repita as cargas de preenchimento nessa etapa.

Após implementar expiração, defina seu prazo antes de repetir o teste. Esperar
10 s só é suficiente se o prazo documentado de expiração for menor que isso.
O critério é admitir fluxos novos sem reiniciar, contabilizando corretamente os
fluxos encerrados ou removidos. Aumentar apenas a capacidade não resolve o ciclo
de vida dos registros.
