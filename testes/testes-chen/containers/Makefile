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
DATA ?= /workspace/dataset/Syn.csv
DURATION_UNIT ?= us
MAX_ROWS ?= 20000
CV ?= 0
JOBS ?= 2
export DATA DURATION_UNIT MAX_ROWS CV JOBS
export NODE MODE KIND DURATION PPS RULES RUN PCAP SERVICE

.PHONY: help check build serve traffic observe ml ml-evaluate test-window
help:
	@echo 'DENTRO DO CONTAINER: check build serve traffic observe ml'
	echo 'observe MODE=baseline|tshark|collection-current|detector-current|xdp-static|iptables|snort'
	echo 'traffic KIND=tcp|latency|syn|udp|replay DURATION=120 PPS=5000'
	echo 'ml-evaluate DATA=/workspace/dataset/Syn.csv MAX_ROWS=20000 CV=0 JOBS=2'
	echo 'ml DATA=/workspace/dataset/Syn.csv; test-window'

# DENTRO DO CONTAINER: valida o nó, o servidor de origem e o enlace isolado.
# Abra o shell com clab-shell; ele já inicia na pasta containers.
check:
	@test -e /.dockerenv
	test "$$(cat /etc/xdp-chen-host)" = servidor
	test "$$(stat -c %u /etc/xdp-chen-host)" = 0
	role=$$(cat /etc/xdp-chen-lab)
	case "$$role" in target) local_ip=192.168.157.20; peer=192.168.157.10;; generator) local_ip=192.168.157.10; peer=192.168.157.20;; *) exit 1;; esac
	if [ "$$(cat /sys/class/net/lab0/mtu)" != 1500 ]; then
		echo 'ERRO: lab0 deve usar MTU 1500 nas duas pontas. Atualize e recrie o laboratório pelo roteiro do servidor.' >&2
		exit 1
	fi
	ip -o -4 addr show dev lab0 | grep -Fq "$$local_ip/24"
	test -z "$$(ip -4 route show default)"
	ip -4 route get "$$peer" | grep -q 'dev lab0'
	test "$$(cat /proc/sys/net/ipv4/ip_forward)" = 0

# DENTRO DO CONTAINER: compila o detector, seu skeleton e o filtro estático IV-C.
# Artefatos ficam em /workspace/build; nenhum programa é anexado nesta etapa.
build: check
	cd "$$REPO_ROOT"
	mkdir -p build
	test "$$(uname -m)" = x86_64
	clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -D__x86_64__ -I "/usr/include/$$(gcc -print-multiarch)" -I xdp-flow-monitor-main -c xdp-flow-monitor-main/flow_monitor.bpf.c -o build/flow_monitor.bpf.o
	bpftool gen skeleton build/flow_monitor.bpf.o > build/flow_monitor.skel.h
	cp xdp-flow-monitor-main/main.c build/main.c
	gcc -O2 -g -Wall -I build -I xdp-flow-monitor-main build/main.c xdp-flow-monitor-main/window.c -o build/flow_monitor -lbpf -lelf -lz

	clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -I "/usr/include/$$(gcc -print-multiarch)" -c testes/letra-c-variantes/xdp_min.c -o build/xdp_min.bpf.o

# Validação de parâmetros repetida por expansão textual do Makefile, sem scripts.
define parameters
duration_limit=600
if [ "$@" = serve ]; then duration_limit=1200; fi
[[ "$$DURATION" =~ ^[0-9]+$$ ]] && (( DURATION >= 1 && DURATION <= duration_limit ))
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
	exec 8>/run/chen-service.lock
	flock -n 8 || { echo 'ERRO: outro serviço do laboratório já está ativo. Encerre-o no terminal 1.' >&2; exit 1; }
	listeners=$$(ss -H -ltnp 'sport = :80')
	if [ -n "$$listeners" ]; then
		echo 'ERRO: porta TCP 80 ocupada. Encerre o serviço anterior antes de iniciar iperf/Ethr.' >&2
		printf '%s\n' "$$listeners" >&2
		exit 1
	fi
	case "$$SERVICE" in
	iperf) command=(iperf3 -s -B 192.168.157.20 -p 80 -J);;
	ethr) command=(ethr -s -ip 192.168.157.20 -port 80 -o "$$out/ethr.json");;
	*) echo 'SERVICE=iperf ou ethr' >&2; exit 1;; esac
	# Preserva o grupo de primeiro plano para o serviço receber Ctrl+C do terminal.
	echo "Iniciando $$SERVICE por até $$DURATION s. Ctrl+C encerra o serviço. Log: $$out/server.log"
	rc=0; timeout --foreground --signal=TERM --kill-after=5 "$$DURATION" "$${command[@]}" > "$$out/server.log" 2>&1 || rc=$$?
	if [[ $$rc != 0 && $$rc != 124 && $$rc != 130 ]] || grep -Eqi 'Fatal error|unable to start listener' "$$out/server.log"; then
		cat "$$out/server.log" >&2
		exit 1
	fi

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
	if [ "$$KIND" = latency ]; then
		if grep -Eqi 'Failed|Fatal error' "$$out/ethr.log" || ! grep -q '"Type":"LatencyResult"' "$$out/ethr.json"; then
			echo 'ERRO: Ethr falhou ou não produziu amostras. Confira o serviço Ethr no terminal 1.' >&2
			cat "$$out/ethr.log" >&2
			exit 1
		fi
	fi
	date -u +%s.%N > "$$out/end-epoch.txt"

