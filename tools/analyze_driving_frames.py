"""Summarize native full-lap frame telemetry, preserving scope and input hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--warmup',type=float,default=30)
    args=p.parse_args();run=args.run.resolve()
    if args.output.exists():raise RuntimeError('Preserve previous performance evidence')
    accepted=json.loads((run/'report.json').read_text())
    if not accepted['full_lap_passed'] or not accepted['rendering']:raise RuntimeError('A full native rendered lap is required')
    name=run.name;frames_path=run/(name+'_frames.csv');meta_path=run/(name+'.json')
    meta=json.loads(meta_path.read_text(encoding='utf-8-sig'))
    rows=np.genfromtxt(frames_path,delimiter=',',names=True)
    rows=rows[(rows['elapsed_s']>=args.warmup)&np.isfinite(rows['frame_ms'])&(rows['frame_ms']>0)]
    frame=rows['frame_ms'];gpu=rows['gpu_ms'];percentiles=[50,95,99,99.9]
    report={'build_id':accepted['build_id'],'runtime_binary_sha256':accepted['runtime_binary_sha256'],
        'input_sha256':{str(path):sha(path) for path in [frames_path,meta_path,run/'report.json']},
        'full_rendered_lap_passed':True,'RHI':meta['RHI'],'viewport':[meta['viewport_width'],meta['viewport_height']],
        'requested_max_fps':accepted.get('requested_max_fps'),'graphics_settings':meta['graphics_settings'],
        'warmup_seconds_excluded':args.warmup,'analyzed_frames':len(rows),
        'wall_interval_seconds':float(rows['elapsed_s'][-1]-rows['elapsed_s'][0]),
        'duration_average_fps':float(1000/frame.mean()),
        'frame_ms_percentiles':dict(zip(map(str,percentiles),np.percentile(frame,percentiles).tolist())),
        'gpu_ms_percentiles':dict(zip(map(str,percentiles),np.percentile(gpu,percentiles).tolist())),
        'frames_over_33_333_ms':int(np.count_nonzero(frame>1000/30)),
        'frames_over_100_ms':int(np.count_nonzero(frame>100)),'maximum_frame_ms':float(frame.max()),
        'process_peak_rss_bytes':meta['process_peak_rss_bytes'],
        'rhi_texture_allocation_bytes':meta['rhi_texture_allocation_bytes'],
        'vram_semantics':meta['vram_semantics'],
        'scope':'Completed driving route with full Yaris, native 3840x2160, profile C and explicit 60 FPS cap. This is the recorded world/binary only.',
        'concurrent_work':'QA simulation, asset import, cooking and compilation also ran on this machine during parts of this lap. This is not an isolated performance benchmark.',
        'remaining_limits':'Stalls remain in the recorded frame stream. No certification of stable 60 FPS or of later structure/vegetation/world revisions.',
        'target_stable_60_certified':False}
    args.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
