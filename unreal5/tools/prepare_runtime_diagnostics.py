"""Version diagnostic runtime code while preserving accepted world/route bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--base-draft',type=Path,required=True);p.add_argument('--revision',required=True);args=p.parse_args()
    import re
    if not re.fullmatch('[a-z][a-z0-9_]{0,31}',args.revision):raise ValueError('Invalid revision')
    base=args.base_draft.resolve();imported=json.loads((base/'import_report.json').read_text());assert imported['all_imported']
    world=json.loads((base/'circuit_driving_world.json').read_text());build=world['build_id']
    out=ROOT/'results/runtime_revisions'/build/args.revision
    if out.exists():raise RuntimeError('Preserve previous diagnostic revision')
    out.mkdir(parents=True)
    for name in ['circuit_driving_world.json','circuit_itinerary.json','import_report.json','structure_preparation.json']:
        shutil.copyfile(base/name,out/name)
    files=[p for p in (ROOT/'Unreal/Source/SoffumbergoLab').rglob('*') if p.is_file() and p.suffix in ['.h','.cpp','.cs']]
    files += list((ROOT/'Unreal/Source').glob('*.cs'))+list((ROOT/'Unreal/Config').glob('*.ini'))+[ROOT/'Unreal/SoffumbergoLab.uproject']
    metadata={'build_id':build,'revision':args.revision,'base_draft':str(base),'recorded_unix':time.time(),
        'source_sha256':{str(p):sha(p) for p in files},
        'editor_binary_sha256':sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'),
        'terrain_editor_binary_sha256':sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll'),
        'world_sha256':sha(out/'circuit_driving_world.json'),'itinerary_sha256':sha(out/'circuit_itinerary.json'),
        'geometry_and_itinerary_changed':False,'activated':False,
        'scope':'Read-only runtime diagnostics for saved vegetation resources and distant mesh membership. No PCG regeneration or vehicle force/camera changes; current native execution and regression evidence required.'}
    assert all(sha(base/name)==sha(out/name) for name in ['circuit_driving_world.json','circuit_itinerary.json'])
    (out/'runtime_revision.json').write_text(json.dumps(metadata,indent=2));print(json.dumps({'draft':str(out),'build_id':build,'revision':args.revision,'editor_binary_sha256':metadata['editor_binary_sha256']},indent=2))


if __name__=='__main__':main()
