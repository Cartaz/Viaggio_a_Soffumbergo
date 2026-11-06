"""Partial-scene 4K renderer diagnostic, static/frozen car; not a full-game benchmark."""
import csv
import json
import statistics
from pathlib import Path
import subprocess
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--presets',nargs='+',default=['A','B'])
args=parser.parse_args()

root=Path(__file__).resolve().parents[1]
output=root/'results/lidar_render_diagnostic';output.mkdir(parents=True,exist_ok=True)
exe=root/'build/Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
reports=[]
for preset in args.presets:
    run='lidar_render_'+preset
    command=[str(exe),'/Game/Maps/ValleLiDAR','-unattended','-RenderOffscreen','-windowed',
             '-ResX=3840','-ResY=2160','-ForceRes','-NoVSync','-LabPreset='+preset,
             '-LabBenchmark=90','-LabRunId='+run,'-LabOutput='+str(output),'-abslog='+str(output/(run+'.log'))]
    with (output/(run+'_console.log')).open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Packaged renderer exited '+str(result.returncode))
    metadata=json.loads((output/(run+'.json')).read_text())
    samples=[r for r in csv.DictReader((output/(run+'_frames.csv')).open()) if 30<=float(r['elapsed_s'])<=90]
    times=sorted(float(r['frame_ms']) for r in samples)
    percentile=lambda p:times[min(len(times)-1,int((len(times)-1)*p))]
    gpus=[float(r['gpu_ms']) for r in samples if float(r['gpu_ms'])>0]
    report={'preset':preset,'sample_frames':len(times),'warmup_s':30,'measurement_s':60,
            'avg_fps':1000/statistics.mean(times),'frame_ms_p95':percentile(.95),'frame_ms_p99':percentile(.99),
            'mean_gpu_ms':statistics.mean(gpus) if gpus else None,'metadata':metadata,
            'scope':'single static camera, frozen vehicle, 252m LiDAR crop and procedural vegetation; no road/borgo/visit',
            'full_game_target_verified':False,'comparable_P3_benchmark':False}
    reports.append(report);print(json.dumps(report),flush=True)
summary=root/'results/lidar_render_diagnostic.json'
previous=json.loads(summary.read_text())['runs'] if summary.exists() else []
previous=[r for r in previous if r['preset'] not in args.presets]
summary.write_text(json.dumps({'runs':previous+reports,'limitations':'One pass per preset; partial static scene, not full-game or stable-60 certification'},indent=2))
