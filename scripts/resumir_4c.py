#!/usr/bin/env python3
"""Gera tabelas IV-C a partir dos dados locais, sem alterar os resultados brutos."""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from resumir_4b import read, epoch, params, samples, avg, fmt


def expected_ips(n):
    return {f'198.18.{i//256}.{i%256}' for i in range(1,n-5)} | {f'192.168.157.{i}' for i in range(101,107)}


def collect(root):
    generators=sorted((root/'generator').glob('*-traffic-fig6-*'))
    rows=[];used=set()
    for obs in sorted((root/'target').glob('*-observe-fig6-*')):
        run=obs.name.split('-observe-',1)[1];op=params(obs)
        a,b=epoch(obs/'start-epoch.txt'),epoch(obs/'end-epoch.txt')
        mode=op.get('MODE','');kind='syn' if run.startswith('fig6-syn-') else 'tcp'
        r=dict(date=obs.name[:8],run=run,observation=obs.name,generator='',kind=kind,mode=mode,
               rules=int(op.get('RULES',0)) if mode!='baseline' else 0,status='revisar',
               throughput_gbps=None,change_baseline_pct=None,retransmits=None,
               cpu_host_pct=None,memory_host_mib=None,rx_pps=None,sent_pps=None,
               cpu_samples=0,memory_samples=0,network_samples=0,
               observed_rules=None,iptables_dropped=None,xdp_mode=None,
               load_seconds=None,observation_seconds=b-a if a is not None and b is not None else None,
               mtu='',kernel=read(obs/'kernel.txt').strip(),notes='')
        notes=[];issues=[]
        mtu=re.search(r'\bmtu (\d+)',read(obs/'interface.txt'));r['mtu']=mtu[1] if mtu else ''
        if a is None or b is None:
            r['notes']='sem início/fim da observação';rows.append(r);continue
        candidates=[g for g in generators if g.name.endswith('-traffic-'+run)
                    and epoch(g/'start-epoch.txt') is not None and a<=epoch(g/'start-epoch.txt')<=b]
        if len(candidates)!=1:
            r['notes']=f'associação ausente/ambígua ({len(candidates)} cargas)';rows.append(r);continue
        g=candidates[0];used.add(g.name);r['generator']=g.name
        c,d=epoch(g/'start-epoch.txt'),epoch(g/'end-epoch.txt');gp=params(g)
        if gp.get('KIND')!=kind: issues.append('tipo da carga difere do RUN')
        if d is None:issues.append('carga sem fim')
        else:
            r['load_seconds']=d-c
            if d>b:issues.append('observação não cobriu toda a carga')
            if d-c<float(gp.get('DURATION',0))-.5:issues.append('carga menor que duração solicitada')
            cpu=samples(obs/'cpu.txt',c,d,'%idle',('CPU','all'))
            mem=samples(obs/'memory.txt',c,d,'kbmemused')
            net=samples(obs/'network.txt',c,d,'rxpck/s',('IFACE','lab0'))
            r.update(cpu_host_pct=100-avg(cpu) if cpu else None,
                     memory_host_mib=avg(mem)/1024 if mem else None,rx_pps=avg(net),
                     cpu_samples=len(cpu),memory_samples=len(mem),network_samples=len(net))
            if not cpu or not mem or not net:issues.append('amostras de recursos ausentes')
        status=read(obs/'status.txt').strip()
        if status!='exit_code=0':issues.append(status or 'sem código de saída')
        if (obs/'shutdown.log').exists():issues.append('encerramento forçado')
        # Kernel e MTU do gerador devem corresponder aos do target.
        gm=re.search(r'\bmtu (\d+)',read(g/'interface.txt'))
        if not gm or gm[1]!=r['mtu']:issues.append('MTU do gerador divergente/ausente')
        try:
            if kind=='tcp':
                data=json.loads(read(g/'iperf.json'))
                if data.get('error'):issues.append('iperf: '+str(data['error']))
                rx=data.get('end',{}).get('sum_received',{})
                if 'bits_per_second' not in rx or rx.get('seconds',0)<float(gp.get('DURATION',50))-.5:
                    issues.append('iperf incompleto')
                else:r['throughput_gbps']=rx['bits_per_second']/1e9
                r['retransmits']=data.get('end',{}).get('sum_sent',{}).get('retransmits')
            else:
                logs=list(g.glob('hping-*.log'))
                counts=[re.findall(r'(\d+) packets transmitted',read(p)) for p in logs]
                if len(counts)==6 and all(counts) and d is not None and d>c:
                    r['sent_pps']=sum(int(v[-1]) for v in counts)/(d-c)
                else:issues.append('hping incompleto')
            if mode=='xdp-static':
                entries=json.loads(read(obs/'xdp-rules.json'))
                ips=set()
                for entry in entries:
                    key=[int(v,16) for v in entry['key']]
                    if len(key)!=8 or key[:4]!=[32,0,0,0]:raise ValueError('chave LPM inesperada')
                    ips.add('.'.join(map(str,key[4:])))
                r['observed_rules']=len(entries)
                if ips!=expected_ips(r['rules']) or len(entries)!=r['rules']:issues.append('regras XDP divergentes')
                attached=json.loads(read(obs/'xdp-attached.json'))[0].get('xdp',{})
                prog=json.loads(read(obs/'xdp-program.json'))
                r['xdp_mode']=attached.get('mode')
                if not attached.get('attached') or attached.get('prog',{}).get('id')!=prog.get('id'):
                    issues.append('programa XDP não confirmado')
                if kind=='syn':notes.append('sem contador XDP_DROP; bloqueio ainda não comprovado por contagem')
            elif mode=='iptables':
                rules=[]
                for line in read(obs/'iptables-counters.txt').splitlines():
                    parts=line.split()
                    if len(parts)>=9 and parts[0].isdigit() and parts[2]=='DROP':
                        rules.append((parts[7],int(parts[0])))
                r['observed_rules']=len(rules)
                if {ip for ip,_ in rules}!=expected_ips(r['rules']) or len(rules)!=r['rules']:
                    issues.append('regras iptables divergentes')
                r['iptables_dropped']=sum(n for ip,n in rules)
                if kind=='syn' and not all(n>0 for ip,n in rules if ip.startswith('192.168.157.')):
                    issues.append('alguma origem simulada sem DROP registrado')
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            issues.append('arquivo inválido: '+str(exc)[:100])
        r['status']='revisar' if issues else 'completa'
        r['notes']='; '.join(issues+notes)
        rows.append(r)
    # Baseline do mesmo dia/kernel/MTU e tipo de carga; não mistura campanhas históricas.
    for r in rows:
        baseline=[x['throughput_gbps'] for x in rows if x['status']=='completa' and x['mode']=='baseline'
                  and x['kind']==r['kind'] and (x['date'],x['kernel'],x['mtu'])==(r['date'],r['kernel'],r['mtu'])
                  and x['throughput_gbps'] is not None]
        if r['status']=='completa' and r['throughput_gbps'] is not None and baseline:
            r['change_baseline_pct']=(r['throughput_gbps']/avg(baseline)-1)*100
    return rows,[g.name for g in generators if g.name not in used]


