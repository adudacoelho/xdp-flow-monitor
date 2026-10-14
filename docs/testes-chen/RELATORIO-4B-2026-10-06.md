# Relatório do experimento 4B — coleta de tráfego com eBPF


## 1. O que conseguimos e o que ainda falta

O laboratório conseguiu executar transferências TCP, gerar SYN flood e medir latência. Depois das correções de anexação e da mudança da MTU para 1500, os registros confirmam que o programa XDP foi anexado e que o monitor recebeu eventos.

Isso representa uma coleta funcional, mas **não significa que todas as métricas calculadas pelo monitor estejam corretas**. Encontramos um erro de contagem que infla os números, limitações no gerenciamento dos fluxos e uma quantidade inesperadamente pequena de janelas durante o SYN flood. Esses problemas precisam ser resolvidos antes de tratar o coletor como implementação validada.


## 2. Para que serve o 4B

A pergunta do experimento é: **quanto observar o tráfego interfere na rede e no consumo de recursos?**

Imagine uma estrada. O tráfego são os veículos e o coletor é um posto que registra suas características. Queremos saber se instalar esse posto diminui a quantidade de veículos que passam, aumenta o tempo de viagem ou exige mais recursos para funcionar.

| Cenário | Significado |
| --- | --- |
| `baseline` | Referência sem TShark e sem o coletor eBPF; as ferramentas de medição continuam ativas. |
| `tshark` | Captura e análise textual de pacotes, gravadas em log. |
| `collection-current` | Programa eBPF e monitor C atuais, sem o daemon de classificação ML. |

O 4B tem três partes:

1. **Throughput TCP:** iperf3 transfere dados por 50 segundos. Throughput é a quantidade efetivamente transferida por segundo; maior valor indica maior capacidade de transferência naquela execução.
2. **CPU e memória sob SYN flood:** o gerador envia muitas solicitações de início de conexão TCP por 120 segundos. Observamos o uso de recursos durante essa carga.
3. **Latência TCP:** Ethr faz medições por aproximadamente 120 segundos. Latência é o tempo medido pela ferramenta na interação TCP; menor valor indica resposta mais rápida naquela medição.

## 3. Ambiente e protocolo utilizados

O laboratório roda diretamente no servidor, com os containers `generator` e `target` conectados pelas interfaces `lab0`. O primeiro gera tráfego; o segundo recebe o tráfego e executa a coleta. Os containers compartilham o kernel e os recursos do servidor.

| Item | Configuração analisada |
| --- | --- |
| Gerador | `192.168.157.10` |
| Destino | `192.168.157.20`, porta 80 |
| MTU das novas rodadas | 1500 nas duas pontas |
| Kernel nos registros novos | `7.0.0-34-generic` |
| CPUs lógicas reportadas | 32 |
| Observação do throughput | Aproximadamente 70 segundos |
| Observação de SYN e latência | Aproximadamente 140 segundos, com uma exceção discutida abaixo |
| Carga SYN solicitada | 5.000 pacotes/s, distribuídos entre seis processos |
| Origens simuladas do SYN | `192.168.157.101` a `192.168.157.106` |

A MTU determina o tamanho máximo do pacote IP permitido na interface. As primeiras execuções usavam MTU 9500; as novas usam 1500. Essa mudança pode afetar o desempenho, por isso os dois conjuntos não devem ser misturados em uma mesma comparação.

As durações de observação de 70 e 140 segundos são decisões do roteiro local, não requisitos atribuídos aqui ao artigo de Chen. A margem de 20 segundos permite iniciar a carga manualmente depois do aviso `PRONTO`. As médias de CPU e memória deste relatório excluem a margem sem carga.

O ambiente é uma reprodução adaptada. Os dados não devem ser apresentados como reprodução exata da infraestrutura ou dos resultados publicados pelos autores.

## 4. Como os arquivos foram interpretados

A análise usou os resultados em `testes/testes-chen/results-servidor/`. Como os arquivos brutos são ignorados pelo Git, quem receber apenas este relatório pelo repositório precisará baixar ou receber esses dados separadamente.

| Arquivo | Uso na análise |
| --- | --- |
| `start-epoch.txt` e `end-epoch.txt` | Verificar início, fim e se a observação cobriu a carga. |
| `interface.txt` | Conferir a MTU e a interface registrada antes da execução. |
| `xdp-attached.json` | Confirmar anexação XDP no início da observação. |
| `monitor.log` | Verificar eventos, janelas e mensagens do monitor. |
| `iperf.json` | Obter o throughput recebido pelo destino. |
| `cpu.txt` e `memory.txt` | Obter amostras de uso de recursos do servidor. |
| `network.txt` | Conferir tráfego da interface no namespace do container. |
| `hping-*.log` | Somar os pacotes reportados como enviados pelos seis processos. |
| `ethr.json` e `ethr.log` | Conferir se houve medições de latência e erros. |
| `tshark.log` | Conferir captura e perdas reportadas pelo TShark. |

