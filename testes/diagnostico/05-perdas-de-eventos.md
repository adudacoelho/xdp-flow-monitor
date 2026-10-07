# 05 — Perdas no ring buffer: preparar instrumentação

**Não iniciar a série de carga ainda.** O coletor atual não conta falhas de
exportação, portanto não permite medir diretamente quantos eventos perdeu.
Este roteiro define o trabalho necessário para tornar o diagnóstico conclusivo.

## 1. Acrescentar contadores sem corrigir silenciosamente a lógica

A equipe deve instrumentar `flow_monitor.bpf.c` com contadores que diferenciem:

| Contador | Momento da atualização |
| --- | --- |
| Pacotes elegíveis | Depois da validação e do filtro, antes da busca no mapa |
| Pacotes bloqueados | Quando a blacklist provoca descarte |
| Falhas de inserção | Quando `bpf_map_update_elem` falha, registrando o retorno |
| Tentativas de exportação | Antes de reservar espaço no ring buffer |
| Falhas de reserva | Quando `bpf_ringbuf_reserve` não consegue espaço |
| Eventos exportados | Após submeter o evento |
| Eventos recebidos | No callback C, com validação do tamanho do evento |

Use uma estratégia de atualização que não perca incrementos entre CPUs. Salve
os contadores antes e depois da carga, identifique o programa/mapa e aguarde a
fila ser consumida antes da leitura final. Registre o que ficou pendente.

## 2. Separar as causas de perda

Use um fluxo com porta fixa, para não preencher o mapa enquanto estuda o ring
buffer. Sem isso, ausência de eventos poderia resultar de mapa cheio, e não de
falta de espaço na fila. O modo de coleta deve continuar sem daemon ML.

## 3. Definir uma série curta e limitada

Depois que a instrumentação for implementada, use observações de 60 s
com cargas de 10 s com taxas
solicitadas de 100, 1.000 e 5.000 pacotes/s. Faça uma rodada de cada vez, com
monitor novo, e registre as taxas realmente alcançadas. Só amplie se essas taxas
não revelarem o limite e a equipe decidir que precisa investigá-lo.

Os comandos finais devem ser escritos quando os nomes dos mapas e o mecanismo
de exportação dos contadores existirem. Não há um comando fictício de medição
neste documento. Para cada rodada, capture também CPU global, CPU do processo,
MTU, configuração de logging e ocupação do mapa.

## 4. Calcular e conferir

- Tentativas de exportação = eventos exportados + falhas de reserva.
- Taxa de perda da fila = falhas de reserva / tentativas, quando tentativas > 0.
- Eventos recebidos devem ser confrontados com exportados após esvaziar a fila.
- Pacotes enviados pelo gerador não substituem os pacotes elegíveis medidos no kernel.

Uma perda zero em baixa carga não garante perda zero em alta carga. Valores
inconsistentes entre os contadores precisam ser investigados antes do benchmark.
Não use a contagem inflada das janelas como contador de recepção.