def table(rows,cols):
    return ['| '+' | '.join(title for key,title in cols)+' |','|'+'---|'*len(cols)]+[
        '| '+' | '.join(fmt(r.get(key)).replace('\n',' ') for key,title in cols)+' |' for r in rows]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,default=Path('testes/testes-chen/results-servidor'))
    ap.add_argument('--out',type=Path,default=Path('docs/testes-chen/tabelas-4c'))
    args=ap.parse_args();rows,unmatched=collect(args.results)
    if not rows:ap.error('Nenhuma observação IV-C encontrada')
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'rodadas.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (args.out/'cargas-sem-par.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['generator']);w.writerows([g] for g in unmatched)
    latest=max(r['date'] for r in rows);recent=[r for r in rows if r['date']==latest]
    lines=['# Avaliação IV-C — filtragem XDP versus iptables','',
           'Gerado por `python3 scripts/resumir_4c.py`. Resultados brutos preservados.', '',
           f'## Comparação de {latest[:4]}-{latest[4:6]}-{latest[6:]}','',
           'Os percentuais de throughput usam a média dos baselines completos do mesmo dia, kernel e MTU. CPU e memória são do servidor inteiro, não exclusivas do filtro. Somente intervalos completos de 1 s dentro da carga entram nas médias. Sem inferência de significância com tão poucas repetições.', '',
           '### Throughput TCP — sem ataque','']
    cols=[('observation','Observação (UTC)'),('mode','Modo'),('rules','Regras'),('status','Estado'),('throughput_gbps','Gbit/s recebidos'),('change_baseline_pct','Δ baseline %'),('retransmits','Retransmissões'),('cpu_host_pct','CPU host %'),('memory_host_mib','Memória host MiB')]
    tcp=[r for r in recent if r['kind']=='tcp' and r['status']=='completa']
    bases=[r['throughput_gbps'] for r in tcp if r['mode']=='baseline']
    if bases:
        lines += [f'Baseline: média de {len(bases)} rodadas = {avg(bases):.3f} Gbit/s. Os baselines individuais permanecem na tabela.', '']
    for r in tcp:
        if r['mode']!='baseline' and r['change_baseline_pct'] is not None:
            lines += [f"- {r['mode']}, {r['rules']} regras: {r['throughput_gbps']:.3f} Gbit/s, variação de {r['change_baseline_pct']:+.2f}% frente ao baseline compatível."]
    for n in sorted({r['rules'] for r in tcp if r['rules']}):
        xr=[r['throughput_gbps'] for r in tcp if r['mode']=='xdp-static' and r['rules']==n]
        ir=[r['throughput_gbps'] for r in tcp if r['mode']=='iptables' and r['rules']==n]
        if xr and ir:
            direction='inferior' if avg(xr)<avg(ir) else 'superior' if avg(xr)>avg(ir) else 'igual'
            lines += ['', f'Com {n} regras, a média observada do XDP foi {direction} à do iptables ({(avg(xr)/avg(ir)-1)*100:+.2f}%). Amostras pequenas não permitem generalizar; a causa da diferença não pode ser deduzida dessas médias.', '']
    lines += ['']
    lines+=table([r for r in recent if r['kind']=='tcp'],cols)
    lines+=['','### CPU e memória sob SYN','']
    lines+=table([r for r in recent if r['kind']=='syn'],[('mode','Modo'),('rules','Regras'),('status','Estado'),('sent_pps','pps enviados'),('rx_pps','rxpck/s em lab0'),('cpu_host_pct','CPU host %'),('memory_host_mib','Memória host MiB'),('iptables_dropped','DROP iptables'),('cpu_samples','Amostras CPU')])
    lines+=['','### Verificação dos filtros','']
    lines+=table([r for r in recent if r['mode']!='baseline'],[('run','RUN'),('observed_rules','Regras conferidas'),('xdp_mode','Modo XDP (valor registrado)'),('notes','Observações')])
    lines+=['','## Todas as tentativas, incluindo históricas','']
    lines+=table(rows,[('observation','Observação (UTC)'),('status','Estado'),('generator','Gerador associado'),('notes','Observações')])
    lines+=['','## Como interpretar','',
            '- Este experimento usa xdp_min, filtro estático isolado. Não avalia o coletor nem o XGBoost do detector completo.',
            '- Completa significa que arquivos, duração, associação e regras passaram nas verificações do script. Não certifica a reprodução do artigo nem o bloqueio XDP.',
            '- A associação exige mesmo RUN e início da carga dentro da observação. Cargas sem par estão no CSV separado; não escolhemos uma tentativa arbitrariamente.',
            '- CPU = 100 − %idle médio das linhas all; inclui espera de I/O. Memória = kbmemused médio / 1024. Memória inclui estado do host e não permite atribuir diferenças ao filtro.',
            '- PPS enviados = soma dos seis hping / duração externa da carga. rxpck/s é a estatística da interface, não um contador de decisões XDP; não permite deduzir descartes XDP.',
            '- iptables: conferimos as regras e seus contadores DROP. XDP: conferimos chaves /32, programa anexado e quantidade de regras; faltam contadores PASS/DROP para confrontar envio e descarte.',
            '- O KIND do parameters.txt da observação usa um padrão tcp mesmo sob SYN. O script usa o nome RUN e confere KIND no gerador, que identifica a carga efetiva.',
            '- MTU e kernel estão em rodadas.csv. Commit, afinidade de CPU e carga concorrente não estão identificados por rodada; são limites da comparação.',
            '- Para avaliar escalabilidade até 512 regras ainda são necessárias outras quantidades, repetições equilibradas, ordem alternada e carga observada calibrada. Resultados de 16 regras não descrevem toda a curva.',
            f'- {len(rows)} observações catalogadas; {len(unmatched)} cargas sem par. Campos ausentes podem resultar de tentativas interrompidas ou download incompleto.', '']
    (args.out/'comparacao.md').write_text('\n'.join(lines))
    print(f'{len(rows)} observações. Relatório: {args.out}/comparacao.md')


if __name__=='__main__':main()