**Cálculos usados:** throughput = `end.sum_received.bits_per_second / 10^9`, em Gbit/s. Latência = média aritmética dos campos `Avg` dos 121 registros `LatencyResult` de cada cenário; não é uma média reconstruída a partir de todas as medições individuais. CPU = média de `100 - %idle` das linhas `all` do mpstat. Memória = média de `kbmemused / 1024`, em MiB, conforme a unidade reportada pelo sar.

Para CPU e memória no SYN, foram selecionadas 119 amostras por rodada, cujos horários de fim estão pelo menos um segundo após o início do gerador e não ultrapassam seu encerramento. Isso evita incluir os intervalos de um segundo que atravessam o início da carga. 

Não foram calculados intervalos de confiança: o conjunto não contém uma série equilibrada de repetições independentes para todos os cenários.

## 5. Resultados do throughput

| Cenário | Throughput recebido | Variação aproximada em relação ao baseline |
| --- | ---: | ---: |
| Baseline | 7,85 Gbit/s | Referência |
| TShark | 4,64 Gbit/s | Queda de 40,9% |
| Coletor eBPF atual | 4,78 Gbit/s | Queda de 39,1% |

Os três clientes terminaram em aproximadamente 50 segundos e não registraram erro no JSON. A observação cobriu as três transferências.

Nesta rodada, o eBPF ficou aproximadamente 3% acima do TShark em throughput. Essa diferença pequena não permite concluir superioridade sem repetições. Ambos ficaram abaixo do baseline. O custo medido do eBPF inclui a implementação atual: envio de eventos por pacote, processamento em C e logging.

O TShark registrou **18.444.277 pacotes capturados e 6.563.295 pacotes perdidos pela captura**. Perder um pacote na captura significa que a ferramenta não conseguiu registrar todos os pacotes; não significa automaticamente que esses pacotes deixaram de chegar à aplicação TCP. O desempenho deve ser apresentado junto com essa limitação de cobertura.

Os valores medem um enlace virtual entre containers do mesmo servidor. Não são uma medição da capacidade de uma conexão externa ou da Internet.

## 6. CPU e memória durante o SYN flood

| Cenário | CPU média do servidor | Memória média usada do servidor | Pacotes/s enviados, aproximadamente |
| --- | ---: | ---: | ---: |
| Baseline | 3,72% | 6.276 MiB | 4.925 |
| TShark | 3,63% | 6.769 MiB | 4.923 |
| eBPF — última execução | 3,50% | 6.906 MiB | 4.923 |

A carga solicitada era 5.000 pacotes/s; os logs dos geradores indicam uma taxa próxima, mas um pouco inferior. Esses números são derivados das estatísticas de envio do hping3, não uma contagem de eventos recebidos pelo coletor eBPF.

**A CPU não é a CPU exclusiva do coletor.** É o uso agregado do servidor, considerando 32 CPUs lógicas e outros processos. Um único núcleo completamente ocupado já representa cerca de 3,125% da capacidade agregada, ilustrando por que um percentual aparentemente pequeno merece cuidado na interpretação.

**A memória também não é a memória exclusiva do coletor.** Diferenças podem envolver outros serviços e mudanças no estado do sistema. Portanto, não podemos dizer que o eBPF “consumiu 6.906 MiB” ou que ele economizou CPU com base nessa tabela.

Houve duas rodadas SYN/eBPF. A primeira registrou cerca de 150,01 segundos de observação, apesar de `DURATION=140`; a segunda registrou 140,18 segundos. A tabela usa a segunda, por corresponder ao protocolo previsto. A primeira permanece como diagnóstico e não deve ser apagada. Os arquivos não determinam sozinhos a causa do tempo adicional; espera por processos e escalonamento são pontos a investigar, não causas comprovadas.

As duas rodadas eBPF produziram apenas **seis janelas no monitor**, aproximadamente uma por origem simulada. Isso é um sinal de cobertura incompleta ou de gerenciamento inadequado dos fluxos. A anexação funcionou, mas ainda não podemos afirmar que o monitor acompanhou corretamente todo o ataque.

Como o gerador usa IPs de origem simulados, a mensagem “100% packet loss” do hping3, se presente, descreve a ausência de respostas recebidas por ele. Ela não deve ser usada isoladamente como prova de que a vítima descartou todo o ataque.

## 7. Resultados de latência

| Cenário | Média dos valores `Avg` do Ethr | Registros de latência |
| --- | ---: | ---: |
| Baseline | 27,50 µs | 121 |
| TShark | 28,55 µs | 121 |
| Coletor eBPF atual | 30,72 µs | 121 |

Um microssegundo, representado por µs, é um milionésimo de segundo. Nesta execução, o TShark ficou cerca de 3,8% acima do baseline, e o eBPF, cerca de 11,7%. Esses percentuais são descritivos da rodada, não garantias sobre outras cargas.

A latência baseline, que havia falhado no conjunto antigo, agora produziu medições. Os clientes duraram aproximadamente 121 segundos, incluindo inicialização e encerramento, e ficaram dentro da observação.

