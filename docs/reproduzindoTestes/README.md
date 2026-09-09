# Reprodução com Containerlab dentro de uma VM

O servidor Ubuntu Server 26.04 hospeda uma VM Ubuntu 22.04 com KVM/libvirt.
**Containerlab cria e conecta os containers que executam os testes dentro dela.**
A VM preserva a separação do kernel do servidor pedida para este laboratório.
Containers Linux compartilham o kernel da VM: não são duas máquinas independentes.

```text
Servidor Ubuntu 26.04
└── VM lab (Ubuntu 22.04, Docker + Containerlab)
    ├── generator 192.168.157.10 ── lab0 / veth ── target 192.168.157.20
    └── gerenciamento SSH da VM: 192.168.156.20
```

Os dois containers usam `network-mode: none`, sem interface de gerenciamento,
portas publicadas ou rota padrão. Containerlab adiciona apenas o enlace de teste.
O XDP é anexado em `lab0` **dentro do container target**, no ingresso da vítima.
O acesso aos containers é por `docker exec`, encapsulado pelo Makefile.

É uma **reprodução adaptada**. O artigo usa seis máquinas, Kubernetes,
DeathStarBench e CIC-DDoS2019 estendido. Esta topologia inicial tem dois containers,
sem Kubernetes/DeathStarBench. O kernel efetivo é o da VM e o detector ainda tem
os [problemas documentados](../ProblemasPendentes/relatorio.md).

## 1. Preparar a VM no servidor

Planejamento inicial: 4 vCPUs, 8 GiB RAM e disco virtual 40 GiB, além de recursos
livres para o host, dados e logs. Gerador e vítima disputarão esses recursos.
Use servidor x86-64 com VT-x/AMD-V habilitado e `/dev/kvm` disponível.

No servidor, por SSH:

```bash
sudo apt update
sudo apt install -y make python3 git rsync
```

Copie esta versão do repositório do PC para o servidor (substitua os nomes):

```bash
rsync -az --exclude=.git --exclude=.lab --exclude=.venv --exclude=results \
  ./ USUARIO@SERVIDOR:~/xdp-flow-monitor/
```

Se o diretório de destino ainda não tem Git, inicialize-o apenas nessa cópia:

```bash
cd ~/xdp-flow-monitor
git init -b elisa
git add .
git -c user.name=Elisa -c user.email=elisa@localhost commit -m 'Cópia do laboratório'
```

Se já clonou a branch `elisa` contendo os arquivos novos, pule a inicialização.
Dentro do repositório, no servidor:

```bash
make host-check
make host-setup
# Saia do SSH e entre novamente para aplicar os grupos libvirt/kvm.
make host-check
make vm-up
# Aguarde o boot; repita vm-sync se o SSH ainda não estiver pronto.
make vm-sync
make vm-status
make ssh-lab
```

O host recebe apenas virtualização/gerenciamento. Docker, Containerlab e os
programas experimentais ficam na VM. `vm-up` cria a VM `xdp-chen-lab-lab` e uma
rede NAT de gerenciamento; não liga a rede dos ataques à interface física.
Preserve `.lab/`, que contém a chave SSH e os arquivos da imagem/cloud-init.
Se tiver criado as duas VMs do roteiro anterior, desligue-as antes; este roteiro
não as remove nem reutiliza seus discos automaticamente.

## 2. Preparar e abrir o Containerlab

Dentro da VM, após `make ssh-lab`:

```bash
cd ~/xdp-flow-monitor
make clab-setup     # Docker e Containerlab 0.69.3 na VM
make clab-image     # constrói chen-lab:local com as ferramentas
make clab-up        # cria generator, target e o enlace veth
make clab-status
make clab-shell NODE=target
```

Dentro do container target, o shell começa em `/workspace`:

```bash
make check
make build
```

Abra outro terminal no servidor, entre na mesma VM (`make ssh-lab`), entre no
repositório e use `make clab-shell NODE=generator`. Execute `make check` também.
As ferramentas já vêm na imagem: não instale pacotes nos containers isolados.
O build gera BPF e skeleton novos usando os fontes de `xdp-flow-monitor-main`.

