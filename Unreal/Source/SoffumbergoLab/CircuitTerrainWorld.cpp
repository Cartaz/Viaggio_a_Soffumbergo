#include "CircuitTerrainWorld.h"
#include "CircuitDataSignature.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

ACircuitTerrainWorld::ACircuitTerrainWorld() {
 PrimaryActorTick.bCanEverTick=true;
 PrimaryActorTick.TickGroup=TG_PrePhysics;
 PrimaryActorTick.TickInterval=0.1f;
}

void ACircuitTerrainWorld::BeginPlay() {
 Super::BeginPlay(); Started=LastProgress=SurveyWaitStarted=FPlatformTime::Seconds();
 bRoadSurvey=FParse::Param(FCommandLine::Get(),TEXT("CircuitRoadSurvey"));
 bVegetationSurvey=FParse::Param(FCommandLine::Get(),TEXT("CircuitVegetationSurvey"));
 bSurvey=bRoadSurvey||bVegetationSurvey||FParse::Param(FCommandLine::Get(),TEXT("CircuitTerrainSurvey"));
 FString Json;TSharedPtr<FJsonObject> Data;
 const bool Driving=GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"));
 if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/(Driving?TEXT("Data/circuit_driving_world.json"):TEXT("Data/circuit_world.json")))) ||
    !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Data)) {
  UE_LOG(LogTemp,Error,TEXT("CIRCUIT_WORLD: missing geographic manifest"));return;
 }
 Data->TryGetStringField(TEXT("build_id"),RoadBuildId);
 DataSHA1=CircuitFileSHA1(FPaths::ProjectContentDir()/(Driving?TEXT("Data/circuit_driving_world.json"):TEXT("Data/circuit_world.json")));
 for(const auto& Value:Data->GetArrayField(TEXT("tiles"))) {
  const auto Item=Value->AsObject();const auto& B=Item->GetArrayField(TEXT("bounds_xy_cm"));
  FCircuitTerrainTile Tile;Tile.Id=Item->GetStringField(TEXT("id"));Tile.Map=Item->GetStringField(TEXT("map"));
  Tile.Bounds=FBox2D(FVector2D(B[0]->AsNumber(),B[1]->AsNumber()),FVector2D(B[2]->AsNumber(),B[3]->AsNumber()));
  Item->TryGetStringField(TEXT("distant_map"),Tile.DistantMap);
  if(!Tile.DistantMap.IsEmpty()){
   ++DistantExpected;
   if(!Tile.DistantMap.StartsWith(TEXT("/Game/World/Distant/")))bDistantConfigValid=false;
  }
  Tiles.Add(MoveTemp(Tile));
 }
 if(DistantExpected!=0&&DistantExpected!=Tiles.Num())bDistantConfigValid=false;
 // Lightweight visual levels remain available beyond the detailed streaming
 // envelope. Legacy worlds without distant_map retain the previous behavior.
 if(bDistantConfigValid&&DistantExpected)for(auto& T:Tiles){
  bool Success=false;T.DistantStream=ULevelStreamingDynamic::LoadLevelInstance(this,T.DistantMap,FVector::ZeroVector,FRotator::ZeroRotator,Success);
  if(Success&&T.DistantStream){
   T.DistantStream->OnLevelShown.AddDynamic(this,&ACircuitTerrainWorld::RefreshDistantVisibility);
   T.DistantStream->SetShouldBeLoaded(true);T.DistantStream->SetShouldBeVisible(true);
  }else UE_LOG(LogTemp,Error,TEXT("DISTANT_WORLD load request failed %s"),*T.DistantMap);
 }
 if(bVegetationSurvey){for(const auto& T:Tiles){const auto P=T.Bounds.GetCenter();SurveyPoints.Add(FVector(P.X,P.Y,0));}}
 else if(bSurvey) for(const auto& V:Data->GetArrayField(bRoadSurvey?TEXT("road_survey_points_cm"):TEXT("survey_points_cm"))) {
  const auto& A=V->AsArray();SurveyPoints.Add(FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber()));
 }
 SurfacePointCount=SurveyPoints.Num();
 const TArray<TSharedPtr<FJsonValue>>* Voids=nullptr;
 if(bRoadSurvey&&Data->TryGetArrayField(TEXT("road_void_probes_cm"),Voids))for(const auto& V:*Voids){const auto& A=V->AsArray();SurveyPoints.Add(FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber()));}
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_WORLD tiles=%d survey_points=%d build=%s"),Tiles.Num(),SurveyPoints.Num(),*RoadBuildId);
 if(DistantExpected)UE_LOG(LogTemp,Display,TEXT("DISTANT_WORLD expected=%d configuration_valid=%d"),DistantExpected,bDistantConfigValid);
}

