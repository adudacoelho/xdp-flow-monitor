#!/bin/bash
IFLINK=$(docker exec clab-xdp-ddos-atacante1 cat /sys/class/net/eth0/iflink)
IFACE=$(ip link show | grep "^${IFLINK}:" | awk -F': ' '{print $2}' | cut -d'@' -f1)
echo "Interface atacante1: $IFACE"
sudo ./flow_monitor $IFACE
