# xdp-flow-monitor

Monitor de rede com XDP/eBPF e classificação de tráfego por XGBoost.
O laboratório atual executa Docker e Containerlab diretamente no servidor,
sem VM. Os containers compartilham o kernel do servidor.

## Preparação e experimentos

Comece por [PREPARANDOSERVIDOR.md](testes/testes-chen/PREPARANDOSERVIDOR.md).
Esse arquivo concentra instalação, criação dos containers e compilação.
Execute os experimentos no servidor seguindo seus roteiros:

| Roteiro | Conteúdo |
| --- | --- |
| [4A — Ambiente](testes/testes-chen/4A-ambiente-experimental.md) | Topologia e registros do ambiente |
| [4B — Coleta eBPF](testes/testes-chen/4B-coleta-ebpf.md) | Throughput, CPU, memória e latência |
| [4C — Filtragem XDP](testes/testes-chen/4C-filtragem-xdp.md) | Comparação com iptables |
| [4D — Classificação](testes/testes-chen/4D-classificacao.md) | Avaliação do modelo |
| [4E — Sistema completo](testes/testes-chen/4E-sistema-completo.md) | Replay e integração |

Os comandos de administração ficam em `testes/testes-chen/Makefile`.
Os comandos internos dos containers ficam em `testes/testes-chen/containers/Makefile`.
Os resultados são gravados em `testes/testes-chen/results-servidor/` no servidor.
Para baixá-los, siga [OBTENDORESULTADOS.md](testes/testes-chen/OBTENDORESULTADOS.md).

## Funcionamento

O programa eBPF observa os pacotes no ponto XDP da interface `lab0` do container
`target`. Consulta a blacklist, coleta métricas e as envia por ring buffer ao
programa C. O userspace agrega os dados por IP de origem em janelas configuradas
para 5 segundos e consulta o daemon Python por socket Unix. Quando a resposta
indica ataque, o C insere a origem na blacklist; pacotes que alcançam essa
consulta são descartados com `XDP_DROP`.

| Arquivo em `xdp-flow-monitor-main/` | Função |
| --- | --- |
| `flow_monitor.bpf.c` | Coleta no kernel, mapas e bloqueio XDP |
| `common.h` | Estrutura de métricas compartilhada |
| `main.c` | Carregamento, recepção de eventos, consulta ML e blacklist |
| `window.c` / `window.h` | Agregação e cálculo de características |
| `ml_daemon.py` | Inferência com o modelo salvo |
| `train_model.py` | Treinamento a partir de CSVs |

## Estado da validação

O primeiro experimento compara baseline, TShark e o coletor atual sem daemon ML.
O sistema completo ainda requer correção da contagem cumulativa, definição do
contrato das características e comprovação dos dados usados no treinamento.
Não há base para apresentar a afirmação antiga de 100% de acurácia como resultado
validado. Consulte [REPRODUCAO.md](REPRODUCAO.md) para o diagnóstico histórico e
as pendências metodológicas. Os roteiros indicam o que ainda precisa ser validado
no servidor.