void ACircuitTerrainWorld::RefreshDistantVisibility(){
 for(const auto& T:Tiles)if(T.DistantStream&&T.DistantStream->IsLevelLoaded())if(auto* L=T.DistantStream->GetLoadedLevel()){
  const bool Hide=T.Stream&&T.Stream->IsLevelVisible();
  for(const auto& ActorRef:L->Actors)if(auto* A=ActorRef.Get())if(A->ActorHasTag(TEXT("DistantTerrain"))){
   if(A->IsHidden()!=Hide){A->SetActorHiddenInGame(Hide);if(Hide)++DistantHideChanges;else ++DistantShowChanges;}
  }
 }
}

TSharedPtr<FJsonObject> ACircuitTerrainWorld::DistantState() const {
 auto R=MakeShared<FJsonObject>();int32 Loaded=0,Actors=0,Visible=0,Hidden=0,Collision=0,Shadows=0,Mismatch=0;
 int64 Triangles=0;TArray<TSharedPtr<FJsonValue>> Meshes;
 for(const auto& T:Tiles)if(!T.DistantMap.IsEmpty()){
  if(T.DistantStream&&T.DistantStream->IsLevelLoaded()&&T.DistantStream->IsLevelVisible()){
   ++Loaded;int32 PerTile=0;
   if(auto* L=T.DistantStream->GetLoadedLevel())for(const auto& ActorRef:L->Actors)if(auto* A=ActorRef.Get())if(A->ActorHasTag(TEXT("DistantTerrain"))){
    ++Actors;++PerTile;const bool WantHidden=T.Stream&&T.Stream->IsLevelVisible();
    if(A->IsHidden())++Hidden;else ++Visible;if(A->IsHidden()!=WantHidden)++Mismatch;
    TInlineComponentArray<UStaticMeshComponent*> Components;A->GetComponents(Components);
    if(Components.Num()!=1)++Mismatch;
    for(const auto* C:Components){if(C->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||C->IsSimulatingPhysics())++Collision;if(C->CastShadow)++Shadows;
     const UStaticMesh* M=C->GetStaticMesh().Get();if(!M)++Mismatch;
     auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("tile"),T.Id);
     Item->SetStringField(TEXT("mesh"),M?M->GetPathName():TEXT(""));
     const int32 Count=M?M->GetNumTriangles(0):0;Triangles+=Count;
     Item->SetNumberField(TEXT("lod0_triangles_if_resident"),Count);Meshes.Add(MakeShared<FJsonValueObject>(Item));
    }
   }
   if(PerTile!=1)++Mismatch;
  }
 }
 R->SetBoolField(TEXT("enabled"),DistantExpected>0);R->SetNumberField(TEXT("expected"),DistantExpected);
 R->SetNumberField(TEXT("loaded_levels"),Loaded);R->SetNumberField(TEXT("proxy_actors"),Actors);
 R->SetNumberField(TEXT("visible_proxies"),Visible);R->SetNumberField(TEXT("hidden_proxies"),Hidden);
 R->SetNumberField(TEXT("collision_violations"),Collision);R->SetNumberField(TEXT("shadow_violations"),Shadows);
 R->SetNumberField(TEXT("visibility_mismatches"),Mismatch);R->SetNumberField(TEXT("hide_changes"),DistantHideChanges);R->SetNumberField(TEXT("show_changes"),DistantShowChanges);
 R->SetNumberField(TEXT("lod0_triangles_if_resident"),Triangles);R->SetArrayField(TEXT("meshes"),Meshes);
 R->SetBoolField(TEXT("passed"),bDistantConfigValid&&Loaded==DistantExpected&&Actors==DistantExpected&&Collision==0&&Shadows==0&&Mismatch==0);
 return R;
}

