#include <string.h>
#include <time.h>
#include "window.h"

/*
 * IMPORTANTE: o programa BPF envia, a cada pacote, os contadores
 * CUMULATIVOS do fluxo (flow_packets, flow_bytes, flags...). Somar esses
 * valores direto contava o mesmo pacote milhares de vezes (pkts/s na casa de
 * 10^10). Aqui guardamos o último valor cumulativo visto de cada fluxo
 * (5-tupla) e acumulamos apenas o DELTA na janela do src_ip.
 */

/* ---------- Estado por fluxo (último valor cumulativo visto) ---------- */
#define FLOW_TABLE_SIZE 8192   /* potência de 2 */
#define FLOW_PROBE_MAX  16

typedef struct {
    int      used;
    uint32_t src_ip, dst_ip;
    uint16_t src_port, dst_port;
    uint8_t  protocol;
    uint64_t start_ts;          /* identifica a "instância" do fluxo no kernel */
    uint64_t last_packets;
    uint64_t last_bytes;
    uint32_t last_ack, last_syn, last_rst, last_urg, last_cwr;
} FlowState;

static FlowState flow_table[FLOW_TABLE_SIZE];

static uint32_t flow_hash(const struct flow_metrics *m) {
    uint32_t h = 2166136261u;
    uint32_t parts[4] = {
        m->src_ip, m->dst_ip,
        ((uint32_t)m->src_port << 16) | m->dst_port,
        m->protocol
    };
    for (int i = 0; i < 4; i++) {
        h ^= parts[i];
        h *= 16777619u;
        h ^= h >> 15;
    }
    return h;
}

static int same_flow(const FlowState *f, const struct flow_metrics *m) {
    return f->used &&
           f->src_ip == m->src_ip && f->dst_ip == m->dst_ip &&
           f->src_port == m->src_port && f->dst_port == m->dst_port &&
           f->protocol == m->protocol;
}

static FlowState *flow_lookup(const struct flow_metrics *m) {
    uint32_t base = flow_hash(m) & (FLOW_TABLE_SIZE - 1);
    for (int i = 0; i < FLOW_PROBE_MAX; i++) {
        FlowState *f = &flow_table[(base + i) & (FLOW_TABLE_SIZE - 1)];
        if (same_flow(f, m)) return f;
        if (!f->used) {
            memset(f, 0, sizeof(*f));
            f->used = 1;
            f->src_ip = m->src_ip;     f->dst_ip = m->dst_ip;
            f->src_port = m->src_port; f->dst_port = m->dst_port;
            f->protocol = m->protocol;
            f->start_ts = m->start_ts;
            return f;
        }
    }
    /* Tabela cheia nessa região: sobrescreve o slot "home" (fluxo novo) */
    FlowState *f = &flow_table[base];
    memset(f, 0, sizeof(*f));
    f->used = 1;
    f->src_ip = m->src_ip;     f->dst_ip = m->dst_ip;
    f->src_port = m->src_port; f->dst_port = m->dst_port;
    f->protocol = m->protocol;
    f->start_ts = m->start_ts;
    return f;
}

static uint64_t delta64(uint64_t cur, uint64_t last) {
    /* cur < last: evento fora de ordem entre CPUs; ignora (delta 0) */
    return cur >= last ? cur - last : 0;
}
static uint32_t delta32(uint32_t cur, uint32_t last) {
    return cur >= last ? cur - last : 0;
}

/* ---------- Janela por src_ip ---------- */
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
    for (int i = 0; i < MAX_FLOWS; i++) {
        if (slots[i].active && slots[i].src_ip == src_ip)
            return &slots[i];
    }
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
    uint64_t now_ns  = m->current_ts;
    WindowSlot *slot = find_or_create(m->src_ip, now_ns);
    if (!slot) return 0;

    /* Calcula o delta em relação ao último evento do mesmo fluxo */
    FlowState *fs = flow_lookup(m);
    uint64_t d_pkts, d_bytes;
    uint32_t d_ack, d_syn, d_rst, d_urg, d_cwr;

    if (fs->start_ts != m->start_ts) {
        /* Fluxo foi recriado no kernel (contadores reiniciaram) */
        memset(&fs->last_packets, 0,
               sizeof(*fs) - __builtin_offsetof(FlowState, last_packets));
        fs->start_ts = m->start_ts;
    }
    d_pkts  = delta64(m->flow_packets, fs->last_packets);
    d_bytes = delta64(m->flow_bytes,   fs->last_bytes);
    d_ack   = delta32(m->ack_count,    fs->last_ack);
    d_syn   = delta32(m->syn_count,    fs->last_syn);
    d_rst   = delta32(m->rst_count,    fs->last_rst);
    d_urg   = delta32(m->urg_count,    fs->last_urg);
    d_cwr   = delta32(m->cwr_count,    fs->last_cwr);

    if (m->flow_packets > fs->last_packets) fs->last_packets = m->flow_packets;
    if (m->flow_bytes   > fs->last_bytes)   fs->last_bytes   = m->flow_bytes;
    if (m->ack_count    > fs->last_ack)     fs->last_ack     = m->ack_count;
    if (m->syn_count    > fs->last_syn)     fs->last_syn     = m->syn_count;
    if (m->rst_count    > fs->last_rst)     fs->last_rst     = m->rst_count;
    if (m->urg_count    > fs->last_urg)     fs->last_urg     = m->urg_count;
    if (m->cwr_count    > fs->last_cwr)     fs->last_cwr     = m->cwr_count;

    /* Acumula só o que é novo */
    slot->total_packets += d_pkts;
    slot->total_bytes   += d_bytes;
    slot->ack_count     += d_ack;
    slot->syn_count     += d_syn;
    slot->rst_count     += d_rst;
    slot->urg_count     += d_urg;
    slot->cwr_count     += d_cwr;
    if (d_pkts > 0 && m->min_packet_len < slot->min_pkt_len)
        slot->min_pkt_len = m->min_packet_len;

    /* Verifica se a janela fechou */
    double elapsed = (now_ns - slot->window_start_ns) / 1e9;
    if (elapsed < WINDOW_SEC) return 0;

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

    /* Reseta o slot para a próxima janela (os baselines por fluxo permanecem) */
    slot->window_start_ns = now_ns;
    slot->total_packets   = 0;
    slot->total_bytes     = 0;
    slot->ack_count       = slot->syn_count = slot->rst_count = 0;
    slot->urg_count       = slot->cwr_count = 0;
    slot->min_pkt_len     = UINT32_MAX;

    return 1;
}
