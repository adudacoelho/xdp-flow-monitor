FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip make sudo iproute2 iputils-ping procps \
    clang llvm gcc libbpf-dev libelf-dev zlib1g-dev linux-tools-common linux-tools-generic \
    iperf3 hping3 tcpreplay tshark tcpdump iptables ethtool sysstat snort \
    ca-certificates golang-go git util-linux && rm -rf /var/lib/apt/lists/*
# Evita o wrapper Ubuntu que procura bpftool pela versão do kernel do host.
# Busca também nos diretórios linux-tools-<versão>, fora de linux-tools/.
RUN tool="$(find /usr/lib -path '/usr/lib/linux-tools*' -type f -name bpftool | sort | tail -n 1)" && \
    { test -n "$tool" || { echo 'bpftool não encontrado nos pacotes linux-tools instalados' >&2; exit 1; }; } && \
    cp "$tool" /usr/local/bin/bpftool
WORKDIR /workspace
RUN python3 -m venv /workspace/.venv && \
    /workspace/.venv/bin/pip install --no-cache-dir \
      numpy==1.26.4 pandas==2.2.3 scikit-learn==1.5.2 xgboost==2.1.4 && \
    /workspace/.venv/bin/pip freeze > /workspace/.venv/installed-versions.txt
# Ethr 1.0.0 não fixa x/net; versões recentes exigem Go posterior ao 1.18.
# Um módulo de build fixa as dependências sem alterar o Go do servidor.
RUN mkdir -p /tmp/ethr-build && cd /tmp/ethr-build && \
    go mod init local/ethr-build && \
    go mod edit -require=github.com/microsoft/ethr@v1.0.0 \
      -require=golang.org/x/net@v0.17.0 -require=golang.org/x/sys@v0.13.0 && \
    GOBIN=/usr/local/bin go install -mod=mod github.com/microsoft/ethr && \
    rm -rf /tmp/ethr-build
COPY . /workspace
CMD ["sleep", "infinity"]
