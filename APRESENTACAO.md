# Demonstração — generator → target → coleta XDP/eBPF

Laboratório já preparado. Abra **4 terminais SSH**. Em cada um:

```bash
ssh SEU_USUARIO@IP_DO_SERVIDOR
cd ~/xdp-flow-monitor
```

## 1. Conferir e mostrar a conexão — terminal 1, no servidor

```bash
make demo-check
make demo-ping
```

## 2. Receber tráfego — terminal 1

```bash
make demo-server
```

## 3. Preparar o gerador — terminal 3

Deixe este comando digitado, **sem Enter**:

```bash
make demo-traffic RUN=demo-r1
```

## 4. Iniciar a coleta — terminal 2

```bash
make demo-monitor RUN=demo-r1
```

Ao aparecer **PRONTO**, pressione Enter no terminal 3 (em até 10 s). Se houver erro, não gere tráfego.

## 5. Mostrar métricas ao vivo — terminal 4, no servidor

```bash
make demo-log RUN=demo-r1
```

Mostre o IP de origem, as janelas e as flags TCP. Esta demo mostra **coleta sem classificação ML**; as taxas ainda têm pendências de validação.

## 6. Encerrar

- Aguarde a carga (50 s) e a observação (70 s) terminarem.
- `Ctrl+C` no terminal 4 encerra o acompanhamento; no terminal 1, encerra o serviço.
- Para repetir, use `RUN=demo-r2` nos terminais 2, 3 e 4.

Todos os comandos são executados na **raiz do projeto no servidor**, fora dos containers. Copie o novo Makefile da raiz para o servidor; esses atalhos não exigem reconstruir a imagem.