`lab/topology.clab.yml` define os nós e o enlace; `lab/Dockerfile` define as
ferramentas. `dataset/` da VM é montado somente para leitura. Resultados de cada
nó ficam em `results/generator/` e `results/target/` na VM, sobrevivendo ao destroy.
Para atualizar código: encerre os testes, `make clab-down` na VM, `make vm-sync`
no servidor e depois `make clab-image`, `make clab-up` e `make build` na target.
Não use `clab-down` enquanto houver medição em andamento.

## 3. Convenção para todas as execuções

Use até quatro shells dos containers: target/serviço, target/observação,
generator/carga e generator/tráfego legítimo simultâneo. Na VM, abra cada shell
com `make clab-shell NODE=target` ou `make clab-shell NODE=generator`.
Os shells já começam em `/workspace`. Os comandos das seções seguintes rodam
**nesses containers**, não diretamente na VM nem no servidor.

`observe` imprime **PRONTO** depois de iniciar o comparador. Só então inicie a
carga. A observação dura um pouco mais que a carga; analise apenas o intervalo
de carga, usando os horários registrados. Não inclua espera manual na média de 120 s.
Os serviços/cargas têm limite de 600 s por chamada; Ctrl+C encerra os processos
da chamada e remove as regras/programa estático que ela criou.

Cada chamada cria `results/<instante>-<papel>-<ação>-<RUN>/`, sem sobrescrever:
`metadata.json`, `status.json`, versões, logs e, quando aplicável, `resources.csv`.
As cargas concluídas gravam `load-window.json` com início/fim em UTC. Os
containers usam o mesmo relógio da VM.
**CPU e memória são agregadas da VM compartilhada**, não de cada container.
O coletor lê `/proc/stat` e `/proc/meminfo`; ambas as leituras incluem gerador,
vítima e Docker. CPU é normalizada de 0 a 100%; memória é
`MemTotal - MemAvailable` em KiB. São definições desta reprodução. RX/TX são
contadores cumulativos da interface, não throughput útil nem contadores universais
de descarte XDP. Throughput útil vem do receptor iperf3 (`end.sum_received`).
`cpu_busy_pct` inclui steal; `cpu_steal_pct` é salvo separadamente para detectar
disputa por tempo de CPU no hipervisor. Não confunda essa métrica com CPU do processo. Para comparar
custo isolado da vítima, ainda precisamos acrescentar instrumentação por cgroup
e contabilizar separadamente o trabalho de rede/kernel. Este arranjo não reproduz
o isolamento de recursos de máquinas distintas do artigo.

Comece com 10 s e baixa carga. Depois faça pelo menos cinco repetições por condição,
alternando a ordem dos comparadores, com um aquecimento separado de 10 s.
Essas repetições/aquecimento são escolhas nossas, não parâmetros publicados.

## 4. Fig. 5 — custo da coleta (seção IV-B)

### Throughput TCP

1. Target/serviço: `make serve SERVICE=iperf DURATION=600 RUN=fig5-server`.
2. Target/observação: `make observe MODE=baseline DURATION=70 RUN=fig5-base-r1`.
3. Depois de PRONTO, generator: `make traffic KIND=tcp DURATION=50 RUN=fig5-base-r1`.
4. Repita passos 2–3 com `MODE=tshark` e, separadamente, `MODE=collection-current`.
5. Para observar 200 s com intervalos de 50 s, use carga de 200 s e observação
   de 220 s; agregue os intervalos de 1 s do JSON iperf3 em quatro blocos de 50 s.

TShark é a variante sem GUI do comparador, com análise textual gravada em log;
não é uma medição da aplicação gráfica Wireshark do artigo. Seu custo de saída
e disco faz parte desta configuração e deve ser declarado. `collection-current`
executa o coletor existente sem daemon ML: há exportação por pacote e logging,
portanto ainda **não representa a coleta corrigida do artigo**.

### CPU e memória sob SYN flood

1. Mantenha o serviço iperf ativo na porta 80 da target.
2. Target: `make observe MODE=baseline DURATION=140 RUN=fig5-syn-base-r1`.
3. Generator: `make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig5-syn-base-r1`.
4. Repita para `tshark` e `collection-current`, conservando duração e carga.
5. Calibre cargas maiores usando as taxas **observadas** no gerador e receptor.

