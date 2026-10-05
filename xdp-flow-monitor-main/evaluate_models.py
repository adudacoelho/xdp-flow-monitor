#!/usr/bin/env python3
"""
evaluate_models.py — Etapa IV-D do artigo (Chen et al., TrustCom 2024):
"Performance of Anomaly Detection".

Compara algoritmos de ML/DL clássicos na detecção de DDoS com as mesmas 10
features da Tabela I e gera:
  - results/model_comparison.csv   (Fig. 7a + 7b em forma de tabela)
  - results/model_comparison.md    (tabela pronta para colar no relatório)
  - results/fig7a_metrics.png      (accuracy, precision, recall, F1 por modelo)
  - results/fig7b_detect_rates.png (taxa de detecção de normal e de ataque)

Uso:
    python3 evaluate_models.py                          # ./dataset/*.csv
    python3 evaluate_models.py --data dataset/Syn.csv   # CIC-DDoS2019 real
    python3 evaluate_models.py --max-rows 200000 --cv 5

Definições (classe positiva = ATAQUE):
  accuracy  = (TP+TN)/total
  precision = TP/(TP+FP)          recall = TP/(TP+FN)       F1 = 2PR/(P+R)
  Atk Detect Rate    = TP/(TP+FN)   (ataques classificados como ataque)
  Normal Detect Rate = TN/(TN+FP)   (tráfego normal classificado como normal)
O texto do artigo descreve essas duas taxas pela proporção de amostras "não
detectadas"; aqui uso a forma padrão (TPR e TNR), em que maior = melhor, que
é o que o eixo da Fig. 7(b) sugere.
"""

import argparse
import os
import time
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier

from features import load_dataset, prepare

warnings.filterwarnings("ignore")

SEED = 42


def log_scale(estimator):
    """As features vão de 1 a 10^9: log1p + padronização para modelos sensíveis a escala."""
    return make_pipeline(FunctionTransformer(np.log1p, validate=False),
                         StandardScaler(), estimator)


def build_models(n_jobs):
    return {
        "Logistic Regression": log_scale(LogisticRegression(max_iter=1000, random_state=SEED)),
        "Naive Bayes":         log_scale(GaussianNB()),
        "KNN":                 log_scale(KNeighborsClassifier(n_neighbors=5, n_jobs=n_jobs)),
        "SVM (RBF)":           log_scale(SVC(kernel="rbf", random_state=SEED)),
        "Decision Tree":       DecisionTreeClassifier(max_depth=10, random_state=SEED),
        "Random Forest":       RandomForestClassifier(n_estimators=100, n_jobs=n_jobs, random_state=SEED),
        "MLP (DL)":            log_scale(MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300,
                                                       early_stopping=True, random_state=SEED)),
        # Mesmos hiperparâmetros do train_model.py
        "XGBoost":             xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1,
                                                 eval_metric="logloss", n_jobs=n_jobs,
                                                 random_state=SEED),
    }


def evaluate(name, model, X_tr, X_te, y_tr, y_te):
    t0 = time.perf_counter()
    model.fit(X_tr, y_tr)
    fit_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = model.predict(X_te)
    pred_s = time.perf_counter() - t0

    tn, fp, fn, tp = confusion_matrix(y_te, y_pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "accuracy":  accuracy_score(y_te, y_pred),
        "precision": precision_score(y_te, y_pred, zero_division=0),
        "recall":    recall_score(y_te, y_pred, zero_division=0),
        "f1":        f1_score(y_te, y_pred, zero_division=0),
        "normal_detect_rate": tn / (tn + fp) if (tn + fp) else float("nan"),
        "atk_detect_rate":    tp / (tp + fn) if (tp + fn) else float("nan"),
        "TN": tn, "FP": fp, "FN": fn, "TP": tp,
        "fit_s": fit_s,
        # Inferência em lote (Python): serve para comparar modelos entre si,
        # NÃO é comparável com os 11,96 µs/pacote da Tabela II (C, em kernel/user).
        "predict_us_per_sample": pred_s / len(X_te) * 1e6,
    }


