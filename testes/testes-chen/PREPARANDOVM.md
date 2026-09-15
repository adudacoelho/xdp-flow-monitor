# Preparar a VM Ubuntu 22.04 ou 26.04

Primeiro conclua [a preparação do servidor](PREPARANDOSERVIDOR.md).
Este roteiro atende às duas versões. Os comandos são os mesmos; escolha a
pasta da versão que deseja usar. Os alvos pertencem ao Makefile **da pasta da
versão**, não à pasta deste documento. O lugar de execução é indicado em cada etapa.

<!-- não há envio automático de testes por SSH. -->


## No servidor:

### 1. Acessar pasta com os alvos pra criação da VM:



Escolha **apenas uma** das opções abaixo. A pasta selecionada define a versão ubuntu que a VM utiliza para realizar os testes:

**Ubuntu 22.04:**

```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2204
```




**Ubuntu 26.04:**

```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2604
```

Permaneça na pasta escolhida para executar os próximos comandos.

### 2. Criar VM

```bash
make vm-up
```
`vm-up` cria a VM na primeira execução e a inicia nas próximas. Aguarde o boot;
se `vm-sync` encontrar SSH ainda indisponível, tente novamente depois.

#### Informações da VM

| Recurso | Ubuntu 22.04 | Ubuntu 26.04 |
| --- | --- | --- |
| Pasta | `vm-ubuntu2204/` | `vm-ubuntu2604/` |
| Nome da VM | `chen-ubuntu2204` | `chen-ubuntu2604` |
| IP de gerenciamento | `192.168.158.22` | `192.168.159.26` |
| Nome do usuário | `root` | `root` |
| Recursos | 4 vCPUs, 8 GiB RAM, disco virtual 40 GiB | 4 vCPUs, 8 GiB RAM, disco virtual 40 GiB |

O disco fica no servidor, em `/var/lib/libvirt/images/chen-ubuntu2204/lab.qcow2`
ou `/var/lib/libvirt/images/chen-ubuntu2604/lab.qcow2`, conforme a versão.

### 3. Conferir se a VM está ligada:
```bash
make vm-status
```
vm-status consulta o estado e os recursos da VM

### 4. Copie o Projeto pra VM:

```bash
make vm-sync
```
`vm-sync` copia o projeto **do servidor para a VM**, em
`/root/xdp-flow-monitor`. Não faz pull/push do GitHub. Não copia datasets,
resultados, `.git`, `.lab`, `.venv` ou `build`.


### 5. Entrar na VM:
```bash
make ssh-lab
```

As chaves de acesso às VMs são guardadas em `.lab/`.



## Dentro da VM:

### 1. Acessar pasta do projeto

Depois de `make ssh-lab`, você está dentro da VM. acesse a pasta do projeto de acordo com a versão escolhida:

**Ubuntu 22.04:**

```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2204
```
**Ubuntu 26.04:**
```bash
cd ~/xdp-flow-monitor/testes/testes-chen/vm-ubuntu2604
```

### 2. Instalar Docker e Containerlab na VM.

```bash
make clab-setup
```

### 3. Construir a imagem
```bash
make clab-image
```
Constrói a imagem Docker que será usada pelos containers, reunindo as ferramentas necessárias e uma cópia do código do projeto. Ainda não inicia o laboratório.
### 4. Criar e iniciar o laboratório
```bash
make clab-up
```
cria `generator`, `target` e o enlace de teste isolado.

### 5. Conferir se os containers estão em execução
```bash
make clab-status
```
Consulta o estado dos containers do laboratório. Use para conferir se `generator` e `target` estão em execução.

Os containers das duas VMs são construídos usando o mesmo `lab/Dockerfile`, baseado no Ubuntu 22.04. Eles compartilham o kernel da VM onde são executados: o da VM Ubuntu 22.04 ou 26.04, conforme a versão escolhida. Execute `uname -r` dentro da VM para registrar a versão exata do kernel.


### 6. Abrir um terminal na vítima
```bash
make clab-shell NODE=target
```
**clab-shell** abre um terminal dentro do container escolhido: `NODE=target` para a vítima ou `NODE=generator` para o gerador de tráfego. Digite `exit` para voltar à VM.

## Dentro do container: compilar e executar

O shell aberto por `clab-shell` já começa na pasta da versão escolhida:
`/workspace/testes/testes-chen/vm-ubuntu2204` ou
`/workspace/testes/testes-chen/vm-ubuntu2604`. Não precisa mudar de pasta:

```bash
make check
make build
```

`check` confere o ambiente e a interface. `build` compila o detector original;
não inicia captura. Use os roteiros [4B](4B-coleta-ebpf.md),
[4C](4C-filtragem-xdp.md), [4D](4D-classificacao.md) e
[4E](4E-sistema-completo.md) para os próximos passos, respeitando as pendências.
Abra outros terminais entrando na mesma VM e usando `clab-shell NODE=generator`
ou `NODE=target`. Os alvos `serve`, `traffic`, `observe` e `ml` são executados
nesses containers. Argumentos como `PCAP=dataset/lab.pcap` são relativos a
`/workspace`, não à pasta do Makefile.

## Encerrar o laboratório e copiar resultados ao servidor

### 1. Encerre as medições e saia dos shells dos containers

No terminal do container, volte à VM:
```bash
exit
```

Dentro da VM, encerre o laboratório:
```bash
make clab-down
```

Depois que concluir sem erro, volte ao servidor:
```bash
exit
```

`clab-down` remove containers e conexões, preservando os dados. O `exit` retorna
ao servidor.

### 2. Pegar resultados:
**No servidor**, na pasta desta versão:

```bash
make vm-results
```
`vm-results` copia os dados da VM para a pasta `results/` no servidor.

### 3. Checar salvamento dos resultados
```bash
ls -lhR results/
```
Você deve encontrar as pastas `generator/` e `target/`, com os arquivos das execuções realizadas. Pastas vazias ou apenas `.gitkeep` não confirmam que houve coleta.

### 4. Desligar VM:

Confira se a cópia dos resultados terminou sem erro antes de desligar a VM. Os arquivos permanecem no disco da VM, mas ela precisa estar ligada para recuperá-los.


```bash
make vm-stop
```

`vm-stop` desliga somente esta VM, sem apagar discos. `RESULTADOS.md` fica fora
das transferências. Os dados são separados por container e por execução.

Para copiar os resultados do servidor para seu PC, siga
[Obter resultados](OBTENDORESULTADOS.md).

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
