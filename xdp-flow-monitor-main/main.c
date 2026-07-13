#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include "common.h"
#include "window.h"
#include "flow_monitor.skel.h"

#define ML_SOCK_PATH "/tmp/ml_engine.sock"

static volatile bool exiting = false;
static int blacklist_map_fd = -1;

static void sig_handler(int sig) {
    exiting = true;
}

// Chave LPM para o blacklist_map
struct lpm_key {
    __u32 prefixlen;
    __u32 ip;
};

// Adiciona um IP na blacklist do kernel
static void update_blacklist(uint32_t ip) {
    if (blacklist_map_fd < 0) return;

    struct lpm_key key = { .prefixlen = 32, .ip = ip };
    uint8_t val = 1;

    if (bpf_map_update_elem(blacklist_map_fd, &key, &val, BPF_ANY) == 0) {
        char ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip, ip_str, sizeof(ip_str));
        printf("[BLOQUEADO] IP adicionado à blacklist: %s\n", ip_str);
    }
}

// Envia features ao ml_daemon.py via socket Unix e recebe resultado
static int query_ml(const FlowFeatures *f) {
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) return -1;

    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, ML_SOCK_PATH, sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -1;
    }

    // Monta JSON com as features
    char buf[512];
    snprintf(buf, sizeof(buf),
        "{\"src_ip\":%u,\"features\":{"
        "\"duration_sec\":%.6f,"
        "\"flow_pkts_per_sec\":%.2f,"
        "\"flow_bytes_per_sec\":%.2f,"
        "\"ack_count\":%u,\"syn_count\":%u,"
        "\"rst_count\":%u,\"urg_count\":%u,"
        "\"cwr_count\":%u,"
        "\"mean_pkt_len\":%.2f,"
        "\"min_pkt_len\":%u}}",
        f->src_ip,
        f->duration_sec,
        f->flow_pkts_per_sec, f->flow_bytes_per_sec,
        f->ack_count, f->syn_count,
        f->rst_count, f->urg_count,
        f->cwr_count,
        f->mean_pkt_len, f->min_pkt_len);

    send(sock, buf, strlen(buf), 0);

    char resp[256] = {0};
    recv(sock, resp, sizeof(resp) - 1, 0);
    close(sock);

    // Retorna 1 se o daemon respondeu "attack": true
    return strstr(resp, "\"attack\": true") != NULL;

}

static int handle_event(void *ctx, void *data, size_t data_sz) {
    const struct flow_metrics *m = data;


    // Tenta fechar a janela de agregação
    FlowFeatures features;
    if (window_update(m, &features) == 0)
        return 0; // janela ainda aberta

    // Imprime as features da janela (igual ao comportamento original)
    char src_ip_str[INET_ADDRSTRLEN];
    char dst_ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &m->src_ip, src_ip_str, sizeof(src_ip_str));
    inet_ntop(AF_INET, &m->dst_ip, dst_ip_str, sizeof(dst_ip_str));

    printf("====================================================\n");
    printf("Janela fechada — src: %s\n", src_ip_str);
    printf("Flow Packets/s   : %.2f\n", features.flow_pkts_per_sec);
    printf("Flow Bytes/s     : %.2f\n", features.flow_bytes_per_sec);
    printf("Packet Len Mean  : %.2f bytes\n", features.mean_pkt_len);
    printf("Min Packet Len   : %u bytes\n", features.min_pkt_len);
    printf("TCP Flags        : SYN:%u ACK:%u RST:%u URG:%u CWR:%u\n",
           features.syn_count, features.ack_count, features.rst_count,
           features.urg_count, features.cwr_count);

    // Consulta o daemon ML
    int is_attack = query_ml(&features);
    if (is_attack < 0) {
        printf("[AVISO] ml_daemon.py não está rodando — sem classificação.\n");
    } else if (is_attack) {
        printf("[ATAQUE DETECTADO] Bloqueando IP...\n");
        update_blacklist(features.src_ip);
    } else {
        printf("[Normal]\n");
    }
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

    signal(SIGINT,  sig_handler);
    signal(SIGTERM, sig_handler);

    skel = flow_monitor_bpf__open_and_load();
    if (!skel) {
        fprintf(stderr, "Falha ao carregar o skeleton BPF\n");
        return 1;
    }

    // Guarda o fd do blacklist_map para uso no update_blacklist()
    blacklist_map_fd = bpf_map__fd(skel->maps.blacklist_map);
    if (blacklist_map_fd < 0) {
        fprintf(stderr, "Falha ao obter fd do blacklist_map\n");
        goto cleanup;
    }

    skel->links.network_flow_monitor = bpf_program__attach_xdp(
        skel->progs.network_flow_monitor, ifindex);
    if (!skel->links.network_flow_monitor) {
        fprintf(stderr, "Falha ao anexar programa BPF na interface\n");
        goto cleanup;
    }

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        fprintf(stderr, "Falha ao criar o ring buffer\n");
        goto cleanup;
    }

    printf("Monitoramento iniciado na interface %s (ifindex %d).\n", argv[1], ifindex);
    printf("Aguardando ml_daemon.py em %s...\n\n", ML_SOCK_PATH);

    while (!exiting) {
        err = ring_buffer__poll(rb, 100);
        if (err == -EINTR) { err = 0; break; }
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
