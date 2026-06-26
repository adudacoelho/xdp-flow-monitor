#!/bin/bash
set -e

echo "[*] Gerando skeleton e compilando main.c em container Docker temporário..."

docker run --rm -v "$(pwd)":/work -w /work ubuntu:24.04 bash -c "
  apt-get update -qq && \
  apt-get install -y -qq clang llvm libbpf-dev libelf-dev zlib1g-dev linux-tools-common linux-tools-generic gcc make > /dev/null && \
  BPFTOOL=\$(command -v bpftool || ls /usr/lib/linux-tools/*/bpftool 2>/dev/null | head -n1) && \
  echo \"[*] usando bpftool em: \$BPFTOOL\" && \
  \$BPFTOOL gen skeleton flow_monitor.bpf.o > flow_monitor.skel.h && \
  gcc -g -Wall main.c -o flow_monitor -lbpf -lelf -lz
"

if [ -f flow_monitor ]; then
  echo "Sucess! loader flow_monitor created."
else
  echo "[!] Falha ao gerar o executável flow_monitor"
  exit 1
fi

