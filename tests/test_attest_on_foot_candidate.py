"""Offline cross-report acceptance tests; never run native Unreal in CI."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from attest_on_foot_candidate import consistent_evidence


def fixture_reports():
    digest="a"*64
    pkg={
        "packaged":True,"promoted_to_active":False,
        "original_road_build_id":"4a05593a4282",
        "map_count":114,"game_binary_sha256":digest,
        "checks":{"uat_succeeded":True,"candidate_executable_new":True,
                  "original_baselines_unchanged":True,"source_code_unchanged":True}
    }
    combos=[(1,False),(0,False),(2,False),(1,True)]
    smoke={
        "completed":True,"all_passed":True,"expected_runs":4,"actual_runs":4,
        "binary_sha256":digest,"candidate_pak_unchanged":True,
        "candidate_binary_unchanged":True,
        "protected_active_pak_unchanged":True,
        "cases":[{
            "stop":stop,"rendered":rendered,"passed":True,"exit_code":0,
            "candidate_binary_sha256":digest,
            "checks":{"has_both_mice":True,"correct_rhi":True}
        } for stop,rendered in combos]
    }
    lap={
        "packaged":True,"rendering":False,
        "full_lap_passed":True,"passed_for_requested_test_scope":True,
        "build_id":"4a05593a4282",
        "runtime_binary_sha256":digest,
        "checks":{"full":True,"mass":True,"no_recovery":True,
                  "native_world":True,"itinerary":True,"terrain":True,
                  "physics":True},
        "drive":{"finished":True,"failed":False,"partial_diagnostic":False,
                 "phase":31,"expected_phases":31,"maneuvers_completed":3,
                 "driven_m":18857.99,"user_resets":0,
                 "max_no_contact_seconds":0,"max_off_driving_surface_seconds":0}
    }
    return pkg,smoke,lap


class OnFootQualificationTests(unittest.TestCase):
    def test_all_independent_reports_are_required(self):
        pkg,smoke,lap=fixture_reports()
        self.assertTrue(all(consistent_evidence(pkg,smoke,lap).values()))

    def test_editor_drive_cannot_substitute_packaged_drive(self):
        pkg,smoke,lap=fixture_reports()
        lap["packaged"]=False
        self.assertFalse(consistent_evidence(pkg,smoke,lap)["full_packaged_lap_valid"])

    def test_source_build_and_exe_hash_mismatches_rejected(self):
        for field,value in (
            ("original_road_build_id","f4373a62b482"),
            ("game_binary_sha256","0"*64),
            ("map_count",113)
        ):
            pkg,smoke,lap=fixture_reports()
            pkg[field]=value
            self.assertFalse(all(consistent_evidence(pkg,smoke,lap).values()),field)

    def test_missing_or_failed_independent_stop_rejected(self):
        pkg,smoke,lap=fixture_reports()
        smoke["cases"][0]["stop"]=2
        self.assertFalse(consistent_evidence(pkg,smoke,lap)["four_actual_packaged_smokes"])
        pkg,smoke,lap=fixture_reports()
        smoke["cases"][3]["checks"]["correct_rhi"]=False
        self.assertFalse(consistent_evidence(pkg,smoke,lap)["four_actual_packaged_smokes"])
        pkg,smoke,lap=fixture_reports()
        smoke["candidate_pak_unchanged"]=False
        self.assertFalse(consistent_evidence(pkg,smoke,lap)["package_pak_and_exe_kept"])

    def test_incomplete_or_cheated_native_lap_rejected(self):
        for key,value in (
            ("phase",30),("driven_m",900.),("maneuvers_completed",2),
            ("user_resets",1),("max_off_driving_surface_seconds",0.2)
        ):
            pkg,smoke,lap=fixture_reports()
            lap["drive"][key]=value
            checks=consistent_evidence(pkg,smoke,lap)
            self.assertFalse(all(checks.values()),key)


if __name__=="__main__":
    unittest.main()