**Os percentis do JSON do Ethr continuam inconsistentes.** Por exemplo, um registro baseline apresenta `P50=61.930us`, `P90=28.930us` e `Max=48.069us`. Um percentil 50 não deveria superar o percentil 90 nem o máximo do mesmo conjunto. Isso sugere um problema na correspondência dos campos exportados ou no cálculo, que precisa ser investigado no Ethr utilizado.

Não publicamos P50, P90 ou P99 como resultados válidos. As médias acima usam o campo `Avg`, mas a inconsistência da ferramenta também recomenda conferir sua exportação antes de uma apresentação definitiva. A média de médias não permite reconstruir os percentis globais.

## 8. Problemas anteriores tratados

| Problema | Alteração realizada | Evidência ou limite atual |
| --- | --- | --- |
| XDP falhava e o programa dizia que havia iniciado | Tratamento do retorno da libbpf com `libbpf_get_error`, saída de erro e validação da anexação no executor | Novos arquivos `xdp-attached.json` e eventos no monitor confirmam anexação nas rodadas analisadas. |
| MTU 9500 associada à falha `ERANGE` | Topologia passou a configurar MTU 1500 nas duas interfaces | Novas rodadas funcionaram nessa configuração; isso não estabelece um limite universal para todos os drivers. |
| Ethr tentava iniciar enquanto a porta 80 estava ocupada | Verificação de porta, trava do serviço e apresentação dos erros | Novas rodadas de latência produziram registros. |
| Cliente Ethr podia terminar sem amostras e sem falha clara no roteiro | Verificação de handshake e presença de registros de latência | A ausência de amostras passou a ser motivo de falha. |
| Ctrl+C não encerrava o serviço como esperado | Uso de `timeout --foreground` no alvo `serve` | Alteração local; sua eficácia específica não é comprovada pelos resultados anteriores à atualização. |
| Cópia parecia parada e era interrompida | Progresso visível e preservação de arquivos parciais no `get-results` | Os registros necessários à análise foram recuperados. |

Não é necessário atualizar o sistema operacional do servidor para explicar essas correções: elas envolvem o projeto e a configuração do laboratório.

## 9. Problemas do código que ainda precisam ser corrigidos

### 9.1. Contagem repetida de pacotes — confirmado no código

**Onde:** [flow_monitor.bpf.c](../../xdp-flow-monitor-main/flow_monitor.bpf.c) e [window.c](../../xdp-flow-monitor-main/window.c), função `window_update`.

O kernel envia uma fotografia dos contadores acumulados do fluxo a cada pacote. O C soma cada fotografia como se representasse apenas pacotes novos.

Exemplo: chegam três pacotes. As fotografias mostram 1, depois 2, depois 3. Somar as fotografias produz `1 + 2 + 3 = 6`, embora só tenham chegado três pacotes. Com muitos pacotes, o erro cresce rapidamente. Bytes e flags TCP sofrem problema equivalente.

**Evidência observada:** no novo throughput eBPF, uma janela informa aproximadamente 402,6 bilhões de pacotes/s. Esse valor interno não deve ser confundido com o throughput de 4,78 Gbit/s medido pelo iperf3.

**Correção necessária:** definir um contrato único. Podemos exportar incrementos de cada evento ou exportar totais por fluxo/janela e consumir diferenças corretamente. Subtrair totais por IP não basta quando existem vários fluxos daquele IP. Uma abordagem por diferenças também precisa lidar com reinício, eventos fora de ordem e perdas.

**Critério de validação futura:** uma sequência conhecida de N pacotes deve produzir N, com bytes e flags corretos; repetir a verificação para vários fluxos da mesma origem. A execução diagnóstica da versão com defeito foi realizada pela equipe em 7 de outubro e está documentada na seção 15: três SYNs resultaram em SYN=6. A validação da versão corrigida continua pendente.

### 9.2. Mapa de fluxos enche e não expira — limitação confirmada, relação com o SYN ainda é hipótese

**Onde:** `flow_map` em [flow_monitor.bpf.c](../../xdp-flow-monitor-main/flow_monitor.bpf.c).

O mapa tem capacidade para 10.000 fluxos. Cada fluxo é identificado pelos IPs, portas e protocolo. Não há remoção nem expiração das entradas. Quando uma inserção falha e a busca seguinte não encontra o fluxo, o programa deixa o pacote passar sem exportar suas métricas.

É como um cadastro com 10.000 fichas que nunca são arquivadas: depois de cheio, novas pessoas deixam de ser registradas. O tráfego pode continuar chegando à vítima enquanto a coleta deixa de acompanhá-lo.

**Hipótese para as seis janelas no SYN:** a mudança de portas pode produzir muitas cinco-tuplas, preencher o mapa rapidamente e impedir o cadastro dos fluxos seguintes. A repetição de portas pode voltar a encontrar entradas antigas mais tarde. Isso é compatível com o comportamento observado, mas os dados atuais não incluem ocupação do mapa nem contadores de falha que comprovem essa sequência.

