# DENTRO DOS CONTAINERS: comandos usados pelos roteiros 4B–4E.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

REPO_ROOT := $(shell cd ../../.. && pwd)
export REPO_ROOT

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

.PHONY: help check build serve traffic observe ml
help:
	@echo 'DENTRO DO CONTAINER: check build serve traffic observe ml'
	echo 'observe MODE=baseline|tshark|collection-current|detector-current|iptables|snort'
	echo 'traffic KIND=tcp|latency|syn|udp|replay DURATION=120 PPS=5000'

# DENTRO DO CONTAINER: valida o nó, o servidor de origem e o enlace isolado.
# Abra o shell com clab-shell; ele já inicia na pasta containers.
check:
	@test -e /.dockerenv
	test "$$(cat /etc/xdp-chen-host)" = servidor
	test "$$(stat -c %u /etc/xdp-chen-host)" = 0
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
cat /etc/xdp-chen-host > "$$out/environment.txt"
cat /etc/os-release > "$$out/container-os.txt"
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
# PCAP é relativo à raiz /workspace, mesmo chamando make na pasta containers.
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
	# /proc: CPU e memória do servidor compartilhado; rede do namespace da vítima.
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
