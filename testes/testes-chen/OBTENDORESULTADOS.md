# Trazer os resultados para o PC sem GitHub

Este roteiro usa SSH e rsync para copiar os resultados do servidor para seu PC.
Cada pessoa configura seu próprio acesso uma vez. Não é necessário fazer commit,
push ou pull dos resultados.

## 1. Antes de copiar

Os containers gravam diretamente em `testes/testes-chen/results-servidor/`
no servidor, nas subpastas `generator/` e `target/`. Após encerrar as execuções,
`make clab-down` preserva esses dados e devolve sua propriedade ao usuário.
Não há etapa intermediária de recuperação de uma VM.

**Os próximos passos são feitos no seu PC**, em um terminal Bash, fora da sessão
SSH. O PC precisa ter uma cópia do projeto com os Makefiles, além de `make`,
`rsync` e cliente SSH instalados, e acesso à rede do servidor.

## 2. Salvar sua configuração local

Crie uma pasta de configuração fora do repositório:

```bash
mkdir -p ~/.config/xdp-flow-monitor
```

Abra o arquivo:

```bash
nano ~/.config/xdp-flow-monitor/servidor.conf
```

Coloque estas duas linhas, substituindo os exemplos pelos seus dados:

```bash
export SERVER='SEU_USUARIO@ENDERECO_DO_SERVIDOR'
export SERVER_REPO='/home/SEU_USUARIO/xdp-flow-monitor'
```

- `SERVER`: seu usuário SSH e o endereço do servidor, como você usa para se conectar.
- `SERVER_REPO`: caminho absoluto da raiz do projeto **no servidor**, sem acrescentar
  `testes/testes-chen` ou a pasta de containers. Se tiver dúvida, execute `pwd`
  dentro da raiz do projeto no servidor.

No nano, salve com `Ctrl+O`, confirme com `Enter` e saia com `Ctrl+X`.
Não coloque senhas nem conteúdo de chaves nesse arquivo. A transferência usa
sua autenticação SSH habitual.

O arquivo fica na sua pasta pessoal, **fora do repositório**. Por isso ele não
é versionado pelo Git deste projeto e não precisa de uma regra no `.gitignore`.
Cada pessoa terá seu próprio arquivo no próprio PC.

## 3. Carregar a configuração no terminal

```bash
source ~/.config/xdp-flow-monitor/servidor.conf
```

Isso disponibiliza os dois valores para o Makefile. Repita este comando ao abrir
um novo terminal; não é necessário reescrever o arquivo.

## 4. Baixar os resultados

Entre na pasta do laboratório **no seu PC**, ajustando o caminho:

```bash
cd /CAMINHO/DO/PROJETO/testes/testes-chen
make get-results
```

O comando copia `results-servidor/` do servidor para a mesma pasta relativa no
PC, preservando as subpastas `generator/` e `target/`. Não remove arquivos
exclusivamente locais, mas pode atualizar arquivos de mesmo nome.

## 5. Conferir a cópia

```bash
ls -lhR results-servidor/
```

Confira se os arquivos correspondem à execução desejada. Pastas vazias não
indicam coleta. Os resultados continuam ignorados pelo Git.

Em caso de erro de conexão, confira seu acesso com `ssh "$SERVER"`. Para erros
de caminho, revise `SERVER_REPO` e a existência de `results-servidor/` no servidor.