**Correção necessária:** gerenciar o ciclo de vida dos fluxos, registrar falhas de inserção e medir ocupação. Aumentar o limite sozinho apenas adia o problema. Um mapa com remoção automática também exige registrar as remoções para não perder métricas silenciosamente.

### 9.3. Janela de 5 segundos depende da chegada de um evento

**Onde:** `window_update` em [window.c](../../xdp-flow-monitor-main/window.c).

O programa só verifica o tempo quando recebe uma nova métrica. Se uma origem para de enviar ou deixa de gerar eventos por falha de coleta, a janela não fecha por conta própria. O último trecho do tráfego pode ficar sem relatório.

**Correção necessária:** fechamento periódico e tratamento de janelas pendentes no encerramento. Definir explicitamente como tratar períodos sem tráfego e janelas finais menores que cinco segundos.

### 9.4. Kernel separa por fluxo, userspace junta por IP

**Onde:** `struct flow_key` em `flow_monitor.bpf.c` e `find_or_create` em `window.c`.

O kernel distingue conexões pela cinco-tupla; o C usa apenas `src_ip`. Assim, conexões diferentes podem ser misturadas na mesma janela. Agrupar por origem pode ser uma decisão válida, mas precisa ser assumida e compatível com os dados usados no treinamento.

Além disso, os 1.024 slots do userspace não são liberados: o campo `active` continua marcado após o fechamento da janela. Depois de muitas origens distintas, novas origens podem não ganhar um slot.

**Correção necessária:** escolher a unidade de agregação, documentá-la e implementar expiração/reutilização de slots. Não apresentar métricas por origem como se fossem automaticamente métricas por conexão.

### 9.5. Perda de eventos sem contador

**Onde:** `bpf_ringbuf_reserve` em `flow_monitor.bpf.c`.

O ring buffer é a área de comunicação entre kernel e C. Se não há espaço, o código deixa o pacote seguir, mas não registra quantos eventos deixou de exportar. Isso é diferente de perder o pacote na rede.

**Correção necessária:** contadores de tentativas de exportação, eventos enviados, eventos perdidos e falhas no mapa. Comparar desempenho sem medir cobertura pode favorecer um coletor que simplesmente deixou de trabalhar sobre parte do tráfego.

### 9.6. Atualizações concorrentes e contadores pequenos

**Onde:** incrementos em `flow_monitor.bpf.c`, estruturas de [common.h](../../xdp-flow-monitor-main/common.h) e `window.c`.

O código altera valores compartilhados com operações como `+= 1`, sem sincronização explícita. Se o mesmo registro for atualizado simultaneamente por CPUs diferentes, incrementos e fotografias podem ficar inconsistentes. Esse risco foi identificado na implementação; o experimento não mediu sua ocorrência.

Contadores de flags usam 32 bits e podem voltar a zero ao ultrapassar sua capacidade. A soma duplicada acelera esse risco.

**Correção necessária:** definir estratégia de concorrência, como contadores por CPU ou sincronização apropriada, e dimensionar os tipos numéricos. Validar contagens sob múltiplos fluxos e CPUs.

### 9.7. O modo de coleta ainda tenta consultar o classificador

**Onde:** `handle_event` e `query_ml` em [main.c](../../xdp-flow-monitor-main/main.c).

No `collection-current`, o daemon não é iniciado, mas o monitor ainda tenta abrir o socket a cada janela e imprime um aviso. O aviso “sem classificação” é esperado nessa configuração, não é a falha de anexação XDP anterior.

**Correção necessária:** um modo explícito de coleta que não faça consultas ao ML. Registrar essa mudança como nova versão experimental, pois ela altera o custo medido. A exportação por pacote e o logging também precisam ser considerados ao comparar com uma arquitetura que exporta apenas resumos por janela.

### 9.8. Comunicação com ML frágil — pendência do sistema completo

**Onde:** `query_ml` em `main.c` e `run` em [ml_daemon.py](../../xdp-flow-monitor-main/ml_daemon.py).

O C envia e recebe uma vez, sem verificar adequadamente os tamanhos transferidos, e procura o texto exato `"attack": true`. O Python também pressupõe que uma única leitura recebeu o JSON inteiro. Uma conexão de fluxo não garante que uma mensagem inteira venha em uma leitura.

**Correção necessária:** delimitar mensagens, ler/escrever até completar, interpretar JSON como estrutura, definir tempo limite e distinguir “normal”, “ataque” e “falha de comunicação”. Uma resposta inválida não deve virar silenciosamente “normal”.

Esse problema não invalida o iperf3 por si só, mas impede considerar o sistema integrado robusto.

### 9.9. Unidades e procedência do modelo — pendência antes da classificação

**Onde:** [train_model.py](../../xdp-flow-monitor-main/train_model.py) e `ml_daemon.py`.

O treinamento renomeia `Flow Duration` para `duration_sec` sem conversão explícita. Se o CSV estiver em microssegundos, o treino e a execução usarão escalas diferentes. O nome da coluna não comprova a unidade do dado original.

