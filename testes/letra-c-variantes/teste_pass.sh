#!/bin/bash
[ "$EUID" -eq 0 ] || { echo "Rode com sudo"; exit 1; }
cd "$(dirname "$0")"
IDX=$(docker exec clab-xdp-ddos-atacante1 cat /sys/class/net/eth0/iflink)
IFACE=$(ip -o link | awk -F': ' -v i="$IDX" '$1==i{print $2}' | cut -d@ -f1)
VIC=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' clab-xdp-ddos-vitima)
cleanup() { bpftool net detach xdp dev "$IFACE" 2>/dev/null; rm -f /sys/fs/bpf/xpass; }
trap cleanup EXIT
echo "veth=$IFACE vitima=$VIC"
bpftool net show dev "$IFACE" | grep -q ' id ' && { echo "ja existe XDP na veth, remova antes"; exit 1; }
for modo in sem_xdp com_xdp_pass sem_xdp_2; do
  if [ "$modo" = com_xdp_pass ]; then
    bpftool prog load xdp_pass.o /sys/fs/bpf/xpass || exit 1
    bpftool net attach xdp pinned /sys/fs/bpf/xpass dev "$IFACE" || exit 1
    bpftool net show dev "$IFACE" | grep "$IFACE"
  fi
  docker exec -d clab-xdp-ddos-vitima iperf3 -s -1
  sleep 1
  echo "--- $modo"
  docker exec clab-xdp-ddos-atacante1 iperf3 -c "$VIC" -t 20 | grep -E "sender|receiver"
  if [ "$modo" = com_xdp_pass ]; then cleanup; fi
  sleep 3
done
