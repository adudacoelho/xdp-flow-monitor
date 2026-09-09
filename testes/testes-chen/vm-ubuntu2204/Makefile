SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# Execute make nesta pasta (ou use make -C caminho/da/pasta).
# Receitas compartilhadas: o Makefile 26.04 inclui este arquivo depois de definir
# seus parâmetros. Não há scripts auxiliares nem duas cópias das receitas.
VM_VERSION ?= 22.04
VM_TAG ?= 2204
VM_NAME ?= chen-ubuntu2204
VM_IP ?= 192.168.158.22
VM_NETWORK ?= chen-mgmt2204
VM_BRIDGE ?= virbr-chen22
VM_SUBNET ?= 192.168.158
VM_MAC ?= 52:54:00:ce:01:22
IMAGE_URL ?= https://cloud-images.ubuntu.com/releases/22.04/release
IMAGE_FILE ?= ubuntu-22.04-server-cloudimg-amd64.img
VM_DIR := $(CURDIR)
REPO_ROOT := $(shell cd ../../.. && pwd)
VM_REL := testes/testes-chen/vm-ubuntu$(VM_TAG)
export VM_VERSION VM_TAG VM_NAME VM_IP VM_NETWORK VM_BRIDGE VM_SUBNET VM_MAC IMAGE_URL IMAGE_FILE VM_DIR REPO_ROOT VM_REL

# Somente get-results usa estas opções: endereço SSH do servidor e caminho
# ABSOLUTO do projeto no servidor (não o caminho do seu PC).
SERVER ?=
SERVER_REPO ?=
export SERVER SERVER_REPO

NODE ?= target
MODE ?= baseline
KIND ?= tcp
DURATION ?= 120
PPS ?= 5000
RULES ?= 16
RUN ?= preliminary
PCAP ?=
SERVICE ?= iperf
export NODE MODE KIND DURATION PPS RULES RUN PCAP SERVICE

.PHONY: help server-check vm-up vm-stop vm-status vm-sync vm-results get-results ssh-lab vm-check clab-setup clab-image clab-up clab-down clab-status clab-shell check build serve traffic observe ml
help:
	@echo "Ambiente Ubuntu $$VM_VERSION — $$VM_NAME ($$VM_IP)"
	echo 'NO SERVIDOR, nesta pasta: vm-up vm-status vm-sync ssh-lab vm-results vm-stop'
	echo 'DENTRO DA VM, nesta mesma pasta relativa: clab-setup clab-image clab-up clab-status clab-shell clab-down'
	echo 'DENTRO DO CONTAINER, na pasta da versão: check build serve traffic observe ml'
	echo 'NO PC, nesta pasta: get-results SERVER=usuario@servidor SERVER_REPO=/caminho/absoluto/xdp-flow-monitor'
	echo 'observe MODE=baseline|tshark|collection-current|detector-current|iptables|snort'
	echo 'traffic KIND=tcp|latency|syn|udp|replay DURATION=120 PPS=5000'

# NO SERVIDOR: impede administrar VMs a partir dos containers ou da VM de teste.
server-check:
	@test ! -e /.dockerenv
	if [ -e /etc/xdp-chen-lab ]; then echo 'Execute este alvo no servidor, fora da VM do laboratório.' >&2; exit 1; fi
	test -f "$$REPO_ROOT/lab/Dockerfile"

