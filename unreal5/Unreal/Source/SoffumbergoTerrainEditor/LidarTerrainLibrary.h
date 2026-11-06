#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LidarTerrainLibrary.generated.h"
class ALandscape;
class UStaticMesh;

UCLASS()
class SOFFUMBERGOTERRAINEDITOR_API ULidarTerrainLibrary : public UBlueprintFunctionLibrary {
 GENERATED_BODY()
public:
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static ALandscape* ImportLidarLandscape(const FString& R16Path, int32 Samples, double XYScaleCm, double ZScale, double OffsetZCm);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static FString VerifyLidarLandscape(const FString& R16Path, int32 Samples);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static ALandscape* ImportLidarWorldTile(const FString& R16Path, const FString& HolesPath, FVector LocationCm, double ZScale);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static FString VerifyLidarWorldTile(const FString& R16Path, const FString& HolesPath);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|Procedural")
 static UStaticMesh* CreateProceduralFoliage(const FString& AssetPath, int32 Seed, int32 Kind, bool WithTrunkCollision = false);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|Procedural")
 static FString InspectProceduralFoliage(const FString& AssetPath);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|Road")
 static UStaticMesh* CreateCircuitMesh(const FString& JsonPath, const FString& AssetPath, const FString& MaterialPath);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static UStaticMesh* CreateDistantTerrainMesh(const FString& BinaryPath, const FString& AssetPath, const FString& MaterialPath);
 UFUNCTION(BlueprintCallable, Category="Soffumbergo|LiDAR")
 static FString VerifyDistantTerrainMesh(const FString& BinaryPath, const FString& AssetPath);
};
