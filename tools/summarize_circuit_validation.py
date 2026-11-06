"""Keep terrain-stage evidence separate from the still-open full driving goal."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((root/p).read_text(encoding='utf-8-sig'))
terrain=read('results/world_terrain_validation.json')
survey=read('results/streaming_packaged/circuit_terrain_survey.json')
run=read('results/streaming_packaged/run_manifest.json')
driving=read('results/circuit_vehicle_packaged_rendered_C_checks.json')
lod=read('results/world_lod_stitching.json')
bootstrap=read('results/circuit_bootstrap_check.json')
world_hash=hashlib.sha256((root/'Unreal/Content/Data/circuit_world.json').read_bytes()).hexdigest()
exe=root/'build/CircuitWindows/Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
checks={'all_113_native_tiles':terrain['tiles']==113 and terrain['all_saved_native_tiles_verified'],
        'source_and_holes_readback':terrain['height_mismatches']==0 and terrain['visibility_mismatches']==0,
        'packaged_streaming':survey['passed'] and survey['checked']==19010 and survey['hits']==19010,
        'current_runtime_data':world_hash==run['runtime_world_data_sha256'],
        'current_runtime_binary':hashlib.sha256(exe.read_bytes()).hexdigest()==run['executable_sha256'],
        'shared_native_lod_group':lod['passed'],
        'manual_launcher_bootstrap':bootstrap['passed'],
        'packaged_three_4k_spawn_maneuvers':driving['passed']}
report={'passed':all(checks.values()),'checks':checks,
        'scope':'Full raw terrain and sampled streaming; three short vehicle maneuvers in packaged Windows at 4K',
        'entire_route_driven':False,'road_built':False,'vegetation_extended':False,
        'moving_full_route_4k60_certified':False,'active_driving_goal_complete':False,
        'visual_review':'Current packaged 4K frame inspected: initial thin white distant edge cracks are no longer visible. This is one frame, not a complete art or motion approval.',
        'reviewed_screenshot':'private/screenshots/circuit_lidar_packaged_lod_group_4k.png'}
(root/'results/circuit_stage_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
if not report['passed']:raise SystemExit(1)
