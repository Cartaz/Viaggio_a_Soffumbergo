"""Read native LOD buffers without drawing, distinct from source MeshDescription."""
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest=Path(os.environ['SOFFUMBERGO_DISTANT_BUFFER_MANIFEST']);m=json.loads(manifest.read_text());build=m['build_id']
draft=ROOT/'results/road_drafts'/build;report_path=draft/'distant_native_buffers.json'
if report_path.exists():raise RuntimeError('Preserve native buffer audit')
assert json.loads((draft/'import_report.json').read_text())['all_imported']
source_guard=json.loads((draft/'distant_native_import.json').read_text())['protected_before']
guard_paths=list(source_guard)+[str(ROOT/'Unreal/Content'/(r['asset'].removeprefix('/Game/')+'.uasset')) for r in m['distant_terrain']['records']]
guard_paths += [str(ROOT/'Unreal/Content'/(r['map'].removeprefix('/Game/')+'.umap')) for r in m['distant_terrain']['records']]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before={p:sha(p) for p in guard_paths}
report={'build_id':build,'started_unix':time.time(),'rendering_executed':False,'passed':False,'tiles':[],
    'scope':'Native source MeshDescription plus actual LOD0 buffer counts; no GPU drawing, material/pixel quality or performance acceptance.'}


def save():report_path.write_text(json.dumps(report,indent=2))
save()


def work():
 try:
    for row in m['distant_terrain']['records']:
        mesh=unreal.load_asset(row['asset'])
        if mesh is None:raise RuntimeError('Missing far mesh')
        started=time.monotonic()
        while mesh.get_num_triangles(0)==0 and time.monotonic()-started<60:yield
        triangles=mesh.get_num_triangles(0);vertices=mesh.get_num_vertices(0)
        source=json.loads(unreal.LidarTerrainLibrary.verify_distant_terrain_mesh(row['binary'],row['asset']))
        passed=source['passed'] and triangles==row['triangles'] and vertices>=row['vertices']
        report['tiles'].append({'id':row['id'],'source_mesh_description_passed':source['passed'],
            'expected_triangles':row['triangles'],'lod0_triangles':triangles,'source_vertices':row['vertices'],
            'lod0_vertices_including_attribute_splits':vertices,'passed':passed})
        save()
        if not passed:raise RuntimeError('Native LOD buffers differ from prepared source '+str(report['tiles'][-1]))
        unreal.log('DISTANT_BUFFER_VERIFIED '+row['id']);yield
    report.update(passed=len(report['tiles'])==113,ended_unix=time.time(),
        total_lod0_triangles=sum(r['lod0_triangles'] for r in report['tiles']),
        protected_files_unchanged=all(sha(p)==expected for p,expected in before.items()))
    if not report['protected_files_unchanged']:raise RuntimeError('Read-only native audit changed assets')
    save();unreal.log('DISTANT_NATIVE_BUFFERS_PASSED '+build)
 except BaseException as e:
    report.update(passed=False,error=repr(e),ended_unix=time.time(),protected_files_unchanged=all(sha(p)==expected for p,expected in before.items()));save();raise


generator=work();last_step=time.monotonic();advancing=False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global last_step,advancing
    if advancing or time.monotonic()-last_step<.05:return
    last_step=time.monotonic();advancing=True
    try:next(generator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally:advancing=False


handle=unreal.register_slate_post_tick_callback(tick)
