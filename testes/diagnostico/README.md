# Diagnósticos do coletor — antes e depois das correções

Estes procedimentos investigam erros de funcionamento. Não são benchmarks de
Chen nem validam detecção DDoS. **Os comandos devem ser executados pela equipe
no servidor. A criação destes roteiros não executou nenhum teste.** Os comandos
ainda precisam ser validados nesse ambiente.

## Duração

As observações dos diagnósticos 01–04 duram **60 segundos por rodada**, com
encerramento automático. No 04 há duas rodadas; no 03 a confirmação por reinício
é uma rodada adicional. Prepare os terminais e comandos antes de iniciar.
O limite é da observação, não inclui preparação e leitura dos resultados.

O 05, ainda dependente de instrumentação, deve usar observações de 60 segundos
com cargas de apenas 10 segundos. O 06 começa pela leitura de arquivos e não
exige esperar uma coleta; uma futura rodada de confirmação deve usar observação
de 60 segundos e carga menor que esse intervalo.

## Ordem sugerida

| Roteiro | Pergunta | Situação |
| --- | --- | --- |
| [01 — Contagem](01-contagem.md) | Três pacotes viram três ou seis na janela? | Executável com o coletor atual |
| [02 — Janela](02-janela.md) | A janela fecha quando o tráfego para? | Executável com o coletor atual |
| [03 — Fluxos e recuperação](03-fluxos-e-recuperacao.md) | O mapa enche e impede novos fluxos? Ele se recupera? | Inspeção do mapa disponível; faltam contadores de falha para diagnóstico completo |
| [04 — Agregação](04-agregacao.md) | Conexões do mesmo IP são misturadas? | Executável com o coletor atual |
| [05 — Perdas de eventos](05-perdas-de-eventos.md) | Quanto o ring buffer deixa de exportar? | Aguardar instrumentação antes de gerar a série |
| [06 — Ethr](06-ethr.md) | Os percentis do JSON correspondem ao log textual? | Primeiro inspecionar dados existentes |

Comece por 01 e 02. No 03, o mapa é acompanhado em etapas com tráfego parado:
o dump não é uma medição de desempenho e não deve ser feito durante benchmarks.

## Antes de executar — NO SERVIDOR

Prepare o laboratório por [PREPARANDOSERVIDOR.md](../testes-chen/PREPARANDOSERVIDOR.md).
Se os roteiros foram adicionados depois de construir a imagem, siga a sequência
de atualização desse documento para que `/workspace/testes/diagnostico` exista
nos containers. Não reconstrua a imagem entre etapas de uma mesma execução.

Com o laboratório preparado, na pasta `~/xdp-flow-monitor/testes/testes-chen`:

```bash
make clab-check
make clab-build
make host-record
```

Esses comandos conferem o laboratório e compilam; são instruções para a equipe,
não comandos executados automaticamente por estes documentos.

No servidor, registre também a versão local em um arquivo novo (não sobrescreve
os registros de campanhas anteriores):

```bash
mkdir -p results-servidor
REGISTRO=results-servidor/diagnostico-codigo-$(date -u +%Y%m%dT%H%M%S).txt
{
    git rev-parse HEAD
    git status --short
    git diff --stat
} > "$REGISTRO"
```

No target, antes de iniciar a observação de cada diagnóstico, preserve os hashes:

```bash
sha256sum /workspace/build/flow_monitor /workspace/build/flow_monitor.bpf.o \
  > /workspace/results/diagnostico-binarios-$(date -u +%Y%m%dT%H%M%S).sha256
```

Encerre benchmarks anteriores. Não inicie `make serve`, daemon ML ou Snort
nos diagnósticos 01–04: eles observam SYNs enviados, não completam conexões TCP.
Use somente os IPs e a interface isolada indicados. Os comandos são limitados
por quantidade de pacotes ou duração; não usam `--flood`.

## Como guardar evidências

Cada roteiro usa um `RUN`, igual nos dois terminais. Nas repetições, troque
`r1` por `r2` em ambos. O gerador cria uma pasta exclusiva e recusa reutilizá-la.
O observador cria uma pasta com timestamp e imprime o caminho após `PRONTO`.

Os resultados ficam no servidor em `results-servidor/target/` e
`results-servidor/generator/`, e podem ser baixados por
[OBTENDORESULTADOS.md](../testes-chen/OBTENDORESULTADOS.md). Não grave evidências
somente em `/tmp` ou `/workspace/build`, pois essas pastas não são preservadas
quando o container é removido.

Registre o commit, hashes dos binários, comandos, timestamps, MTU e versão do
kernel. Guarde dados originais antes de corrigir o código. Para comparar depois,
repita a mesma entrada com outro `RUN` e identifique a versão corrigida.

O hping3 informa pacotes enviados, mas isso sozinho não comprova que todos
chegaram ao coletor. Os IPs de origem .101 e .102 são simulados para evitar
respostas TCP do gerador; não interprete ausência de resposta como perda na captura.
Qualquer divergência deve ser confrontada com o mapa e, quando disponíveis,
contadores de entrada e perda. Não conclua “corrigido” apenas porque o processo terminou.

## Encerramento

Espere o observador terminar e devolver o prompt antes de iniciar o diagnóstico
seguinte. Cada novo monitor cria mapas novos. Essa separação é essencial: um
mapa previamente cheio não serve como ponto inicial de um teste de contagem.
Se não aparecer `PRONTO` ou houver erro, não inicie a carga. Preserve o log e
investigue antes de continuar. Não desligue o servidor para encerrar um teste.
