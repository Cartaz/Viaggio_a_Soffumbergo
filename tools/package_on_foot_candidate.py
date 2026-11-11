"""Build a separate UE Windows *candidate* after an actual fresh native full lap.

No active game, native terrain, LiDAR or packaged build is overwritten. Uses
the bundled UE DotNet AutomationTool with native Windows process arguments
to avoid cmd.exe length limits for the 113 streaming maps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

if sys.platform == "win32":
    import _winapi
else:
    _winapi = None  # Allows CPU-only source/validation tests on GitHub Linux.

ROOT=Path(__file__).resolve().parents[1]
UE=Path(r"C:\Program Files\Epic Games\UE_5.8")
ACTIVE_PAK=ROOT/"build/DrivingWindows/Windows/SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak"
ORIGINAL=ROOT/"Unreal"
SOURCE_FILES=[
    "Source/SoffumbergoLab/LabVehicle.h",
    "Source/SoffumbergoLab/LabVehicle.cpp",
    "Source/SoffumbergoLab/SoffumbergoFootMouse.h",
    "Source/SoffumbergoLab/SoffumbergoFootMouse.cpp",
    "Source/SoffumbergoLab/SoffumbergoCompanionMouse.h",
    "Source/SoffumbergoLab/SoffumbergoCompanionMouse.cpp",
    "Config/DefaultInput.ini"
]


def sha(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(4*1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs(lap_report:Path):
    report=json.loads(lap_report.read_text(encoding="utf-8"))
    if not report.get("full_lap_passed") or report.get("packaged") or report.get("rendering"):
        raise ValueError("A genuine full editor NullRHI driving lap must pass on this source")
    world=ORIGINAL/"Content/Data/circuit_driving_world.json"
    itinerary=ORIGINAL/"Content/Data/circuit_itinerary.json"
    road=json.loads(world.read_text(encoding="utf-8"))
    route=json.loads(itinerary.read_text(encoding="utf-8"))
    if (road["build_id"]!=route["build_id"] or
        report["build_id"]!=road["build_id"] or
        len(road["tiles"])!=113):
        raise ValueError("Native road/itinerary/build mismatch")
    if (report["runtime_world_sha256"]!=sha(world) or
        report["itinerary_sha256"]!=sha(itinerary)):
        raise ValueError("Driving world or itinerary changed after accepted full lap")
    module=ORIGINAL/"Binaries/Win64/UnrealEditor-SoffumbergoLab.dll"
    if report["runtime_binary_sha256"]!=sha(module):
        raise ValueError("Unreal Editor game DLL changed since passing full lap")
    for key,value in report["checks"].items():
        if not value:
            raise ValueError("Original native driving audit failed: "+key)
    maps=["/Game/Maps/CircuitoGuidabile"]+[t["map"] for t in road["tiles"]]
    distant=[t["distant_map"] for t in road["tiles"] if t.get("distant_map")]
    if distant:
        if len(distant)!=113:
            raise ValueError("Incomplete distant map list; refuse partial visual world")
        maps+=distant
    if len(set(maps))!=len(maps):
        raise ValueError("Duplicate map source in route")
    for name in maps:
        if not name.startswith("/Game/"):
            raise ValueError("Unexpected non-project map")
        path=ORIGINAL/"Content"/(name.removeprefix("/Game/")+".umap")
        if not path.is_file():
            raise FileNotFoundError("Missing native tile asset: "+str(path))
    return world,itinerary,road,maps,module


def validate_candidate_tag(tag:str):
    if not re.fullmatch(r"onfoot_[a-z0-9_]{5,40}",tag):
        raise ValueError("Use a stable onfoot_* candidate identifier")
    return tag


def package(lap_report:Path,tag:str):
    if _winapi is None:
        raise RuntimeError("Windows and installed Unreal Engine 5.8 required")
    validate_candidate_tag(tag)
    lap_report=lap_report.resolve()
    if not lap_report.is_file():
        raise FileNotFoundError("Native full lap report not found")
    world,itinerary,road,maps,module=verify_inputs(lap_report)
    qa=ROOT/"build"/("Q"+tag)
    archive=ROOT/"build/OnFootCandidateWindows"/tag
    if qa.exists() or archive.exists():
        raise FileExistsError("Candidate already exists: choose a new tag to preserve evidence")
    protected=[world,itinerary,ORIGINAL/"Content/Maps/CircuitoGuidabile.umap",
               ROOT/"parameters/current_road_design.json",
               ROOT/"results/current_road_import.json",module,ACTIVE_PAK]
    for entry in protected:
        if not entry.is_file():
            raise FileNotFoundError("Protected baseline absent: "+str(entry))
    before={str(f):sha(f) for f in protected}
    source_hashes={rel:sha(ORIGINAL/rel) for rel in SOURCE_FILES}
    started=time.time()
    qa.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(ORIGINAL/"SoffumbergoLab.uproject",qa/"SoffumbergoLab.uproject")
    shutil.copytree(ORIGINAL/"Config",qa/"Config")
    shutil.copytree(ORIGINAL/"Source",qa/"Source")
    if (ORIGINAL/"Binaries").is_dir():
        shutil.copytree(ORIGINAL/"Binaries",qa/"Binaries",
                        ignore=shutil.ignore_patterns("*.pdb"))
    content=qa/"Content"
    content.mkdir()
    for item in (ORIGINAL/"Content").iterdir():
        target=content/item.name
        if item.name=="Data":
            shutil.copytree(item,target)
        elif item.is_dir():
            _winapi.CreateJunction(str(item.resolve()),str(target))
        elif item.is_file():
            shutil.copyfile(item,target)
    copied=qa/"Config/DefaultEngine.ini"
    old=copied.read_text(encoding="utf-8")
    marker="GameDefaultMap=/Game/Maps/ValleLiDAR"
    if old.count(marker)!=1:
        raise ValueError("Unexpected launch-map configuration; original remains intact")
    copied.write_text(old.replace(marker,"GameDefaultMap=/Game/Maps/CircuitoGuidabile"),
                      encoding="utf-8")
    if sha(qa/"Content/Data/circuit_driving_world.json")!=sha(world):
        raise ValueError("Local project copy corrupted")
    dotnet=UE/"Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe"
    uat=UE/"Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll"
    cmd=[str(dotnet),str(uat),"BuildCookRun",
         "-project="+str(qa/"SoffumbergoLab.uproject"),
         "-noP4","-platform=Win64","-target=SoffumbergoLab",
         "-clientconfig=Development","-build","-cook","-stage","-pak",
         "-archive","-archivedirectory="+str(archive),
         "-unattended","-utf8output","-nocompileeditor","-nodebuginfo",
         "-map="+"+".join(maps),
         "-AdditionalCookerOptions=-nullrhi","-UbtArgs=-MaxParallelActions=2"]
    if len(subprocess.list2cmdline(cmd))>=32700:
        raise ValueError("Packaging command is longer than Windows CreateProcess limit")
    env=os.environ.copy()
    env.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_MULTILEVEL_LOOKUP="0",
        DOTNET_ROLL_FORWARD="LatestMajor",UE_DOTNET_VERSION="10.0",
        UE_DOTNET_ARCH="win-x64",UE_DOTNET_DIR=str(dotnet.parent))
    env["PATH"]=str(dotnet.parent)+os.pathsep+env.get("PATH","")
    for name in ("VisualStudioDir","VSSKUEDITION","PkgDefApplicationConfigFile",
                 "VSAPPIDDIR","VisualStudioEdition","VisualStudioVersion"):
        env.pop(name,None)
    manifest={
        "tag":tag,"project":str(qa),"archive":str(archive),
        "original_project":str(ORIGINAL),"active_package_preserved":str(ACTIVE_PAK),
        "original_road_build_id":road["build_id"],"map_count":len(maps),
        "source_sha256":source_hashes,
        "world_sha256":sha(world),"itinerary_sha256":sha(itinerary),
        "native_editor_game_module_sha256":sha(module),
        "native_full_lap_report":str(lap_report),
        "native_full_lap_report_sha256":sha(lap_report),
        "protected_before":before,
        "cook_rendering_disabled":True,
        "command":cmd,"started_unix":started,
        "status":"packaging_in_progress","promoted_to_active":False
    }
    launch=qa/"on_foot_packaging_launch.json"
    launch.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    log=qa/"on_foot_packaging.log"
    with log.open("x",encoding="utf-8") as fp:
        try:
            result=subprocess.run(cmd,cwd=uat.parent,env=env,
                   stdout=fp,stderr=subprocess.STDOUT,
                   creationflags=subprocess.CREATE_NO_WINDOW,timeout=1800)
            exit_code=result.returncode
        except subprocess.TimeoutExpired:
            exit_code=124
    exe=archive/"Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe"
    protected_ok=all(sha(Path(path))==digest for path,digest in before.items())
    checked_sources=all(sha(ORIGINAL/name)==digest for name,digest in source_hashes.items())
    checks={
       "uat_succeeded":exit_code==0,
       "candidate_executable_new":exe.is_file() and exe.stat().st_mtime>=started,
       "original_baselines_unchanged":protected_ok,
       "source_code_unchanged":checked_sources
    }
    report={
       **manifest,"ended_unix":time.time(),"exit_code":exit_code,
       "checks":checks,"packaged":all(checks.values()),
       "candidate_executable":str(exe),
       "game_binary_sha256":sha(exe) if exe.is_file() else None,
       "promoted_to_active":False
    }
    report["status"]="packaged_unverified" if report["packaged"] else "failed"
    (qa/"on_foot_packaging_report.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "tag","status","exit_code","checks","candidate_executable",
        "game_binary_sha256")},ensure_ascii=False,indent=2),flush=True)
    if not report["packaged"]:
        raise RuntimeError("On-foot candidate package failed; no active release modified")
    return report


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--lap-report",type=Path,required=True)
    a.add_argument("--tag",default="onfoot_20261111_v1")
    args=a.parse_args()
    package(args.lap_report,args.tag)


if __name__=="__main__":
    main()
