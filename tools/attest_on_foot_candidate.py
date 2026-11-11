"""Read-only qualification gate for an isolated Bernie+Bianca Windows candidate.

Requires *separate*, mutually consistent native evidence from:
  1. Windows UAT BuildCookRun exporting one isolated candidate,
  2. Three genuine packaged NullRHI stop tests plus one 720p D3D12 test,
  3. A complete packaged Chaos driving lap, all 31 phases.

Always reports release_promotion_authorized=False. The current 4K/60 FPS,
full village exploration, animations and factual building collisions remain
unverified. Never overwrites an existing QA report or active Windows game.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from verify_on_foot_candidate import sha, artifact_integrity

ROOT=Path(__file__).resolve().parents[1]
ACTIVE_PAK=ROOT/"build/DrivingWindows/Windows/SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak"
EXPECTED_STOPS={(1,False),(0,False),(2,False),(1,True)}


def consistent_evidence(pkg:dict, smoke:dict, lap:dict):
    """Return truth-valued checks; no inference from missing source evidence."""
    cases=smoke.get("cases",[])
    car=lap.get("drive",{})
    return {
        "unpromoted_package_exported":pkg.get("packaged") is True and
            pkg.get("promoted_to_active") is False and
            all(pkg.get("checks",{}).values()) and len(pkg.get("checks",{}))>=4,
        "all_114_maps_staged":pkg.get("map_count")==114,
        "packaged_build_matches_lap":pkg.get("original_road_build_id")==lap.get("build_id"),
        "packaged_exe_matches_lap":pkg.get("game_binary_sha256")==lap.get("runtime_binary_sha256"),
        "four_actual_packaged_smokes":smoke.get("completed") is True and
            smoke.get("all_passed") is True and
            smoke.get("expected_runs")==4 and smoke.get("actual_runs")==4 and
            len(cases)==4 and
            {(x.get("stop"),x.get("rendered")) for x in cases}==EXPECTED_STOPS and
            all(x.get("passed") is True and x.get("exit_code")==0 and
                all(x.get("checks",{}).values()) and
                x.get("candidate_binary_sha256")==pkg.get("game_binary_sha256")
                for x in cases),
        "smoke_hash_matches_candidate":smoke.get("binary_sha256")==pkg.get("game_binary_sha256"),
        "smoke_protected_active_pak":smoke.get("protected_active_pak_unchanged") is True,
        "package_pak_and_exe_kept":smoke.get("candidate_pak_unchanged") is True and
            smoke.get("candidate_binary_unchanged") is True,
        "full_packaged_lap_valid":lap.get("packaged") is True and
            lap.get("rendering") is False and
            lap.get("full_lap_passed") is True and
            lap.get("passed_for_requested_test_scope") is True and
            all(lap.get("checks",{}).values()) and len(lap.get("checks",{}))>=7 and
            car.get("finished") is True and car.get("failed") is False and
            car.get("partial_diagnostic") is False,
        "all_31_phases_and_three_maneuvers":car.get("phase")==31 and
            car.get("expected_phases")==31 and car.get("maneuvers_completed")==3 and
            isinstance(car.get("driven_m"),(int,float)) and
            math.isfinite(car["driven_m"]) and car["driven_m"]>18000,
        "no_vehicle_resets_or_surface_departure":car.get("user_resets")==0 and
            car.get("max_no_contact_seconds")==0 and
            car.get("max_off_driving_surface_seconds")==0,
    }


def attest(package_report:Path,smoke_report:Path,lap_report:Path,output:Path):
    output=output.resolve()
    if output.exists():
        raise FileExistsError("Do not overwrite an existing native qualification report")
    files=[p.resolve() for p in (package_report,smoke_report,lap_report)]
    if any(not p.is_file() for p in files):
        raise FileNotFoundError("Missing authoritative source report")
    pkg,smoke,lap=(json.loads(p.read_text(encoding="utf-8")) for p in files)
    checks=consistent_evidence(pkg,smoke,lap)
    checks["smoke_bound_to_package_report"]=(
        smoke.get("archive_report_sha256")==sha(files[0]))
    exe=Path(pkg.get("candidate_executable","missing")).resolve()
    checked,pak=artifact_integrity(pkg,exe,ACTIVE_PAK)
    checks.update(checked)
    checks["candidate_pak_matches_smoke"]=(
        checked["candidate_pak_present"] and
        isinstance(smoke.get("candidate_pak_sha256"),str) and
        sha(pak)==smoke["candidate_pak_sha256"])
    original=ROOT/"Unreal"
    source_records=pkg.get("source_sha256",{})
    checks["all_source_versions_unchanged"]=len(source_records)>=7 and all(
        (original/name).is_file() and sha(original/name)==digest
        for name,digest in source_records.items())
    world=original/"Content/Data/circuit_driving_world.json"
    itinerary=original/"Content/Data/circuit_itinerary.json"
    checks["original_road_data_unchanged"]=(world.is_file() and
        itinerary.is_file() and
        sha(world)==pkg.get("world_sha256") and
        sha(itinerary)==pkg.get("itinerary_sha256"))
    checks["active_packaged_game_never_promoted"]=pkg.get("promoted_to_active") is False
    accepted=all(checks.values())
    report={
        "functional_native_qa_passed":accepted,
        "release_promotion_authorized":False,
        "rendered_full_lap_4k_60_certified":False,
        "full_village_walk_collision_verified":False,
        "character_animation_approved":False,
        "scope":"Windows 5.8 Development candidate; 3 NullRHI mouse exploration stops, one D3D12 1280x720 stop, full packaged Chaos NullRHI driving lap",
        "base_world_build_id":pkg.get("original_road_build_id"),
        "packaged_game_sha256":pkg.get("game_binary_sha256"),
        "packaged_pak_sha256":sha(pak) if pak.is_file() else None,
        "active_original_pak_sha256":sha(ACTIVE_PAK) if ACTIVE_PAK.is_file() else None,
        "candidate":pkg.get("tag"),
        "full_lap_driven_m":lap.get("drive",{}).get("driven_m"),
        "checks":checks,
        "source_report_sha256":{
            "packaging":sha(files[0]),
            "native_smoke":sha(files[1]),
            "packaged_full_lap":sha(files[2])
        },
        "limitations":"Not an art or real village QA, not pathfinding validation, not final packaging promotion, not a rendered 4K/60 lap. No production files changed."
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(output),"passed":accepted,
                      "checks":checks,
                      "release_promotion_authorized":False},ensure_ascii=False,indent=2))
    if not accepted:
        raise RuntimeError("Native Windows candidate lacks required independent evidence")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package-report",type=Path,required=True)
    p.add_argument("--smoke-report",type=Path,required=True)
    p.add_argument("--full-lap-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    attest(a.package_report,a.smoke_report,a.full_lap_report,a.output)


if __name__=="__main__":
    main()
