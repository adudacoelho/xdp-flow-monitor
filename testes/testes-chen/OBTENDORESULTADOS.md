# Trazer os resultados para o PC sem GitHub

Este roteiro usa SSH e rsync para copiar os resultados do servidor para seu PC.
Cada pessoa configura seu próprio acesso uma vez. Não é necessário fazer commit,
push ou pull dos resultados.

## 1. Antes de copiar

Os resultados precisam ter sido recuperados da VM com `make vm-results`,
executado **no servidor**, na pasta da versão correspondente. Confira se esse
comando terminou sem erro. `get-results` busca os arquivos no servidor, não na VM.

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
  `testes/testes-chen` ou a pasta de uma versão. Se tiver dúvida, execute `pwd`
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

## 4. Baixar os resultados da versão desejada

Para Ubuntu 22.04, entre na pasta correspondente **no seu PC**, ajustando o caminho:

```bash
cd /CAMINHO/DO/PROJETO/testes/testes-chen/vm-ubuntu2204
```

Depois execute:

```bash
make get-results
```

Aguarde terminar sem erro. Para Ubuntu 26.04, use os mesmos comandos na pasta
`vm-ubuntu2604`. A configuração do servidor é a mesma para as duas versões.

Cada comando copia os dados para a pasta `results/` da versão selecionada no PC.
As subpastas `generator/` e `target/` são preservadas. A cópia não remove arquivos
locais que só existam no PC, mas pode atualizar arquivos de mesmo nome.
`RESULTADOS.md` não faz parte dessa transferência.

## 5. Conferir a cópia

Ainda na pasta do Makefile da versão, execute:

```bash
ls -lhR results/
```

Confira se os arquivos correspondem à execução desejada. Pastas vazias ou apenas
`.gitkeep` não indicam que houve coleta. Os dados de `results/` continuam ignorados
pelo Git; `.gitkeep` apenas mantém a estrutura da pasta no repositório.

Se aparecer erro de conexão ou autenticação, confira seu acesso com
`ssh "$SERVER"`. Se aparecer erro de caminho, revise `SERVER_REPO` e confirme
que `vm-results` já foi executado no servidor para aquela versão.