# NO SERVIDOR: baixa a imagem oficial, valida checksum, cria disco e cloud-init.
# Depois da primeira criação, apenas inicia a VM existente. Não apaga discos.
# .lab/ desta pasta contém a imagem baixada, chave SSH e configurações geradas.
vm-up: server-check
	test -e /dev/kvm
	test "$$(uname -m)" = x86_64
	mkdir -p .lab
	exec 9>.lab/create.lock; flock -n 9
	if virsh -c qemu:///system dominfo "$$VM_NAME" >/dev/null 2>&1; then
		if ! virsh -c qemu:///system net-list --name | grep -Fxq "$$VM_NETWORK"; then virsh -c qemu:///system net-start "$$VM_NETWORK"; fi
		if ! virsh -c qemu:///system list --name | grep -Fxq "$$VM_NAME"; then virsh -c qemu:///system start "$$VM_NAME"; fi
		exit 0
	fi
	if ! virsh -c qemu:///system net-info "$$VM_NETWORK" >/dev/null 2>&1; then
		if ip -4 route | grep -Fq "$$VM_SUBNET."; then echo "Sub-rede $$VM_SUBNET.0/24 ocupada." >&2; exit 1; fi
		printf '<network><name>%s</name><bridge name="%s"/><forward mode="nat"/><ip address="%s.1" netmask="255.255.255.0"><dhcp><range start="%s.100" end="%s.200"/><host mac="%s" ip="%s"/></dhcp></ip></network>\n' "$$VM_NETWORK" "$$VM_BRIDGE" "$$VM_SUBNET" "$$VM_SUBNET" "$$VM_SUBNET" "$$VM_MAC" "$$VM_IP" > .lab/network.xml
		virsh -c qemu:///system net-define .lab/network.xml
	fi
	if ! virsh -c qemu:///system net-list --name | grep -Fxq "$$VM_NETWORK"; then virsh -c qemu:///system net-start "$$VM_NETWORK"; fi
	if [ ! -f .lab/id_ed25519 ]; then ssh-keygen -q -t ed25519 -N '' -f .lab/id_ed25519; fi
	if [ ! -f ".lab/$$IMAGE_FILE" ]; then
		curl -fL --retry 3 "$$IMAGE_URL/SHA256SUMS" -o .lab/SHA256SUMS
		curl -fL --retry 3 "$$IMAGE_URL/$$IMAGE_FILE" -o ".lab/$$IMAGE_FILE.part"
		cd .lab
		expected=$$(awk -v name="$$IMAGE_FILE" '{f=$$2; sub(/^\*/,"",f); if(f==name) print $$1}' SHA256SUMS)
		test -n "$$expected"
		printf '%s  %s\n' "$$expected" "$$IMAGE_FILE.part" | sha256sum -c -
		mv "$$IMAGE_FILE.part" "$$IMAGE_FILE"
		cd ..
	fi
	printf '%s\n' '#cloud-config' "hostname: $$VM_NAME" 'package_update: true' 'packages: [make, rsync]' 'users:' '  - name: ubuntu' '    groups: [sudo]' '    sudo: ALL=(ALL) NOPASSWD:ALL' '    shell: /bin/bash' '    ssh_authorized_keys:' "      - $$(cat .lab/id_ed25519.pub)" 'ssh_pwauth: false' 'write_files:' '  - path: /etc/xdp-chen-lab' "    permissions: '0644'" "    content: '$$VM_TAG'" > .lab/user.yaml
	printf 'instance-id: %s\nlocal-hostname: %s\n' "$$VM_NAME" "$$VM_NAME" > .lab/meta.yaml
	printf '%s\n' 'version: 2' 'ethernets:' '  mgmt0:' "    match: {macaddress: '$$VM_MAC'}" '    set-name: mgmt0' '    dhcp4: true' > .lab/network.yaml
	cloud-localds --network-config=.lab/network.yaml .lab/seed.iso .lab/user.yaml .lab/meta.yaml
	disk_dir="/var/lib/libvirt/images/$$VM_NAME"
	sudo mkdir -p "$$disk_dir"
	if sudo test -e "$$disk_dir/lab.qcow2"; then echo 'Disco existente sem VM: inspecione antes de reutilizar.' >&2; exit 1; fi
	sudo cp --sparse=always ".lab/$$IMAGE_FILE" "$$disk_dir/lab.qcow2"
	sudo qemu-img resize "$$disk_dir/lab.qcow2" 40G
	sudo cp .lab/seed.iso "$$disk_dir/seed.iso"
	# Não exige que o osinfo-db do servidor 24.04 já conheça Ubuntu 26.04.
	virt-install --connect qemu:///system --name "$$VM_NAME" --memory 8192 --vcpus 4 --cpu host-passthrough --import --osinfo detect=on,require=off --disk "path=$$disk_dir/lab.qcow2,format=qcow2,bus=virtio" --disk "path=$$disk_dir/seed.iso,device=cdrom" --network "network=$$VM_NETWORK,model=virtio,mac=$$VM_MAC" --graphics none --noautoconsole