**Correção necessária:** documentar nomes, unidades e significado das características; verificar o dataset real; registrar sua origem, separação de treino/teste e prevenção de vazamento entre conjuntos. Também é necessário vincular o modelo salvo ao treinamento que o gerou.

O 4B não fornece evidência de acurácia, recall, falsos positivos ou qualidade da detecção. Não sustenta uma afirmação de “100% de acurácia”.

### 9.10. Validação dos pacotes e cobertura do filtro

**Onde:** análise dos cabeçalhos e consulta da blacklist em `flow_monitor.bpf.c`.

O programa verifica limites de memória de alguns cabeçalhos, mas não trata explicitamente todos os casos de fragmentação IPv4, tamanho inválido do cabeçalho IP, VLAN e IPv6. No TCP, o filtro de porta 80 ocorre antes da blacklist; portanto, a blacklist atual não equivale a bloquear irrestritamente todo tráfego daquele IP.

**Correção necessária:** definir o escopo suportado, validar os cabeçalhos e testar os casos de protocolo relevantes antes de apresentar o programa como proteção geral de rede. Essas limitações não foram avaliadas pelas cargas simples deste 4B.

## 10. Melhorias necessárias no executor e na metodologia

| Questão | Consequência | Ajuste proposto |
| --- | --- | --- |
| Um cenário por vez, com poucas repetições | Não separa efeito do coletor de variações do servidor | Repetições independentes e ordem alternada, com dispersão além da média. |
| CPU/memória globais | Não atribui consumo ao coletor | Registrar processos/cgroups e uso global separadamente, incluindo limitações para recursos do kernel. |
| `KIND=tcp` aparece nos parâmetros da observação SYN | O campo tem valor padrão e pode confundir a identificação | Separar parâmetros locais da observação dos parâmetros da carga; criar manifesto comum da rodada. |
| Reutilização de `RUN=...-r1` | Várias tentativas têm o mesmo rótulo | Identificador único e indicação explícita de rodada válida, abortada ou diagnóstica. |
| Espera manual antes de iniciar a carga | Pode haver transferência fora da observação | Preservar timestamps e validar automaticamente a cobertura; futuramente sincronizar início. |
| Espera adicional na primeira rodada SYN/eBPF | Duração real pode divergir da solicitada | Registrar duração efetiva dos coletores e motivo de término; investigar espera e sinais. |
| Logs textuais grandes do TShark | Custo de disco, cópia demorada e perdas na captura | Definir política de armazenamento; mudar formato somente com nova identificação de protocolo e nova comparação. |
| Percentis incoerentes do Ethr | P50/P90/P99 não confiáveis | Conferir implementação/exportação e versão; não “consertar” os dados apenas ordenando os campos. |
| Falta de contadores de cobertura eBPF | Não sabemos quanto da carga foi observado | Instrumentar mapa e ring buffer antes de comparar eficiência. |

O percentual de perda informado pelo hping3 e o número de pacotes perdidos pelo TShark descrevem coisas diferentes. Da mesma forma, bytes/s da interface, throughput útil do iperf3 e bytes/s calculados pelo coletor não são métricas intercambiáveis.

## 11. Ordem recomendada das próximas atividades

Os procedimentos de diagnóstico propostos estão em
[testes/diagnostico/README.md](../../testes/diagnostico/README.md).
Eles distinguem verificações possíveis com a versão atual das que dependem de
instrumentação adicional. Sua elaboração não representa execução ou validação
desses testes.

1. Preservar este conjunto como **resultados preliminares da implementação atual, MTU 1500**.
2. Corrigir a contagem duplicada e decidir o contrato de agregação.
3. Instrumentar ocupação/falhas do mapa e perdas de eventos; corrigir expiração e fechamento de janelas.
4. Investigar as seis janelas do SYN com essas informações disponíveis.
5. Conferir a exportação do Ethr e melhorar a identificação das rodadas e o encerramento dos serviços.
6. Quando a equipe autorizar a execução no servidor, validar contagens conhecidas e cobertura antes de iniciar nova série de desempenho.
7. Depois das correções, repetir os cenários comparáveis com configurações documentadas e repetições suficientes.
8. Só então avançar para conclusões sobre classificação e sistema integrado, com dados e modelo validados.

Não se recomenda refazer indefinidamente o 4B antes de corrigir o coletor: repetir uma implementação que perde cobertura ou conta errado não elimina o problema.

## 12. Por que os experimentos 4C, 4D e 4E foram adiados

**Nesta etapa do trabalho, optou-se por não avançar para novas campanhas de desempenho antes de corrigir e validar os componentes necessários a cada experimento.** O 4B revelou problemas que podem comprometer a interpretação dos testes seguintes. Executar os comandos disponíveis, por si só, não garante que a pergunta de cada experimento seja respondida.

O adiamento evita consumir tempo do servidor e da equipe com medições que provavelmente teriam de ser repetidas após mudanças na implementação. Trata-se de uma decisão sobre a sequência do trabalho, e não de um resultado negativo dos testes 4C, 4D ou 4E: esses experimentos completos não foram realizados na campanha documentada aqui. Essa delimitação não pretende descrever eventuais execuções de outros integrantes em versões ou ambientes diferentes.

