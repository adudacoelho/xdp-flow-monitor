#!/usr/bin/env python3
"""Resume IV-B sem ler logs de pacotes inteiros; usa somente a biblioteca padrão."""
import argparse
import csv
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path


def read(p):
    return p.read_text(errors='replace') if p.is_file() else ''


def epoch(p):
    try:
        return float(read(p).strip())
    except ValueError:
        return None


def params(p):
    return dict(line.split('=', 1) for line in read(p / 'parameters.txt').splitlines() if '=' in line)


def avg(values):
    return statistics.mean(values) if values else None


def samples(path, start, end, column, entity=None):
    """Sysstat de 1 s: exclui intervalos que atravessam os limites da carga.

    Infere offset do relógio textual pelo primeiro cabeçalho e início epoch;
    não interpreta a linha Average como uma amostra. Trata virada de dia.
    """
    text = read(path)
    header = None
    anchor = None
    previous = None
    result = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or not re.fullmatch(r'\d\d:\d\d:\d\d', parts[0]):
            continue
        h, m, s = map(int, parts[0].split(':'))
        seconds = h * 3600 + m * 60 + s
        if column in parts:
            header = parts[1:]
            if anchor is None:
                anchor = seconds
            continue
        if header is None or len(parts[1:]) != len(header):
            continue
        if previous is not None and seconds < previous:
            anchor -= 86400
        previous = seconds
        # O primeiro cabeçalho marca o início da observação em segundos locais.
        observation_start = epoch(path.parent / 'start-epoch.txt')
        if observation_start is None:
            continue
        t = int(observation_start) + seconds - anchor
        row = dict(zip(header, parts[1:]))
        if t - 1 < start or t > end or (entity and row.get(entity[0]) != entity[1]):
            continue
        try:
            result.append(float(row[column]))
        except (KeyError, ValueError):
            pass
    return result


def us(value):
    match = re.fullmatch(r'([\d.]+)(ns|us|µs|ms|s)', value)
    if not match:
        raise ValueError(value)
    return float(match[1]) * {'ns': .001, 'us': 1, 'µs': 1, 'ms': 1000, 's': 1e6}[match[2]]


def summarize(root):
    generators = list((root / 'generator').glob('*-traffic-fig5-*'))
    used = set()
    rows = []
    for obs in sorted((root / 'target').glob('*-observe-fig5-*')):
        run = obs.name.split('-observe-', 1)[1]
        kind = 'syn' if run.startswith('fig5-syn-') else 'latency' if run.startswith('fig5-lat-') else 'tcp'
        a, b = epoch(obs / 'start-epoch.txt'), epoch(obs / 'end-epoch.txt')
        r = dict(date=obs.name[:8], observation=obs.name, run=run, kind=kind,
                 mode=params(obs).get('MODE', ''), generator='', status='incompleta', notes='',
                 throughput_gbps=None, cpu_host_pct=None, memory_host_mib=None,
                 sent_pps=None, latency_avg_us=None, cpu_samples=0, memory_samples=0,
                 latency_samples=0, bad_percentiles=0, load_seconds=None,
                 observation_seconds=b-a if a is not None and b is not None else None,
                 mtu='', kernel=read(obs/'kernel.txt').strip())
        mtu = re.search(r'\bmtu (\d+)', read(obs/'interface.txt'))
        r['mtu'] = mtu[1] if mtu else ''
        notes = []
        if a is None:
            r['notes'] = 'sem início da observação'; rows.append(r); continue
        # Mesmo RUN e início da carga dentro da duração prevista/observada.
        limit = b if b is not None else a + float(params(obs).get('DURATION', 0))
        candidates = [g for g in generators if g.name.endswith('-traffic-'+run)
                      and epoch(g/'start-epoch.txt') is not None
                      and a <= epoch(g/'start-epoch.txt') <= limit]
        if len(candidates) != 1:
            r['notes'] = f'associação ambígua/ausente: {len(candidates)} cargas'; rows.append(r); continue
        g = candidates[0]; used.add(g.name); r['generator'] = g.name
        c, d = epoch(g/'start-epoch.txt'), epoch(g/'end-epoch.txt')
        if b is None: notes.append('observação sem fim registrado')
        if d is None: notes.append('carga sem fim registrado')
        if d is not None:
            r['load_seconds'] = d-c
            if b is not None and d > b: notes.append('observação não cobriu toda a carga')
            cpu = samples(obs/'cpu.txt', c, d, '%idle', ('CPU','all'))
            mem = samples(obs/'memory.txt', c, d, 'kbmemused')
            r['cpu_samples'], r['memory_samples'] = len(cpu), len(mem)
            r['cpu_host_pct'] = 100-avg(cpu) if cpu else None
            r['memory_host_mib'] = avg(mem)/1024 if mem else None
            if not cpu or not mem: notes.append('sem amostras de recursos no intervalo')
        status = read(obs/'status.txt').strip()
        if status and status != 'exit_code=0': notes.append(status)
        if (obs/'shutdown.log').exists(): notes.append('captura encerrada à força; revisar log')
        if r['mode'] == 'collection-current':
            try:
                attached = json.loads(read(obs/'xdp-attached.json'))
                if not any(x.get('xdp',{}).get('attached',0) for x in attached): notes.append('XDP não confirmado')
            except (ValueError, TypeError): notes.append('XDP não confirmado')
        try:
            if kind == 'tcp':
                data = json.loads(read(g/'iperf.json'))
                if data.get('error'): notes.append('iperf: '+str(data['error']))
                received = data.get('end',{}).get('sum_received',{})
                if 'bits_per_second' in received and received.get('seconds',0) >= float(params(g).get('DURATION',50))-.5:
                    r['throughput_gbps'] = received['bits_per_second']/1e9
                else: notes.append('iperf incompleto')
            elif kind == 'syn':
                logs = list(g.glob('hping-*.log'))
                counts = [re.findall(r'(\d+) packets transmitted', read(p)) for p in logs]
                if len(counts)==6 and all(counts) and d is not None and d>c:
                    r['sent_pps'] = sum(int(x[-1]) for x in counts)/(d-c)
                else: notes.append('estatísticas hping incompletas')
            else:
                records = [json.loads(line) for line in read(g/'ethr.json').splitlines() if line.strip()]
                records = [x for x in records if x.get('Type')=='LatencyResult']
                r['latency_samples'] = len(records)
                r['latency_avg_us'] = avg([us(x['Avg']) for x in records])
                for x in records:
                    values = [us(x[k]) for k in ['Min','P50','P90','P95','P99','P999','P9999','Max']]
                    r['bad_percentiles'] += not all(v<=w for v,w in zip(values,values[1:]))
                if not records: notes.append('Ethr sem amostras')
                if r['bad_percentiles']: notes.append('percentis Ethr inconsistentes; Avg provisório')
        except (ValueError, KeyError, TypeError) as exc:
            notes.append('arquivo de métrica inválido: '+str(exc)[:90])
        critical = [x for x in notes if not x.startswith('percentis Ethr')]
        r['status'] = 'revisar' if critical else 'completa*' if kind=='latency' and r['bad_percentiles'] else 'completa'
        r['notes'] = '; '.join(notes)
        rows.append(r)
    return rows, [g.name for g in generators if g.name not in used]


