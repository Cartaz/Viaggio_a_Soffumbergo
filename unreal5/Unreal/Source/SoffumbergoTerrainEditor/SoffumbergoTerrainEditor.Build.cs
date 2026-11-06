using UnrealBuildTool;
public class SoffumbergoTerrainEditor : ModuleRules {
 public SoffumbergoTerrainEditor(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","Landscape"});
  PrivateDependencyModuleNames.AddRange(new string[]{"UnrealEd","Json","JsonUtilities","Foliage","MeshDescription","StaticMeshDescription","MeshConversion","AssetRegistry","PhysicsCore"});
 }
}