| Experimento | Pergunta que deveria responder | Por que não avançamos agora |
| --- | --- | --- |
| **4C — Filtragem** | Como XDP e iptables se comportam bloqueando as mesmas origens, com diferentes quantidades de regras? | Existe o cenário iptables, mas falta preparar um modo XDP de filtragem estática equivalente e sua validação. |
| **4D — Classificação** | Com que qualidade os modelos distinguem tráfego normal de ataques? | Faltam a definição verificável dos dados, das unidades e das partições de avaliação, além da comparação entre modelos. |
| **4E — Sistema completo** | O sistema detecta e mitiga ataques preservando o tráfego legítimo, e quanto tempo cada etapa consome? | A integração depende de métricas corretas, classificação validada e instrumentação de tempos que ainda não estão prontas. |

### 12.1. Teste 4C: anexar XDP não equivale a preparar a comparação de filtros

O código já possui uma blacklist, isto é, uma lista de origens a bloquear. Entretanto, o caminho atual foi organizado para que o classificador alimente essa lista. O experimento 4C precisa de regras previamente definidas, aplicadas de forma equivalente no XDP e no iptables, sem misturar o custo de classificação com o custo de filtragem.

No executor atual existe `MODE=iptables`, mas não existe `MODE=xdp`. Ainda precisamos carregar as listas de regras no lado XDP, separar a filtragem da coleta e registrar se os pacotes de ataque foram bloqueados enquanto o tráfego legítimo continuou passando.

Executar apenas iptables produziria dados de um dos lados, sem concluir a comparação. Por isso, essa medição parcial foi adiada junto com a campanha. **O 4C não depende obrigatoriamente de corrigir todo o aprendizado de máquina:** pode ser retomado quando o filtro estático e o protocolo de comparação estiverem preparados e validados.

### 12.2. Teste 4D: conseguir treinar não significa ter uma avaliação confiável

O comando `make ml` permite treinar o XGBoost existente, mas ainda não implementa a comparação completa entre os modelos. Antes da avaliação, é necessário identificar os CSVs utilizados, conferir suas unidades e definir quais dados serão usados para aprender e quais serão reservados para avaliar.

Em termos simples, não podemos avaliar um aluno apenas com perguntas cujas respostas ele já decorou. Da mesma forma, amostras iguais ou muito relacionadas presentes tanto no treino quanto no teste podem produzir uma nota alta sem demonstrar capacidade de reconhecer novos ataques.

O erro de contagem do coletor também impede assumir que as características recebidas em operação representam corretamente o tráfego. Isso não impede tecnicamente uma avaliação offline com um dataset independente e correto, mas impede extrapolar esse resultado para o sistema atual sem validar a compatibilidade entre treino e execução.

**Condição para retomar:** dados e procedência documentados, características com significado e unidades definidos, partições adequadas, métricas de avaliação e comparadores implementados. A integração posterior exige ainda que o coletor produza essas mesmas características corretamente.

### 12.3. Teste 4E: a integração depende da confiabilidade das etapas anteriores

O sistema completo forma uma sequência: coletar, calcular características, classificar e bloquear. Se a coleta conta um pacote várias vezes ou deixa de acompanhar novos fluxos, o classificador recebe uma descrição incorreta do tráfego. Nesse caso, não conseguimos atribuir um erro de detecção ao modelo, à coleta ou à comunicação entre os componentes.

Além disso, os comandos de replay disponíveis reproduzem pacotes, mas não medem automaticamente os tempos individuais de coleta, inferência e filtragem. Ainda faltam os pontos de início e fim de cada medição e o registro das amostras correspondentes.

Baseline e Snort poderiam ser executados isoladamente, mas isso constituiria uma avaliação parcial. O Snort configurado gera alertas; não oferece automaticamente um comparador equivalente ao bloqueio do nosso sistema. Foi decidido não iniciar essa série agora, para evitar coletar dados que precisem ser refeitos após a definição do protocolo integrado.

**Condição para retomar:** corrigir as métricas e a cobertura do coletor, validar o modelo e sua comunicação, confirmar bloqueio e continuidade do tráfego legítimo e implementar a instrumentação de tempos. Depois disso, definir cenários comparáveis e iniciar a campanha completa.

### 12.4. O que deve acontecer antes de novas campanhas

A prioridade passa a ser a correção dos componentes e sua validação funcional direcionada, em vez de novas séries extensas de benchmark. Validação funcional significa conferir se cada parte faz o que deveria: por exemplo, se dez pacotes são contados como dez e se uma regra bloqueia a origem prevista sem afetar as demais.

Essas verificações futuras devem ocorrer no ambiente apropriado e com execução acordada pela equipe. Nenhuma foi executada para acrescentar esta seção. Após obter uma versão confiável e registrar sua configuração, a equipe poderá retomar cada experimento conforme seus requisitos, sem exigir que todas as pendências do projeto sejam resolvidas ao mesmo tempo.

