#!/usr/bin/env python3
"""Demonstracao offline do modelo existente; nao treina nem altera artefatos."""
import argparse
import csv
import hashlib
import math
import random
import sys
from pathlib import Path

FEATURES = [
    ('Flow Duration', 'duration_sec'),
    ('Flow Packets/s', 'flow_pkts_per_sec'),
    ('Flow Bytes/s', 'flow_bytes_per_sec'),
    ('ACK Flag Count', 'ack_count'), ('SYN Flag Count', 'syn_count'),
    ('RST Flag Count', 'rst_count'), ('URG Flag Count', 'urg_count'),
    ('CWR Flag Count', 'cwr_count'),
    ('Packet Length Mean', 'mean_pkt_len'),
    ('Min Packet Length', 'min_pkt_len'),
]


def load_rows(path):
    rows = []
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
        missing = {key for key, _ in FEATURES} | {'Label'}
        missing -= set(reader.fieldnames or [])
        if missing:
            raise ValueError('Colunas ausentes: ' + ', '.join(sorted(missing)))
        for line, row in enumerate(reader, 2):
            label = row['Label'].strip()
            if not label:
                raise ValueError(f'Rotulo vazio na linha {line}')
            values = [float(row[key]) for key, _ in FEATURES]
            if not all(math.isfinite(v) and v >= 0 for v in values):
                raise ValueError(f'Valor negativo ou nao finito na linha {line}')
            rows.append((line, values, label, label.upper() != 'BENIGN'))
    if not rows:
        raise ValueError('CSV sem amostras')
    return rows


def select_rows(rows, count):
    # Alterna classes usando somente rotulos; nunca escolhe com base na previsao.
    groups = [[row for row in rows if row[3] == cls] for cls in (False, True)]
    rng = random.Random(42)
    for group in groups:
        rng.shuffle(group)
    selected = []
    while len(selected) < count and any(groups):
        for group in groups:
            if group and len(selected) < count:
                selected.append(group.pop())
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--batch', action='store_true', help='Executar sem pausas')
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples deve ser positivo')
    try:
        import numpy as np
        import xgboost as xgb
    except ImportError:
        parser.exit(1, 'Dependencias ausentes: numpy e xgboost.\n'
                    'No servidor com a imagem pronta, use make demo-csv-docker.\n'
                    'Ou indique CSV_PYTHON=/caminho/da/venv/bin/python.\n')
    try:
        rows = load_rows(args.csv)
        model = xgb.Booster(params={'nthread': 1})
        model.load_model(args.model)
        names = [name for _, name in FEATURES]
        if model.feature_names != names:
            raise ValueError('Nomes/ordem das features do modelo diferem do treinador atual')
        if model.num_features() != len(names):
            raise ValueError('Quantidade de features incompativel')
        selected = select_rows(rows, args.samples)
        # Replica o treinador atual: renomeia duracao SEM converter a escala.
        # Isso demonstra o modelo no dominio do CSV, nao corrige a inferencia ao vivo.
        matrix = xgb.DMatrix(np.asarray([r[1] for r in selected], dtype=np.float32),
                             feature_names=names)
        probabilities = model.predict(matrix)
        if probabilities.shape != (len(selected),) or not np.isfinite(probabilities).all():
            raise ValueError('Saida do modelo nao e um vetor binario finito')
        if ((probabilities < 0) | (probabilities > 1)).any():
            raise ValueError('Saida fora de [0, 1]; confira o objetivo do modelo')
        print('CSV E MODELO CARREGADOS')
        print(f'CSV: {args.csv.name} | {len(rows)} linhas')
        print(f'Modelo: {args.model.name}')
        print('SHA256: ' + hashlib.sha256(args.model.read_bytes()).hexdigest())
        print('Duracao: escala original do CSV, como no treinador atual.')
        print('Procedencia treino/teste nao comprovada; nao demonstra generalizacao.')
        print('CSV sintetico local contem inconsistencias; nao valida trafego real.')
        if args.check:
            print(f'Inferencia conferida em {len(selected)} amostras. Nenhum arquivo alterado.')
            return
        interactive = not args.batch
        if interactive and not sys.stdin.isatty():
            raise ValueError('Use terminal interativo ou --batch')
        if interactive:
            input('\nEnter para iniciar; Ctrl+C para sair...')
        correct = 0
        for index, (row, probability) in enumerate(zip(selected, probabilities), 1):
            line, values, label, expected = row
            predicted = bool(probability > 0.5)
            correct += predicted == expected
            print('\n' + '=' * 60)
            print('XGBOOST | DEMONSTRACAO OFFLINE\n')
            print(f'AMOSTRA {index}/{len(selected)} | LINHA {line} DO CSV\n')
            print(f'VOLUME: {values[1]:,.1f} pacotes/s\n')
            print('ROTULO ESPERADO:  ' + ('ATAQUE' if expected else 'NORMAL'))
            print('PREVISAO REAL:    ' + ('ATAQUE' if predicted else 'NORMAL'))
            print(f'PONTUACAO ATAQUE: {float(probability):.4f} | limiar > 0.5\n')
            print('RESULTADO: ' + ('ACERTO' if predicted == expected else 'ERRO'))
            print(f'ACERTOS: {correct} | ERROS: {index - correct}\n')
            print('DECISAO: ' + ('SOLICITARIA BLOQUEIO' if predicted else 'NAO SOLICITARIA BLOQUEIO'))
            print()
            print('Dados podem ter sido usados no treino.')
            print('Escala original do CSV; nao valida coleta ao vivo.')
            if interactive:
                input('\nEnter para continuar; Ctrl+C para sair...')
        print(f'\nFIM: {correct} acertos e {len(selected) - correct} erros nas amostras exibidas.')
        print('Resultado ilustrativo; nao e uma avaliacao independente do modelo.')
    except (OSError, ValueError, xgb.core.XGBoostError) as exc:
        parser.exit(1, f'ERRO: {exc}\n')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nDemonstracao encerrada.')
