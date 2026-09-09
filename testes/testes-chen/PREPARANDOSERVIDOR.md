# Preparar o servidor (host)

Este roteiro prepara o servidor Ubuntu Server 24.04 para hospedar as VMs do
laboratório. A criação de cada VM está no documento específico da sua versão.

## 1. Acessar o servidor e localizar o projeto

No seu computador, entre no servidor substituindo os campos abaixo:

```bash
ssh SEU_USUARIO@IP_DO_SERVIDOR
```

**Os próximos comandos são executados no servidor**, usando seu usuário comum
com acesso a `sudo`. A pasta do projeto deve conter o Makefile atualizado e os
arquivos do repositório. O projeto fica em `~/xdp-flow-monitor`; o Makefile do servidor fica em
`testes/testes-chen/`:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
ls Makefile
```

Se a pasta ainda não estiver no servidor, copie o projeto antes de continuar.
Não use `sudo make`: os alvos já usam `sudo` nos comandos que precisam dele.

Caso o comando `make` não esteja instalado:

```bash
sudo apt-get -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources -o Dir::Etc::sourceparts=- update
sudo apt-get -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources -o Dir::Etc::sourceparts=- install -y make
```

## 2. Conferir os recursos disponíveis

```bash
make host-check
```

Esse comando mostra arquitetura, memória, quantidade de CPUs, disponibilidade
de `/dev/kvm` e ferramentas de virtualização já instaladas.

Confira a memória e o espaço em disco disponíveis para hospedar os laboratórios.
A arquitetura esperada é `x86_64`.

Ferramentas ausentes serão instaladas no próximo passo. Se aparecer
`KVM ausente`, confira novamente após a instalação; se continuar ausente,
será necessário verificar o suporte/habilitação de virtualização antes de criar a VM.

## 3. Instalar a infraestrutura de virtualização

Execute:

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
cd ~/xdp-flow-monitor/testes/testes-chen
make host-check
```

## Próxima etapa

Siga a preparação da versão desejada:

- [VM Ubuntu 22.04](vm-ubuntu2204/PREPARANDOVM.md)
- [VM Ubuntu 26.04](vm-ubuntu2604/PREPARANDOVM.md)