## 13. Como explicar estes resultados em uma apresentação

> “Conseguimos executar o laboratório e confirmar a anexação do programa XDP após ajustar o tratamento de erro e a MTU. Na rodada analisada, o throughput caiu de aproximadamente 7,85 Gbit/s sem coletor para 4,64 Gbit/s com TShark e 4,78 Gbit/s com nosso coletor eBPF. Também obtivemos medições de latência nos três cenários. Os resultados ainda são preliminares: identificamos contagem duplicada, limitações no gerenciamento dos fluxos e inconsistências nos percentis exportados pelo Ethr. Por isso, estamos usando esta etapa para validar e corrigir a implementação antes da comparação experimental definitiva.”

## 14. Como reproduzir o 4B

O passo a passo completo está no [roteiro 4B](../../testes/testes-chen/4B-coleta-ebpf.md).
Prepare o laboratório pelo [roteiro do servidor](../../testes/testes-chen/PREPARANDOSERVIDOR.md)
e use a mesma configuração nos três cenários: baseline, TShark e coletor eBPF.

| Parte | Procedimento | O que comparar |
| --- | --- | --- |
| Throughput | Serviço iperf3 no target; observação de 70 s; transferência TCP de 50 s no generator após `PRONTO`. Repetir nos três cenários. | Throughput recebido no `iperf.json` e perdas reportadas pelo coletor. |
| CPU/memória | Serviço iperf3 no target; observação de 140 s; SYN flood de 120 s com taxa solicitada de 5.000 pacotes/s. Repetir nos três cenários. | Amostras de CPU e memória somente durante a carga, taxa alcançada e cobertura do monitor. |
| Latência | Encerrar iperf3 e iniciar Ethr na porta 80; observação de 140 s; cliente Ethr por 120 s. Repetir nos três cenários. | Médias de latência e consistência dos campos exportados. |

Use MTU 1500 em ambos os containers, mapas limpos em cada execução e daemon ML
desligado no modo de coleta. Confirme a anexação XDP antes da carga, mantenha
os parâmetros iguais entre cenários e preserve os logs. Repita as rodadas para
avaliar variação; um resultado isolado não demonstra superioridade geral.

As durações acima descrevem o **4B** e permanecem inalteradas. A redução para um
minuto aplica-se às observações dos **diagnósticos**, que têm outro objetivo.

O conjunto analisado demonstrou o funcionamento do laboratório e a anexação
XDP, além de diferenças preliminares de throughput e latência. Não validou a
correção das métricas internas, a cobertura completa da coleta nem a detecção
DDoS. Os números e suas limitações estão nas seções 5–7; os problemas de código,
na seção 9.

### Fontes do projeto

- [Roteiro 4B](../../testes/testes-chen/4B-coleta-ebpf.md).
- [Preparação do servidor](../../testes/testes-chen/PREPARANDOSERVIDOR.md).
- [Makefile dos containers](../../testes/testes-chen/containers/Makefile).
- [Topologia](../../lab/topology.clab.yml).
- [Diagnóstico histórico](../../REPRODUCAO.md).

O código inspecionado é a cópia local atual. Não há um identificador imutável de build por rodada que permita afirmar que cada arquivo atual é idêntico ao executado no servidor; por isso, o relatório diferencia evidências dos logs, achados no código e hipóteses a investigar.

## 15. Diagnóstico 01 — contagem conhecida de pacotes

### Objetivo

Verificar se o monitor conta corretamente uma sequência pequena de pacotes.
Este diagnóstico foi executado pela equipe no servidor, com o coletor atual
ativo e sem classificação por aprendizado de máquina.

### Como o teste foi realizado

Foram enviados três pacotes TCP com a flag SYN para `192.168.157.20`, porta 80.
Todos usaram a origem simulada `192.168.157.101` e a porta de origem `12345`,
mantida fixa com `--keep`. Assim, os três pertenciam ao mesmo fluxo.

Cada chamada do hping3 foi limitada a um pacote, com uma pausa de três segundos
entre chamadas. O tempo de execução das chamadas somado às pausas fez com que
o terceiro evento chegasse depois do limite de cinco segundos da janela,
provocando seu fechamento na implementação atual.

### Resultado observado

O monitor exibiu:

```text
Janela fechada — src: 192.168.157.101
Flow Packets/s   : 0.74
Flow Bytes/s     : 40.20
Packet Len Mean  : 54.00 bytes
Min Packet Len   : 54 bytes
TCP Flags        : SYN:6 ACK:0 RST:0 URG:0 CWR:0
[AVISO] ml_daemon.py não está rodando — sem classificação.
```

**Para a sequência de três SYNs, a janela informou seis SYNs.** O aviso de ausência
do daemon é esperado neste diagnóstico e não é a causa do erro.

### O que o teste demonstrou

O resultado reproduziu a contagem duplicada identificada no código. O kernel
exporta contadores acumulados, enquanto o userspace soma cada atualização como
se ela representasse apenas os pacotes novos:

