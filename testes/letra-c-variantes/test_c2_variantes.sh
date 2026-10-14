#!/bin/bash
# Teste C2: variantes da letra C
# Modos: baseline, iptables, xdp_min (so lookup no blacklist_map), xdp_full (flow_monitor)
# Flood com taxa limitada (hping3 -i u$INTERVAL_US). Tempo por pacote do XDP via bpf_stats.
set -u
[ "$EUID" -eq 0 ] || { echo "Rode com sudo"; exit 1; }

VICTIM_C="clab-xdp-ddos-vitima"
ATTACKER_C="clab-xdp-ddos-atacante1"
REAL_USER="${SUDO_USER:-$USER}"
BASE="/home/${REAL_USER}"
MON_BIN="$BASE/xdp-flow-monitor/xdp-flow-monitor-main/flow_monitor"
XMIN_OBJ="$BASE/xdp-letra-c/testes/letra-c-variantes/xdp_min.o"
DURATION="${DURATION:-60}"
NS="${NS:-1 64 512}"
INTERVAL_US="${INTERVAL_US:-10}"
XMIN_MODE="${XMIN_MODE:-xdp}"
OUT="$BASE/teste_c2_resultados"
PIN="/sys/fs/bpf/xmin"
mkdir -p "$OUT"
MON_PID=""; PID_PROG=""; MAPSPEC=""; S0="0 0"
OLD_STATS=$(cat /proc/sys/kernel/bpf_stats_enabled)

VICTIM_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$VICTIM_C")
IDX=$(docker exec "$ATTACKER_C" cat /sys/class/net/eth0/iflink)
IFACE=$(ip -o link | awk -F': ' -v i="$IDX" '$1==i{print $2}' | cut -d@ -f1)
VPID=$(docker inspect -f '{{.State.Pid}}' "$VICTIM_C")
if [ -z "$VICTIM_IP" ] || [ -z "$IFACE" ] || [ -z "$VPID" ]; then
    echo "Falha na descoberta: VICTIM_IP='$VICTIM_IP' IFACE='$IFACE' VPID='$VPID'"; exit 1
fi
[ -f "$XMIN_OBJ" ] || { echo "Nao achei $XMIN_OBJ"; exit 1; }
pgrep -x flow_monitor > /dev/null && { echo "flow_monitor ja esta rodando, feche antes"; exit 1; }
bpftool net show dev "$IFACE" | grep -q ' id ' && { echo "Ja existe XDP em $IFACE, remova antes"; exit 1; }
echo "Vitima: $VICTIM_IP | veth: $IFACE | duracao: ${DURATION}s | N: $NS | flood: -i u${INTERVAL_US} | xdp_min: $XMIN_MODE"
echo "$VICTIM_IP $IFACE intervalo_us=$INTERVAL_US xmin_mode=$XMIN_MODE" > "$OUT/descoberta.txt"
echo 1 > /proc/sys/kernel/bpf_stats_enabled

fake_ip() { echo "10.99.$(( $1 / 250 )).$(( $1 % 250 + 1 ))"; }
vns() { nsenter -t "$VPID" -n "$@"; }
ipt_fill()  { for ((i=0;i<$1;i++)); do vns iptables -A INPUT -s "$(fake_ip $i)" -j DROP; done; }
ipt_clear() { vns iptables -F INPUT; }

fill_map() {
    for ((i=0;i<$1;i++)); do
        IFS=. read -r a b c d <<< "$(fake_ip $i)"
        bpftool map update $MAPSPEC \
            key hex 20 00 00 00 $(printf '%02x %02x %02x %02x' "$a" "$b" "$c" "$d") \
            value hex 01 > /dev/null || return 1
    done
}
start_min() {
    mkdir -p "$PIN"
    bpftool prog load "$XMIN_OBJ" "$PIN/prog" pinmaps "$PIN" || return 1
    bpftool net attach "$XMIN_MODE" pinned "$PIN/prog" dev "$IFACE" || return 1
    MAPSPEC="pinned $PIN/blacklist_map"
}
stop_min() {
    bpftool net detach "$XMIN_MODE" dev "$IFACE" 2>/dev/null
    rm -rf "$PIN"
}
start_full() {
    "$MON_BIN" "$IFACE" > "$OUT/monitor_${1}.log" 2>&1 &
    MON_PID=$!
    sleep 3
    kill -0 "$MON_PID" 2>/dev/null || { echo "flow_monitor nao subiu"; MON_PID=""; return 1; }
    MAPSPEC="name blacklist_map"
}

