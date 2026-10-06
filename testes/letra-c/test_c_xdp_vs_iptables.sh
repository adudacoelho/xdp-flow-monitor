#!/bin/bash
# Teste C: XDP vs iptables com 1 a 512 regras (Fig. 6 do artigo)
# iptables: regras DROP no INPUT do netns da vitima (br_netfilter nao esta carregado)
# XDP: mesmas N entradas no blacklist_map, flow_monitor SEM ml_daemon (nao bloqueia sozinho)
# As N regras sao IPs falsos (10.99.x.x) que NAO casam com o trafego: o pacote percorre a lista toda.
set -u
[ "$EUID" -eq 0 ] || { echo "Rode com sudo"; exit 1; }

VICTIM_C="clab-xdp-ddos-vitima"
ATTACKER_C="clab-xdp-ddos-atacante1"
REAL_USER="${SUDO_USER:-$USER}"
MON_BIN="/home/${REAL_USER}/xdp-flow-monitor/xdp-flow-monitor-main/flow_monitor"
DURATION="${DURATION:-60}"
NS="${NS:-1 2 4 8 16 32 64 128 256 512}"
OUT="/home/${REAL_USER}/teste_c_resultados"
mkdir -p "$OUT"
MON_PID=""

# ===== descoberta automatica (IPs e veths mudam a cada reinicio) =====
VICTIM_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$VICTIM_C")
IDX=$(docker exec "$ATTACKER_C" cat /sys/class/net/eth0/iflink)
IFACE=$(ip -o link | awk -F': ' -v i="$IDX" '$1==i{print $2}' | cut -d@ -f1)
VPID=$(docker inspect -f '{{.State.Pid}}' "$VICTIM_C")
if [ -z "$VICTIM_IP" ] || [ -z "$IFACE" ] || [ -z "$VPID" ]; then
    echo "Falha na descoberta: VICTIM_IP='$VICTIM_IP' IFACE='$IFACE' VPID='$VPID'"; exit 1
fi
echo "Vitima: $VICTIM_IP | veth do atacante1: $IFACE | duracao: ${DURATION}s | N: $NS"
echo "$VICTIM_IP $IFACE" > "$OUT/descoberta.txt"

fake_ip() { echo "10.99.$(( $1 / 250 )).$(( $1 % 250 + 1 ))"; }
vns() { nsenter -t "$VPID" -n "$@"; }

ipt_fill()  { for ((i=0;i<$1;i++)); do vns iptables -A INPUT -s "$(fake_ip $i)" -j DROP; done; }
ipt_clear() { vns iptables -F INPUT; }

xdp_fill() {
    for ((i=0;i<$1;i++)); do
        IFS=. read -r a b c d <<< "$(fake_ip $i)"
        bpftool map update name blacklist_map \
            key hex 20 00 00 00 $(printf '%02x %02x %02x %02x' "$a" "$b" "$c" "$d") \
            value hex 01 > /dev/null || return 1
    done
}
start_xdp() {
    "$MON_BIN" "$IFACE" > "$OUT/monitor_${1}.log" 2>&1 &
    MON_PID=$!
    sleep 3
    kill -0 "$MON_PID" 2>/dev/null || { echo "flow_monitor nao subiu, veja monitor_${1}.log"; MON_PID=""; return 1; }
}
stop_xdp() {
    if [ -n "$MON_PID" ]; then kill "$MON_PID" 2>/dev/null; wait "$MON_PID" 2>/dev/null; fi
    MON_PID=""
}
cleanup() { stop_xdp; ipt_clear 2>/dev/null; docker exec "$ATTACKER_C" pkill hping3 2>/dev/null; true; }
trap cleanup EXIT INT TERM

rxstat() { cat "/sys/class/net/$IFACE/statistics/$1"; }

run_one() {
    local mode=$1 n=$2 tag="${1}_${2}"
    echo ">>> [$tag]"
    case $mode in
        iptables) ipt_fill "$n" ;;
        xdp) start_xdp "$tag" || return 1
             xdp_fill "$n" || { echo "falha ao preencher o mapa"; stop_xdp; return 1; } ;;
    esac
    sleep 2
    case $mode in iptables) vns iptables -S INPUT | grep -c DROP > "$OUT/regras_${tag}.txt" ;; xdp) bpftool map dump name blacklist_map | grep -c key > "$OUT/regras_${tag}.txt" ;; esac

    # --- throughput (Fig. 6a): iperf3 sem ataque ---
    docker exec -d "$VICTIM_C" iperf3 -s -1
    sleep 1
    docker exec "$ATTACKER_C" iperf3 -c "$VICTIM_IP" -t "$DURATION" -J > "$OUT/throughput_${tag}.json"
    sleep 3

    # --- CPU e memoria sob SYN flood (Fig. 6b/6c) ---
    free -m > "$OUT/mem_${tag}.txt"
    vmstat 1 "$DURATION" > "$OUT/cpu_vmstat_${tag}.log" &
    local vm_pid=$!
    local pd_pid=""
    if [ "$mode" = "xdp" ]; then
        pidstat -u -r -p "$MON_PID" 1 "$DURATION" > "$OUT/cpu_mem_monitor_${tag}.log" &
        pd_pid=$!
    fi
    local p0 b0 p1 b1
    p0=$(rxstat rx_packets); b0=$(rxstat rx_bytes)
    docker exec "$ATTACKER_C" timeout "$DURATION" hping3 -S -p 80 --flood "$VICTIM_IP" > /dev/null 2>&1 || true
    p1=$(rxstat rx_packets); b1=$(rxstat rx_bytes)
    wait "$vm_pid" 2>/dev/null
    [ -n "$pd_pid" ] && wait "$pd_pid" 2>/dev/null
    free -m >> "$OUT/mem_${tag}.txt"
    echo "pps=$(( (p1-p0)/DURATION )) gbps=$(awk -v b=$((b1-b0)) -v d=$DURATION 'BEGIN{printf "%.3f", b*8/d/1e9}')" > "$OUT/flood_rate_${tag}.txt"
    cat "$OUT/flood_rate_${tag}.txt"

    case $mode in
        iptables) ipt_clear ;;
        xdp) stop_xdp ;;
    esac
    sleep 3
}

run_one baseline 0
for n in $NS; do run_one iptables "$n"; done
for n in $NS; do run_one xdp "$n"; done
run_one baseline 1

chown -R "$REAL_USER:$REAL_USER" "$OUT" 2>/dev/null || true
echo "Concluido. Resultados em: $OUT"
