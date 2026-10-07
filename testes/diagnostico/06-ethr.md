# 06 — Conferir a exportação de latência do Ethr

**Primeiro use os dados existentes.** Não é necessário repetir a latência para
mostrar que o JSON tem percentis inconsistentes. Trabalhe no PC, na cópia dos
resultados; não execute Ethr nesta etapa.

## 1. Abrir o log e o JSON da mesma execução

No terminal do PC, ajuste o caminho se a pasta foi arquivada:

```bash
cd ~/Área\ de\ trabalho/ProjetoIC/xdp-flow-monitor/testes/testes-chen
PASTA=results-servidor/generator/20261007T020840866353809-traffic-fig5-lat-baseline-r1
head -n 18 "$PASTA/ethr.log"
head -n 8 "$PASTA/ethr.json"
```

O JSON contém um objeto por linha; não é um único array. Compare cabeçalhos e
valores, respeitando a ordem das amostras. Não suponha correspondência temporal
exata se o log textual não contiver timestamps; nesse caso registre a limitação.

## 2. Verificar as relações que deveriam valer

Para cada conjunto, esperamos `Min <= P50 <= P90 <= P95 <= P99 <= P999 <= P9999 <= Max`.
A média deve estar entre mínimo e máximo, mas não precisa coincidir com P50.
Converta unidades antes de comparar números se houver ns, us ou ms misturados.

No registro já analisado, `P50=61.930us`, `P90=28.930us` e `Max=48.069us`
violam essas relações. Guarde a linha original. Não ordene os valores para
“corrigir” os campos: isso esconderia a origem do defeito.

## 3. Localizar a origem e documentar a correção

A equipe deve conferir, na versão Ethr compilada na imagem, onde os valores
são calculados e como são associados aos nomes JSON. Diferencie defeito de
cálculo de defeito de formatação. Registre versão, revisão e dependências.
Uma correção deve ser conferida com uma sequência de valores conhecida antes
de depender de novas medições de rede.

## 4. Quando repetir a medição

Depois de corrigir/atualizar a ferramenta, repita uma rodada com observação de 60 s e carga de 30 s e confira
novamente JSON e texto. Só então refaça a série comparativa. A média dos campos
`Avg` não permite recuperar percentis globais nem reparar os percentis antigos.