O artigo informa aproximadamente **1,92 Gbps**, não uma opção de hping3 que
garanta essa taxa. Nosso PPS controla o intervalo solicitado ao hping3; seis
processos usam IPs de origem 192.168.157.101–106. O gerador pode não alcançar a
taxa pedida. Não declare 1,92 Gbps sem medi-la; informe também o tamanho dos
pacotes e a camada da contagem de bytes. Não substitua silenciosamente o teste
por UDP iperf3 ou suponha que `--flood` equivale à carga publicada.

### Latência TCP com Ethr

1. Encerre o serviço iperf (Ctrl+C): ambos usam a porta 80 para passar pelo
   filtro TCP do monitor atual.
2. Target/serviço: `make serve SERVICE=ethr DURATION=600 RUN=fig5-lat-server`.
3. Target: `make observe MODE=baseline DURATION=140 RUN=fig5-lat-base-r1`.
4. Generator: `make traffic KIND=latency DURATION=120 RUN=fig5-lat-base-r1`.
5. Repita observação/carga com `tshark` e `collection-current`. Guarde os logs
   Ethr; reporte média e percentis disponíveis. Não use ping ICMP como substituto.

## 5. Fig. 6 — XDP versus iptables (seção IV-C)

O laboratório fornece `scripts/lab/filter.bpf.c`: filtragem estática por LPM
separada do detector, sem ML ou coleta. Use XDP nativo (`xdpdrv`); não há fallback
silencioso para modo genérico. O comparador é `iptables-legacy` com regras lineares.

1. Target/serviço: `make serve SERVICE=iperf DURATION=600 RUN=fig6-server`.
2. Target: `make observe MODE=xdp RULES=16 DURATION=70 RUN=fig6-xdp-16-tcp-r1`.
3. Generator: `make traffic KIND=tcp DURATION=50 RUN=fig6-xdp-16-tcp-r1`.
4. Repita com `MODE=iptables` e depois com **16, 32, 64, 128, 256 e 512 regras**
   (pontos identificados na Fig. 6). Cada observação remove suas regras ao terminar.
5. Em rodadas separadas de CPU/memória, use observação de 140 s e
   `make traffic KIND=syn PPS=5000 DURATION=120 RUN=fig6-syn-r1`; calibre a carga
   conforme a seção anterior e repita todos os números de regras/comparadores.

As seis origens simuladas estão no final da lista e são bloqueadas. O IP real
192.168.157.10 fica permitido para throughput legítimo. As demais regras usam
198.18.0.0/15 como preenchimento, sem gerar tráfego para essa rede. `rules.json`
registra a ordem; prefixos são /32 em ambos os casos. É uma escolha controlada
da reprodução, pois a distribuição/ordem completa das regras não é especificada.
Não compare throughput de pacotes descartados com throughput útil do iperf3.

Antes da série, faça uma rodada curta de SYN e confira contadores de iptables
e ausência do tráfego bloqueado na captura da target sob XDP. Uma captura extra
serve à validação funcional; encerre-a antes de medir desempenho.

## 6. Fig. 7 — classificação (seção IV-D)

1. Obtenha os CSVs reais do CIC-DDoS2019 e registre origem, licença, hashes e
   limpeza. A extensão com ataques de aplicação usada pelos autores não está
   fornecida neste repositório. Dados sintéticos servem apenas a teste funcional.
2. Separe treino e teste por captura/dia antes de ajustar modelos. Remova vazamento
   entre partições; não selecione parâmetros usando o conjunto de teste.
3. Copie `train.csv` e `test.csv` para `~/xdp-flow-monitor/dataset/` **na VM**;
   o diretório aparece como `/workspace/dataset/` nos containers, somente leitura.
4. Confira a unidade de `Flow Duration` e execute na target:

```bash
make ml TRAIN=dataset/train.csv TEST=dataset/test.csv DURATION_UNIT=us
```

O executor recusa labels ausentes, NaN/Inf, uma única classe e vetores idênticos
entre partições. Não faz limpeza silenciosa. Troque `us` por `s` somente se a
fonte já estiver em segundos. Grandes CSVs precisam caber na RAM da VM.

