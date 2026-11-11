#!/usr/bin/env python3
"""
features.py — Definição única das features e do carregamento de dataset.

Usado por train_model.py e evaluate_models.py, para o treino e a avaliação
verem exatamente os mesmos dados.

Features da Tabela I do artigo (Chen et al., TrustCom 2024).

UNIDADES (corrige o problema 2):
  - No CIC-DDoS2019, "Flow Duration" vem em MICROSSEGUNDOS.
  - O ml_daemon.py recebe "duration_sec" em SEGUNDOS (vem do window.c).
  Por isso converto a duração do CSV para segundos ao carregar.
"""

import os
import glob
import numpy as np
import pandas as pd

# Colunas do CSV no formato CIC-DDoS2019 (nomes originais)
FEATURES = [
    "Flow Duration",
    "Flow Packets/s",
    "Flow Bytes/s",
    "ACK Flag Count",
    "SYN Flag Count",
    "RST Flag Count",
    "URG Flag Count",
    "CWR Flag Count",
    "Packet Length Mean",
    "Min Packet Length",
]

# Nomes usados no ml_daemon.py / main.c
RENAME = {
    "Flow Duration":       "duration_sec",
    "Flow Packets/s":      "flow_pkts_per_sec",
    "Flow Bytes/s":        "flow_bytes_per_sec",
    "ACK Flag Count":      "ack_count",
    "SYN Flag Count":      "syn_count",
    "RST Flag Count":      "rst_count",
    "URG Flag Count":      "urg_count",
    "CWR Flag Count":      "cwr_count",
    "Packet Length Mean":  "mean_pkt_len",
    "Min Packet Length":   "min_pkt_len",
}

FEATURE_ORDER = [RENAME[c] for c in FEATURES]

DURATION_DIVISOR = {"us": 1e6, "ms": 1e3, "s": 1.0}


def load_dataset(path="./dataset/"):
    """Carrega um CSV, ou todos os CSVs de uma pasta."""
    if os.path.isfile(path):
        csvs = [path]
    else:
        csvs = sorted(glob.glob(os.path.join(path, "*.csv")))
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {path}")

    print(f"[INFO] Carregando {len(csvs)} arquivo(s): "
          f"{', '.join(os.path.basename(c) for c in csvs)}")
    dfs = []
    for f in csvs:
        df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def prepare(df, duration_unit="us"):
    """
    Converte o DataFrame bruto em (X, y).
      X: 10 colunas com os nomes do daemon, duração em segundos
      y: 0 = BENIGN, 1 = qualquer ataque
    """
    missing = [c for c in FEATURES + ["Label"] if c not in df.columns]
    if missing:
        raise KeyError(f"Colunas não encontradas: {missing}\n"
                       f"Disponíveis: {list(df.columns)}")

    df = df.dropna(subset=["Label"]).copy()
    y = (df["Label"].astype(str).str.strip().str.upper() != "BENIGN").astype(int)

    X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    X["Flow Duration"] = X["Flow Duration"] / DURATION_DIVISOR[duration_unit]
    X = X.rename(columns=RENAME)[FEATURE_ORDER]
    return X.reset_index(drop=True), y.reset_index(drop=True)