# NO SERVIDOR: abre um terminal na VM escolhida. Não entra em containers.
ssh-lab: server-check
	ssh -i .lab/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=.lab/known_hosts "ubuntu@$$VM_IP"

# NO SERVIDOR: copia projeto SERVIDOR -> VM. Não consulta GitHub nem copia dados.
# Após mudar código, reconstrua a imagem dos containers dentro da VM.
vm-sync: server-check
	ssh -i .lab/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=.lab/known_hosts "ubuntu@$$VM_IP" 'sudo cloud-init status --wait'
	rsync -az --exclude=.git --exclude=.lab --exclude=.venv --exclude=build --exclude=results --exclude=dataset -e 'ssh -i .lab/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=.lab/known_hosts' "$$REPO_ROOT/" "ubuntu@$$VM_IP:xdp-flow-monitor/"

# NO SERVIDOR: recupera VM -> results/ DESTA versão. Execute clab-down antes,
# dentro da VM, para encerrar o laboratório e devolver a propriedade dos arquivos.
vm-results: server-check
	mkdir -p results
	rsync -az --exclude=.gitkeep -e 'ssh -i .lab/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=.lab/known_hosts' "ubuntu@$$VM_IP:xdp-flow-monitor/$$VM_REL/results/" results/

# NO PC: copia SERVIDOR -> results/ DESTA versão, usando sua chave SSH normal.
# Exemplo: make get-results SERVER=elisa@servidor SERVER_REPO=/home/elisa/xdp-flow-monitor
# Não faz commit/push e não apaga arquivos locais. RESULTADOS.md fica fora da cópia.
get-results:
	@test ! -e /etc/xdp-chen-lab
	test ! -e /.dockerenv
	if [ -z "$$SERVER" ] || [[ "$$SERVER" == -* ]] || [[ "$$SERVER" == *[[:space:]]* ]]; then echo 'Informe SERVER=usuario@servidor.' >&2; exit 1; fi
	if [[ "$$SERVER_REPO" != /* ]]; then echo 'Informe SERVER_REPO com o caminho absoluto do projeto no servidor.' >&2; exit 1; fi
	mkdir -p results
	rsync -azs --exclude=.gitkeep "$$SERVER:$$SERVER_REPO/$$VM_REL/results/" results/

# NO SERVIDOR: consulta ou solicita desligamento só da VM desta pasta.
vm-status: server-check
	virsh -c qemu:///system dominfo "$$VM_NAME"
vm-stop: server-check
	virsh -c qemu:///system shutdown "$$VM_NAME"

# DENTRO DA VM: confere também a versão para evitar usar a pasta errada.
vm-check:
	@test ! -e /.dockerenv
	case "$$(systemd-detect-virt --vm)" in kvm|qemu|vmware|oracle|microsoft|xen) ;; *) echo 'Execute dentro da VM dedicada.' >&2; exit 1;; esac
	test "$$(cat /etc/xdp-chen-lab)" = "$$VM_TAG"
	test "$$(stat -c %u /etc/xdp-chen-lab)" = 0
	. /etc/os-release; test "$$VERSION_ID" = "$$VM_VERSION"

# DENTRO DA VM: instala Docker/Containerlab; não instala isso no servidor físico.
clab-setup: vm-check
	sudo apt-get update
	sudo apt-get install -y docker.io curl
	sudo systemctl enable --now docker
	mkdir -p .lab
	curl -fL --retry 3 https://github.com/srl-labs/containerlab/releases/download/v0.69.3/containerlab_0.69.3_linux_amd64.deb -o .lab/containerlab.deb
	sudo apt-get install -y "$$VM_DIR/.lab/containerlab.deb"

# DENTRO DA VM: constrói a mesma imagem Ubuntu 22.04 dos containers em ambas
# as VMs. O kernel continua sendo o da VM, não o da imagem do container.
clab-image: vm-check
	sudo docker build -t chen-lab:local -f "$$REPO_ROOT/lab/Dockerfile" "$$REPO_ROOT"

# DENTRO DA VM: cria containers e enlace. As variáveis do YAML direcionam os
# resultados para esta versão e o shell para a pasta do Makefile correspondente.
clab-up: vm-check
	mkdir -p "$$REPO_ROOT/dataset" results/generator results/target
	sudo env CHEN_ROOT="$$REPO_ROOT" CHEN_RESULTS="$$VM_DIR/results" CHEN_VM_TAG="$$VM_TAG" containerlab deploy -t "$$REPO_ROOT/lab/topology.clab.yml"
	for node in generator target; do sudo docker exec -w "/workspace/$$VM_REL" "clab-chen-$$node" make check; done

# DENTRO DA VM: remove a topologia, mas preserva results/ no disco da VM.
clab-down: vm-check
	sudo env CHEN_ROOT="$$REPO_ROOT" CHEN_RESULTS="$$VM_DIR/results" CHEN_VM_TAG="$$VM_TAG" containerlab destroy -t "$$REPO_ROOT/lab/topology.clab.yml"
	if [ -d results ]; then sudo chown -R "$$(id -u):$$(id -g)" results; fi

# DENTRO DA VM: mostra o laboratório ou abre shell no nó escolhido.
clab-status: vm-check
	sudo env CHEN_ROOT="$$REPO_ROOT" CHEN_RESULTS="$$VM_DIR/results" CHEN_VM_TAG="$$VM_TAG" containerlab inspect -t "$$REPO_ROOT/lab/topology.clab.yml"
clab-shell: vm-check
	case "$$NODE" in generator|target) ;; *) echo 'NODE=generator ou target' >&2; exit 1;; esac
	sudo docker exec -it -w "/workspace/$$VM_REL" "clab-chen-$$NODE" bash

# DENTRO DO CONTAINER: valida o nó, a VM selecionada e o enlace isolado.
# Abra o shell com clab-shell; ele já inicia na pasta desta versão.
check:
	@test -e /.dockerenv
	test "$$(cat /etc/xdp-chen-vm)" = "$$VM_TAG"
	test "$$(stat -c %u /etc/xdp-chen-vm)" = 0
	role=$$(cat /etc/xdp-chen-lab)
	case "$$role" in target) local_ip=192.168.157.20; peer=192.168.157.10;; generator) local_ip=192.168.157.10; peer=192.168.157.20;; *) exit 1;; esac
	ip -o -4 addr show dev lab0 | grep -Fq "$$local_ip/24"
	test -z "$$(ip -4 route show default)"
	ip -4 route get "$$peer" | grep -q 'dev lab0'
	test "$$(cat /proc/sys/net/ipv4/ip_forward)" = 0

# DENTRO DO CONTAINER: compila somente o detector original e gera seu skeleton.
# Artefatos ficam em /workspace/build; nenhum programa é anexado nesta etapa.
build: check
	cd "$$REPO_ROOT"
	mkdir -p build
	test "$$(uname -m)" = x86_64
	clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -D__x86_64__ -I "/usr/include/$$(gcc -print-multiarch)" -I xdp-flow-monitor-main -c xdp-flow-monitor-main/flow_monitor.bpf.c -o build/flow_monitor.bpf.o
	bpftool gen skeleton build/flow_monitor.bpf.o > build/flow_monitor.skel.h
	cp xdp-flow-monitor-main/main.c build/main.c
	gcc -O2 -g -Wall -I build -I xdp-flow-monitor-main build/main.c xdp-flow-monitor-main/window.c -o build/flow_monitor -lbpf -lelf -lz

# Validação de parâmetros repetida por expansão textual do Makefile, sem scripts.
define parameters
[[ "$$DURATION" =~ ^[0-9]+$$ ]] && (( DURATION >= 1 && DURATION <= 600 ))
[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]]
out="results/$$(date -u +%Y%m%dT%H%M%S%N)-$@-$$RUN"
mkdir -p "$$out"
printf '%s\n' "$$VM_VERSION" > "$$out/vm-version.txt"
uname -a > "$$out/kernel.txt"
dpkg-query -W > "$$out/packages.txt"
ip -details link show lab0 > "$$out/interface.txt"
printf 'DURATION=%s\nMODE=%s\nKIND=%s\nPPS=%s\nRULES=%s\n' "$$DURATION" "$$MODE" "$$KIND" "$$PPS" "$$RULES" > "$$out/parameters.txt"
endef

# DENTRO DO CONTAINER target: inicia iperf/Ethr por tempo limitado.
serve: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = target
	$(parameters)
	case "$$SERVICE" in
	iperf) command=(iperf3 -s -B 192.168.157.20 -p 80 -J);;
	ethr) command=(ethr -s -ip 192.168.157.20 -port 80 -o "$$out/ethr.json");;
	*) echo 'SERVICE=iperf ou ethr' >&2; exit 1;; esac
	rc=0; timeout --signal=TERM --kill-after=5 "$$DURATION" "$${command[@]}" > "$$out/server.log" 2>&1 || rc=$$?
	[[ $$rc == 0 || $$rc == 124 ]]

# DENTRO DO CONTAINER generator: envia carga somente ao enlace de teste.
# PCAP é relativo à raiz /workspace, mesmo chamando make na pasta da versão.
traffic: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = generator
	$(parameters)
	case "$$KIND" in tcp|latency|syn|udp|replay) ;; *) echo 'KIND inválido' >&2; exit 1;; esac
	exec 9>"/run/chen-traffic-$$KIND.lock"; flock -n 9
	date -u +%s.%N > "$$out/start-epoch.txt"
	case "$$KIND" in
	tcp) timeout --kill-after=5 "$$((DURATION+15))" iperf3 -c 192.168.157.20 -B 192.168.157.10 -p 80 -t "$$DURATION" -i 1 -J > "$$out/iperf.json";;
	latency) timeout --kill-after=5 "$$((DURATION+15))" ethr -c 192.168.157.20 -ip 192.168.157.10 -port 80 -p tcp -t l -d "$${DURATION}s" -o "$$out/ethr.json" > "$$out/ethr.log";;
	syn|udp)
		[[ "$$PPS" =~ ^[0-9]+$$ ]] && (( PPS >= 6 && PPS <= 1000000 ))
		count=1; flag=--udp; if [ "$$KIND" = syn ]; then count=6; flag=-S; fi
		interval=$$((1000000*count/PPS)); (( interval > 0 )) || interval=1
		pids=(); trap 'for pid in "$${pids[@]}"; do kill "$$pid" 2>/dev/null || true; done; wait || true' EXIT
		for (( i=101; i<101+count; i++ )); do
			timeout --signal=TERM --kill-after=5 "$$DURATION" hping3 -I lab0 -a "192.168.157.$$i" "$$flag" -p 80 -i "u$$interval" 192.168.157.20 > "$$out/hping-$$i.log" 2>&1 & pids+=("$$!")
		done
		for pid in "$${pids[@]}"; do rc=0; wait "$$pid" || rc=$$?; [[ $$rc == 0 || $$rc == 124 ]]; done
		;;
	replay)
		[[ "$$PPS" =~ ^[0-9]+$$ ]] && (( PPS >= 1 && PPS <= 1000000 ))
		test -f "$$PCAP"
		# Recusa frames fora do enlace/destino do laboratório antes de enviar.
		count=$$(tshark -r "$$PCAP" -T fields -e frame.number 2>"$$out/pcap-check.log" | wc -l)
		(( count > 0 ))
		bad=$$(tshark -r "$$PCAP" -Y 'not (eth.src == 52:54:00:ce:02:10 and eth.dst == 52:54:00:ce:02:20 and ip.src == 192.168.157.0/24 and ip.dst == 192.168.157.20)' -T fields -e frame.number 2>>"$$out/pcap-check.log")
		test -z "$$bad"
		timeout --kill-after=5 "$$((DURATION+15))" tcpreplay --intf1=lab0 --pps="$$PPS" --loop=0 --duration="$$DURATION" "$$PCAP" > "$$out/tcpreplay.log" 2>&1;;
	esac
	date -u +%s.%N > "$$out/end-epoch.txt"

# DENTRO DO CONTAINER target: executa o comparador e registra as métricas.
observe: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = target
	$(parameters)
	exec 9>/run/chen-observe.lock; flock -n 9
	if ip -details link show lab0 | grep -q 'prog/xdp'; then echo 'Já há XDP anexado em lab0. Encerre a execução anterior.' >&2; exit 1; fi
	pids=(); chain=0; jump=0; ml_started=0
	trap 'for pid in "$${pids[@]}"; do kill "$$pid" 2>/dev/null || true; done; wait || true; if (( jump )); then iptables-legacy -D INPUT -i lab0 -j CHEN_LAB; fi; if (( chain )); then iptables-legacy -F CHEN_LAB; iptables-legacy -X CHEN_LAB; fi; if (( ml_started )); then rm -f /tmp/ml_engine.sock; fi' EXIT
	case "$$MODE" in
	baseline) ;;
	tshark) tshark -n -l -i lab0 > "$$out/tshark.log" 2>&1 & pids+=("$$!");;
	collection-current|detector-current)
		test -x build/flow_monitor
		test ! -e /tmp/ml_engine.sock
		if [ "$$MODE" = detector-current ]; then
			root=$$PWD
			(cd xdp-flow-monitor-main; exec "$$root/.venv/bin/python" -u ml_daemon.py) > "$$out/ml.log" 2>&1 & pids+=("$$!"); ml_started=1
			for i in {1..100}; do test ! -S /tmp/ml_engine.sock || break; sleep 0.1; done
			test -S /tmp/ml_engine.sock
		fi
		stdbuf -oL build/flow_monitor lab0 > "$$out/monitor.log" 2>&1 & pids+=("$$!");;
	iptables)
		[[ "$$RULES" =~ ^[0-9]+$$ ]] && (( RULES >= 6 && RULES <= 512 ))
		iptables-legacy -N CHEN_LAB; chain=1
		for (( i=1; i<=RULES-6; i++ )); do iptables-legacy -A CHEN_LAB -s "198.18.$$((i/256)).$$((i%256))" -j DROP; done
		for i in {101..106}; do iptables-legacy -A CHEN_LAB -s "192.168.157.$$i" -j DROP; done
		iptables-legacy -I INPUT 1 -i lab0 -j CHEN_LAB; jump=1;;
	snort)
		printf '%s\n' 'ipvar EXTERNAL_NET 192.168.157.20/32' 'output alert_fast: alerts.log' 'alert udp any any -> $$EXTERNAL_NET any (msg:"Possible UDP Flood detected"; threshold: type threshold, track by_src, count 100, seconds 10; sid:1000003; rev:1;)' > "$$out/snort.conf"
		snort -T -c "$$out/snort.conf" -i lab0 > "$$out/snort-check.log" 2>&1
		snort -q -c "$$out/snort.conf" -i lab0 -l "$$out" -k none > "$$out/snort.log" 2>&1 & pids+=("$$!");;
	*) echo 'MODE não disponível. O filtro BPF adicional foi removido; XDP estático não está implementado no detector original.' >&2; exit 1;;
	esac
	sleep 2
	for pid in "$${pids[@]}"; do kill -0 "$$pid"; done
	echo "PRONTO: inicie a carga em generator. Resultados: $$out"
	date -u +%s.%N > "$$out/start-epoch.txt"
	# /proc: CPU e memória da VM compartilhada; rede do namespace da vítima.
	LC_ALL=C mpstat -P ALL 1 "$$DURATION" > "$$out/cpu.txt" & pids+=("$$!")
	LC_ALL=C sar -r 1 "$$DURATION" > "$$out/memory.txt" & pids+=("$$!")
	LC_ALL=C sar -n DEV 1 "$$DURATION" > "$$out/network.txt" & pids+=("$$!")
	for (( i=0; i<DURATION; i++ )); do
		sleep 1
		# Monitor/comparador deve continuar vivo durante a coleta.
		for (( j=0; j<$${#pids[@]}-3; j++ )); do kill -0 "$${pids[j]}"; done
	done
	for (( j=$${#pids[@]}-3; j<$${#pids[@]}; j++ )); do wait "$${pids[j]}"; done
	date -u +%s.%N > "$$out/end-epoch.txt"
	if (( chain )); then iptables-legacy -nvxL CHEN_LAB > "$$out/iptables-counters.txt"; fi

# Usa apenas o treinador que já existia. Não implementa a comparação da Fig. 7.
ml: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = target
	mkdir -p build/ml
	ln -sfn /workspace/dataset build/ml/dataset
	cd build/ml
	../../.venv/bin/python ../../xdp-flow-monitor-main/train_model.py | tee training.log
