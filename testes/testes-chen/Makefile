# NO SERVIDOR: preparação comum às duas versões. Não cria VMs nem roda testes.
# Execute nesta pasta: cd testes/testes-chen
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help
.PHONY: help host-check host-setup

help:
	@echo 'NO SERVIDOR: make host-check; make host-setup'
	echo 'Depois entre em vm-ubuntu2204/ ou vm-ubuntu2604/ para administrar a VM.'

# Somente virtualização/gerenciamento no servidor físico.
host-check:
	@uname -m
	free -h
	nproc
	test -e /dev/kvm && echo 'KVM disponível' || echo 'KVM ausente'
	for tool in virsh virt-install cloud-localds qemu-img curl rsync ssh; do command -v "$$tool" || true; done

host-setup:
	if [ ! -r /etc/apt/sources.list.d/ubuntu.sources ]; then echo 'Arquivo /etc/apt/sources.list.d/ubuntu.sources ausente ou sem permissão de leitura.' >&2; exit 1; fi
	sudo apt-get -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources -o Dir::Etc::sourceparts=- update
	sudo apt-get -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources -o Dir::Etc::sourceparts=- install -y qemu-kvm qemu-utils libvirt-daemon-system libvirt-clients virtinst cloud-image-utils curl rsync openssh-client
	sudo usermod -aG libvirt,kvm "$$(id -un)"
	@echo 'Saia do SSH e entre novamente para aplicar os grupos.'

