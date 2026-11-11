"""Synthetic native report-gate tests; never start Unreal in CI."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from verify_on_foot_candidate import report_checks, artifact_integrity, sha


class NativeOnFootEvidenceTests(unittest.TestCase):
    def valid(self,render):
        data={k:True for k in ("entered","moved_more_than_10_cm","reentered",
              "walking_on_ground","bianca_spawned","bianca_followed_more_than_10_cm",
              "bianca_walking_on_ground","bianca_near_parked_car","passed")}
        data.update(parked_vehicle_displacement_cm=0.15,
                    mouse_travel_cm=113.0,bianca_travel_cm=128.0,
                    nullrhi=not render,rhi="D3D12" if render else "Null")
        if render:
            data.update(viewport_width=1280,viewport_height=720,
                        diagnostic_view_restored=True)
        return data

    def test_headless_complete_evidence(self):
        self.assertTrue(all(report_checks(self.valid(False),rendered=False).values()))

    def test_rendered_complete_evidence(self):
        self.assertTrue(all(report_checks(self.valid(True),rendered=True).values()))

    def test_rendered_requires_real_d3d12_and_viewport(self):
        for field,value in (("rhi","Null"),("nullrhi",True),
                            ("viewport_width",0),("viewport_height",2160),
                            ("diagnostic_view_restored",False)):
            with self.subTest(field=field):
                data=self.valid(True);data[field]=value
                self.assertFalse(all(report_checks(data,rendered=True).values()))

    def test_companion_fails_if_airborne_or_missing(self):
        for field,value in (("bianca_spawned",False),
                            ("bianca_walking_on_ground",False),
                            ("bianca_near_parked_car",False),
                            ("bianca_travel_cm",0)):
            with self.subTest(field=field):
                data=self.valid(False);data[field]=value
                self.assertFalse(all(report_checks(data,rendered=False).values()))

    def test_export_integrity_requires_both_paks_and_verified_binary(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            exe=root/"Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"packaged test executable")
            candidate=exe.parents[2]/"Content/Paks/SoffumbergoLab-Windows.pak"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"packaged test data" * 900)
            active=root/"stable/SoffumbergoLab-Windows.pak"
            active.parent.mkdir(parents=True)
            active.write_bytes(b"protected baseline")
            manifest={
                "game_binary_sha256":sha(exe),
                "protected_before":{str(active):sha(active)}
            }
            checks,pak=artifact_integrity(manifest,exe,active)
            self.assertEqual(pak,candidate)
            self.assertTrue(all(checks.values()))
            active.write_bytes(b"tampered distribution")
            checks,_=artifact_integrity(manifest,exe,active)
            self.assertFalse(checks["active_pak_matches_original_export"])
            active.write_bytes(b"protected baseline")
            exe.write_bytes(b"changed executable")
            checks,_=artifact_integrity(manifest,exe,active)
            self.assertFalse(checks["candidate_executable_hash_matches_export"])
            exe.write_bytes(b"packaged test executable")
            candidate.unlink()
            checks,_=artifact_integrity(manifest,exe,active)
            self.assertFalse(checks["candidate_pak_present"])

    def test_stationary_car_is_bounded(self):
        data=self.valid(False);data["parked_vehicle_displacement_cm"]=50.01
        self.assertFalse(all(report_checks(data,rendered=False).values()))


if __name__=="__main__":
    unittest.main()
