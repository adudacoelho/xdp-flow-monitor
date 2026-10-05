/* Teste do window.c sem precisar de BPF: simula o que o kernel manda
 * (contadores CUMULATIVOS por fluxo, um evento por pacote).
 * Compilar: gcc -O2 -Wall -o test_window test_window.c window.c && ./test_window */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "window.h"

static int fails = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FALHOU: %s\n", msg); fails++; } else printf("ok: %s\n", msg); } while (0)

int main(void) {
    /* Cenário 1: 1 fluxo SYN, 54 B/pacote, 1000 pkts/s por 6 s */
    struct flow_metrics m = {0};
    m.src_ip = 0x0600140a; m.dst_ip = 0x0500140a;
    m.src_port = 12345; m.dst_port = 80; m.protocol = 6;
    m.start_ts = 1000000000ULL; m.min_packet_len = 54;
    FlowFeatures f; int closed = 0; FlowFeatures got = {0};
    for (int i = 1; i <= 6000; i++) {
        m.current_ts = m.start_ts + (uint64_t)i * 1000000ULL;   /* 1 ms */
        m.flow_packets = i; m.flow_bytes = (uint64_t)i * 54; m.syn_count = i;
        if (window_update(&m, &f)) { if (!closed) got = f; closed++; }
    }
    printf("pkts/s=%.1f bytes/s=%.1f syn=%u mean=%.1f min=%u dur=%.3f\n",
           got.flow_pkts_per_sec, got.flow_bytes_per_sec, got.syn_count,
           got.mean_pkt_len, got.min_pkt_len, got.duration_sec);
    CHECK(closed >= 1, "janela fechou");
    CHECK(fabs(got.flow_pkts_per_sec - 1000.0) < 5.0, "pkts/s ~ 1000 (antes do fix seria ~10^6+)");
    CHECK(fabs(got.flow_bytes_per_sec - 54000.0) < 300.0, "bytes/s ~ 54000");
    CHECK(fabs(got.mean_pkt_len - 54.0) < 0.01, "tamanho médio = 54");
    CHECK(got.syn_count >= 4990 && got.syn_count <= 5010, "SYN count ~ pacotes na janela (5000)");

    /* Cenário 2: fluxo recriado no kernel (contadores zeram, novo start_ts) */
    struct flow_metrics n = m;
    n.src_ip = 0x0700140a; n.start_ts = 9000000000ULL;
    FlowFeatures g; int c2 = 0; FlowFeatures got2 = {0};
    for (int i = 1; i <= 2500; i++) {            /* 2500 pkts em 2.5 s */
        n.current_ts = n.start_ts + (uint64_t)i * 1000000ULL;
        n.flow_packets = i; n.flow_bytes = (uint64_t)i * 100; n.syn_count = i;
        window_update(&n, &g);
    }
    n.start_ts = 9000000000ULL + 2600000000ULL;  /* recria o fluxo */
    for (int i = 1; i <= 4000; i++) {
        n.current_ts = n.start_ts + (uint64_t)i * 1000000ULL;
        n.flow_packets = i; n.flow_bytes = (uint64_t)i * 100; n.syn_count = i;
        if (window_update(&n, &g)) { if (!c2) got2 = g; c2++; }
    }
    printf("(recriado) pkts/s=%.1f\n", got2.flow_pkts_per_sec);
    CHECK(c2 >= 1 && fabs(got2.flow_pkts_per_sec - 1000.0) < 20.0, "fluxo recriado não duplica contagem");

    /* Cenário 3: 3 portas de origem diferentes do mesmo src_ip somam */
    struct flow_metrics p = m; p.src_ip = 0x0800140a; FlowFeatures h, got3 = {0}; int c3 = 0;
    for (int i = 1; i <= 2000; i++) {
        for (int k = 0; k < 3; k++) {
            p.src_port = 40000 + k; p.start_ts = 20000000000ULL;
            p.current_ts = p.start_ts + (uint64_t)i * 3000000ULL;
            p.flow_packets = i; p.flow_bytes = (uint64_t)i * 60; p.syn_count = i;
            if (window_update(&p, &h)) { if (!c3) got3 = h; c3++; }
        }
    }
    printf("(3 portas) pkts/s=%.1f\n", got3.flow_pkts_per_sec);
    CHECK(c3 >= 1 && fabs(got3.flow_pkts_per_sec - 3 * 333.3) < 15.0, "3 fluxos do mesmo IP somam ~1000 pkts/s");

    printf(fails ? "\n%d teste(s) falharam\n" : "\nTodos os testes passaram\n", fails);
    return fails != 0;
}
