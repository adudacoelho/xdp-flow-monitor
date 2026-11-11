#!/bin/bash
# Teste B — Performance of eBPF (equivalente à Fig. 5 do artigo)
# Compara: baseline (sem captura) vs eBPF (flow_monitor) vs tcpdump
# Métricas: throughput, CPU, memória, latência

set -e

# ===== CONFIGURAÇÃO — ajuste se os IPs/nomes mudarem =====
VICTIM_CONTAINER="clab-xdp-ddos-vitima"
VICTIM_IP="172.20.20.6"
ATTACKER_CONTAINER="clab-xdp-ddos-atacante1"
ATTACKER_IP="172.20.20.3"
HOST_IFACE="vethdbcc23c"          # interface do atacante1 no host
FLOW_MONITOR_BIN="$HOME/xdp-flow-monitor/xdp-flow-monitor-main/flow_monitor"

DURATION=120                       # segundos por sub-teste (igual ao artigo)
REAL_USER="${SUDO_USER:-$USER}"
RESULTS_DIR="/home/${REAL_USER}/teste_b_resultados"
mkdir -p "$RESULTS_DIR"
chown "$REAL_USER:$REAL_USER" "$RESULTS_DIR" 2>/dev/null || true

# Caminho completo do pidstat, pra não depender do $PATH do sudo
PIDSTAT_BIN=$(command -v pidstat || echo /usr/bin/pidstat)

# ===== FUNÇÕES DE CAPTURA =====

start_capture() {
    local mode=$1
    case $mode in
        baseline)
            echo "" # nada a iniciar
            ;;
        ebpf)
            sudo "$FLOW_MONITOR_BIN" "$HOST_IFACE" > "$RESULTS_DIR/ebpf_stdout.log" 2>&1 &
            echo $!
            ;;
        tcpdump)
            sudo tcpdump -i "$HOST_IFACE" -w "$RESULTS_DIR/tcpdump_capture.pcap" > /dev/null 2>&1 &
            echo $!
            ;;
    esac
}

stop_capture() {
    local mode=$1
    local pid=$2
    if [ "$mode" != "baseline" ] && [ -n "$pid" ]; then
        sudo kill "$pid" 2>/dev/null || true
        sleep 1
    fi
}

# ===== SUB-TESTE 1: THROUGHPUT (equivalente Fig. 5a) =====
# iperf3 server na vítima, client no atacante1, sem ataque.

run_throughput_test() {
    local mode=$1
    echo ">>> [$mode] Throughput..."

    docker exec -d "$VICTIM_CONTAINER" iperf3 -s -1
    sleep 1

    local cap_pid
    cap_pid=$(start_capture "$mode")
    sleep 2

    docker exec "$ATTACKER_CONTAINER" iperf3 -c "$VICTIM_IP" -t "$DURATION" -J \
        > "$RESULTS_DIR/throughput_${mode}.json"

    stop_capture "$mode" "$cap_pid"
    echo "    salvo em throughput_${mode}.json"
}

# ===== SUB-TESTE 2: CPU e MEMÓRIA sob ataque (equivalente Fig. 5b/5c) =====
# hping3 SYN flood do atacante1 para a vítima; pidstat monitora o processo de captura.

run_cpu_mem_test() {
    local mode=$1
    echo ">>> [$mode] CPU/Memória sob SYN flood..."

    local cap_pid
    cap_pid=$(start_capture "$mode")
    sleep 2

    if [ "$mode" != "baseline" ]; then
        "$PIDSTAT_BIN" -u -r -p "$cap_pid" 1 "$DURATION" > "$RESULTS_DIR/cpu_mem_${mode}.log" &
        local pidstat_pid=$!
    fi

    # SYN flood — ajuste -i unXXXXX (velocidade) conforme sua VM aguentar
    docker exec "$ATTACKER_CONTAINER" timeout "$DURATION" \
        hping3 -S -p 80 --flood "$VICTIM_IP" > /dev/null 2>&1 || true

    if [ "$mode" != "baseline" ]; then
        wait "$pidstat_pid" 2>/dev/null || true
    fi

    stop_capture "$mode" "$cap_pid"
    echo "    salvo em cpu_mem_${mode}.log"
}

# ===== SUB-TESTE 3: LATÊNCIA (equivalente Fig. 5d) =====
# ping do atacante1 para a vítima, sem ataque.

run_latency_test() {
    local mode=$1
    echo ">>> [$mode] Latência..."

    local cap_pid
    cap_pid=$(start_capture "$mode")
    sleep 2

    docker exec "$ATTACKER_CONTAINER" ping -c "$DURATION" -i 1 "$VICTIM_IP" \
        > "$RESULTS_DIR/latency_${mode}.log"

    stop_capture "$mode" "$cap_pid"
    echo "    salvo em latency_${mode}.log"
}

# ===== EXECUÇÃO =====

for mode in baseline ebpf tcpdump; do
    echo "===== Modo: $mode ====="
    run_throughput_test "$mode"
    sleep 3
    run_cpu_mem_test "$mode"
    sleep 3
    run_latency_test "$mode"
    sleep 3
done

chown -R "$REAL_USER:$REAL_USER" "$RESULTS_DIR" 2>/dev/null || true

echo ""
echo "Testes concluídos. Resultados em: $RESULTS_DIR"
