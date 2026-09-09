# Preparar a VM Ubuntu 26.04

Primeiro conclua [a preparação do servidor](../PREPARANDOSERVIDOR.md).
Todos os alvos abaixo pertencem ao Makefile **desta pasta**. O lugar de execução
é indicado em cada etapa; não há envio automático de testes por SSH.

## 1. No servidor: criar e acessar a VM

```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2604
make vm-up
make vm-status
make vm-sync
make ssh-lab
```

`vm-up` cria a VM na primeira execução e a inicia nas próximas. Aguarde o boot;
se `vm-sync` encontrar SSH ainda indisponível, tente novamente depois.

| Recurso | Valor |
| --- | --- |
| VM | `chen-ubuntu2604` |
| IP de gerenciamento | `192.168.159.26` |
| Usuário SSH | `ubuntu` |
| Recursos | 4 vCPUs, 8 GiB RAM, disco virtual 40 GiB |
| Chave e arquivos de preparação | `.lab/` nesta pasta do servidor |
| Disco | `/var/lib/libvirt/images/chen-ubuntu2604/lab.qcow2` |

`vm-sync` copia o projeto **do servidor para a VM**, em
`/home/ubuntu/xdp-flow-monitor`. Não faz pull/push do GitHub. Não copia datasets,
resultados, `.git`, `.lab`, `.venv` ou `build`. Preserve `.lab/`: ela contém sua
chave de acesso. Este ambiente usa recursos novos e não altera a VM antiga
`xdp-chen-lab-lab`, se ela já existir.

## 2. Dentro da VM: preparar Containerlab

Depois de `make ssh-lab`, você está dentro da VM:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2604
make clab-setup
make clab-image
make clab-up
make clab-status
make clab-shell NODE=target
```

- `clab-setup`: instala Docker e Containerlab na VM.
- `clab-image`: constrói a imagem com ferramentas e código do projeto.
- `clab-up`: cria `generator`, `target` e o enlace de teste isolado.
- `clab-status`: mostra os containers.
- `clab-shell`: entra no container escolhido.

Ambas as VMs usam a **mesma imagem Ubuntu 22.04 dos containers**, definida em
`lab/Dockerfile`. O kernel usado pelo eBPF é o da VM Ubuntu 26.04.
Registre o kernel efetivo com `uname -r`; ele não é fixado ao kernel do artigo.
A imagem da VM vem da [distribuição oficial Ubuntu](https://cloud-images.ubuntu.com/releases/26.04/release/).

## 3. Dentro do container: compilar e executar

O shell aberto por `clab-shell` já começa em
`/workspace/testes/testes-chen/vm-ubuntu2604`:

```bash
make check
make build
```

`check` confere o ambiente e a interface. `build` compila o detector original;
não inicia captura. Use os roteiros [4B](../4B-coleta-ebpf.md),
[4C](../4C-filtragem-xdp.md), [4D](../4D-classificacao.md) e
[4E](../4E-sistema-completo.md) para os próximos passos, respeitando as pendências.
Abra outros terminais entrando na mesma VM e usando `clab-shell NODE=generator`
ou `NODE=target`. Os alvos `serve`, `traffic`, `observe` e `ml` são executados
nesses containers. Argumentos como `PCAP=dataset/lab.pcap` são relativos a
`/workspace`, não à pasta do Makefile.

## 4. Encerrar o laboratório e copiar resultados ao servidor

Encerre as medições e saia dos shells dos containers com `exit`. **Dentro da VM**,
na pasta desta versão:

```bash
make clab-down
exit
```

`clab-down` remove containers e conexões, preservando os dados. O `exit` retorna
ao servidor. **No servidor**, na pasta desta versão:

```bash
make vm-results
make vm-stop
```

`vm-results` copia os dados da VM para `results/` nesta pasta do servidor.
`vm-stop` desliga somente esta VM, sem apagar discos. `RESULTADOS.md` fica fora
das transferências. Os dados são separados por container e por execução.

## 5. No PC: trazer os resultados sem GitHub

```bash
cd /CAMINHO/DO/PROJETO/testes/testes-chen/vm-ubuntu2604
make get-results SERVER=elisa.jesus@srv01-gpro-r6615 SERVER_REPO=/home/elisa.jesus/xdp-flow-monitor
```

Ajuste os caminhos e o endereço SSH. `SERVER_REPO` é o caminho **absoluto no
servidor**, não no PC. O alvo copia servidor → `results/` local desta versão,
sem apagar arquivos locais e sem fazer commits. Use sua autenticação SSH habitual.
O `.gitkeep` permanece versionável; os dados brutos continuam ignorados pelo Git.

## Atualizações e execução simultânea

Após atualizar o repositório no servidor, execute `vm-sync`. Com as medições
encerradas, dentro da VM execute `clab-down`, `clab-image` e `clab-up`; depois
compile novamente no container target. A imagem dos containers contém uma cópia
do código e não muda automaticamente com `vm-sync`.

Você pode manter as duas VMs ligadas: nomes, redes, IPs, discos, chaves e destinos
de resultados são distintos. Elas ainda disputam recursos físicos; para comparar
performance, registre a concorrência ou execute as medições uma VM por vez.

Os comandos foram preparados e verificados localmente, mas criação, instalação
e execução deste ambiente ainda precisam ser validadas no servidor.
