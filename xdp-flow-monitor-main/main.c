#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <signal.h>
#include <unistd.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <bpf/libbpf.h>
#include "common.h"
#include "flow_monitor.skel.h"

static volatile bool exiting = false;

static void sig_handler(int sig) {
    exiting = true;
}

static int handle_event(void *ctx, void *data, size_t data_sz) {
    const struct flow_metrics *metrics = data;

    char src_ip_str[INET_ADDRSTRLEN];
    char dst_ip_str[INET_ADDRSTRLEN];

    inet_ntop(AF_INET, &metrics->src_ip, src_ip_str, sizeof(src_ip_str));
    inet_ntop(AF_INET, &metrics->dst_ip, dst_ip_str, sizeof(dst_ip_str));

    double duration_sec = (metrics->current_ts - metrics->start_ts) / 1000000000.0;

    double pkts_per_sec = (duration_sec > 0) ? (metrics->flow_packets / duration_sec) : metrics->flow_packets;
    double bytes_per_sec = (duration_sec > 0) ? (metrics->flow_bytes / duration_sec) : metrics->flow_bytes;
    double mean_packet_len = (double)metrics->flow_bytes / metrics->flow_packets;

    printf("====================================================\n");
    printf("Flow: %s:%d -> %s:%d (Proto: %d)\n",
           src_ip_str, ntohs(metrics->src_port),
           dst_ip_str, ntohs(metrics->dst_port),
           metrics->protocol);

    printf("Interval (s)     : %.6f\n", duration_sec);
    printf("Flow Packets/s   : %.2f\n", pkts_per_sec);
    printf("Flow Bytes/s     : %.2f\n", bytes_per_sec);
    printf("Packet Len Mean  : %.2f bytes\n", mean_packet_len);
    printf("Min Packet Len   : %u bytes\n", metrics->min_packet_len);
    printf("TCP Flags        : SYN:%u ACK:%u RST:%u URG:%u CWR:%u\n",
           metrics->syn_count, metrics->ack_count, metrics->rst_count,
           metrics->urg_count, metrics->cwr_count);
    printf("====================================================\n\n");

    return 0;
}

int main(int argc, char **argv) {
    struct flow_monitor_bpf *skel;
    struct ring_buffer *rb = NULL;
    int err;

    if (argc < 2) {
        fprintf(stderr, "Uso: %s <interface_de_rede>\n", argv[0]);
        return 1;
    }
    int ifindex = if_nametoindex(argv[1]);
    if (!ifindex) {
        fprintf(stderr, "Falha ao encontrar interface %s\n", argv[1]);
        return 1;
    }

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    skel = flow_monitor_bpf__open_and_load();
    if (!skel) {
        fprintf(stderr, "Falha ao carregar o skeleton BPF\n");
        return 1;
    }

    skel->links.network_flow_monitor = bpf_program__attach_xdp(skel->progs.network_flow_monitor, ifindex);
    if (!skel->links.network_flow_monitor) {
        fprintf(stderr, "Falha ao anexar programa BPF na interface\n");
        goto cleanup;
    }

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        fprintf(stderr, "Falha ao criar o ring buffer\n");
        goto cleanup;
    }

    printf("Monitoramento iniciado na interface %s (ifindex %d). Pressione Ctrl+C para sair.\n", argv[1], ifindex);

    while (!exiting) {
        err = ring_buffer__poll(rb, 100);
        if (err == -EINTR) {
            err = 0;
            break;
        }
        if (err < 0) {
            printf("Erro no polling do ring buffer: %d\n", err);
            break;
        }
    }

cleanup:
    ring_buffer__free(rb);
    flow_monitor_bpf__destroy(skel);
    printf("\nMonitoramento encerrado.\n");
    return err < 0 ? -err : 0;
}

