# NO SERVIDOR: execute em testes/testes-chen (ou use make -C nessa pasta).
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

CHEN_ROOT := $(shell cd ../.. && pwd)
CHEN_RESULTS := $(CURDIR)/results-servidor
CHEN_STATE := $(CURDIR)/.lab
CLAB_VERSION := 0.69.3
NODE ?= target
export CHEN_ROOT CHEN_RESULTS CHEN_STATE CLAB_VERSION NODE

.PHONY: help server-check host-check host-setup clab-setup clab-image clab-up clab-status clab-check clab-build clab-shell host-record clab-down

help:
	@echo 'NO SERVIDOR, nesta pasta:'
	echo '  make host-check       — conferir sistema e recursos'
	echo '  make host-setup       — instalar Docker e Containerlab'
	echo '  make clab-image       — construir imagem'
	echo '  make clab-up          — criar containers e enlace'
	echo '  make clab-status      — consultar containers'
	echo '  make clab-check       — verificar rede e suporte BPF'
	echo '  make clab-build       — compilar eBPF e monitor dentro de target'
	echo '  make clab-shell NODE=target|generator — abrir terminal'
	echo '  make host-record      — salvar informações do ambiente'
	echo '  make clab-down        — remover laboratório, preservando resultados'

server-check:
	@test ! -e /.dockerenv || { echo 'Execute no servidor, fora dos containers.' >&2; exit 1; }
	test -f "$$CHEN_ROOT/lab/Dockerfile"
	test -f "$$CHEN_ROOT/lab/topology.clab.yml"

host-check: server-check
	@cat /etc/os-release
	uname -m
	uname -r
	free -h
	nproc
	df -h "$$CHEN_ROOT"
	for tool in docker containerlab; do
		command -v "$$tool" || echo "$$tool ainda não instalado"
	done

# Mantém instalações existentes. Não instala infraestrutura de virtualização.
host-setup: server-check
	test "$$(uname -m)" = x86_64
	sudo apt-get update
	sudo apt-get install -y ca-certificates curl make git
	if ! command -v docker >/dev/null; then sudo apt-get install -y docker.io; fi
	sudo systemctl enable --now docker
	sudo docker info
	if ! command -v containerlab >/dev/null; then
		mkdir -p "$$CHEN_STATE"
		curl -fL --retry 3 "https://github.com/srl-labs/containerlab/releases/download/v$$CLAB_VERSION/containerlab_$${CLAB_VERSION}_linux_amd64.deb" -o "$$CHEN_STATE/containerlab.deb"
		sudo apt-get install -y "$$CHEN_STATE/containerlab.deb"
	fi
	containerlab version

clab-setup: host-setup

clab-image: server-check
	sudo docker build -t chen-lab:local -f "$$CHEN_ROOT/lab/Dockerfile" "$$CHEN_ROOT"
	sudo docker image inspect chen-lab:local --format '{{.Id}}'

# O marcador é montado pela topologia existente. Não sobrescreve outro ambiente.
clab-up: server-check
	if sudo test -e /etc/xdp-chen-lab; then
		if [ "$$(sudo cat /etc/xdp-chen-lab)" != servidor ]; then
			echo 'Marcador /etc/xdp-chen-lab pertence a outro ambiente; confira antes de continuar.' >&2
			exit 1
		fi
	else
		printf 'servidor\n' | sudo tee /etc/xdp-chen-lab >/dev/null
		sudo chown root:root /etc/xdp-chen-lab
		sudo chmod 644 /etc/xdp-chen-lab
	fi
	test "$$(sudo stat -c %u /etc/xdp-chen-lab)" = 0
	mkdir -p "$$CHEN_ROOT/dataset" "$$CHEN_RESULTS/generator" "$$CHEN_RESULTS/target"
	sudo env CHEN_ROOT="$$CHEN_ROOT" CHEN_RESULTS="$$CHEN_RESULTS" containerlab deploy -t "$$CHEN_ROOT/lab/topology.clab.yml"

clab-status: server-check
	sudo env CHEN_ROOT="$$CHEN_ROOT" CHEN_RESULTS="$$CHEN_RESULTS" containerlab inspect -t "$$CHEN_ROOT/lab/topology.clab.yml"

# Reutiliza somente os alvos internos de check/build, sem administrar VMs.
clab-check: server-check
	for node in generator target; do
		sudo docker exec "clab-chen-$$node" make -C /workspace/testes/testes-chen/vm-ubuntu2204 VM_TAG=servidor check
	done
	sudo docker exec clab-chen-generator ping -c 3 192.168.157.20
	sudo docker exec clab-chen-target findmnt -t bpf /sys/fs/bpf
	sudo docker exec clab-chen-target bpftool feature probe kernel

clab-build: server-check
	sudo docker exec clab-chen-target make -C /workspace/testes/testes-chen/vm-ubuntu2204 VM_TAG=servidor build

clab-shell: server-check
	@case "$$NODE" in generator|target) ;; *) echo 'Use NODE=generator ou NODE=target.' >&2; exit 1;; esac
	sudo docker exec -it -e VM_TAG=servidor -w /workspace/testes/testes-chen/vm-ubuntu2204 "clab-chen-$$NODE" bash

host-record: server-check
	mkdir -p "$$CHEN_RESULTS"
	cat /etc/os-release > "$$CHEN_RESULTS/servidor-os.txt"
	uname -a > "$$CHEN_RESULTS/servidor-kernel.txt"
	git -C "$$CHEN_ROOT" rev-parse HEAD > "$$CHEN_RESULTS/codigo-commit.txt"
	git -C "$$CHEN_ROOT" status --short > "$$CHEN_RESULTS/codigo-status.txt"
	containerlab version > "$$CHEN_RESULTS/containerlab-version.txt"
	sudo docker version > "$$CHEN_RESULTS/docker-version.txt"
	sudo docker image inspect chen-lab:local > "$$CHEN_RESULTS/imagem.json"
	@echo "Registros salvos em $$CHEN_RESULTS"

clab-down: server-check
	sudo env CHEN_ROOT="$$CHEN_ROOT" CHEN_RESULTS="$$CHEN_RESULTS" containerlab destroy -t "$$CHEN_ROOT/lab/topology.clab.yml"
	if [ -d "$$CHEN_RESULTS" ]; then sudo chown -R "$$(id -u):$$(id -g)" "$$CHEN_RESULTS"; fi
