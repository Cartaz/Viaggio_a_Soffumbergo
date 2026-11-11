"""Offline contract checks for the on-foot Unreal prototype.

These are source/config checks only; native UE 5.8 runtime evidence is
separately required before advertising feature as tested.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/"Unreal/Source/SoffumbergoLab"


class FootMouseContractTests(unittest.TestCase):
    def test_input_mappings_are_present_and_not_duplicated(self):
        text=(ROOT/"Unreal/Config/DefaultInput.ini").read_text(encoding="utf-8")
        actions=re.findall(r'^\+ActionMappings=\(ActionName="(.*?)".*?Key=([^\)]+)\)',text,re.M)
        self.assertEqual([key for action,key in actions if action=="Interact"],["E"])
        axes=re.findall(r'^\+AxisMappings=\(AxisName="([^"]+)".*?Key=([^\)]+)\)',text,re.M)
        for axis,keys in {"WalkForward":{"W","S","Up","Down"},
                          "WalkRight":{"A","D","Left","Right"},
                          "MouseLookYaw":{"MouseX"},
                          "MouseLookPitch":{"MouseY"}}.items():
            self.assertEqual({k for a,k in axes if a==axis},keys)
            self.assertEqual(len([k for a,k in axes if a==axis]),len(keys))

    def test_reentry_uses_persistent_vehicle_link_not_pawn_owner(self):
        mouse=(CODE/"SoffumbergoFootMouse.h").read_text(encoding="utf-8")
        cpp=(CODE/"LabVehicle.cpp").read_text(encoding="utf-8")
        self.assertIn("ParkedVehicle.Get()==InVehicle",mouse)
        self.assertIn("Explorer->IsAssociatedWith(this)",cpp)
        self.assertNotIn("Explorer->GetOwner()!=this",cpp)
        self.assertIn("PC->Possess(this)",cpp)
        self.assertIn("PC->Possess(Explorer)",cpp)

    def test_physics_and_diagnostic_isolation_contract(self):
        cpp=(CODE/"LabVehicle.cpp").read_text(encoding="utf-8")
        self.assertIn("bInputCheck||CircuitPilot||InputKeys.Num()||BenchmarkSeconds>0",cpp)
        self.assertIn("OverlapBlockingTestByChannel",cpp)
        self.assertIn("ImpactNormal.Z<0.72f",cpp)
        self.assertIn('M->SetBrakeTorque(5000,Wheel)',cpp)
        self.assertIn("LabOnFootSmokeTest",cpp)
        self.assertIn("walking_on_ground",cpp)
        self.assertIn("parked_vehicle_displacement_cm",cpp)

    def test_bianca_is_real_companion_without_teleporting(self):
        follower=(CODE/"SoffumbergoCompanionMouse.cpp").read_text(encoding="utf-8")
        header=(CODE/"SoffumbergoCompanionMouse.h").read_text(encoding="utf-8")
        car=(CODE/"LabVehicle.cpp").read_text(encoding="utf-8")
        self.assertIn("bRunPhysicsWithNoController=true",follower)
        self.assertIn('bianca.bianca',follower)
        self.assertIn("GetCharacterMovement()->AddInputVector(To/Dist,true)",follower)
        self.assertIn("if(Dist>65.f)",follower)
        self.assertNotIn("Dist<500.f",follower)
        self.assertIn("InitCapsuleSize(5.f,11.f)",follower)
        self.assertIn("VisualBounds.BoxExtent.Z",follower)
        self.assertIn("GetMesh()->SetRelativeLocation(FVector(-VisualBounds.Origin.X*UniformScale",follower)
        self.assertNotIn("SetActorLocation(",follower)
        self.assertNotIn("TeleportTo(",follower)
        self.assertIn("HasLeader",header)
        self.assertIn("WalkingCompanion=Bianca;",car)
        self.assertIn("Bianca->Follow(Explorer);",car)
        self.assertIn("bFootSmokeCompanionGrounded",car)
        self.assertIn("bianca_near_parked_car",car)
        self.assertIn("Friend->Destroy()",car)
        self.assertIn("no safe ground for companion Bianca",car)

    def test_no_second_orphan_mouse_if_possession_fails(self):
        car=(CODE/"LabVehicle.cpp").read_text(encoding="utf-8")
        self.assertRegex(car,r"if\(PC->GetPawn\(\)!=Explorer\)[\s\S]{0,500}Friend->Destroy\(\)")
        self.assertIn("WalkingCompanion.Reset()",car)
        self.assertIn("bFootSmokeCompanionSpawned&&bFootSmokeCompanionMoved",car)

    def test_mouse_proportions_and_character_movement(self):
        cpp=(CODE/"SoffumbergoFootMouse.cpp").read_text(encoding="utf-8")
        self.assertIn("InitCapsuleSize(5.f,11.f)",cpp)
        self.assertIn("MaxWalkSpeed=85.f",cpp)
        self.assertIn("/Game/Imported/bernie.bernie",cpp)
        self.assertIn("Existing->GetBounds()",cpp)
        self.assertIn("VisualBounds.BoxExtent.Z",cpp)
        self.assertIn("GetMesh()->SetRelativeLocation(FVector(-VisualBounds.Origin.X*Scale",cpp)
        self.assertIn("SetRelativeScale3D(FVector(Scale))",cpp)
        self.assertNotIn("SetActorLocation(",cpp)
        self.assertNotIn("TeleportTo(",cpp)


if __name__=="__main__":
    unittest.main()
