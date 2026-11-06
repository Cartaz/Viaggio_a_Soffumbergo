"""Exercise all terrain samples with actual native async level loading."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('--packaged',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
out=root/'results'/('streaming_packaged' if args.packaged else 'streaming')
out.mkdir(parents=True,exist_ok=True)
exe=(root/'build/CircuitWindows/Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe') if args.packaged else Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
command=[str(exe)]
if not args.packaged:command.append(str(root/'Unreal/SoffumbergoLab.uproject'))
command+=['/Game/Maps/CircuitoSoffumbergo','-game','-unattended','-nullrhi','-nosound','-nosplash','-CircuitTerrainSurvey',
          '-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
started=time.time()
with (out/'console.log').open('w') as stream:
    process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
report_path=out/'circuit_terrain_survey.json'
if process.returncode or not report_path.exists() or report_path.stat().st_mtime < started:
    raise RuntimeError('Engine did not produce a fresh completed survey')
report=json.loads(report_path.read_text())
manifest={'command':command,'packaged':args.packaged,'exit_code':process.returncode,
          'runtime_world_data_sha256':hashlib.sha256((root/'Unreal/Content/Data/circuit_world.json').read_bytes()).hexdigest(),
          'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'passed':report['passed'],
          'scope':report['scope']}
(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(report))
if not report['passed']:raise SystemExit(1)
