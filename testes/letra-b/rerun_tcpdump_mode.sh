#!/bin/bash
# Reexecuta o modo "tcpdump" completo (throughput, CPU/memória, latência)
# Corrige o bug do sudo duplicado que fazia o pidstat medir o processo errado.

set -e

VICTIM_CONTAINER="clab-xdp-ddos-vitima"
VICTIM_IP="172.20.20.6"
ATTACKER_CONTAINER="clab-xdp-ddos-atacante1"
HOST_IFACE="vethdbcc23c"
REAL_USER="${SUDO_USER:-$USER}"
DURATION=120
RESULTS_DIR="/home/${REAL_USER}/teste_b_resultados"
PIDSTAT_BIN=$(command -v pidstat)

if [ -z "$PIDSTAT_BIN" ]; then
    echo "ERRO: pidstat não encontrado."
    exit 1
fi

# ---- Throughput ----
echo ">>> [tcpdump] Throughput..."
docker exec -d "$VICTIM_CONTAINER" iperf3 -s -1
sleep 1
tcpdump -i "$HOST_IFACE" -w "$RESULTS_DIR/tcpdump_capture.pcap" > /dev/null 2>&1 &
CAP_PID=$!
sleep 2
docker exec "$ATTACKER_CONTAINER" iperf3 -c "$VICTIM_IP" -t "$DURATION" -J \
    > "$RESULTS_DIR/throughput_tcpdump.json"
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em throughput_tcpdump.json"

sleep 3

# ---- CPU / Memória sob SYN flood ----
echo ">>> [tcpdump] CPU/Memória sob SYN flood..."
tcpdump -i "$HOST_IFACE" -w "$RESULTS_DIR/tcpdump_capture.pcap" > /dev/null 2>&1 &
CAP_PID=$!
sleep 2
"$PIDSTAT_BIN" -u -r -p "$CAP_PID" 1 "$DURATION" > "$RESULTS_DIR/cpu_mem_tcpdump.log" &
PIDSTAT_PID=$!
docker exec "$ATTACKER_CONTAINER" timeout "$DURATION" \
    hping3 -S -p 80 --flood "$VICTIM_IP" > /dev/null 2>&1 || true
wait "$PIDSTAT_PID" 2>/dev/null || true
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em cpu_mem_tcpdump.log"

sleep 3

# ---- Latência ----
echo ">>> [tcpdump] Latência..."
tcpdump -i "$HOST_IFACE" -w "$RESULTS_DIR/tcpdump_capture.pcap" > /dev/null 2>&1 &
CAP_PID=$!
sleep 2
docker exec "$ATTACKER_CONTAINER" ping -c "$DURATION" -i 1 "$VICTIM_IP" \
    > "$RESULTS_DIR/latency_tcpdump.log"
kill "$CAP_PID" 2>/dev/null || true
sleep 1
echo "    salvo em latency_tcpdump.log"

chown -R "$REAL_USER:$REAL_USER" "$RESULTS_DIR" 2>/dev/null || true
echo ""
echo "Modo tcpdump refeito com sucesso em: $RESULTS_DIR"
