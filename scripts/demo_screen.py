#!/usr/bin/env python3
"""Mostra as ultimas janelas e decisoes reais do monitor."""
import argparse
import re
import shutil
import sys
import time
from pathlib import Path


def parse_log(content):
    rows = {}
    current = None
    for line in content.splitlines():
        if line.startswith('Janela fechada — src: '):
            current = line.split(': ', 1)[1].strip()
            blocked = rows.get(current, {}).get('blocked', False)
            rows[current] = dict(pps=0.0, decision='AGUARDANDO', blocked=blocked)
        elif current and line.startswith('Flow Packets/s'):
            try:
                rows[current]['pps'] = float(line.split(':', 1)[1])
            except ValueError:
                pass
        elif current and line == '[Normal]':
            rows[current]['decision'] = 'NORMAL'
        elif current and line.startswith('[ATAQUE DETECTADO]'):
            rows[current]['decision'] = 'ATAQUE'
        elif current and line.startswith('[AVISO] ml_daemon'):
            rows[current]['decision'] = 'SEM MODELO'
        elif line.startswith('[BLOQUEADO] IP adicionado à blacklist: '):
            ip = line.rsplit(': ', 1)[1].strip()
            if ip in rows:
                rows[ip]['blocked'] = True
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.run):
        parser.error('RUN invalido')
    paths = sorted(args.results.glob(f'*-observe-{args.run}/monitor.log'))
    if not paths:
        parser.error('Inicie make demo-detector e aguarde PRONTO primeiro.')
    if not sys.stdout.isatty():
        parser.error('Abra em um terminal interativo.')
    path = paths[-1]
    try:
        print('\033[?25l', end='', flush=True)
        while True:
            content = path.read_text(errors='replace')
            rows = parse_log(content)
            lines = ['XDP FLOW MONITOR | AO VIVO', f'RODADA: {args.run}', '',
                     'ULTIMA JANELA DE CADA IP (5 s)',
                     'IP               PACOTES/s  MODELO      BLACKLIST', '-' * 57]
            peak = max((r['pps'] for r in rows.values()), default=1) or 1
            for ip, row in sorted(rows.items(), key=lambda item: -item[1]['pps']):
                lines += [f"{ip:<16} {row['pps']:>9.1f}  {row['decision']:<11} "
                          f"{'REGISTRADO' if row['blocked'] else '--'}",
                          '  ' + '#' * min(30, round(30 * row['pps'] / peak)), '']
            if not rows:
                lines += ['AGUARDANDO A PRIMEIRA JANELA...', '']
            lines += ['.10: TCP de referencia | .101-.106: carga simulada',
                      'Barras relativas; ultima janela, nao taxa instantanea.',
                      'Sem nova janela, o ultimo valor permanece.',
                      'BLACKLIST: insercao no log; nao mede descartes.',
                      'Ctrl+C fecha somente este painel.']
            if '[ERRO]' in content:
                lines += ['ERRO NO MONITOR: confira make demo-log.']
            if shutil.get_terminal_size().columns < 64:
                lines.insert(0, 'AMPLIE O TERMINAL PARA 64 COLUNAS')
            print('\033[2J\033[H' + '\n'.join(lines), end='', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print('\033[?25h\033[0m')


if __name__ == '__main__':
    main()
