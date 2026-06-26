#ifndef __WINDOW_H
#define __WINDOW_H

#include <stdint.h>
#include "common.h"

#define WINDOW_SEC 5  // Janela de agregação em segundos

typedef struct {
    uint32_t src_ip;
    double   duration_sec;
    double   flow_pkts_per_sec;
    double   flow_bytes_per_sec;
    uint32_t ack_count;
    uint32_t syn_count;
    uint32_t rst_count;
    uint32_t urg_count;
    uint32_t cwr_count;
    double   mean_pkt_len;
    uint32_t min_pkt_len;
} FlowFeatures;

// Atualiza a janela com um novo evento do ring buffer.
// Retorna 1 quando a janela fechou e preenche *out com as features.
// Retorna 0 enquanto a janela ainda está aberta.
int window_update(const struct flow_metrics *m, FlowFeatures *out);

#endif
