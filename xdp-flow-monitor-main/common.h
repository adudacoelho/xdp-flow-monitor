#ifndef __COMMON_H
#define __COMMON_H

struct flow_metrics {
    unsigned int src_ip;
    unsigned int dst_ip;     // NOVO: IP de Destino
    unsigned short src_port;
    unsigned short dst_port;
    unsigned char protocol;
    // O compilador C adicionará 3 bytes de padding automático aqui para manter
    // o alinhamento de 64 bits para os próximos campos.

    unsigned long long start_ts;
    unsigned long long current_ts;

    unsigned long long flow_packets;
    unsigned long long flow_bytes;

    unsigned int ack_count;
    unsigned int syn_count;
    unsigned int rst_count;
    unsigned int urg_count;
    unsigned int cwr_count;

    unsigned int min_packet_len;
};

#endif