def fmt(v):
    return '—' if v is None or v=='' else f'{v:.2f}' if isinstance(v,float) else str(v).replace('|','/')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,default=Path('testes/testes-chen/results-servidor'))
    ap.add_argument('--out',type=Path,default=Path('docs/testes-chen/tabelas-4b'))
    args=ap.parse_args()
    rows, unmatched=summarize(args.results)
    if not rows: ap.error('Nenhuma observação fig5 encontrada')
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'rodadas.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    latest=max(r['date'] for r in rows)
    lines=['# Comparação IV-B', '', 'Gerado por `python3 scripts/resumir_4b.py`. Todos os dados originais foram preservados.', '',
           'CPU e memória são do servidor compartilhado, selecionadas somente em intervalos completos de 1 s dentro da carga. Não representam consumo exclusivo do coletor. O CSV inclui todas as datas e caminhos para auditoria.', '',
           'Cada associação exige mesmo RUN e início da carga dentro da observação. Tentativas sem correspondência única são separadas. A categoria completa verifica arquivos e duração; não certifica a correção do coletor ou independência experimental.', '',
           'Não agrupamos dias, kernels, MTUs ou versões diferentes. Não há comparação percentual contra baseline de outro dia. Falta identificação de commit por rodada para assegurar equivalência de versão. Arquivos antigos arquivados em resultados-antigos não são duplicados nesta análise.', '',
           f'## Dia mais recente: {latest}', '',
           'Neste recorte, a ausência de algum cenário significa que ele precisa ser medido ou baixado; não substituímos por uma rodada antiga.', '', 'Todas as tentativas desse dia aparecem abaixo, inclusive as que precisam de revisão. Os horários nos nomes das pastas são UTC.', '']
    columns=[('observation','Observação (UTC)'),('mode','Modo'),('status','Estado'),('throughput_gbps','Gbit/s recebidos'),('cpu_host_pct','CPU host %'),('memory_host_mib','Memória host MiB'),('sent_pps','pps enviados'),('latency_avg_us','Latência Avg µs'),('cpu_samples','Amostras CPU'),('notes','Observações')]
    for kind,title in [('tcp','Throughput TCP'),('syn','SYN: CPU e memória'),('latency','Latência TCP')]:
        lines += ['### '+title,'','| '+' | '.join(y for x,y in columns)+' |','|'+'---|'*len(columns)]
        for r in rows:
            if r['date']==latest and r['kind']==kind:
                lines.append('| '+' | '.join(fmt(r[k]) for k,_ in columns)+' |')
        if not any(r['date']==latest and r['kind']==kind and r['mode']=='baseline' and r['status']=='completa' for r in rows) and kind=='tcp':
            lines.append('\nBaseline TCP ausente nesse dia: não é possível calcular a queda relativa com equivalência temporal.')
        lines.append('')
    lines += ['## Limites e próximos passos','',
              '- Latência: média aritmética dos Avg de cada registro, não média de todas as medições individuais. Percentis inconsistentes não são publicados; Avg permanece provisório.',
              '- PPS: soma dos transmitidos pelo hping dividida pela duração externa da carga; não comprova recepção pelo kernel.',
              '- MTU e kernel estão no CSV; conferir antes de comparar. Repetições com mesmo RUN não são fundidas.',
              '- Arquivos ausentes podem indicar download incompleto. Preserve a tentativa até verificar no servidor.',
              '- Logs TShark/monitor de vários GB não foram varridos; perdas da captura e erros internos exigem análise adicional desses logs.',
              f'- {len(rows)} observações catalogadas; {len(unmatched)} cargas sem associação única listadas em cargas-sem-par.csv.', '']
    (args.out/'comparacao.md').write_text('\n'.join(lines))
    with (args.out/'cargas-sem-par.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['generator']);w.writerows([x] for x in unmatched)
    print(f'{len(rows)} observações. Tabelas em {args.out}/comparacao.md; detalhes em rodadas.csv')


if __name__=='__main__': main()