int32 ACircuitTerrainWorld::ResidentCount() const {
 int32 Count=0;for(const auto& T:Tiles) if(T.Stream&&T.Stream->IsLevelVisible()) ++Count;return Count;
}

void ACircuitTerrainWorld::UpdateStreaming(const FVector& Position) {
 const FVector2D P(Position.X,Position.Y);
 for(auto& T:Tiles) {
  const double D2=T.Bounds.ComputeSquaredDistanceToPoint(P);
  if(T.Stream&&T.Stream->GetIsRequestingUnloadAndRemoval()) {
   // Keep a strong reference while the engine finishes the removal; don't
   // instantiate a duplicate level during rapid direction changes.
   if(!T.Stream->IsLevelLoaded()) T.Stream=nullptr;
   else continue;
  }
  if(D2<=FMath::Square(LoadRadiusCm)&&!T.Stream) {
   bool Success=false;
   T.Stream=ULevelStreamingDynamic::LoadLevelInstance(this,T.Map,FVector::ZeroVector,FRotator::ZeroRotator,Success);
   if(Success&&T.Stream){++Loads;
    T.Stream->OnLevelShown.AddDynamic(this,&ACircuitTerrainWorld::RefreshDistantVisibility);
    T.Stream->OnLevelHidden.AddDynamic(this,&ACircuitTerrainWorld::RefreshDistantVisibility);
    T.Stream->SetShouldBeLoaded(true);T.Stream->SetShouldBeVisible(true);}
   else UE_LOG(LogTemp,Error,TEXT("CIRCUIT_WORLD load request failed %s"),*T.Map);
  } else if(D2>FMath::Square(UnloadRadiusCm)&&T.Stream) {
   T.Stream->SetShouldBeVisible(false);T.Stream->SetShouldBeLoaded(false);
   T.Stream->SetIsRequestingUnloadAndRemoval(true);++Unloads;
  }
 }
 PeakResident=FMath::Max(PeakResident,ResidentCount());
}

bool ACircuitTerrainWorld::IsAreaReady(const FVector& Position) const {
 const FVector2D P(Position.X,Position.Y);bool bInside=false;
 for(const auto& T:Tiles) {
  if(T.Bounds.IsInsideOrOn(P))bInside=true;
  if(T.Bounds.ComputeSquaredDistanceToPoint(P)<=FMath::Square(SupportRadiusCm)&&
     (!T.Stream||!T.Stream->IsLevelVisible()))return false;
 }
 return bInside;
}

