#include "CircuitTerrainWorld.h"
#include "LidarVegetation.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Serialization/JsonSerializer.h"
#include "DynamicRHI.h"

namespace {
// Preserve the exact double, including signed zero, for external round/sort
// comparison with the original Python snapshot. JSON numeric writers may
// otherwise emit -0 as an integer and lose its sign during parsing.
TSharedPtr<FJsonValue> Number(double Value){return MakeShared<FJsonValueString>(FString::Printf(TEXT("%.17g"),Value));}
}

void ACircuitTerrainWorld::TickVegetationSurvey(){
 if(bSurveySaved)return;
 if(SurveyIndex<Tiles.Num()){
  const FVector P=SurveyPoints[SurveyIndex];UpdateStreaming(P);
  if(IsAreaReady(P)){
   const auto& Tile=Tiles[SurveyIndex];auto* L=Tile.Stream?Tile.Stream->GetLoadedLevel():nullptr;
   TArray<UInstancedStaticMeshComponent*> Components;int32 Areas=0,Instances=0;
   if(L)for(const auto& Ref:L->Actors)if(auto* A=Ref.Get())if(A->IsA<ALidarProceduralArea>()){
    ++Areas;TInlineComponentArray<UInstancedStaticMeshComponent*> Found;A->GetComponents(Found);Components.Append(Found);
   }
   FString Signature=FString::Printf(TEXT("%d/%d"),Areas,Components.Num());
   for(const auto* C:Components){Instances+=C->GetInstanceCount();Signature+=FString::Printf(TEXT("/%s:%d"),*C->GetName(),C->GetInstanceCount());}
   if(Signature==VegetationStableSignature)++VegetationStableTicks;
   else {VegetationStableSignature=Signature;VegetationStableTicks=0;}
   // Observe two stable updates after the complete near support area is
   // visible. This never triggers, repairs or regenerates PCG resources.
   if(VegetationStableTicks>=2){
    auto Result=MakeShared<FJsonObject>();Result->SetStringField(TEXT("tile"),Tile.Id);
    Result->SetNumberField(TEXT("procedural_actors"),Areas);Result->SetNumberField(TEXT("instances"),Instances);
    auto Counts=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Rows,Descriptions;
    int32 MissingMeshes=0,MissingTransforms=0;
    for(const auto* C:Components){
     const UStaticMesh* Mesh=C->GetStaticMesh().Get();if(!Mesh){++MissingMeshes;continue;}
     FString Name=Mesh->GetName();Name.RemoveFromStart(TEXT("SM_"));
     double Previous=0;Counts->TryGetNumberField(Name,Previous);Counts->SetNumberField(Name,Previous+C->GetInstanceCount());
     auto Description=MakeShared<FJsonObject>();Description->SetStringField(TEXT("mesh_name"),Name);
     Description->SetStringField(TEXT("mesh"),Mesh->GetPathName());Description->SetNumberField(TEXT("instances"),C->GetInstanceCount());
     Description->SetNumberField(TEXT("collision_enabled"),static_cast<int32>(C->GetCollisionEnabled()));
     Description->SetNumberField(TEXT("visibility_response"),static_cast<int32>(C->GetCollisionResponseToChannel(ECC_Visibility)));
     Description->SetBoolField(TEXT("simulating_physics"),C->IsSimulatingPhysics());
     const auto* Body=Mesh->GetBodySetup();Description->SetNumberField(TEXT("convex_hulls"),Body?Body->AggGeom.ConvexElems.Num():-1);
     Description->SetNumberField(TEXT("lod0_triangles_if_resident"),Mesh->GetNumTriangles(0));Descriptions.Add(MakeShared<FJsonValueObject>(Description));
     for(int32 I=0;I<C->GetInstanceCount();++I){FTransform T;
      if(!C->GetInstanceTransform(I,T,true)||T.ContainsNaN()){++MissingTransforms;continue;}
      const auto V=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
      TArray<TSharedPtr<FJsonValue>> Row{MakeShared<FJsonValueString>(Name),Number(V.X),Number(V.Y),Number(V.Z),Number(Q.X),Number(Q.Y),Number(Q.Z),Number(Q.W),Number(S.X),Number(S.Y),Number(S.Z)};
      Rows.Add(MakeShared<FJsonValueArray>(MoveTemp(Row)));
     }
    }
    Result->SetObjectField(TEXT("counts"),Counts);Result->SetArrayField(TEXT("components"),Descriptions);
    Result->SetNumberField(TEXT("missing_meshes"),MissingMeshes);Result->SetNumberField(TEXT("missing_transforms"),MissingTransforms);
    Result->SetBoolField(TEXT("native_readback_passed"),MissingMeshes==0&&MissingTransforms==0&&Rows.Num()==Instances);
    auto Data=MakeShared<FJsonObject>();Data->SetStringField(TEXT("tile"),Tile.Id);Data->SetStringField(TEXT("numeric_encoding"),TEXT("float64 round-trip strings, 17 significant digits"));Data->SetArrayField(TEXT("instances"),Rows);
    FString Json;FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Json));
    FString Folder=FPaths::ProjectSavedDir()/TEXT("Telemetry");FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
    IFileManager::Get().MakeDirectory(*Folder,true);const FString Filename=FString::Printf(TEXT("vegetation_%s.json"),*Tile.Id);
    const bool Saved=FFileHelper::SaveStringToFile(Json,*(Folder/Filename));Result->SetBoolField(TEXT("rows_saved"),Saved);
    Result->SetStringField(TEXT("rows_file"),Filename);VegetationResults.Add(MakeShared<FJsonValueObject>(Result));
    if(!Saved||!Result->GetBoolField(TEXT("native_readback_passed"))){auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("tile"),Tile.Id);Failures.Add(MakeShared<FJsonValueObject>(Failure));}
    UE_LOG(LogTemp,Display,TEXT("CIRCUIT_VEGETATION tile=%s instances=%d areas=%d %d/%d"),*Tile.Id,Instances,Areas,SurveyIndex+1,Tiles.Num());
    ++SurveyIndex;SurveyWaitStarted=FPlatformTime::Seconds();VegetationStableSignature.Reset();VegetationStableTicks=0;
   }
  }
 }
 const double Now=FPlatformTime::Seconds();
 if(Now-LastProgress>10){UE_LOG(LogTemp,Display,TEXT("CIRCUIT_VEGETATION_PROGRESS %d/%d resident=%d"),SurveyIndex,Tiles.Num(),ResidentCount());LastProgress=Now;}
 if(SurveyIndex==Tiles.Num()||Now-SurveyWaitStarted>120){SaveVegetationSurvey(SurveyIndex==Tiles.Num());if(auto* PC=GetWorld()->GetFirstPlayerController())PC->ConsoleCommand(TEXT("quit"));}
}

