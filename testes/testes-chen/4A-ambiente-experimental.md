# IV-A — Ambiente experimental

A preparação está em [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md).

O laboratório usa Docker e Containerlab diretamente no servidor srv01 com
Ubuntu Server 24.04. Os containers Ubuntu 22.04 `generator` e `target` estão
ligados por `lab0` e compartilham o kernel e os recursos do servidor.
O monitor é anexado à `lab0` dentro de `target`.

O artigo usa seis máquinas, Kubernetes e DeathStarBench: este ambiente é uma
reprodução adaptada. Registre sistema e kernel do servidor, recursos, versão
do código, imagem dos containers e carga utilizada.

CPU e memória coletadas por `mpstat` e `sar` refletem o servidor compartilhado,
não somente o container da vítima. Registre também outros serviços em execução.

Os procedimentos e pendências de cada experimento ficam nos arquivos
[4B](4B-coleta-ebpf.md), [4C](4C-filtragem-xdp.md),
[4D](4D-classificacao.md) e [4E](4E-sistema-completo.md).
