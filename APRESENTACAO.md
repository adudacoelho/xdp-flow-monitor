# Demonstração visual — tráfego, classificação e blacklist

Execute todos os comandos na **raiz do projeto no servidor**, fora dos containers.
O roteiro usa o modelo real: não força respostas de ataque ou normal. Ensaie antes.

## Preparação antes da aula

O laboratório deve estar preparado conforme
[PREPARANDOSERVIDOR.md](testes/testes-chen/PREPARANDOSERVIDOR.md).
Abra quatro terminais SSH e entre na raiz do projeto em cada um:

```bash
cd ~/xdp-flow-monitor
```

**Atenção à versão:** o detector fica dentro da imagem, não montado da raiz do
servidor. Se atualizou o detector, o modelo ou arquivos internos, atualize a
imagem e recrie o laboratório pelo roteiro de preparação antes do ensaio.
`demo-check` compila os fontes existentes no container; não copia fontes novos.
O Makefile da raiz e `scripts/demo_screen.py` rodam diretamente no servidor.

No terminal 1:

```bash
make demo-check
```

Não prossiga se houver erro. O modo detector exige o modelo
`xdp-flow-monitor-main/ddos_model.ubj` e o ambiente Python da imagem.

## Projetor: fonte grande e pouca informação

- Projete somente o terminal do painel, em tela cheia; os outros ficam em abas.
- Aumente a fonte no menu do terminal ou com Ctrl + Shift + +, conforme o aplicativo.
  Comece com 24–32 pontos e confira a leitura do fundo da sala.
- Mantenha pelo menos 64 colunas e cerca de 36 linhas para até sete origens.
  Ajuste fonte/resolução para não cortar as últimas linhas.
- O painel usa texto e barras; nenhuma informação depende de cores.

## 1. Serviço — terminal 1

```bash
make demo-server
```

O serviço iperf fica ativo por até 600 segundos. Deixe este terminal aberto.

## 2. Detector e modelo — terminal 2

```bash
make demo-detector RUN=demo-r1
```

**Espere PRONTO.** A observação dura 180 segundos a partir desse aviso.
Esse comando inicia monitor e XGBoost. `demo-monitor` continua sendo apenas
coleta, sem iniciar o modelo, e não é o comando deste roteiro.

## 3. Painel projetado — terminal 4

```bash
make demo-screen RUN=demo-r1
```

O painel lê os logs a cada segundo. As janelas chegam aproximadamente a cada
cinco segundos quando existe tráfego para exportar.

Fala: **“Vamos acompanhar o volume por origem e a decisão real do modelo.”**

## 4. Tráfego de referência — terminal 3

```bash
make demo-normal
```

TCP de `192.168.157.10`, limitado a 1 Mbit/s solicitado, por 60 segundos.
Aguarde as janelas no painel. A classificação não é garantida: se o modelo
bloquear essa origem, o iperf pode falhar ou terminar por timeout. No ensaio,
preserve os logs e investigue esse possível falso positivo.

Fala: **“Esta origem faz uma transferência com taxa limitada.”**

## 5. Carga simulada — terminal 3

Depois de terminar o comando anterior:

```bash
make demo-attack RUN=demo-r1
```

Carga SYN por 20 segundos, 600 pacotes/s solicitados **no total**, distribuídos
entre seis IPs simulados: `192.168.157.101` a `.106`. São origens simuladas por
um gerador, não seis máquinas independentes. A carga usa apenas o enlace
isolado do laboratório; a taxa observada pode diferir da solicitada.

O painel mostra:

- **PACOTES/s:** taxa da última janela exportada de cada origem.
- **MODELO:** a resposta real, NORMAL ou ATAQUE; SEM MODELO indica falha de conexão.
- **BLACKLIST / REGISTRADO:** inserção do IP confirmada pelo log do monitor.

Fala: **“Iniciamos uma carga simulada. Vamos observar se o modelo a identifica
como ataque e se o sistema registra os IPs na blacklist.”**

Se o modelo responder NORMAL, explique que não detectou essa carga na rodada.
Não troque a decisão por um rótulo baseado apenas no volume.

## 6. Conferir acesso depois da carga — terminal 3

Se ainda houver tempo na observação:

```bash
make demo-normal
```

Confira a transferência real no iperf. Isso verifica acesso depois da carga;
não demonstra continuidade simultânea durante o ataque.

## Como interpretar sem tirar conclusões erradas

As barras são relativas à maior taxa exibida. Valores permanecem na tela até
chegar outra janela: não são taxas instantâneas e não zeram ao parar a carga.

O detector consulta a blacklist antes de atualizar estatísticas. Pacotes
bloqueados não geram novas janelas. Portanto, a ausência de janelas não prova
sozinha que o ataque parou ou que houve descarte.

REGISTRADO confirma a inserção reportada pelo monitor, não conta pacotes
descartados. Contadores de descarte exigem instrumentação adicional, que não foi
adicionada ao detector nesta alteração. O painel não valida acurácia ou
reprodução dos resultados de Chen. Falhas do protocolo de comunicação atual
também precisam ser investigadas nos logs.

## Encerrar, repetir e consultar logs

- Aguarde as cargas limitadas por tempo terminarem.
- Ctrl+C no painel encerra apenas a visualização.
- Ctrl+C no terminal 2 encerra a observação; no terminal 1, encerra o serviço.
- Não dependa só de Ctrl+C para parar cargas via Docker: elas têm timeout
  dentro do container (até 75 s no TCP; 20 s mais margem de encerramento no SYN).
- Para repetir, espere o detector e cargas anteriores encerrarem. Use
  `RUN=demo-r2` no detector, painel e carga simulada. Mapas novos são criados
  a cada monitor, incluindo uma blacklist nova.
- O painel escolhe a última pasta da rodada ao abrir. Reabra após reiniciar o
  detector. Reinicie o serviço se tiver terminado.

Para ver mensagens completas:

```bash
make demo-log RUN=demo-r1
```

Resultados: `testes/testes-chen/results-servidor/target/` (monitor.log e ml.log)
e `generator/` (carga simulada). `demo-normal` mostra o iperf no terminal;
salve sua saída ou grave a tela para preservar essa evidência.

**Tenha uma gravação do ensaio e os logs como alternativa para a apresentação.**
