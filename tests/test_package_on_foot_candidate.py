"""CPU-only provenance and safety tests for on-foot Windows QA packaging."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import package_on_foot_candidate as qa


class OnFootPackagingTests(unittest.TestCase):
    def test_candidate_tag_rejects_traversal(self):
        self.assertEqual(qa.validate_candidate_tag("onfoot_20261111_v1"),
                         "onfoot_20261111_v1")
        for bad in ("", "../onfoot_foo", "onfoot_a", "onfoot_20261111;rm",
                    "onfoot_20261111/../../", "other_20261111"):
            with self.subTest(tag=bad):
                with self.assertRaises(ValueError):
                    qa.validate_candidate_tag(bad)

    def test_file_sha256_streaming(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"bytes.bin"
            data=(b"geographic verification"+bytes(range(256)))*5000
            file.write_bytes(data)
            self.assertEqual(qa.sha(file),hashlib.sha256(data).hexdigest())

    def test_requires_proven_editor_full_lap_and_all_streamed_maps(self):
        with tempfile.TemporaryDirectory() as folder:
            original=Path(folder)/"Unreal"
            data=original/"Content/Data"
            data.mkdir(parents=True)
            build="4a05593a4282"
            tiles=[{"map":f"/Game/World/Terrain/Q_{i:03d}"}
                   for i in range(113)]
            world=data/"circuit_driving_world.json"
            itinerary=data/"circuit_itinerary.json"
            world.write_text(json.dumps({"build_id":build,"tiles":tiles}),encoding="utf-8")
            itinerary.write_text(json.dumps({"build_id":build}),encoding="utf-8")
            root_map=original/"Content/Maps/CircuitoGuidabile.umap"
            root_map.parent.mkdir(parents=True)
            root_map.write_bytes(b"test-only driving scene")
            module=original/"Binaries/Win64/UnrealEditor-SoffumbergoLab.dll"
            module.parent.mkdir(parents=True)
            module.write_bytes(b"verified native editor game module")
            for tile in tiles:
                asset=original/"Content"/(tile["map"][len("/Game/"):] + ".umap")
                asset.parent.mkdir(parents=True,exist_ok=True)
                asset.write_bytes(b"test-only native map")
            root=Path(folder)
            report_path=root/"lap_report.json"
            report={"full_lap_passed":True,"packaged":False,"rendering":False,
                    "build_id":build,
                    "runtime_world_sha256":qa.sha(world),
                    "itinerary_sha256":qa.sha(itinerary),
                    "runtime_binary_sha256":qa.sha(module),
                    "checks":{"driver_scope_completed":True,"no_recovery":True}}
            report_path.write_text(json.dumps(report),encoding="utf-8")
            with mock.patch.object(qa,"ORIGINAL",original):
                _,_,road,maps,dll=qa.verify_inputs(report_path)
                self.assertEqual(len(maps),114)
                self.assertEqual(dll,module)
                self.assertEqual(len(road["tiles"]),113)
                report["full_lap_passed"]=False
                report_path.write_text(json.dumps(report),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"genuine full editor"):
                    qa.verify_inputs(report_path)
                report["full_lap_passed"]=True
                report["runtime_binary_sha256"]="0"*64
                report_path.write_text(json.dumps(report),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"DLL changed"):
                    qa.verify_inputs(report_path)
                report["runtime_binary_sha256"]=qa.sha(module)
                report_path.write_text(json.dumps(report),encoding="utf-8")
                (original/"Content/World/Terrain/Q_005.umap").unlink()
                with self.assertRaisesRegex(FileNotFoundError,"Missing native tile asset"):
                    qa.verify_inputs(report_path)


if __name__=="__main__":
    unittest.main()
