"""Verify and export a code revision of unchanged native road/terrain data.

This one-shot worker retains earlier packages and results. Native camera gallery
and an explicit image review precede the long Windows rendering test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import _winapi

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--gallery',type=Path,required=True)
    p.add_argument('--wait-gallery-pid',type=int,required=True)
    p.add_argument('--background-log',type=Path,required=True)
    args=p.parse_args();sys.stdout=args.background_log.open('x',buffering=1);sys.stderr=sys.stdout
    draft=args.draft.resolve();revision=json.loads((draft/'runtime_revision.json').read_text(encoding='utf-8'))
    state_path=draft/'verification_pipeline.json'
    if state_path.exists():raise RuntimeError('Preserve earlier runtime revision pipeline')
    state={'build_id':revision['build_id'],'revision':revision['revision'],'status':'waiting_for_gallery',
        'started_unix':time.time(),'stages':[],'promoted':False,'full_objective_complete':False}
    def save():state_path.write_text(json.dumps(state,indent=2),encoding='utf-8')
    save()
    def check_code():
        if sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll')!=revision['editor_binary_sha256']:
            raise RuntimeError('Current Editor binary differs from the selected revision')
        if any(sha(path)!=value for path,value in revision['source_sha256'].items()):
            raise RuntimeError('Runtime source changed after revision preparation')
    def run(stage,script,extra,report,key):
        check_code();state['status']=stage;save();started=time.time()
        result=subprocess.run([sys.executable,str(ROOT/'tools'/script),*extra],cwd=ROOT,
            stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise RuntimeError(stage+' failed; inspect retained native evidence')
        data=json.loads(report.read_text(encoding='utf-8-sig'))
        if report.stat().st_mtime<started or not data.get(key):raise RuntimeError(stage+' lacks fresh accepted evidence')
        state['stages'].append({'name':stage,'report':str(report),'ended_unix':time.time()});save()
    try:
        check_code()
        try:handle=_winapi.OpenProcess(0x00100000,False,args.wait_gallery_pid)
        except OSError:handle=None
        if handle is not None:
            try:
                while _winapi.WaitForSingleObject(handle,30000)==258:pass
            finally:_winapi.CloseHandle(handle)
        gallery=json.loads(args.gallery.read_text(encoding='utf-8'))
        if not gallery['passed'] or not gallery['full_six_control_gallery'] or gallery['runtime']!='Editor':
            raise RuntimeError('Six-control native Editor gallery did not pass')
        if gallery['source_package_sha256'].get('Binaries\\Win64\\UnrealEditor-SoffumbergoLab.dll')!=revision['editor_binary_sha256']:
            raise RuntimeError('Gallery ran different native code')
        state['status']='waiting_for_image_review';save()
        review_path=args.gallery.parent/'visual_review.json'
        while not review_path.exists():time.sleep(30)
        review=json.loads(review_path.read_text(encoding='utf-8'))
        if not review['native_camera_check_accepted'] or review['inspected_images']!=18 or review['build_id']!=revision['build_id']:
            raise RuntimeError('Native image review rejected this revision')
        if not review.get('roadside_geometry_accepted_for_long_lap',False):
            raise RuntimeError('Repair the geometry identified by the image review before the long rendering sequence')
        state['stages'].append({'name':'reviewed_editor_gallery','report':str(review_path),'ended_unix':time.time()});save()
        prefix='runtime_'+revision['build_id']+'_'+revision['revision']
        surface_id=prefix+'_surface_editor_v1';lap_id=prefix+'_full_editor_v1'
        surface=ROOT/'results/road_draft_checks'/surface_id/'report.json'
        lap=ROOT/'results/road_draft_checks'/lap_id/'report.json'
        run('editor_surface','run_draft_road_check.py',['--draft',str(draft),'--run-id',surface_id,'--mode','survey'],surface,'passed')
        run('editor_full_lap','run_draft_road_check.py',['--draft',str(draft),'--run-id',lap_id,'--mode','lap','--timeout','1800'],lap,'full_lap_passed')
        run('windows_export','package_road_draft.py',['--draft',str(draft),'--revision',revision['revision'],
            '--lap-report',str(lap),'--surface-report',str(surface)],draft/'candidate_packaging_report.json','packaged')
        run('windows_native_pipeline','verify_road_candidate.py',['--draft',str(draft),'--attempt','v3',
            '--include-structure-reentry','--background-log',str(draft/'windows_native_pipeline_v3.log')],
            draft/'candidate_verification_pipeline_v3.json','stages')
        completed=json.loads((draft/'candidate_verification_pipeline_v3.json').read_text())
        if completed['status']!='native_pipeline_finished':raise RuntimeError('Windows pipeline did not finish')
        state.update(status='native_checks_finished',ended_unix=time.time(),remaining='Windows gallery image review, remaining grading/anthropic coverage, representative performance and final promotion are still required.')
        save()
    except BaseException as error:
        state.update(status='failed',error=repr(error),ended_unix=time.time());save();raise


if __name__=='__main__':main()