```text
Pacotes enviados:       1 + 1 + 1 = 3
Snapshots acumulados:   1, 2, 3
Soma feita pelo código: 1 + 2 + 3 = 6
```

Por isso, as taxas de pacotes e bytes também ficam infladas. O tamanho médio
pode continuar aparentemente correto: se o total de bytes e o de pacotes são
inflados na mesma proporção, a divisão entre eles ainda resulta em 54 bytes.

Esta é uma reprodução do defeito para uma entrada controlada. Não comprova a
correção do sistema nem valida outros aspectos, como concorrência, saturação do
mapa, múltiplos fluxos ou perdas de eventos.

### Como reproduzir

O procedimento completo, com comandos para copiar e indicação dos terminais,
está em [01-contagem.md](../../testes/diagnostico/01-contagem.md).

O fechamento atual depende de novos eventos. Se o segundo pacote chegar antes
do limite de cinco segundos e o terceiro depois, a janela pode reproduzir
`SYN:6`. Se os eventos caírem em outras janelas, é necessário considerar essa
distribuição antes de interpretar o resultado. Os números exatos de pacotes/s
e bytes/s variam conforme os intervalos reais; não são o critério de aprovação.

### O que esperar depois da correção

Repita a mesma entrada após corrigir a agregação. O total deve corresponder aos
três pacotes e três SYNs efetivamente recebidos. Se o fechamento periódico também
for corrigido, os pacotes podem se distribuir entre janelas: nesse caso, some
as janelas relevantes, incluindo a última.

**A versão corrigida ainda não foi avaliada neste diagnóstico.** A evidência
atual demonstra o erro e serve como referência para a comparação antes/depois.


## 16. Diagnóstico 02 — fechamento da janela durante uma pausa

### Objetivo e procedimento

Verificar se o monitor fecha uma janela quando passam cinco segundos, mesmo
sem receber novos pacotes. Uma janela é o período de tráfego que o programa
reúne para calcular suas características e, posteriormente, classificá-lo.

A equipe executou uma observação de 60 segundos no modo `collection-current`,
sem daemon ML. O gerador enviou dois pacotes SYN do mesmo fluxo, com origem
simulada `192.168.157.101:12345` e destino `192.168.157.20:80`. Cada chamada do
hping3 reportou exatamente um pacote transmitido.

Entre os envios, foi feita uma inspeção do log: cerca de 15,7 segundos após o
primeiro envio, ainda não aparecia nenhuma janela fechada. O segundo envio
ocorreu cerca de 33,3 segundos após o primeiro. Ambos ficaram dentro da
observação. Ao final, o monitor apresentou uma janela.

### Resultado observado

```text
Janela fechada — src: 192.168.157.101
Flow Packets/s   : 0.09
Flow Bytes/s     : 4.87
Packet Len Mean  : 54.00 bytes
Min Packet Len   : 54 bytes
TCP Flags        : SYN:3 ACK:0 RST:0 URG:0 CWR:0
[AVISO] ml_daemon.py não está rodando — sem classificação.
```

### Problema demonstrado e suas consequências

**O prazo de cinco segundos não provoca sozinho o fechamento da janela.**
O log durante a pausa estava sem resultados; uma janela apareceu no log final
após o segundo envio. Esse comportamento é consistente com o código de
`window_update`, em `xdp-flow-monitor-main/window.c`: a verificação do tempo
ocorre quando um novo evento é processado, sem um fechamento periódico
independente da chegada de pacotes.

Em termos simples, o programa espera alguém tocar a campainha novamente para
conferir se já passou da hora de terminar a contagem. Se o tráfego parar, as
informações podem ficar pendentes. Isso pode atrasar a classificação posterior
e fazer com que tráfego curto não apareça no resultado antes do encerramento.
Este teste não mediu o atraso da inferência nem do bloqueio: o ML estava desligado.

A rodada também reforçou o defeito do diagnóstico 01: para dois SYNs enviados,
o monitor informou três. O resultado é compatível com somar os snapshots
acumulados `1 + 2`, em vez de contar apenas os dois pacotes novos. As taxas
exportadas ficam afetadas tanto pela contagem incorreta quanto pela duração
real da janela; seus valores exatos não devem ser usados como resultado esperado
em outra execução.

A evidência demonstra o comportamento nesta rodada controlada. Não é uma
medição exata do instante de fechamento, pois o log final não contém esse
instante; a inspeção intermediária e os registros dos envios delimitam a
sequência observada. A ausência do daemon ML é esperada e não invalida o teste.

### Como reproduzir

O [roteiro 02 — janela](../../testes/diagnostico/02-janela.md) contém os blocos
completos para copiar, sem precisar preencher caminhos de resultados.

### O que esperar depois da correção

Na implementação avaliada, espera-se ausência de janela durante a pausa e uma
janela no log final após o segundo evento. Depois da correção, a primeira janela
deve fechar perto do prazo previsto mesmo sem novo pacote. A contagem também
deve corresponder aos pacotes recebidos, considerando sua distribuição entre
janelas. **A versão corrigida ainda não foi avaliada.**