void ACircuitTerrainWorld::Tick(float Delta) {
 Super::Tick(Delta);
 if(bVegetationSurvey){TickVegetationSurvey();return;}
 if(bSurvey) {
  // Diagnostic probe only. No vehicle poses are changed; this is explicitly
  // terrain/streaming validation and cannot count as a driven circuit.
  for(int32 Batch=0;Batch<(bRoadSurvey?512:32)&&SurveyIndex<SurveyPoints.Num();++Batch) {
   const FVector P=SurveyPoints[SurveyIndex];UpdateStreaming(P);
   if(!IsAreaReady(P))break;
   FHitResult Hit;FCollisionQueryParams Query;Query.bTraceComplex=false;
   const bool Void=bRoadSurvey&&SurveyIndex>=SurfacePointCount;
   const bool Found=GetWorld()->LineTraceSingleByChannel(Hit,Void?P:P+FVector(0,0,200000),Void?P-FVector(0,0,20):P-FVector(0,0,200000),ECC_WorldStatic,Query);
   const double Error=Found&&!Void?FMath::Abs(Hit.ImpactPoint.Z-P.Z):0;
   if(Void){++VoidChecks;if(!Found)++VoidClear;}else if(Found)++SurveyHits;
   MaxErrorCm=FMath::Max(MaxErrorCm,Error);
   const bool SurfaceMatches=!bRoadSurvey||(Found&&Hit.GetActor()&&Hit.GetActor()->ActorHasTag(TEXT("RoadSurface")));
   if(Void?Found:(!Found||!SurfaceMatches||Error>(bRoadSurvey?.2:1.4))) {
    auto Failure=MakeShared<FJsonObject>();Failure->SetNumberField(TEXT("index"),SurveyIndex);
    Failure->SetBoolField(TEXT("hit"),Found);Failure->SetNumberField(TEXT("error_cm"),Error);
    Failure->SetBoolField(TEXT("expected_surface"),SurfaceMatches);
    Failure->SetBoolField(TEXT("expected_air_below_deck"),Void);
    if(Found&&Hit.GetActor())Failure->SetStringField(TEXT("hit_actor"),Hit.GetActor()->GetName());
    Failure->SetStringField(TEXT("point_cm"),P.ToString());Failures.Add(MakeShared<FJsonValueObject>(Failure));
   }
   ++SurveyIndex;SurveyWaitStarted=FPlatformTime::Seconds();
  }
  const double Now=FPlatformTime::Seconds();
  if(Now-LastProgress>10) {
   UE_LOG(LogTemp,Display,TEXT("CIRCUIT_SURVEY %d/%d resident=%d loads=%d unloads=%d"),SurveyIndex,SurveyPoints.Num(),ResidentCount(),Loads,Unloads);LastProgress=Now;
  }
  if(SurveyIndex==SurveyPoints.Num()||Now-SurveyWaitStarted>120) {
   SaveSurvey(SurveyPoints.Num()>0&&SurveyIndex==SurveyPoints.Num());
   if(auto* PC=GetWorld()->GetFirstPlayerController())PC->ConsoleCommand(TEXT("quit"));
  }
 } else if(auto* PC=GetWorld()->GetFirstPlayerController()) if(APawn* Pawn=PC->GetPawn()) UpdateStreaming(Pawn->GetActorLocation());
}

void ACircuitTerrainWorld::SaveSurvey(bool bCompleted) {
 if(bSurveySaved)return;bSurveySaved=true;
 const auto Distant=DistantState();
 auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),bCompleted&&Failures.IsEmpty()&&Distant->GetBoolField(TEXT("passed")));
 R->SetObjectField(TEXT("distant_terrain"),Distant);
 R->SetStringField(TEXT("build_id"),RoadBuildId);
 R->SetStringField(TEXT("world_data_sha1"),DataSHA1);
 R->SetBoolField(TEXT("completed"),bCompleted);R->SetNumberField(TEXT("expected"),SurveyPoints.Num());
 R->SetNumberField(TEXT("checked"),SurveyIndex);R->SetNumberField(TEXT("hits"),SurveyHits);
 R->SetNumberField(TEXT("surface_expected"),SurfacePointCount);R->SetNumberField(TEXT("void_checks"),VoidChecks);R->SetNumberField(TEXT("void_clear"),VoidClear);
 R->SetNumberField(TEXT("max_error_cm"),MaxErrorCm);R->SetNumberField(TEXT("peak_resident_tiles"),PeakResident);
 R->SetNumberField(TEXT("loads"),Loads);R->SetNumberField(TEXT("unloads"),Unloads);
 R->SetNumberField(TEXT("wall_seconds"),FPlatformTime::Seconds()-Started);R->SetArrayField(TEXT("failures"),Failures);
 R->SetStringField(TEXT("scope"),bRoadSurvey?TEXT("Moving diagnostic probe along entire built road; expected road actors and heights checked; not a driven lap"):TEXT("Moving diagnostic ray probe over streamed native terrain; no vehicle driving or rendering/performance certification"));
 FString Output;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Output));
 FString Folder=FPaths::ProjectSavedDir()/TEXT("Telemetry");FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
 IFileManager::Get().MakeDirectory(*Folder,true);FFileHelper::SaveStringToFile(Output,*(Folder/(bRoadSurvey?TEXT("circuit_road_survey.json"):TEXT("circuit_terrain_survey.json"))));
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_SURVEY_RESULT %s"),*Output);
}

void ACircuitTerrainWorld::EndPlay(const EEndPlayReason::Type Reason) {
 if(bVegetationSurvey)SaveVegetationSurvey(false);else if(bSurvey)SaveSurvey(false);Super::EndPlay(Reason);
}