# DENTRO DO CONTAINER target: executa o comparador e registra as métricas.
observe: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = target
	$(parameters)
	exec 9>/run/chen-observe.lock; flock -n 9
	if ip -j -details link show lab0 | python3 -c 'import json,sys; sys.exit(0 if any(d.get("xdp", {}).get("attached", 0) for d in json.load(sys.stdin)) else 1)'; then echo 'Já há XDP anexado em lab0. Encerre a execução anterior.' >&2; exit 1; fi
	pids=(); chain=0; jump=0; ml_started=0; static_started=0; pin=""; capture_pid=""
	cleanup_observe() {
		rc=$$?
		trap - EXIT INT TERM
		set +e
		printf 'exit_code=%s\n' "$$rc" > "$$out/status.txt"
		echo "Encerrando processos da observação (até 5 s de tolerância)..."
		if [ -n "$$capture_pid" ]; then kill -TERM -- "-$$capture_pid" 2>/dev/null; fi
		for pid in "$${pids[@]}"; do kill -TERM "$$pid" 2>/dev/null; done
		deadline=$$((SECONDS+5))
		while (( SECONDS < deadline )); do
			alive=0
			for pid in $$(jobs -pr); do alive=1; done
			if [ -n "$$capture_pid" ] && kill -0 -- "-$$capture_pid" 2>/dev/null; then alive=1; fi
			(( alive )) || break
			sleep 0.1
		done
		if [ -n "$$capture_pid" ] && kill -0 -- "-$$capture_pid" 2>/dev/null; then
			echo 'TShark/dumpcap excedeu a tolerância; encerramento forçado.' | tee -a "$$out/shutdown.log"
			kill -KILL -- "-$$capture_pid" 2>/dev/null
		fi
		for pid in $$(jobs -pr); do kill -KILL "$$pid" 2>/dev/null; done
		for pid in "$${pids[@]}"; do wait "$$pid" 2>/dev/null; done
		if (( static_started )); then bpftool net detach xdp dev lab0; fi
		if [ -n "$$pin" ]; then rm -f "$$pin/prog" "$$pin/blacklist_map"; rmdir "$$pin"; fi
		if (( jump )); then iptables-legacy -D INPUT -i lab0 -j CHEN_LAB; fi
		if (( chain )); then iptables-legacy -F CHEN_LAB; iptables-legacy -X CHEN_LAB; fi
		if (( ml_started )); then rm -f /tmp/ml_engine.sock; fi
		date -u +%s.%N > "$$out/cleanup-end-epoch.txt"
		echo "Observação encerrada (código $$rc). Resultados: $$out"
		exit "$$rc"
	}
	trap cleanup_observe EXIT
	trap 'exit 130' INT
	trap 'exit 143' TERM
	case "$$MODE" in
	baseline) ;;
	tshark) setsid tshark -n -l -i lab0 > "$$out/tshark.log" 2>&1 9>&- & capture_pid=$$!; pids+=("$$capture_pid");;
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
	xdp-static)
		[[ "$$RULES" =~ ^[0-9]+$$ ]] && (( RULES >= 6 && RULES <= 512 ))
		test -f build/xdp_min.bpf.o
		pin=$$(mktemp -d /sys/fs/bpf/chen-static-XXXXXX)
		bpftool prog load build/xdp_min.bpf.o "$$pin/prog" pinmaps "$$pin"
		for (( i=1; i<=RULES-6; i++ )); do
			bpftool map update pinned "$$pin/blacklist_map" key hex 20 00 00 00 c6 12 $$(printf '%02x %02x' "$$((i/256))" "$$((i%256))") value hex 01
		done
		for i in {101..106}; do
			bpftool map update pinned "$$pin/blacklist_map" key hex 20 00 00 00 c0 a8 9d $$(printf '%02x' "$$i") value hex 01
		done
		bpftool -j map dump pinned "$$pin/blacklist_map" > "$$out/xdp-rules.json"
		bpftool net attach xdp pinned "$$pin/prog" dev lab0; static_started=1
		bpftool -j prog show pinned "$$pin/prog" > "$$out/xdp-program.json";;
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
	*) echo 'MODE não disponível. Use baseline, tshark, collection-current, detector-current, xdp-static, iptables ou snort.' >&2; exit 1;;
	esac
	sleep 2
	for pid in "$${pids[@]}"; do
		if ! kill -0 "$$pid" 2>/dev/null; then
			echo "ERRO: coletor/comparador encerrou antes de PRONTO. Consulte $$out" >&2
			if [ -f "$$out/monitor.log" ]; then cat "$$out/monitor.log" >&2; fi
			exit 1
		fi
	done
	case "$$MODE" in collection-current|detector-current|xdp-static)
		ip -j -details link show lab0 > "$$out/xdp-attached.json"
		if ! python3 -c 'import json,sys; sys.exit(0 if any(d.get("xdp", {}).get("attached", 0) for d in json.load(open(sys.argv[1]))) else 1)' "$$out/xdp-attached.json"; then
			echo 'ERRO: XDP não está anexado; rodada cancelada antes de PRONTO.' >&2
			if [ -f "$$out/monitor.log" ]; then cat "$$out/monitor.log" >&2; fi
			exit 1
		fi;;
	esac
	# Duração limitada evita coleta esquecida; não garante tráfego constante.
	# Analise o intervalo da carga para não misturar ociosidade com tráfego.
	echo "ATENÇÃO: a observação termina automaticamente após $$DURATION segundos; não espera pelo gerador."
	echo 'Deixe o comando de tráfego preparado e execute imediatamente após PRONTO.'
	echo 'No roteiro 4B, a margem é de 20 s: procure iniciar em até 10 s e confira os horários registrados.'
	echo 'Analise somente o período da carga; incluir ociosidade pode distorcer CPU e memória.'
	echo "PRONTO: inicie a carga em generator. Resultados: $$out"
	date -u +%s.%N > "$$out/start-epoch.txt"
	# /proc: CPU e memória do servidor compartilhado; rede do namespace da vítima.
	LC_ALL=C mpstat -P ALL 1 "$$DURATION" > "$$out/cpu.txt" & pids+=("$$!")
	LC_ALL=C sar -r 1 "$$DURATION" > "$$out/memory.txt" & pids+=("$$!")
	LC_ALL=C sar -n DEV 1 "$$DURATION" > "$$out/network.txt" & pids+=("$$!")
	for (( i=0; i<DURATION; i++ )); do
		sleep 1
		# Monitor/comparador deve continuar vivo durante a coleta.
		for (( j=0; j<$${#pids[@]}-3; j++ )); do
			if ! kill -0 "$${pids[j]}" 2>/dev/null; then echo "ERRO: processo $${pids[j]} encerrou durante a observação. Consulte $$out" >&2; exit 1; fi
		done
	done
	echo "Coleta de métricas concluída; aguardando os arquivos de CPU, memória e rede."
	for (( j=$${#pids[@]}-3; j<$${#pids[@]}; j++ )); do wait "$${pids[j]}"; done
	date -u +%s.%N > "$$out/end-epoch.txt"
	if (( chain )); then iptables-legacy -nvxL CHEN_LAB > "$$out/iptables-counters.txt"; fi

# Artefatos de ML ficam no volume persistente de resultados.
ml ml-evaluate: check
	cd "$$REPO_ROOT"
	test "$$(cat /etc/xdp-chen-lab)" = target
	$(parameters)
	test -e "$$DATA"
	sha256sum xdp-flow-monitor-main/features.py xdp-flow-monitor-main/train_model.py xdp-flow-monitor-main/evaluate_models.py > "$$out/code.sha256"
	if [ -d "$$DATA" ]; then find "$$DATA" -maxdepth 1 -type f -name '*.csv' -exec sha256sum {} +; else sha256sum "$$DATA"; fi > "$$out/dataset.sha256"
	printf 'DATA=%s\nDURATION_UNIT=%s\nMAX_ROWS=%s\nCV=%s\nJOBS=%s\n' "$$DATA" "$$DURATION_UNIT" "$$MAX_ROWS" "$$CV" "$$JOBS" > "$$out/ml-parameters.txt"
	if [ "$@" = ml ]; then
		.venv/bin/python -u xdp-flow-monitor-main/train_model.py --data "$$DATA" --duration-unit "$$DURATION_UNIT" --out "$$out/ddos_model.ubj" | tee "$$out/training.log"
	else
		.venv/bin/python -u xdp-flow-monitor-main/evaluate_models.py --data "$$DATA" --duration-unit "$$DURATION_UNIT" --max-rows "$$MAX_ROWS" --cv "$$CV" --jobs "$$JOBS" --out "$$out" | tee "$$out/evaluation.log"
	fi
	echo "Resultados persistentes: $$out"

test-window:
	cd "$$REPO_ROOT"
	mkdir -p build
	gcc -O2 -Wall -Wextra xdp-flow-monitor-main/test_window.c xdp-flow-monitor-main/window.c -o build/test_window
	build/test_window
