FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip make sudo iproute2 iputils-ping procps \
    clang llvm gcc libbpf-dev libelf-dev zlib1g-dev linux-tools-common linux-tools-generic \
    iperf3 hping3 tcpreplay tshark tcpdump iptables ethtool sysstat snort \
    ca-certificates golang-go git util-linux && rm -rf /var/lib/apt/lists/*
# Evita o wrapper Ubuntu que procura bpftool pela versão do kernel do host.
RUN tool="$(find /usr/lib/linux-tools -type f -name bpftool | sort | tail -n 1)" && \
    test -n "$tool" && cp "$tool" /usr/local/bin/bpftool
WORKDIR /workspace
RUN python3 -m venv /workspace/.venv && \
    /workspace/.venv/bin/pip install --no-cache-dir \
      numpy==1.26.4 pandas==2.2.3 scikit-learn==1.5.2 xgboost==2.1.4 && \
    /workspace/.venv/bin/pip freeze > /workspace/.venv/installed-versions.txt
RUN GOBIN=/usr/local/bin go install github.com/microsoft/ethr@v1.0.0
COPY . /workspace
CMD ["sleep", "infinity"]
