// XDP minimo: so o lookup no blacklist_map (LPM trie), sem flow_map
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

struct lpm_key { __u32 prefixlen; __u32 ip; };

struct {
    __uint(type, BPF_MAP_TYPE_LPM_TRIE);
    __uint(max_entries, 1024);
    __uint(map_flags, BPF_F_NO_PREALLOC);
    __type(key, struct lpm_key);
    __type(value, __u8);
} blacklist_map SEC(".maps");

SEC("xdp")
int xdp_min(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *end  = (void *)(long)ctx->data_end;
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > end) return XDP_PASS;
    struct lpm_key k = { .prefixlen = 32, .ip = ip->saddr };
    if (bpf_map_lookup_elem(&blacklist_map, &k)) return XDP_DROP;
    return XDP_PASS;
}

char LICENSE[] SEC("license") = "GPL";