Saída: métricas e matriz de confusão para **XGBoost, LR, GB, RF, KNN, DT e MLP**,
com seed e parâmetros registrados. Acurácia, precisão, recall e F1 usam ataque
como positivo. Detecção de normais = TN/(TN+FP); de ataques = TP/(TP+FN).
Isso explicita a interpretação da definição ambígua de “undetected” no texto.

**Comparação parcial:** a figura também contém GRU, LSTM, CRNN e RNN; suas
arquiteturas/treinamento precisam ser definidos e implementados antes de afirmar
reprodução de todos os modelos. Os hiperparâmetros fornecidos são nossos. Este
executor não substitui o modelo do daemon: a integração depende do contrato de
features e das correções. O treino antigo do README não valida a Fig. 7.

## 7. Tabela II — replay e tempos por etapa (seção IV-E)

1. Obtenha um PCAP real, selecione somente o sentido atacante → vítima e
   preserve o original. Não transforme o tráfego de retorno em ataque.
2. Na generator, converta a cópia selecionada em PCAP clássico Ethernet/IPv4
   (sem VLAN), e reescreva endereços/MACs para o laboratório:

```bash
editcap -F pcap dataset/attack-only.pcapng results/attack-only.pcap
tcprewrite --infile=results/attack-only.pcap --outfile=results/lab.pcap \
  --srcipmap=0.0.0.0/0:192.168.157.101/32 \
  --dstipmap=0.0.0.0/0:192.168.157.20/32 \
  --enet-smac=52:54:00:ce:02:10 --enet-dmac=52:54:00:ce:02:20 --fixcsum
```

3. Target: `make observe MODE=collection-current DURATION=140 RUN=table2-r1`.
4. Generator:

```bash
make traffic KIND=replay PCAP=results/lab.pcap PPS=180163 DURATION=120 RUN=table2-r1
```

O executor valida os endereços antes de enviar; guarde estatísticas do tcpreplay
e checksum do PCAP original e reescrito. A cópia converte origens para um IP e
altera a diversidade de fluxos: declare essa adaptação; não use seu resultado
como avaliação da diversidade original. Repita com as etapas relevantes após
corrigir/instrumentar o sistema.

**Pendente:** replay pronto não mede tempos individuais. Para reproduzir a
Tabela II ainda precisamos instrumentar coleta, inferência e filtragem,
definir início/fim de cada medição, medir overhead e salvar amostras. Inferência
por janela não é tempo por pacote. Não dividir 120 s pelo número de pacotes
nem tratar o inverso de 180.163 pps como latência de processamento. Referências
publicadas: 12,68 µs (eBPF), 11,96 µs (XGBoost), 5,72 µs (XDP).

## 8. Fig. 8 — sistema completo versus Snort (seção IV-E)

1. Target/serviço: inicie iperf como antes.
2. Target: `make observe MODE=snort DURATION=150 RUN=fig8-snort-5000-r1`.
3. Generator/carga: `make traffic KIND=udp PPS=5000 DURATION=120 RUN=fig8-snort-5000-r1`.
4. Em outro terminal generator, durante a mesma carga, execute
   `make traffic KIND=tcp DURATION=110 RUN=fig8-snort-5000-tcp-r1`.
5. Repita usando `MODE=baseline` e `MODE=detector-current`.
6. Repita para **5.000, 10.000, 50.000, 100.000 e 150.000 pps** (Fig. 8),
   sempre registrando a taxa realmente alcançada, e faça as cinco repetições.

Para permitir tráfego TCP legítimo simultâneo ao UDP, cada tipo de carga usa um
lock próprio. As janelas de medição são diferentes: CPU/memória durante os 120 s
de ataque e throughput durante os 110 s sobrepostos. Isso é uma adaptação explícita;
sincronização automática de 120 s para todas as métricas ainda não foi implementada.

`snort.conf` usa a regra de UDP da Tabela III com limiar de 100 eventos em 10 s
por origem, SID 1000003. `EXTERNAL_NET` foi definido como a vítima para a regra
disparar neste laboratório. A ação é **alert**, não bloqueio. `snort -T` valida
a configuração antes de observar. O pacote instalado é Snort 2, não Snort 3.

