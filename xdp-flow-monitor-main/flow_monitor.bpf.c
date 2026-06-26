#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/in.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/icmp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
#include "common.h"

// Chave do Fluxo (5-tuple completo)
struct flow_key {
    __u32 src_ip;    // 4 bytes
    __u32 dst_ip;    // 4 bytes
    __u16 src_port;  // 2 bytes  — para ICMP: type
    __u16 dst_port;  // 2 bytes  — para ICMP: code
    __u8  protocol;  // 1 byte
    __u8  pad[3];    // 3 bytes de padding para fechar em 16 bytes exatos
};

// Mapa Hash de fluxos
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, struct flow_key);
    __type(value, struct flow_metrics);
} flow_map SEC(".maps");

// Ring Buffer
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

SEC("xdp")
int network_flow_monitor(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end) return XDP_PASS;

    __u32 pkt_len = data_end - data;

    // Inicialização da chave 5-tuple
    struct flow_key key = {0};
    key.src_ip   = ip->saddr;
    key.dst_ip   = ip->daddr;
    key.protocol = ip->protocol;

    struct tcphdr *tcp = NULL;

    if (ip->protocol == IPPROTO_TCP) {
        tcp = (void *)ip + (ip->ihl * 4);
        if ((void *)(tcp + 1) > data_end) return XDP_PASS;
        key.src_port = tcp->source;
        key.dst_port = tcp->dest;

    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = (void *)ip + (ip->ihl * 4);
        if ((void *)(udp + 1) > data_end) return XDP_PASS;
        key.src_port = udp->source;
        key.dst_port = udp->dest;

    } else if (ip->protocol == IPPROTO_ICMP) {
        struct icmphdr *icmp = (void *)ip + (ip->ihl * 4);
        if ((void *)(icmp + 1) > data_end) return XDP_PASS;
        // ICMP não tem portas; reutilizamos os campos para type e code
        key.src_port = icmp->type;
        key.dst_port = icmp->code;

    } else {
        return XDP_PASS;
    }

    struct flow_metrics *metrics = bpf_map_lookup_elem(&flow_map, &key);
    __u64 now = bpf_ktime_get_ns();

    if (!metrics) {
        struct flow_metrics new_metrics = {0};
        new_metrics.src_ip   = key.src_ip;
        new_metrics.dst_ip   = key.dst_ip;
        new_metrics.src_port = key.src_port;
        new_metrics.dst_port = key.dst_port;
        new_metrics.protocol = key.protocol;

        new_metrics.start_ts      = now;
        new_metrics.current_ts    = now;
        new_metrics.flow_packets  = 1;
        new_metrics.flow_bytes    = pkt_len;
        new_metrics.min_packet_len = pkt_len;

        bpf_map_update_elem(&flow_map, &key, &new_metrics, BPF_ANY);
        metrics = bpf_map_lookup_elem(&flow_map, &key);
        if (!metrics) return XDP_PASS;
    } else {
        metrics->current_ts = now;
        metrics->flow_packets += 1;
        metrics->flow_bytes   += pkt_len;

        if (pkt_len < metrics->min_packet_len)
            metrics->min_packet_len = pkt_len;
    }

    // Flags TCP (apenas para pacotes TCP; ICMP/UDP ficam com zeros)
    if (tcp) {
        if (tcp->ack) metrics->ack_count++;
        if (tcp->syn) metrics->syn_count++;
        if (tcp->rst) metrics->rst_count++;
        if (tcp->urg) metrics->urg_count++;
        if (tcp->cwr) metrics->cwr_count++;
    }

    struct flow_metrics *ring_data;
    ring_data = bpf_ringbuf_reserve(&rb, sizeof(struct flow_metrics), 0);
    if (!ring_data)
        return XDP_PASS;

    __builtin_memcpy(ring_data, metrics, sizeof(struct flow_metrics));
    bpf_ringbuf_submit(ring_data, 0);

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";