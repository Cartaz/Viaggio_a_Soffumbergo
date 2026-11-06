using UnrealBuildTool;
using System.Collections.Generic;
public class SoffumbergoLabEditorTarget : TargetRules {
 public SoffumbergoLabEditorTarget(TargetInfo Target) : base(Target) {
  Type = TargetType.Editor;
  DefaultBuildSettings = BuildSettingsVersion.Latest;
  ExtraModuleNames.Add("SoffumbergoLab");
 }
}
