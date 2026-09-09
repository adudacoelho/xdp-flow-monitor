# Problemas pendentes — reprodução de Chen et al. (2024)

Revisão em 09/09/2026, branch `elisa`. As correções abaixo ainda não foram
aplicadas ao detector. O laboratório novo facilita a execução, mas não valida
automaticamente as métricas do código existente.

| Problema | Consequência | Solução plausível |
| --- | --- | --- |
| Kernel envia totais acumulados; `window.c` soma cada total novamente | Pacotes, bytes e flags inflados. Teste local: snapshots 1, 2, 3 resultaram em 6 pacotes | Agregar e exportar uma vez por janela no kernel; alternativa: calcular deltas por cinco-tupla no userspace |
| Janela userspace agrupada só por IP | Mistura fluxos distintos e difere do artigo | Usar IPs, portas e protocolo como identidade do fluxo |
| Atualizações compartilhadas sem sincronização | CPUs podem perder incrementos ou disputar fechamento/reset | Proteger o estado com sincronização compatível com BPF, copiando o resumo sob proteção; ou usar mapas por CPU e consolidar corretamente |
| Fechamento depende da chegada de outro pacote | Fluxos que ficam inativos não são enviados no prazo | Temporizador BPF ou coleta periódica userspace com transferência consistente de estado |
| Slots e mapa sem expiração | Novos fluxos deixam de ser acompanhados quando a capacidade acaba | Expirar fluxos e liberar slots; contabilizar falhas de inserção e perdas |
| Duas árvores de código e skeleton antigo versionado | Compilação e comportamento dependem da pasta/artefato escolhido | Consolidar uma implementação. O novo build usa a subpasta, inclui `window.c` e garante skeleton recém-gerado |
| Resposta ML interpretada por busca de texto e uma única leitura | Espaços e mensagens parciais podem quebrar a classificação | Enquadrar mensagens, tratar leituras/escritas parciais, timeout e parsing JSON |
| `Flow Duration` renomeada sem contrato de unidade | Treino e inferência podem receber escalas diferentes | Confirmar unidade da fonte, converter e versionar o contrato de features |
| CSV sintético e modelo sem relatório de procedência | A alegação de treino real/100% de acurácia não está comprovada | Identificar dados e hashes, separar capturas de treino/teste e salvar matriz de confusão |
| Filtro TCP por porta 80 e diferenças de ponto de captura | Parte do tráfego pode não ser medida | Documentar cobertura e capturar no ingresso da vítima; validar todos os emissores |

## Como tratar o reset

Se adotarmos janelas no kernel, enviar o resumo e só então iniciar a próxima
janela, preservando a identidade do fluxo. Não zerar dados sem contabilizar
falha de exportação. O reset e a atualização por pacote devem ser coordenados.
Um `if` dentro do programa XDP não dispara sozinho quando o prazo vence.

Se adotarmos deltas, preservar o último contador de **cada fluxo** entre
janelas; detectar recriação do fluxo, overflow e eventos fora de ordem. Trocar
`+=` por `=` isoladamente não resolve. O mínimo do tamanho dos pacotes também
precisa ser calculado por janela, não pela vida inteira do fluxo.

## Prioridade e validação

1. Corrigir contagem e identidade; testar pacotes conhecidos e vários fluxos por IP.
2. Validar concorrência, janelas inativas, reset, perdas e mapa cheio.
3. Padronizar features e comunicação; validar normal passa e ataque é bloqueado.
4. Executar comparações com repetições, dados brutos e ambiente registrado.

Baseline, captura e filtragem estática podem ser preparados separadamente.
Resultados do detector atual devem ser apresentados como diagnóstico preliminar.
O artigo usa seis máquinas e CIC-DDoS2019 estendido; Containerlab em uma VM e o dataset
original constituem uma reprodução adaptada. Veja o [roteiro](../../testes/testes-chen/4A-ambiente-experimental.md).
