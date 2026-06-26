#!/usr/bin/env python3
"""
ml_daemon.py — Daemon de classificação XGBoost para DDoS.
Ouve num socket Unix, recebe features em JSON, responde "attack": true/false.
"""

import os
import json
import socket
import numpy as np
import xgboost as xgb

SOCK_PATH   = "/tmp/ml_engine.sock"
MODEL_PATH  = "ddos_model.ubj"

# Ordem exata das features — deve ser igual à usada no treinamento
FEATURE_ORDER = [
    "duration_sec",
    "flow_pkts_per_sec",
    "flow_bytes_per_sec",
    "ack_count",
    "syn_count",
    "rst_count",
    "urg_count",
    "cwr_count",
    "mean_pkt_len",
    "min_pkt_len",
]

def load_model():
    if not os.path.exists(MODEL_PATH):
        print(f"[ERRO] Modelo não encontrado: {MODEL_PATH}")
        print("[INFO] Rode train_model.py primeiro para gerar o modelo.")
        exit(1)
    model = xgb.Booster()
    model.load_model(MODEL_PATH)
    print(f"[OK] Modelo carregado: {MODEL_PATH}")
    return model

def classify(model, features: dict) -> bool:
    """Retorna True se for ataque DDoS."""
    x = np.array([[features.get(f, 0.0) for f in FEATURE_ORDER]], dtype=np.float32)
    dmatrix = xgb.DMatrix(x, feature_names=FEATURE_ORDER)
    prob = model.predict(dmatrix)[0]
    return bool(prob > 0.5)

def run(model):
    # Remove socket antigo se existir
    if os.path.exists(SOCK_PATH):
        os.unlink(SOCK_PATH)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.bind(SOCK_PATH)
        srv.listen(10)
        os.chmod(SOCK_PATH, 0o777)
        print(f"[OK] Escutando em {SOCK_PATH}")

        while True:
            conn, _ = srv.accept()
            with conn:
                try:
                    raw = conn.recv(4096).decode()
                    data = json.loads(raw)
                    is_attack = classify(model, data["features"])
                    response = {
                        "attack":  is_attack,
                        "src_ip":  data.get("src_ip", 0),
                    }
                    conn.sendall(json.dumps(response).encode())

                    status = "ATAQUE" if is_attack else "normal"
                    print(f"[{status}] src_ip={data.get('src_ip')} "
                          f"pkts/s={data['features'].get('flow_pkts_per_sec', 0):.1f}")
                except Exception as e:
                    print(f"[ERRO] {e}")

if __name__ == "__main__":
    model = load_model()
    run(model)
