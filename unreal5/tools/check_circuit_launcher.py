"""Check the exported bootstrap and the same map selected by the manual launcher."""
import json
from pathlib import Path
import subprocess
import time

root=Path(__file__).resolve().parents[1]
exe=root/'build/CircuitWindows/Windows/SoffumbergoLab.exe'
out=root/'results/circuit_bootstrap';out.mkdir(parents=True,exist_ok=True)
launcher=(root/'Avvia territorio completo LiDAR.cmd').read_text()
assert 'build\\CircuitWindows\\Windows\\SoffumbergoLab.exe' in launcher
assert '/Game/Maps/CircuitoSoffumbergo' in launcher
command=[str(exe),'/Game/Maps/CircuitoSoffumbergo','-game','-unattended','-nullrhi','-nosound',
         '-LabTest=LIDAR_STATIC','-LabRunId=circuit_bootstrap','-UseFixedTimeStep','-FPS=120',
         '-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
started=time.time()
with (out/'console.log').open('w') as stream:
    result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
meta_path=out/'circuit_bootstrap.json'
if not meta_path.exists() or meta_path.stat().st_mtime<started:raise RuntimeError('No fresh bootstrap execution')
meta=json.loads(meta_path.read_text())
checks={'bootstrap_exit_zero':result.returncode==0,'scripted_execution':meta['status']=='executed',
        'geographic_scene':meta['geographic_scene'],'full_assets':meta['final_assets_loaded'],
        'full_dynamic_mass':meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<0.1,
        'no_recovery':meta['user_resets']==0,'full_duration':meta['simulated_s']>=14.9,
        'streamed_world':'CIRCUIT_WORLD tiles=113' in (out/'engine.log').read_text(errors='replace')}
report={'passed':all(checks.values()),'checks':checks,'command':command,
        'scope':'Manual launcher target and exported bootstrap; scripted spawn only, not a driven circuit'}
(root/'results/circuit_bootstrap_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
if not report['passed']:raise SystemExit(1)