# ----------------------------- gráficos -----------------------------
# Paleta categórica validada (slots 1-4, modo claro): azul, laranja, verde-água, amarelo.
# Aqua/amarelo ficam abaixo de 3:1 no fundo claro, então todo valor vai rotulado
# na barra e a tabela CSV acompanha (regra de "relief").
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def grouped_bars(df, cols, labels, title, path, ymin):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_models, n_series = len(df), len(cols)
    width = 0.8 / n_series
    x = np.arange(n_models)

    fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE)
    style_axes(ax)
    for i, (c, lab) in enumerate(zip(cols, labels)):
        # Pequeno vão (borda na cor da superfície) entre barras adjacentes
        bars = ax.bar(x + (i - (n_series - 1) / 2) * width, df[c].values * 100,
                      width=width, color=COLORS[i], label=lab,
                      edgecolor=SURFACE, linewidth=1.5, zorder=3)
        for b, v in zip(bars, df[c].values * 100):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.08,
                    f"{v:.1f}", ha="center", va="bottom", fontsize=6.5,
                    color=INK2, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels(df["model"].values, rotation=20, ha="right", color=INK)
    ax.set_ylim(ymin, 100.8)
    ax.set_ylabel(f"% (eixo começa em {ymin:.0f}%)", color=INK2)
    ax.set_title(title, loc="left", color=INK, fontsize=12, fontweight="bold", pad=34)
    leg = ax.legend(ncol=n_series, frameon=False, loc="lower left",
                    bbox_to_anchor=(0, 1.0), fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def to_markdown(df):
    cols = ["model", "accuracy", "precision", "recall", "f1",
            "normal_detect_rate", "atk_detect_rate"]
    heads = ["Modelo", "Accuracy", "Precision", "Recall", "F1",
             "Normal Detect Rate", "Atk Detect Rate"]
    lines = ["| " + " | ".join(heads) + " |", "|" + "---|" * len(heads)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(
            [r["model"]] + [f"{r[c] * 100:.2f}%" for c in cols[1:]]) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./dataset/")
    ap.add_argument("--duration-unit", choices=["us", "ms", "s"], default="us")
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--max-rows", type=int, default=200000,
                    help="amostra estratificada (o CIC real tem milhões de linhas; "
                         "KNN/SVM ficam inviáveis sem limite). 0 = usar tudo")
    ap.add_argument("--cv", type=int, default=0,
                    help="se > 0, também faz validação cruzada estratificada (F1 médio ± desvio)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--jobs", type=int, default=-1)
    args = ap.parse_args()

    X, y = prepare(load_dataset(args.data), args.duration_unit)
    if args.max_rows and len(X) > args.max_rows:
        X, _, y, _ = train_test_split(X, y, train_size=args.max_rows,
                                      stratify=y, random_state=SEED)
        X, y = X.reset_index(drop=True), y.reset_index(drop=True)
        print(f"[INFO] Amostra estratificada: {len(X)} linhas")
    print(f"[INFO] Normal: {(y == 0).sum()} | Ataque: {(y == 1).sum()}")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=args.test_size, random_state=SEED, stratify=y)
    print(f"[INFO] Treino: {len(X_tr)} | Teste: {len(X_te)}\n")

    rows = []
    for name, model in build_models(args.jobs).items():
        r = evaluate(name, model, X_tr, X_te, y_tr, y_te)
        if args.cv > 0:
            skf = StratifiedKFold(args.cv, shuffle=True, random_state=SEED)
            scores = cross_val_score(build_models(args.jobs)[name], X, y, cv=skf, scoring="f1")
            r["cv_f1_mean"], r["cv_f1_std"] = scores.mean(), scores.std()
        rows.append(r)
        print(f"{name:20s} acc={r['accuracy']:.4f} P={r['precision']:.4f} "
              f"R={r['recall']:.4f} F1={r['f1']:.4f}  "
              f"fit={r['fit_s']:.1f}s")

    df = pd.DataFrame(rows).sort_values("f1", ascending=False).reset_index(drop=True)

    os.makedirs(args.out, exist_ok=True)
    df.to_csv(os.path.join(args.out, "model_comparison.csv"), index=False)
    with open(os.path.join(args.out, "model_comparison.md"), "w") as f:
        f.write(to_markdown(df) + "\n")

    lo = max(0, np.floor(min(df[["accuracy", "precision", "recall", "f1"]].min().min(),
                             df[["normal_detect_rate", "atk_detect_rate"]].min().min()) * 20) / 20 * 100 - 5)
    grouped_bars(df, ["accuracy", "precision", "recall", "f1"],
                 ["Accuracy", "Precision", "Recall", "F1"],
                 "Fig. 7(a) Desempenho dos modelos (conjunto de teste)",
                 os.path.join(args.out, "fig7a_metrics.png"), lo)
    grouped_bars(df, ["normal_detect_rate", "atk_detect_rate"],
                 ["Normal Detect Rate", "Atk Detect Rate"],
                 "Fig. 7(b) Taxa de detecção de tráfego normal e de ataque",
                 os.path.join(args.out, "fig7b_detect_rates.png"), lo)

    print("\n" + to_markdown(df))
    print(f"\n[OK] Resultados em {args.out}/")


if __name__ == "__main__":
    main()
