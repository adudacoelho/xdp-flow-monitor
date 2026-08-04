#!/bin/bash
# Reexecuta o modo "ebpf" completo (throughput, CPU/memória, latência)
# Baseline e tcpdump já estão OK, não são refeitos.

set -e

VICTIM_CONTAINER="clab-xdp-ddos-vitima"
VICTIM_IP="172.20.20.6"
ATTACKER_CONTAINER="clab-xdp-ddos-atacante1"
HOST_IFACE="vethdbcc23c"
REAL_USER="${SUDO_USER:-$USER}"
FLOW_MONITOR_BIN="/home/${REAL_USER}/xdp-flow-monitor/xdp-flow-monitor-main/flow_monitor"
DURATION=120
RESULTS_DIR="/home/${REAL_USER}/teste_b_resultados"
PIDSTAT_BIN=$(command -v pidstat)

if [ ! -x "$FLOW_MONITOR_BIN" ]; then
    echo "ERRO: flow_monitor não encontrado ou sem permissão em $FLOW_MONITOR_BIN"
    exit 1
fi
if [ -z "$PIDSTAT_BIN" ]; then
    echo "ERRO: pidstat não encontrado."
    exit 1
fi

echo "Usando flow_monitor em: $FLOW_MONITOR_BIN"

# ---- Throughput ----
echo ">>> [ebpf] Throughput..."
docker exec -d "$VICTIM_CONTAINER" iperf3 -s -1
sleep 1
"$FLOW_MONITOR_BIN" "$HOST_IFACE" > "$RESULTS_DIR/ebpf_stdout.log" 2>&1 &
CAP_PID=$!
sleep 2
docker exec "$ATTACKER_CONTAINER" iperf3 -c "$VICTIM_IP" -t "$DURATION" -J \
    > "$RESULTS_DIR/throughput_ebpf.json"
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em throughput_ebpf.json"

sleep 3

# ---- CPU / Memória sob SYN flood ----
echo ">>> [ebpf] CPU/Memória sob SYN flood..."
"$FLOW_MONITOR_BIN" "$HOST_IFACE" > "$RESULTS_DIR/ebpf_stdout.log" 2>&1 &
CAP_PID=$!
sleep 2
"$PIDSTAT_BIN" -u -r -p "$CAP_PID" 1 "$DURATION" > "$RESULTS_DIR/cpu_mem_ebpf.log" &
PIDSTAT_PID=$!
docker exec "$ATTACKER_CONTAINER" timeout "$DURATION" \
    hping3 -S -p 80 --flood "$VICTIM_IP" > /dev/null 2>&1 || true
wait "$PIDSTAT_PID" 2>/dev/null || true
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em cpu_mem_ebpf.log"

sleep 3

# ---- Latência ----
echo ">>> [ebpf] Latência..."
"$FLOW_MONITOR_BIN" "$HOST_IFACE" > "$RESULTS_DIR/ebpf_stdout.log" 2>&1 &
CAP_PID=$!
sleep 2
docker exec "$ATTACKER_CONTAINER" ping -c "$DURATION" -i 1 "$VICTIM_IP" \
    > "$RESULTS_DIR/latency_ebpf.log"
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em latency_ebpf.log"

chown -R "$REAL_USER:$REAL_USER" "$RESULTS_DIR" 2>/dev/null || true
echo ""
echo "Modo ebpf refeito com sucesso em: $RESULTS_DIR"
