#!/usr/bin/env python3
"""
gen_dataset.py — Gera um dataset SINTÉTICO no formato CIC-DDoS2019.

ATENÇÃO: isto NÃO é o CIC-DDoS2019. É um substituto para desenvolvimento
quando o CSV real não está disponível. A versão anterior usava duas nuvens
totalmente separadas (qualquer modelo tirava 100%). Aqui as classes se
SOBREPÕEM de propósito, com subtipos de tráfego legítimo "difícil"
(rajadas, muitas conexões curtas) e ataques "difíceis" (flood de baixa taxa,
floods com ACK/RST), para as métricas da etapa IV-D serem informativas.

Semântica das colunas = a mesma do que o window.c calcula em runtime:
contagens de flags e pacotes DENTRO da janela, "Flow Duration" em
microssegundos (como no CIC; o features.py converte para segundos).

Uso:
    python3 gen_dataset.py                  # 20000 linhas -> dataset/synthetic_ddos.csv
    python3 gen_dataset.py --n 50000 --seed 1
"""

import argparse
import os
import numpy as np
import pandas as pd

rng = None


def lognormal_between(lo, hi, size):
    """Lognormal com ~95% da massa entre lo e hi."""
    mu = (np.log(lo) + np.log(hi)) / 2
    sigma = (np.log(hi) - np.log(lo)) / 4
    return rng.lognormal(mu, sigma, size)


def build(n, kind):
    """Gera n linhas do subtipo `kind`."""
    if kind == "web":            # navegação: poucos pps, pacotes médios
        pps = lognormal_between(2, 400, n)
        mean_len = rng.uniform(150, 1100, n)
        syn_frac = rng.uniform(0.005, 0.08, n)
        ack_frac = rng.uniform(0.4, 0.9, n)
        rst_frac = rng.uniform(0, 0.02, n)
        min_len = rng.integers(40, 80, n)
        dur = lognormal_between(0.3, 90, n)
        label = "BENIGN"
    elif kind == "bulk":         # download/streaming: pps alto, pacote grande
        pps = lognormal_between(1500, 80000, n)
        mean_len = rng.uniform(900, 1450, n)
        syn_frac = rng.uniform(0, 0.002, n)
        ack_frac = rng.uniform(0.45, 0.95, n)
        rst_frac = rng.uniform(0, 0.003, n)
        min_len = rng.integers(40, 70, n)
        dur = lognormal_between(1, 120, n)
        label = "BENIGN"
    elif kind == "burst":        # muitas conexões curtas (flash crowd, API, scanner interno)
        pps = lognormal_between(200, 20000, n)
        mean_len = rng.uniform(55, 400, n)
        syn_frac = rng.uniform(0.1, 0.5, n)
        ack_frac = rng.uniform(0.3, 0.8, n)
        rst_frac = rng.uniform(0.01, 0.2, n)
        min_len = rng.integers(40, 62, n)
        dur = lognormal_between(0.05, 20, n)
        label = "BENIGN"
    elif kind == "syn_high":     # SYN flood volumétrico (hping3 --flood)
        pps = lognormal_between(40000, 2000000, n)
        mean_len = rng.normal(55, 3, n).clip(40, 70)
        syn_frac = rng.uniform(0.9, 1.0, n)
        ack_frac = rng.uniform(0, 0.05, n)
        rst_frac = rng.uniform(0, 0.02, n)
        min_len = rng.integers(40, 62, n)
        dur = lognormal_between(0.05, 60, n)
        label = "Syn"
    elif kind == "syn_low":      # SYN flood de baixa taxa (difícil)
        pps = lognormal_between(300, 12000, n)
        mean_len = rng.uniform(54, 120, n)
        syn_frac = rng.uniform(0.6, 1.0, n)
        ack_frac = rng.uniform(0, 0.25, n)
        rst_frac = rng.uniform(0, 0.1, n)
        min_len = rng.integers(40, 66, n)
        dur = lognormal_between(0.2, 60, n)
        label = "Syn"
    else:                        # "mixed": flood ACK/RST + algum SYN
        pps = lognormal_between(5000, 600000, n)
        mean_len = rng.uniform(40, 200, n)
        syn_frac = rng.uniform(0.05, 0.5, n)
        ack_frac = rng.uniform(0.3, 0.9, n)
        rst_frac = rng.uniform(0.1, 0.6, n)
        min_len = rng.integers(40, 62, n)
        dur = lognormal_between(0.1, 60, n)
        label = "DDoS"

    pkts = pps * dur
    # Pequena variação de medição (jitter) e pps recalculado de pkts/dur
    pps = pkts / dur
    return pd.DataFrame({
        "Flow Duration": (dur * 1e6).round().astype(np.int64),   # µs, como no CIC
        "Flow Packets/s": pps,
        "Flow Bytes/s": pps * mean_len,
        "ACK Flag Count": (pkts * ack_frac).round().astype(np.int64),
        "SYN Flag Count": (pkts * syn_frac).round().astype(np.int64),
        "RST Flag Count": (pkts * rst_frac).round().astype(np.int64),
        "URG Flag Count": np.zeros(n, dtype=np.int64),
        "CWR Flag Count": np.zeros(n, dtype=np.int64),
        "Packet Length Mean": mean_len,
        "Min Packet Length": min_len,
        "Label": label,
    })


def main():
    global rng
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000, help="total de linhas")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="dataset/synthetic_ddos.csv")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    # 60% benigno / 40% ataque
    mix = {"web": 0.30, "bulk": 0.15, "burst": 0.15,
           "syn_high": 0.20, "syn_low": 0.12, "mixed": 0.08}
    parts = [build(int(args.n * w), k) for k, w in mix.items()]
    df = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=args.seed)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"[OK] {len(df)} linhas -> {args.out}")
    print(df["Label"].value_counts().to_string())


if __name__ == "__main__":
    main()