stop_full() {
    if [ -n "$MON_PID" ]; then kill "$MON_PID" 2>/dev/null; wait "$MON_PID" 2>/dev/null; fi
    MON_PID=""; sleep 1
}
cleanup() {
    stop_full; stop_min
    ipt_clear 2>/dev/null
    docker exec "$ATTACKER_C" pkill hping3 2>/dev/null
    echo "$OLD_STATS" > /proc/sys/kernel/bpf_stats_enabled
    true
}
trap cleanup EXIT INT TERM

prog_id()    { bpftool net show dev "$IFACE" | grep -o ' id [0-9]*' | head -1 | awk '{print $2}'; }
prog_stats() { bpftool prog show id "$1" | grep -o 'run_time_ns [0-9]*\|run_cnt [0-9]*' | awk '{print $2}' | paste -sd' '; }
stats_begin() { [ -n "$PID_PROG" ] && S0=$(prog_stats "$PID_PROG"); true; }
stats_end() {
    [ -n "$PID_PROG" ] || return 0
    local S1 t0 c0 t1 c1
    S1=$(prog_stats "$PID_PROG")
    read -r t0 c0 <<< "$S0"; read -r t1 c1 <<< "$S1"
    awk -v dt=$((t1-t0)) -v dc=$((c1-c0)) 'BEGIN{ if(dc>0) printf "ns_por_pacote=%.1f pacotes=%d\n", dt/dc, dc; else print "sem pacotes" }' > "$OUT/xdp_ns_${1}_${tag}.txt"
}
rxstat() { cat "/sys/class/net/$IFACE/statistics/$1"; }

run_one() {
    local mode=$1 n=$2 tag="${1}_${2}"
    echo ">>> [$tag]"
    PID_PROG=""; MAPSPEC=""
    case $mode in
        iptables) ipt_fill "$n"
                  vns iptables -S INPUT | grep -c DROP > "$OUT/regras_${tag}.txt" ;;
        xdp_min)  start_min || return 1
                  fill_map "$n" || { echo "falha ao preencher"; stop_min; return 1; }
                  PID_PROG=$(prog_id)
                  bpftool map dump $MAPSPEC | grep -c key > "$OUT/regras_${tag}.txt" ;;
        xdp_full) start_full "$tag" || return 1
                  fill_map "$n" || { echo "falha ao preencher"; stop_full; return 1; }
                  PID_PROG=$(prog_id)
                  bpftool map dump $MAPSPEC | grep -c key > "$OUT/regras_${tag}.txt" ;;
    esac
    [ -n "$PID_PROG" ] && bpftool net show dev "$IFACE" > "$OUT/netshow_${tag}.txt"
    sleep 2

    docker exec -d "$VICTIM_C" iperf3 -s -1
    sleep 1
    stats_begin
    docker exec "$ATTACKER_C" iperf3 -c "$VICTIM_IP" -t "$DURATION" -J > "$OUT/throughput_${tag}.json"
    stats_end iperf
    sleep 3
    free -m > "$OUT/mem_${tag}.txt"
    vmstat 1 "$DURATION" > "$OUT/cpu_vmstat_${tag}.log" &
    local vm_pid=$! pd_pid=""

    if [ "$mode" = "xdp_full" ]; then
        pidstat -u -r -p "$MON_PID" 1 "$DURATION" > "$OUT/cpu_mem_monitor_${tag}.log" &
        pd_pid=$!
    fi
    local p0 p1
    p0=$(rxstat rx_packets)
    stats_begin
    docker exec "$ATTACKER_C" timeout "$DURATION" hping3 -S -p 80 --flood "$VICTIM_IP" > /dev/null 2>&1 || true
    stats_end flood
    p1=$(rxstat rx_packets)
    wait "$vm_pid" 2>/dev/null
    [ -n "$pd_pid" ] && wait "$pd_pid" 2>/dev/null
    free -m >> "$OUT/mem_${tag}.txt"
    echo "pps=$(( (p1-p0)/DURATION ))" > "$OUT/flood_rate_${tag}.txt"
    cat "$OUT/flood_rate_${tag}.txt"
    [ -f "$OUT/xdp_ns_flood_${tag}.txt" ] && cat "$OUT/xdp_ns_flood_${tag}.txt"
    case $mode in
        iptables) ipt_clear ;;
        xdp_min)  stop_min ;;
        xdp_full) stop_full ;;
    esac
    sleep 3
}

run_one baseline 0
for n in $NS; do run_one iptables "$n"; done
for n in $NS; do run_one xdp_min "$n"; done
for n in $NS; do run_one xdp_full "$n"; done
run_one baseline 1

chown -R "$REAL_USER:$REAL_USER" "$OUT" 2>/dev/null || true
echo "Concluido. Resultados em: $OUT"
