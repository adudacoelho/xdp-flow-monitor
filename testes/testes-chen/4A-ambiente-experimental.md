# IV-A — Ambiente experimental

Preparação do servidor: [PREPARANDOSERVIDOR.md](PREPARANDOSERVIDOR.md).

- [Preparar a VM Ubuntu 22.04 ou 26.04](PREPARANDOVM.md)

O laboratório usa Containerlab dentro de uma VM, com os containers `generator`
e `target` ligados por `lab0`. Os containers compartilham o kernel e os recursos
da VM. O artigo usa seis máquinas, Kubernetes e DeathStarBench: este ambiente
é uma reprodução adaptada.

Registre versão do Ubuntu e kernel, recursos da VM, versão do código, imagem
dos containers e carga utilizada. Mantenha o mesmo protocolo entre versões.

CPU e memória coletadas por `mpstat` e `sar` refletem a VM compartilhada, não
somente o container da vítima. As etapas detalhadas de cada teste serão revisadas
individualmente antes da execução.
