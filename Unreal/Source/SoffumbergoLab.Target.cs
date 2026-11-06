using UnrealBuildTool;
using System.Collections.Generic;
public class SoffumbergoLabTarget : TargetRules {
 public SoffumbergoLabTarget(TargetInfo Target) : base(Target) {
  Type = TargetType.Game;
  DefaultBuildSettings = BuildSettingsVersion.Latest;
  ExtraModuleNames.Add("SoffumbergoLab");
 }
}
