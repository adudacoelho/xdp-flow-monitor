#!/bin/bash
set -e

echo "[*] Compilando flow_monitor.bpf.c em container Docker temporário..."

docker run --rm -v "$(pwd)":/work -w /work ubuntu:22.04 bash -c "
  apt-get update -qq && \
  apt-get install -y -qq clang llvm libbpf-dev linux-tools-common linux-tools-generic make gcc-multilib > /dev/null && \
  clang -g -O2 -target bpf -D__TARGET_ARCH_x86 -c flow_monitor.bpf.c -o flow_monitor.bpf.o
"

if [ -f flow_monitor.bpf.o ]; then
  echo "Success! flow_monitor.bpf.o created."
else
  echo "[!] Falha ao gerar flow_monitor.bpf.o"
  exit 1
fi

