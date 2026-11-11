"""Native evidence gate for a separately packaged on-foot Yaris candidate.

Runs genuine 3-stop NullRHI tests and optionally one short D3D12 720p stop.
Never runs concurrently with another render from this tool, modifies a level,
or replaces the existing Windows distribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def sha(path:Path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for buf in iter(lambda:handle.read(4*1024*1024),b""):
            digest.update(buf)
    return digest.hexdigest()


def report_checks(result:dict, *, rendered:bool):
    expected=("entered","moved_more_than_10_cm","reentered",
              "walking_on_ground","bianca_spawned",
              "bianca_followed_more_than_10_cm","bianca_walking_on_ground",
              "bianca_near_parked_car","passed")
    checks={k:result.get(k) is True for k in expected}
    checks["vehicle_essentially_parked"]=(
        isinstance(result.get("parked_vehicle_displacement_cm"),(int,float)) and
        0<=result["parked_vehicle_displacement_cm"]<50)
    checks["mouse_moved_metrically"]=result.get("mouse_travel_cm",0)>10
    checks["bianca_moved_metrically"]=result.get("bianca_travel_cm",0)>10
    if rendered:
        checks["native_D3D12"]=result.get("rhi")=="D3D12" and result.get("nullrhi") is False
        checks["actual_viewport_720p"]=(
            result.get("viewport_width")==1280 and
            result.get("viewport_height")==720)
        checks["second_camera_restored"]=result.get("diagnostic_view_restored") is True
    else:
        checks["genuine_NullRHI"]=result.get("nullrhi") is True and result.get("rhi")=="Null"
    return checks


def artifact_integrity(package_report:dict,exe:Path,active:Path):
    """Check both distributions against export-time SHA-256, not just each other."""
    candidate_pak=exe.parents[2]/"Content/Paks/SoffumbergoLab-Windows.pak"
    old=package_report.get("protected_before",{}).get(str(active))
    return {
        "candidate_executable_hash_matches_export":exe.is_file() and
            sha(exe)==package_report.get("game_binary_sha256"),
        "candidate_pak_present":candidate_pak.is_file() and
            candidate_pak.stat().st_size>10000,
        "active_pak_matches_original_export":active.is_file() and
            isinstance(old,str) and sha(active)==old,
    }, candidate_pak


def run_one(exe:Path,project_dir:Path,folder:Path,stop:int,render:bool,timeout:int):
    folder.mkdir(parents=True,exist_ok=False)
    command=[str(exe),"/Game/Maps/CircuitoGuidabile",
             "-game","-unattended","-nosplash","-nosound",
             "-LabOnFootSmokeTest",f"-CircuitTestStop={stop}",
             "-LabOutput="+str(folder)]
    if render:
        command+=["-windowed","-ForceRes","-ResX=1280","-ResY=720","-LabPreset=C"]
    else:
        command+=["-nullrhi","-UseFixedTimeStep","-FPS=120"]
    start=time.time()
    with (folder/"console.log").open("wb") as output:
        process=subprocess.Popen(command,cwd=project_dir,stdout=output,
                                 stderr=subprocess.STDOUT)
        try:
            exit_code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=20)
            exit_code=124
    file=folder/"on_foot_smoke.json"
    data=json.loads(file.read_text(encoding="utf-8-sig")) if file.is_file() else {}
    checks=report_checks(data,rendered=render)
    checks["process_successful"]=exit_code==0
    if render:
        for name in ("on_foot_midwalk.png","on_foot_companion_review.png"):
            image=folder/name
            checks["screenshot_"+name]=image.is_file() and image.stat().st_size>10000
    result={
        "stop":stop,"rendered":render,"started_unix":start,"ended_unix":time.time(),
        "exit_code":exit_code,"checks":checks,"passed":all(checks.values()),
        "world_map":"/Game/Maps/CircuitoGuidabile",
        "candidate_binary_sha256":sha(exe),"source_data":data,
        "command":command
    }
    (folder/"verification.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"stop":stop,"rendered":render,"passed":result["passed"],
                      "checks":checks},ensure_ascii=False),flush=True)
    return result


def verify(package_report:Path,output:Path,render:bool,timeout:int):
    if sys.platform!="win32":
        raise RuntimeError("Native Win64 executable tests require Windows")
    package_report=package_report.resolve()
    output=output.resolve()
    if output.exists():
        raise FileExistsError("Preserve previously recorded QA result: "+str(output))
    packaged=json.loads(package_report.read_text(encoding="utf-8"))
    if not packaged.get("packaged") or packaged.get("promoted_to_active") or \
       not all(packaged.get("checks",{}).values()):
        raise ValueError("Only a passing unpromoted candidate package is allowed")
    exe=Path(packaged["candidate_executable"])
    if not exe.is_file() or sha(exe)!=packaged["game_binary_sha256"]:
        raise ValueError("Packaged game binary is absent or has changed since export")
    active=ROOT/"build/DrivingWindows/Windows/SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak"
    if not active.is_file():
        raise FileNotFoundError("Original Windows distribution is missing")
    export_integrity,candidate_pak=artifact_integrity(packaged,exe,active)
    if not all(export_integrity.values()):
        raise RuntimeError("Exported candidate or protected original differs from recorded evidence")
    original_sha=sha(active)
    candidate_pak_sha=sha(candidate_pak)
    output.mkdir(parents=True)
    root=exe.parents[3]  # .../Windows/SoffumbergoLab/Binaries/Win64/exe
    results=[]
    for stop in (1,0,2):
        results.append(run_one(exe,root,output/f"stop_{stop}_null",stop,False,timeout))
    if render:
        results.append(run_one(exe,root,output/"valle_720p",1,True,timeout))
    report={
        "completed":True,
        "all_passed":all(x["passed"] for x in results),
        "expected_runs":len(results),
        "actual_runs":len(results),
        "archive_report_sha256":sha(package_report),
        "binary_sha256":sha(exe),
        "protected_active_pak_unchanged":original_sha==sha(active),
        "active_pak_matches_original_export":export_integrity["active_pak_matches_original_export"],
        "candidate_pak_unchanged":candidate_pak_sha==sha(candidate_pak),
        "candidate_binary_unchanged":sha(exe)==packaged["game_binary_sha256"],
        "candidate_pak_sha256":candidate_pak_sha,
        "world_geometry_changed":False,
        "rendered_4k_60_certified":False,
        "cases":results
    }
    report["all_passed"]=report["all_passed"] and all(
        report[k] for k in ("protected_active_pak_unchanged",
                            "active_pak_matches_original_export",
                            "candidate_pak_unchanged","candidate_binary_unchanged"))
    (output/"report.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"completed":report["completed"],
                      "all_passed":report["all_passed"],
                      "runs":len(results),"active_pak_unchanged":report["protected_active_pak_unchanged"]},
                     ensure_ascii=False),flush=True)
    if not report["all_passed"]:
        raise RuntimeError("Packaged on-foot smoke failed; do not promote")
    return report


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--package-report",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--render-720p",action="store_true")
    a.add_argument("--timeout",type=int,default=180)
    args=a.parse_args()
    if args.timeout<30 or args.timeout>900:
        a.error("timeout must be between 30 and 900 seconds per native process")
    verify(args.package_report,args.output,args.render_720p,args.timeout)


if __name__=="__main__":
    main()
