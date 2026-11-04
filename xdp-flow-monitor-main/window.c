#include <string.h>
#include <time.h>
#include <stdio.h>
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

// Guarda o último snapshot de cada conexão.
// Não deve ser zerado quando uma janela fecha.
#define MAX_PREVIOUS_FLOWS 10000

typedef struct {
    int used;
    struct flow_metrics last;
} PreviousFlow;

static PreviousFlow previous_flows[MAX_PREVIOUS_FLOWS];

static PreviousFlow *find_previous(const struct flow_metrics *m) {
    PreviousFlow *free_entry = NULL;

    for (int i = 0; i < MAX_PREVIOUS_FLOWS; i++) {
        PreviousFlow *entry = &previous_flows[i];

        if (!entry->used) {
            if (!free_entry)
                free_entry = entry;
            continue;
        }

        const struct flow_metrics *last = &entry->last;

        // Identifica a conexão pelos dois IPs, portas e protocolo.
        if (last->src_ip == m->src_ip &&
            last->dst_ip == m->dst_ip &&
            last->src_port == m->src_port &&
            last->dst_port == m->dst_port &&
            last->protocol == m->protocol) {
            return entry;
        }
    }

    return free_entry;
}

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

static void close_window(WindowSlot *slot, uint64_t end_ns,
                         FlowFeatures *out) {
    double elapsed = (end_ns - slot->window_start_ns) / 1e9;

    out->src_ip             = slot->src_ip;
    out->duration_sec       = elapsed;
    out->flow_pkts_per_sec  = (elapsed > 0)
                              ? slot->total_packets / elapsed : 0;
    out->flow_bytes_per_sec = (elapsed > 0)
                              ? slot->total_bytes / elapsed : 0;
    out->ack_count          = slot->ack_count;
    out->syn_count          = slot->syn_count;
    out->rst_count          = slot->rst_count;
    out->urg_count          = slot->urg_count;
    out->cwr_count          = slot->cwr_count;
    out->mean_pkt_len       = (slot->total_packets > 0)
                              ? (double)slot->total_bytes
                                / slot->total_packets : 0;
    out->min_pkt_len        = (slot->min_pkt_len == UINT32_MAX)
                              ? 0 : slot->min_pkt_len;

    // Libera somente a janela; previous_flows permanece intacto.
    memset(slot, 0, sizeof(*slot));
}

int window_next(uint64_t now_ns, int flush, FlowFeatures *out) {
    for (int i = 0; i < MAX_FLOWS; i++) {
        WindowSlot *slot = &slots[i];

        if (!slot->active || slot->total_packets == 0)
            continue;

        uint64_t deadline = slot->window_start_ns +
                            (uint64_t)WINDOW_SEC * 1000000000ULL;

        if (now_ns >= deadline) {
            close_window(slot, deadline, out);
            return 1;
        }

        if (flush) {
            uint64_t end = now_ns > slot->window_start_ns
                           ? now_ns : slot->window_start_ns;
            close_window(slot, end, out);
            return 1;
        }
    }

    return 0;
}

int window_update(const struct flow_metrics *m, FlowFeatures *out) {
    uint64_t now_ns = m->current_ts;
    WindowSlot *slot = find_or_create(m->src_ip, now_ns);
    if (!slot)
        return 0;

    PreviousFlow *previous = find_previous(m);
    if (!previous) {
        fprintf(stderr,
                "[ERRO] Sem espaço para guardar contadores anteriores.\n");
        return 0;
    }

    // Na primeira observação, os contadores anteriores são zero.
    struct flow_metrics before = {0};

    if (previous->used) {
        const struct flow_metrics *last = &previous->last;

        // Ignora eventos de uma geração antiga da conexão.
        if (m->start_ts < last->start_ts)
            return 0;

        if (m->start_ts == last->start_ts) {
            // Impede que um snapshot antigo faça a contagem retroceder.
            if (m->current_ts < last->current_ts ||
                m->flow_packets < last->flow_packets ||
                m->flow_bytes < last->flow_bytes ||
                m->ack_count < last->ack_count ||
                m->syn_count < last->syn_count ||
                m->rst_count < last->rst_count ||
                m->urg_count < last->urg_count ||
                m->cwr_count < last->cwr_count) {
                fprintf(stderr,
                        "[AVISO] Snapshot regressivo ignorado.\n");
                return 0;
            }

            before = *last;
        }

        // Se start_ts aumentou, a entrada foi recriada.
        // Nesse caso, os contadores anteriores continuam zerados.
    }

    // Fecha a janela anterior antes de acrescentar o evento novo.
    int closed = 0;
    uint64_t deadline = slot->window_start_ns +
                        (uint64_t)WINDOW_SEC * 1000000000ULL;

    if (slot->total_packets > 0 && now_ns >= deadline) {
        close_window(slot, deadline, out);

        // O evento novo abre outra janela.
        slot->src_ip = m->src_ip;
        slot->window_start_ns = now_ns;
        slot->min_pkt_len = UINT32_MAX;
        slot->active = 1;

        closed = 1;
    }

    // Acumula somente o que aumentou desde o último snapshot.
    slot->total_packets += m->flow_packets - before.flow_packets;
    slot->total_bytes   += m->flow_bytes   - before.flow_bytes;
    slot->ack_count     += m->ack_count    - before.ack_count;
    slot->syn_count     += m->syn_count    - before.syn_count;
    slot->rst_count     += m->rst_count    - before.rst_count;
    slot->urg_count     += m->urg_count    - before.urg_count;
    slot->cwr_count     += m->cwr_count    - before.cwr_count;

    // Guarda o snapshot sem apagá-lo quando a janela fecha.
    previous->last = *m;
    previous->used = 1;

    if (m->min_packet_len < slot->min_pkt_len)
        slot->min_pkt_len = m->min_packet_len;

    return closed;
}
