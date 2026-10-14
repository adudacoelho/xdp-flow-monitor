#!/usr/bin/env python3
"""Somente leitura: salva o mapa flow_map do programa registrado na observação."""
import argparse
import json
from pathlib import Path
import subprocess


def bpf(*args):
    return json.loads(subprocess.check_output(['bpftool', '-j', *args], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observacao', type=Path)
    parser.add_argument('etapa', choices=['antes', 'fixa', 'cheio', 'espera', 'novo', 'final'])
    args = parser.parse_args()
    out = args.observacao / ('mapa-' + args.etapa + '.json')
    if out.exists():
        parser.error(f'{out} já existe; escolha uma nova execução para preservar a evidência.')
    attached = json.loads((args.observacao / 'xdp-attached.json').read_text())
    prog_id = attached[0]['xdp']['prog']['id']
    prog = bpf('prog', 'show', 'id', str(prog_id))
    if isinstance(prog, list):
        prog = prog[0]
    candidates = []
    for map_id in prog.get('map_ids', []):
        info = bpf('map', 'show', 'id', str(map_id))
        if isinstance(info, list):
            info = info[0]
        if info.get('name') == 'flow_map':
            candidates.append(info)
    if len(candidates) != 1:
        raise RuntimeError('Não foi encontrado exatamente um flow_map deste programa.')
    info = candidates[0]
    entries = bpf('map', 'dump', 'id', str(info['id']))
    if not isinstance(entries, list):
        raise RuntimeError('Formato inesperado do dump; não interpretar como mapa vazio.')
    result = dict(programa=prog_id, mapa=info, quantidade=len(entries), entradas=entries)
    with out.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(f'{len(entries)} entradas; capacidade {info["max_entries"]}. Salvo em {out}')


if __name__ == '__main__':
    main()
