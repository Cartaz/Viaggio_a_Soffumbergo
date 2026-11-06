"""Read-only timing context for an accepted native rendered lap, not a profiler."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import numpy as np


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run=args.run.resolve();name=run.name
    if args.output.exists():raise RuntimeError('Preserve previous analysis')
    accepted=json.loads((run/'report.json').read_text(encoding='utf-8-sig'))
    if not accepted['full_lap_passed'] or not accepted['rendering']:
        raise RuntimeError('A completed native rendered lap is required')
    frames=run/(name+'_frames.csv');log=run/'engine.log'
    a=np.genfromtxt(frames,delimiter=',',names=True)
    a=a[(a['elapsed_s']>=30)&np.isfinite(a['frame_ms'])&(a['frame_ms']>0)]
    rx=re.compile(r'^\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]')
    events=[]
    for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
        m=rx.match(line)
        if m:
            t=datetime.datetime.strptime(m[1],'%Y.%m.%d-%H.%M.%S:%f').replace(tzinfo=datetime.timezone.utc).timestamp()
            events.append((t,line))
    # This native initialization log immediately precedes the monotonic frame
    # clock initialization. It is an approximate anchor, never an exact trace.
    anchor=next(t for t,s in events if 'CIRCUIT_DRIVE initialized' in s)
    events=[(t-anchor,s) for t,s in events]
    compactions=np.array([t for t,s in events if 'Compacting FUObjectHashTables' in s])
    hitch_indices=np.flatnonzero(a['frame_ms']>1000/30)
    groups=[]
    for i in hitch_indices:
        if not groups or a['elapsed_s'][i]-a['elapsed_s'][groups[-1][-1]]>2:
            groups.append([])
        groups[-1].append(int(i))
    clusters=[]
    for group in groups:
        rows=a[group];start=float(rows['elapsed_s'][0]);end=float(rows['elapsed_s'][-1])
        clusters.append({'start_elapsed_s':start,'end_elapsed_s':end,'hitch_frames':len(group),
            'frame_max_ms':float(rows['frame_ms'].max()),'gpu_max_ms':float(rows['gpu_ms'].max()),
            'approximate_utc_start':datetime.datetime.fromtimestamp(anchor+start,datetime.timezone.utc).isoformat(),
            'compaction_events_within_half_second':int(np.count_nonzero((compactions>=start-.5)&(compactions<=end+.5)))})
    worst=[]
    for i in np.flatnonzero(a['frame_ms']>100):
        t=float(a['elapsed_s'][i]);nearest=sorted(events,key=lambda e:abs(e[0]-t))[:2]
        worst.append({'elapsed_s':t,'frame_ms':float(a['frame_ms'][i]),'gpu_ms':float(a['gpu_ms'][i]),
            'nearest_compaction_distance_s':float(np.min(np.abs(compactions-t))) if len(compactions) else None,
            'nearest_native_logs':[{'offset_s':round(et-t,4),'text':s} for et,s in nearest]})
    report={'build_id':accepted['build_id'],'runtime_binary_sha256':accepted['runtime_binary_sha256'],
        'input_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [frames,log,run/'report.json']},
        'clock_alignment':'Approximate UTC anchor from CIRCUIT_DRIVE initialized; no exact shared timestamp or per-thread trace was recorded.',
        'warmup_excluded_s':30,'frames_over_33_333_ms':len(hitch_indices),'hitch_clusters':len(clusters),
        'largest_clusters':sorted(clusters,key=lambda c:c['hitch_frames'],reverse=True)[:20],
        'frames_over_100_ms':worst,
        'limitations':'Compaction log duration is not total garbage collection time. GPU timing may be delayed. Event proximity cannot establish causality; absent events cannot exclude unlogged streaming or work. Concurrent QA/import/cook/compile prevents an isolated benchmark.',
        'causal_attribution_established':False,'performance_fix_applied':False}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'frames_over_100_ms':len(worst),'hitch_clusters':len(clusters),'largest_clusters':report['largest_clusters'][:3],
        'minimum_compaction_distance_for_over_100ms_frames_s':min((w['nearest_compaction_distance_s'] for w in worst),default=None)}))


if __name__=='__main__':main()
