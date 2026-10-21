"""Install the driving increment while preserving the known private Windows variant.

Three initial upgrades are guarded by exact LF hashes. Everything is preflighted
before writing; backups and an ownership receipt allow safe idempotent updates.
Third-party models, rig, characters, exercise controls and project.godot stay local.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINES = {
    'godot/scripts/vehicle_lab.gd':'65bce6a641548acc4045fa175d6eece16bc6ca77f214caf45d70de4b39fe7834',
    'godot/scripts/lab.gd':'1cd4cbbbc4379b8b37b6f3f8eb88337341b418006b8e5fe4efc4165715bc2d68',
    'data/config/vehicle_lab.json':'6e4f5ba859f682ba840172bda8d312d6a8190055a2ae2a0dfd453e95a642cfbe',
}
FILES = ['data/config/yaris_performance.json','tools/build_drive_pilot.py','tests/test_drive_pilot.py',
         'tools/blender/build_drive_pilot.py','reports/GUIDA_PILOTA_VERIFICA.json',
         'tools/sync_drive_local.py','godot/scripts/yaris_powertrain.gd','godot/scripts/yaris_powertrain.gd.uid',
         'godot/scripts/drive_pilot.gd','godot/scripts/drive_pilot.gd.uid','godot/scenes/drive_pilot.tscn',
         'godot/tests/yaris_performance_check.gd','godot/tests/yaris_performance_check.gd.uid',
         'godot/tests/drive_pilot_check.gd','godot/tests/drive_pilot_check.gd.uid',
         'godot/tests/drive_missing_check.gd','godot/tests/drive_missing_check.gd.uid',
         'godot/scripts/trial_progress.gd','godot/scripts/trial_progress.gd.uid',
         'godot/tests/trial_progress_check.gd','godot/tests/trial_progress_check.gd.uid',
         'reports/CHECKPOINT_PILOTA_VERIFICA.json',
         'godot/scripts/parking_pilot.gd','godot/scripts/parking_pilot.gd.uid',
         'godot/scripts/parking_state.gd','godot/scripts/parking_state.gd.uid',
         'godot/scenes/parking_pilot.tscn','tools/build_parking_pilot.py',
         'godot/tests/parking_pilot_check.gd','godot/tests/parking_pilot_check.gd.uid',
         'godot/tests/parking_state_check.gd','godot/tests/parking_state_check.gd.uid',
         'tests/test_parking_pilot.py','docs/SOSTA_PILOTA.md','reports/SOSTA_PILOTA_VERIFICA.json',
         'docs/GUIDA_PILOTA.md','docs/YARIS_PRESTAZIONI.md']


def digest(b):
    return hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()


def replace_once(s,a,b):
    if s.count(a) != 1:
        raise ValueError('Unexpected local code context: '+a[:70])
    return s.replace(a,b,1)


def patch_vehicle(s):
    reference = (ROOT/'godot/scripts/vehicle_lab.gd').read_text(encoding='utf-8')
    old = subprocess.check_output(['git','show','a1127eb3fecc9b61079f58bfd3e88e756cf88fbc:godot/scripts/vehicle_lab.gd'],cwd=ROOT).decode()
    s = replace_once(s,'var config: Dictionary','const Powertrain = preload("res://godot/scripts/yaris_powertrain.gd")\n\nvar performance: Dictionary\nvar stock_reference := false\nvar wheel_collision_mask := 1\nvar support_normal := Vector3.UP\nvar support_velocity_sum := Vector3.ZERO\nvar reset_transform := Transform3D(Basis.IDENTITY, Vector3(0, 0.2, 8))\nvar config: Dictionary')
    a=reference.index('\tperformance = '); b=reference.index('\tproperties = ',a)
    s=replace_once(s,'\tproperties = MassProperties.calculate(config.components)',reference[a:b]+'\tproperties = MassProperties.calculate(config.components)')
    s=replace_once(s,'\tangular_damp = 0.0','\tangular_damp = 0.0\n\tlinear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE\n\tangular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE')
    s=replace_once(s,'state.transform = Transform3D(Basis.IDENTITY, Vector3(0, 0.2, 8))','state.transform = reset_transform')
    a=old.index('\tvar drive_total := ('); b=old.index('\tsample_clock += dt',a)
    c=reference.index('\tvar drive_total := '); d=reference.index('\tsample_clock += dt',c)
    # Local code calls _capture_support_motion before this block; preserve it.
    s=replace_once(s,old[a:b].rstrip(),reference[c:d].rstrip())
    s=replace_once(s,'query.collision_mask = 1','query.collision_mask = wheel_collision_mask')
    s=replace_once(s,'\tdiagnostic_contact_count += 1','\tdiagnostic_contact_count += 1\n\tsupport_normal += normal\n\tsupport_velocity_sum += point_velocity.slide(normal)')
    a=reference.index('\tif absf(throttle) < 0.001'); b=reference.index('\n\tlongitudinal_force -= (',a)
    s=replace_once(s,'\tvar longitudinal_force := drive * 0.5 if index < 2 else 0.0','\tvar longitudinal_force := drive * 0.5 if index < 2 else 0.0\n'+reference[a:b].rstrip())
    old_brake='braking * float(config.powertrain.brake_force_total_n) * 0.25 * clampf(vx / 0.5, -1.0, 1.0)'
    s=replace_once(s,old_brake,'Powertrain.brake_force(\n\t\t\tvx, state.total_gravity.dot(forward), mass, state.step, braking,\n\t\t\tfloat(config.powertrain.brake_force_total_n), longitudinal_force\n\t\t)')
    a=reference.index('func road_speed_m_s() -> float:'); b=reference.index('\n\nfunc ',a)
    return s+'\n\n'+reference[a:b]+'\n'


def patch_lab(s):
    s=replace_once(s,'var vehicle: LaboratoryVehicle','var recovery_message := ""\nvar vehicle: LaboratoryVehicle')
    guard=('func _physics_process(_delta: float) -> void:\n'
           '\tvar outside_pad := absf(vehicle.position.x) > 190 or absf(vehicle.position.z) > 190\n'
           '\tvar floor_y := 0.0\n'
           '\tif exercise.exercise == 1:\n'
           '\t\tfloor_y = -tan(deg_to_rad(8.0)) * vehicle.position.z\n'
           '\tif not exercise.automatic and (outside_pad or vehicle.position.y < floor_y - 4):\n'
           '\t\t_select_exercise(exercise.exercise, true)\n'
           '\t\trecovery_message = "Fuori dal piazzale: prova ripristinata"\n\t\treturn')
    s=replace_once(s,'func _physics_process(_delta: float) -> void:',guard)
    s=replace_once(s,'var state := "MANUALE"','var state := (\n\t\trecovery_message if not recovery_message.is_empty() else "MANUALE"\n\t)')
    return replace_once(s,'vehicle.linear_velocity.length() * 3.6','vehicle.road_speed_m_s() * 3.6')


def sync(target,godot):
    target=target.resolve(); godot=godot.resolve()
    if target==ROOT or not (target/'project.godot').is_file() or not godot.is_file():
        raise ValueError('Expected a distinct existing project and Godot executable')
    receipt=target/'build/drive_sync_receipt.json'
    owned=json.loads(receipt.read_text())['files'] if receipt.exists() else {}
    previous=target/'build/circuit_sync_receipt.json'
    inherited=json.loads(previous.read_text())['files'] if previous.exists() else {}
    updates={}
    for rel,expected in BASELINES.items():
        b=(target/rel).read_bytes()
        if rel in owned:
            if digest(b)!=owned[rel]:
                raise ValueError('User edits preserved: '+rel)
            b=(target/'build/drive_backups'/expected/rel).read_bytes()
        if digest(b)!=expected:
            raise ValueError('Unknown local variant preserved: '+rel)
        s=b.decode('utf-8').replace('\r\n','\n')
        if rel.endswith('vehicle_lab.gd'):
            s=patch_vehicle(s)
        elif rel.endswith('lab.gd'):
            s=patch_lab(s)
        else:
            d=json.loads(s)
            d['components'][0]['position_m'][2]=-.256
            d['powertrain']['drive_force_limit_n']=6500
            d['powertrain']['power_limit_w']=60000
            d['longitudinal_model']='yaris_performance.json; effective envelope, other parameters experimental'
            s=json.dumps(d,indent=2)+'\n'
        updates[rel]=s.encode()
    additions=FILES+['godot/scripts/circuit.gd','build/circuit/pilot_manifest.json',
                    'build/circuit/pilot_road.json','build/circuit/pilot_generation_report.json']
    manifest=json.loads((ROOT/'build/circuit/pilot_manifest.json').read_text())
    additions += ['build/circuit/'+e['path'] for e in manifest['sectors'] if '/drive_' in e['path']]
    parking=json.loads((ROOT/'build/circuit/parking_manifest.json').read_text())
    additions += ['build/circuit/parking_manifest.json','build/circuit/parking_road.json',
                  'build/circuit/parking_generation_report.json']
    additions += ['build/circuit/'+e['path'] for e in parking['sectors'] if '/parking_' in e['path']]
    for rel in additions:
        src,dst=ROOT/rel,target/rel
        if not dst.resolve().is_relative_to(target):
            raise ValueError('Unsafe output path')
        b=src.read_bytes()
        if dst.exists() and digest(dst.read_bytes()) not in [digest(b),owned.get(rel),inherited.get(rel)]:
            raise ValueError('Existing differing file preserved: '+rel)
        if not dst.exists() or dst.read_bytes()!=b:
            updates[rel]=b
    launchers={'Avvia accesso a Valle.cmd':'drive_pilot','Avvia sosta a Valle.cmd':'parking_pilot'}
    for rel,scene in launchers.items():
        b=('@echo off\r\n"'+str(godot)+'" --path "%~dp0." res://godot/scenes/'+scene+'.tscn\r\n').encode()
        if (target/rel).exists() and digest((target/rel).read_bytes())!=digest(b):
            raise ValueError('Existing launcher preserved')
        updates[rel]=b
    updates={p:b for p,b in updates.items() if not (target/p).exists() or (target/p).read_bytes()!=b}
    main=(target/'project.godot').read_bytes()
    for rel,b in updates.items():
        dst=target/rel
        if dst.exists() and dst.read_bytes()!=b:
            backup=target/'build/drive_backups'/digest(dst.read_bytes())/rel
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():
                backup.write_bytes(dst.read_bytes())
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(b)
    subprocess.run([sys.executable,'tools/design_report.py'],cwd=target,check=True,stdout=subprocess.DEVNULL)
    assert (target/'project.godot').read_bytes()==main
    installed=set(additions)|set(BASELINES)|set(launchers)
    receipt.write_text(json.dumps({'files':{p:digest((target/p).read_bytes()) for p in sorted(installed)},'default_scene_changed':False},indent=2)+'\n')
    print(json.dumps({'updated':len(updates),'default_scene_changed':False,'backups':'build/drive_backups'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',type=Path,required=True)
    p.add_argument('--godot',type=Path,required=True)
    a=p.parse_args(); sync(a.target,a.godot)
