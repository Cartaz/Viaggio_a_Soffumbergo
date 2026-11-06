using UnrealBuildTool;
public class SoffumbergoLab : ModuleRules {
 public SoffumbergoLab(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","InputCore","ChaosVehicles","PhysicsCore","Chaos","ChaosSolverEngine","Json","JsonUtilities","RHI","RenderCore","PCG"});
  PrivateDependencyModuleNames.Add("ApplicationCore");
 }
}
