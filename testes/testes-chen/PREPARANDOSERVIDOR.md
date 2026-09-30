# Preparar o servidor e os containers (sem VM)

Este roteiro prepara o servidor srv01 com Ubuntu Server 24.04, arquitetura
`x86_64`, para executar o laboratório diretamente com Docker e Containerlab.
Os containers usam Ubuntu 22.04, mas compartilham o **kernel do servidor**.
O eBPF será executado na interface `lab0` dentro do container `target`.

## 1. Acessar o servidor e entrar na pasta do laboratório

No seu computador:

```bash
ssh SEU_USUARIO@IP_DO_SERVIDOR
```

No servidor, com o projeto atualizado:

```bash
cd ~/xdp-flow-monitor/testes/testes-chen
```

Ajuste o caminho se necessário. **Execute todos os comandos `make` abaixo nessa
pasta, no servidor.** Use seu usuário comum com acesso a `sudo`; não use
`sudo make`, pois os alvos já pedem os privilégios necessários.

Se `make` ainda não estiver instalado:

```bash
sudo apt-get update
sudo apt-get install -y make
```

## 2. Conferir o servidor

```bash
make host-check
```

Mostra sistema, arquitetura, kernel, memória, CPUs, espaço em disco e ferramentas
instaladas. A compilação atual espera `x86_64`. Confira os recursos disponíveis
para a imagem, os datasets e os resultados.

## 3. Instalar Docker e Containerlab

```bash
make host-setup
```

Instala as dependências, inicia Docker e instala Containerlab 0.69.3 quando ele
estiver ausente. Preserva instalações existentes de Docker e Containerlab.
Precisa de internet e acesso a `sudo`. Não instala KVM/libvirt nem cria uma VM.
`make clab-setup` é um nome alternativo para a mesma etapa.

## 4. Construir a imagem

```bash
make clab-image
```

Reúne as ferramentas de rede, compiladores, bibliotecas eBPF, ambiente Python e
uma cópia do código, conforme `lab/Dockerfile`. Ainda não inicia os containers.
Essa etapa precisa de internet e pode demorar.

## 5. Criar e iniciar os containers

```bash
make clab-up
```

Prepara automaticamente os diretórios de datasets e resultados, o marcador do
ambiente e as variáveis exigidas pela topologia. Cria:

| Container | Função | Interface | IP de teste |
| --- | --- | --- | --- |
| `clab-chen-generator` | Gerador de tráfego | `lab0` | `192.168.157.10/24` |
| `clab-chen-target` | Vítima e monitor eBPF | `lab0` | `192.168.157.20/24` |

Os containers têm um enlace direto, sem rota padrão nem portas publicadas.
Use esse enlace para o tráfego e anexe o monitor à `lab0` dentro de `target`.
Eles compartilham os recursos e o kernel do servidor.

Há uma instância `chen` por servidor. Se ela já existir, consulte seu estado antes
de repetir o deploy. Se o alvo indicar que `/etc/xdp-chen-lab` pertence a outro
ambiente, confira a origem do arquivo antes de alterá-lo.

## 6. Conferir containers e conectividade

```bash
make clab-status
make clab-check
```

Espere os dois containers em execução, verificações sem erro e respostas ao ping.
O segundo comando confere a rede, a montagem BPF e mostra o suporte do kernel.
Confira na saída do probe o suporte a BPF e ao tipo de programa XDP antes de
iniciar medições.

## 7. Compilar o eBPF dentro de target

Ainda no servidor:

```bash
make clab-build
```

Executa a compilação dentro de `target`: gera o programa eBPF, o skeleton e o
monitor userspace em `/workspace/build`. Não inicia captura nem tráfego.
O carregamento do programa no kernel será validado na etapa de execução.

## 8. Abrir um terminal nos containers

Para entrar na vítima:

```bash
make clab-shell NODE=target
```

Para entrar no gerador, em outra sessão SSH na mesma pasta do servidor:

```bash
make clab-shell NODE=generator
```

Digite `exit` para voltar ao servidor. O terminal já abre na pasta dos alvos
internos, com a identificação do ambiente configurada. Essa pasta ainda se chama
`vm-ubuntu2204` porque reutilizamos seus alvos de compilação e verificação; não
há criação ou acesso a uma VM.

## 9. Registrar o ambiente e localizar resultados

No servidor:

```bash
make host-record
```

Salva informações do sistema, kernel, código, Docker, Containerlab e imagem em
`testes/testes-chen/results-servidor/`. Os dados gravados em `/workspace/results`
pelos containers ficam diretamente nas subpastas `generator/` e `target/` desse
diretório. Não é necessário copiar resultados de uma VM.

Os roteiros [4B](4B-coleta-ebpf.md), [4C](4C-filtragem-xdp.md),
[4D](4D-classificacao.md) e [4E](4E-sistema-completo.md) ainda têm referências ao
fluxo antigo e pendências experimentais. Antes das medições, adapte os registros:
CPU e memória coletadas por `mpstat`/`sar` refletem o servidor compartilhado; o
campo legado `vm-version.txt` dos alvos de testes não identifica este ambiente.
Registre também a concorrência com outros serviços.

## 10. Encerrar ou atualizar o laboratório

Encerre os testes, saia dos shells dos containers e execute no servidor:

```bash
make clab-down
```

Remove os containers e o enlace, preserva os datasets e resultados montados no
servidor e devolve a propriedade dos resultados ao seu usuário. Arquivos somente
internos, como os binários em `/workspace/build`, são perdidos.

Após atualizar o código, com os testes encerrados, execute nesta ordem:

```bash
make clab-down
make clab-image
make clab-up
make clab-check
make clab-build
```

A imagem contém uma cópia do projeto e precisa ser reconstruída para incorporar
alterações. Para consultar os comandos disponíveis, use `make help`.

Os comandos foram revisados localmente; instalação e execução do laboratório
ainda precisam ser validadas no servidor.