`detector-current` inicia o daemon e o monitor sem mudar seu código ou modelo.
Os bugs de contagem e procedência do modelo impedem usar essa rodada como
reprodução válida da detecção. Após as correções, valide bloqueio, falsos positivos,
continuidade do tráfego legítimo e latência até bloquear, antes da série completa.

## 9. Recuperar resultados e encerrar

Encerre as chamadas com Ctrl+C ou aguarde seus prazos. Saia dos shells e,
**na VM**, execute `make clab-down`. Isso remove apenas a topologia `chen`,
preserva os resultados em disco e ajusta sua propriedade. Depois, no host:

```bash
make vm-results
make vm-stop
```

Isso copia os resultados para `results/lab/generator` e `results/lab/target`
no host e solicita o desligamento da VM sem excluir o disco. Copie essa pasta ao PC.
Não misture `status=failed` com rodadas válidas; preserve falhas para diagnóstico.
Reporte médias, dispersão, carga alcançada e adaptações, nunca números do artigo
como se fossem medidos aqui. Não há gráficos automáticos nesta entrega.

## 10. Quando algo falhar

| Mensagem/situação | Próximo passo |
| --- | --- |
| `/dev/kvm` ausente | Verificar virtualização no BIOS ou suporte aninhado; não fazer fallback para emulação em benchmarks |
| Permissão no libvirt | Reentrar no SSH após host-setup e verificar `id`/`virsh -c qemu:///system list` |
| SSH da VM recusado | Aguardar boot; verificar `make vm-status` e console com `virsh -c qemu:///system console xdp-chen-lab-lab` |
| Sub-rede já utilizada | Ajustar endereçamento nos scripts antes de criar redes; não remover a rede existente |
| Pacote do kernel não encontrado | Na VM, atualizar índices e verificar kernel instalado; registrar mudanças e reiniciar antes dos testes |
| XDP nativo não suportado | Registrar driver/kernel e revisar suporte XDP da veth; não comparar modo genérico sem declarar a mudança |
| Pin/socket/regra já existe após falha abrupta | Destruir/recriar a topologia dentro da VM antes de nova rodada; não limpar firewall/BPF do host |
| CPU steal alto, swap ou PPS baixo | Reduzir carga, reservar recursos e verificar concorrência no host; a VM não garante isolamento de desempenho |

## Referências e estado da validação

Fonte experimental: PDF fornecido, Chen et al., TrustCom 2024,
DOI 10.1109/TrustCom63139.2024.00258, seções IV-B a IV-E, Figuras 5–8 e Tabelas II–III.

Topologia baseada na [documentação de nós Linux do Containerlab](https://containerlab.dev/manual/kinds/linux/)
e no [modo de rede](https://containerlab.dev/manual/network/). Containerlab é instalado
na versão 0.69.3; a imagem Docker registra suas dependências no build.
Infraestrutura baseada na [documentação Ubuntu de libvirt](https://ubuntu.com/server/docs/how-to/virtualisation/libvirt/)
e em [imagens cloud com libvirt](https://ubuntu.com/docs/public-images/public-images-how-to/launch-with-libvirt/).
O isolamento da rede segue o [formato XML do libvirt](https://libvirt.org/formatnetwork.html).
Parâmetros de carga: [iperf3](https://iperf.fr/iperf-doc.php),
[Ethr](https://github.com/microsoft/ethr), [tcpreplay](https://tcpreplay.appneta.com/reference/man/tcpreplay/).
Versão do comparador: [Snort no Ubuntu 22.04](https://packages.ubuntu.com/jammy/snort).

Validação local: oito testes de guardas/PCAP passaram; scripts Python e YAML
foram verificados; BPF, skeleton e userspace compilaram em diretório temporário
na etapa anterior (o detector não foi alterado),
sem carregar programas no kernel ou gerar tráfego. `make selfcheck` repete os
testes unitários sem privilégios; não executa os experimentos do artigo.

Os arquivos foram preparados e verificados localmente; build da imagem Docker,
criação da VM, deploy do Containerlab e instalação
e benchmarks ainda precisam ser validados no servidor. Não houve acesso remoto
nem execução de tráfego durante a elaboração deste roteiro.
