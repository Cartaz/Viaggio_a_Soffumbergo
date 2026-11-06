"""Record the local source/assets/package used for this increment."""
import hashlib
import json
import argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--circuit',action='store_true')
parser.add_argument('--driving',action='store_true')
args=parser.parse_args()
if args.circuit and args.driving:parser.error('Choose circuit or driving')
files=[]
for folder in ['Unreal/Source','Unreal/Config','Unreal/Content','tools']:
    files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.append(root/'Unreal/SoffumbergoLab.uproject')
package=root/('build/DrivingWindows/Windows' if args.driving else 'build/CircuitWindows/Windows' if args.circuit else 'build/Windows')
exe=package/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
if exe.exists():files.append(exe)
if args.driving:
    files.extend(p for p in package.rglob('*') if p.is_file() and p.suffix.lower() in ['.pak','.utoc','.ucas','.ini'])
    bootstrap=package/'SoffumbergoLab.exe'
    if bootstrap.exists():files.append(bootstrap)
    files.extend(root/p for p in ['parameters/current_road_design.json','parameters/road_design.json','package_lidar.ps1','Avvia percorso Soffumbergo.cmd'])
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
manifest={'engine':'5.8.4-58902052','platform':'Windows','local_only':True,'game_complete':False,
          'map':'/Game/Maps/CircuitoGuidabile' if args.driving else '/Game/Maps/CircuitoSoffumbergo' if args.circuit else '/Game/Maps/ValleLiDAR','default_profile':'C native 4K balanced; manual play capped at 60 FPS',
          'files':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(set(files))]}
if args.driving:manifest['build_id']=json.loads((root/'parameters/current_road_design.json').read_text())['build_id']
(root/('results/driving_build_manifest.json' if args.driving else 'results/circuit_build_manifest.json' if args.circuit else 'results/current_build_manifest.json')).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Manifest records:',len(files))