void ACircuitTerrainWorld::SaveVegetationSurvey(bool bCompleted){
 if(bSurveySaved)return;bSurveySaved=true;
 auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("build_id"),RoadBuildId);R->SetStringField(TEXT("world_data_sha1"),DataSHA1);
 R->SetBoolField(TEXT("completed"),bCompleted);R->SetNumberField(TEXT("expected_tiles"),Tiles.Num());R->SetNumberField(TEXT("checked_tiles"),VegetationResults.Num());
 R->SetArrayField(TEXT("tiles"),VegetationResults);R->SetArrayField(TEXT("failures"),Failures);R->SetObjectField(TEXT("distant_terrain"),DistantState());
 R->SetStringField(TEXT("RHI"),GDynamicRHI?GDynamicRHI->GetName():TEXT("None"));
 R->SetBoolField(TEXT("native_readback_passed"),bCompleted&&VegetationResults.Num()==Tiles.Num()&&Failures.IsEmpty());
 R->SetNumberField(TEXT("wall_seconds"),FPlatformTime::Seconds()-Started);R->SetNumberField(TEXT("peak_resident_near_tiles"),PeakResident);
 R->SetStringField(TEXT("method"),TEXT("Read-only census of saved ISM/HISM resources on every streamed near tile. No PCG generate/cleanup/repair, driving, pose assignment or renderer acceptance. Counts/transforms require external comparison with the accepted Editor baseline."));
 FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
 FString Folder=FPaths::ProjectSavedDir()/TEXT("Telemetry");FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
 IFileManager::Get().MakeDirectory(*Folder,true);FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("circuit_vegetation_survey.json")));
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_VEGETATION_RESULT completed=%d checked=%d/%d"),bCompleted,VegetationResults.Num(),Tiles.Num());
}
