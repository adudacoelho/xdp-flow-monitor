#include <string.h>
#include <time.h>
#include "window.h"

// Estado interno da janela por fluxo (simplificado: um slot por src_ip)
#define MAX_FLOWS 1024

typedef struct {
    uint32_t src_ip;
    uint64_t window_start_ns;
    uint64_t total_packets;
    uint64_t total_bytes;
    uint32_t ack_count;
    uint32_t syn_count;
    uint32_t rst_count;
    uint32_t urg_count;
    uint32_t cwr_count;
    uint32_t min_pkt_len;
    int      active;
} WindowSlot;

static WindowSlot slots[MAX_FLOWS];

static WindowSlot *find_or_create(uint32_t src_ip, uint64_t now_ns) {
    // Procura slot existente
    for (int i = 0; i < MAX_FLOWS; i++) {
        if (slots[i].active && slots[i].src_ip == src_ip)
            return &slots[i];
    }
    // Cria novo slot
    for (int i = 0; i < MAX_FLOWS; i++) {
        if (!slots[i].active) {
            memset(&slots[i], 0, sizeof(WindowSlot));
            slots[i].src_ip          = src_ip;
            slots[i].window_start_ns = now_ns;
            slots[i].min_pkt_len     = UINT32_MAX;
            slots[i].active          = 1;
            return &slots[i];
        }
    }
    return NULL;
}

int window_update(const struct flow_metrics *m, FlowFeatures *out) {
    uint64_t now_ns   = m->current_ts;
    WindowSlot *slot  = find_or_create(m->src_ip, now_ns);
    if (!slot) return 0;

    // Acumula métricas
    slot->total_packets += m->flow_packets;
    slot->total_bytes   += m->flow_bytes;
    slot->ack_count     += m->ack_count;
    slot->syn_count     += m->syn_count;
    slot->rst_count     += m->rst_count;
    slot->urg_count     += m->urg_count;
    slot->cwr_count     += m->cwr_count;
    if (m->min_packet_len < slot->min_pkt_len)
        slot->min_pkt_len = m->min_packet_len;

    // Verifica se a janela fechou
    double elapsed = (now_ns - slot->window_start_ns) / 1e9;
    if (elapsed < WINDOW_SEC) return 0;

    // Janela fechou — preenche as features
    out->src_ip             = slot->src_ip;
    out->duration_sec       = elapsed;
    out->flow_pkts_per_sec  = (elapsed > 0) ? slot->total_packets / elapsed : 0;
    out->flow_bytes_per_sec = (elapsed > 0) ? slot->total_bytes   / elapsed : 0;
    out->ack_count          = slot->ack_count;
    out->syn_count          = slot->syn_count;
    out->rst_count          = slot->rst_count;
    out->urg_count          = slot->urg_count;
    out->cwr_count          = slot->cwr_count;
    out->mean_pkt_len       = (slot->total_packets > 0)
                              ? (double)slot->total_bytes / slot->total_packets : 0;
    out->min_pkt_len        = (slot->min_pkt_len == UINT32_MAX) ? 0 : slot->min_pkt_len;

    // Reseta o slot para a próxima janela
    slot->window_start_ns = now_ns;
    slot->total_packets   = 0;
    slot->total_bytes     = 0;
    slot->ack_count       = slot->syn_count = slot->rst_count = 0;
    slot->urg_count       = slot->cwr_count = 0;
    slot->min_pkt_len     = UINT32_MAX;

    return 1;
}
