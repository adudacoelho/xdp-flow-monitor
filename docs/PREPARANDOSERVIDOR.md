# Preparar o servidor e entrar na VM

Este roteiro vai da preparação do servidor Ubuntu Server 26.04 até o acesso à
VM Ubuntu 22.04 do laboratório. Containerlab e os testes serão executados dentro
dessa VM; sua configuração fica para a próxima etapa.

## 1. Acessar o servidor e localizar o projeto

No seu computador, entre no servidor substituindo os campos abaixo:

```bash
ssh SEU_USUARIO@IP_DO_SERVIDOR
```

**Os próximos comandos são executados no servidor**, usando seu usuário comum
com acesso a `sudo`. A pasta do projeto deve conter o Makefile atualizado e os
arquivos do repositório. Os exemplos assumem que ela está em `~/xdp-flow-monitor`:

```bash
cd ~/xdp-flow-monitor
ls Makefile
```

Se a pasta ainda não estiver no servidor, copie o projeto antes de continuar.
Não use `sudo make`: os alvos já usam `sudo` nos comandos que precisam dele.

Caso o comando `make` não esteja instalado:

```bash
sudo apt-get update
sudo apt-get install -y make
```

## 2. Conferir os recursos disponíveis

```bash
make host-check
```

Esse comando mostra arquitetura, memória, quantidade de CPUs, disponibilidade
de `/dev/kvm` e ferramentas de virtualização já instaladas.

O Makefile cria uma VM com **4 vCPUs, 8 GiB de RAM e disco virtual de 40 GiB**.
O servidor precisa ter recursos adicionais para seu próprio sistema e espaço
para a imagem, dados e resultados. A arquitetura esperada é `x86_64`.

Ferramentas ausentes serão instaladas no próximo passo. Se aparecer
`KVM ausente`, confira novamente após a instalação; se continuar ausente,
será necessário verificar o suporte/habilitação de virtualização antes de criar a VM.

## 3. Instalar a infraestrutura de virtualização

```bash
make host-setup
```

Esse alvo instala KVM/QEMU, libvirt e as ferramentas de criação e acesso à VM.
Também adiciona seu usuário aos grupos `libvirt` e `kvm`.

Ao terminar, **saia da sessão SSH** para que a próxima sessão receba os grupos:

```bash
exit
```

No seu computador, conecte-se novamente:

```bash
ssh SEU_USUARIO@IP_DO_SERVIDOR
```

De volta ao servidor:

```bash
cd ~/xdp-flow-monitor
make host-check
```

## 4. Criar e iniciar a VM

```bash
make vm-up
```

Na primeira execução, o alvo baixa a imagem Ubuntu 22.04, verifica seu checksum,
gera a chave SSH do laboratório e cria a VM. O download e o primeiro boot podem
levar alguns minutos. Se a VM já existir, o alvo a inicia quando estiver desligada.

Identificação usada pelo Makefile:

| Item | Valor |
| --- | --- |
| Nome da VM | `xdp-chen-lab-lab` |
| IP de gerenciamento | `192.168.156.20` |
| Usuário dentro da VM | `ubuntu` |
| Chave SSH no servidor | `.lab/id_ed25519` |
| Disco da VM | `/var/lib/libvirt/images/xdp-chen-lab/lab.qcow2` |

Preserve a pasta `.lab` do projeto no servidor: ela contém a chave e os arquivos
de preparação. Se houver erro de sub-rede ocupada ou disco já existente, interrompa
esta sequência e examine a mensagem antes de repetir ou remover qualquer recurso.

Confira o estado da VM:

```bash
make vm-status
```

A VM deve estar em execução. Isso não garante que o primeiro boot já terminou.

## 5. Copiar o projeto para dentro da VM

```bash
make vm-sync
```

Esse alvo conecta por SSH, espera a configuração inicial do Ubuntu terminar e
copia o projeto para `/home/ubuntu/xdp-flow-monitor` dentro da VM.
Datasets, resultados, `.git`, `.lab`, `.venv` e `build` ficam fora dessa cópia.

Se ocorrer conexão recusada logo após `vm-up`, aguarde o boot e repita
`make vm-sync`. Continue somente quando o comando terminar sem erro.

## 6. Entrar na VM

Ainda no servidor, dentro da pasta do projeto:

```bash
make ssh-lab
```

**A partir daqui, o terminal está dentro da VM.** Para conferir e entrar na pasta:

```bash
hostname
cd ~/xdp-flow-monitor
```

O hostname esperado é `xdp-chen-lab-lab`. O ambiente está pronto para a próxima
etapa de instalação do Containerlab dentro da VM. Os roteiros individuais dos
testes serão adicionados posteriormente em `docs/testesChen/`.

## Retornar ao servidor e desligar a VM

Para sair da VM e voltar à sessão do servidor:

```bash
exit
```

Quando não houver testes em execução, no servidor:

```bash
make vm-stop
```

Esse comando solicita o desligamento sem apagar o disco. Para voltar em outro
momento, execute `make vm-up` e, após o boot, `make ssh-lab`.
