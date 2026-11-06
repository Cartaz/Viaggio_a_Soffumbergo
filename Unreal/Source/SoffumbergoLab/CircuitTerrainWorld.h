#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CircuitTerrainWorld.generated.h"

USTRUCT()
struct FCircuitTerrainTile {
 GENERATED_BODY()
 FString Id, Map, DistantMap;
 FBox2D Bounds;
 UPROPERTY() TObjectPtr<class ULevelStreamingDynamic> Stream;
 UPROPERTY() TObjectPtr<class ULevelStreamingDynamic> DistantStream;
};

/** Geographic native Landscape levels. All coordinates remain in the saved frame. */
UCLASS()
class ACircuitTerrainWorld : public AActor {
 GENERATED_BODY()
public:
 ACircuitTerrainWorld();
 virtual void BeginPlay() override;
 virtual void Tick(float Delta) override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 bool IsAreaReady(const FVector& Position) const;
 bool IsSurvey() const { return bSurvey; }
 int32 ResidentCount() const;
 const FString& GetRoadBuildId() const { return RoadBuildId; }
 const FString& GetDataSHA1() const { return DataSHA1; }
private:
 FString RoadBuildId,DataSHA1;
 void UpdateStreaming(const FVector& Position);
 void SaveSurvey(bool bCompleted);
 void TickVegetationSurvey();
 void SaveVegetationSurvey(bool bCompleted);
 UFUNCTION() void RefreshDistantVisibility();
 TSharedPtr<class FJsonObject> DistantState() const;
 UPROPERTY() TArray<FCircuitTerrainTile> Tiles;
 TArray<FVector> SurveyPoints;
 TArray<TSharedPtr<class FJsonValue>> Failures;
 TArray<TSharedPtr<class FJsonValue>> VegetationResults;
 FString VegetationStableSignature;
 int32 VegetationStableTicks=0;
 int32 SurveyIndex=0, SurveyHits=0, PeakResident=0, Loads=0, Unloads=0;
 int32 SurfacePointCount=0,VoidChecks=0,VoidClear=0;
 double Started=0, LastProgress=0, SurveyWaitStarted=0, MaxErrorCm=0;
 bool bSurvey=false, bSurveySaved=false, bRoadSurvey=false, bVegetationSurvey=false;
 bool bDistantConfigValid=true;
 int32 DistantExpected=0, DistantHideChanges=0, DistantShowChanges=0;
 // Hysteresis prevents repeated unload/reload at a boundary. Load well ahead
 // of the support radius, so normal travel does not freeze the car for I/O.
 double LoadRadiusCm=85000, UnloadRadiusCm=115000, SupportRadiusCm=12000;
};
