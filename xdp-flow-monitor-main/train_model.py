#!/usr/bin/env python3
"""
train_model.py — Treina o XGBoost no dataset CIC-DDoS2019.

Baixe o dataset em: https://www.unb.ca/cic/datasets/ddos-2019.html
Coloque os CSVs na pasta ./dataset/ e rode:
    python3 train_model.py
"""

import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Features da Tabela I do artigo (Chen et al., 2024)
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

# Mapeamento para os nomes usados no ml_daemon.py
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

def load_dataset(path="./dataset/"):
    csvs = glob.glob(os.path.join(path, "*.csv"))
    if not csvs:
        print(f"[ERRO] Nenhum CSV encontrado em {path}")
        exit(1)

    print(f"[INFO] Carregando {len(csvs)} arquivo(s)...")
    dfs = []
    for f in csvs:
        df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def main():
    df = load_dataset()

    # Verifica se as colunas necessárias existem
    missing = [c for c in FEATURES + ["Label"] if c not in df.columns]
    if missing:
        print(f"[ERRO] Colunas não encontradas: {missing}")
        print(f"[INFO] Colunas disponíveis: {list(df.columns)}")
        exit(1)

    # Label: 0 = normal, 1 = ataque
    df["label"] = (df["Label"].str.strip().str.upper() != "BENIGN").astype(int)
    print(f"[INFO] Normal: {(df['label']==0).sum()} | Ataque: {(df['label']==1).sum()}")

    X = df[FEATURES].copy()
    X = X.replace([np.inf, -np.inf], 0).fillna(0)
    X = X.rename(columns=RENAME)
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("[INFO] Treinando XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="logloss",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[RESULTADO] Acurácia: {acc:.4f} ({acc*100:.1f}%)")
    print(classification_report(y_test, y_pred, target_names=["Normal", "Ataque"]))

    model.get_booster().save_model("ddos_model.ubj")
    print("[OK] Modelo salvo em ddos_model.ubj")

if __name__ == "__main__":
    main()
