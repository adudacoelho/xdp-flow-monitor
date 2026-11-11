#!/usr/bin/env python3
"""
train_model.py — Treina o XGBoost e salva ddos_model.ubj (usado pelo ml_daemon.py).

Uso:
    python3 train_model.py                         # lê ./dataset/*.csv
    python3 train_model.py --data dataset/Syn.csv  # CIC-DDoS2019 real
    python3 train_model.py --duration-unit us      # padrão (CIC usa microssegundos)
"""

import argparse
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from features import load_dataset, prepare, FEATURE_ORDER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./dataset/")
    ap.add_argument("--duration-unit", choices=["us", "ms", "s"], default="us",
                    help="unidade de 'Flow Duration' no CSV (CIC = us)")
    ap.add_argument("--out", default="ddos_model.ubj")
    args = ap.parse_args()

    X, y = prepare(load_dataset(args.data), args.duration_unit)
    print(f"[INFO] Normal: {(y == 0).sum()} | Ataque: {(y == 1).sum()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    print("[INFO] Treinando XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=100, max_depth=6, learning_rate=0.1,
        eval_metric="logloss", n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[RESULTADO] Acurácia: {acc:.4f} ({acc * 100:.1f}%)")
    print(classification_report(y_test, y_pred, target_names=["Normal", "Ataque"]))

    imp = pd.Series(model.get_booster().get_score(importance_type="gain"))
    print("[INFO] Importância das features (gain):")
    print(imp.reindex(FEATURE_ORDER).fillna(0).sort_values(ascending=False).round(1).to_string())

    model.get_booster().save_model(args.out)
    print(f"\n[OK] Modelo salvo em {args.out}")


if __name__ == "__main__":
    main()
