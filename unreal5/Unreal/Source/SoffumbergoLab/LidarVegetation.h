#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "PCGSettings.h"
#include "GameFramework/Actor.h"
#include "LidarVegetation.generated.h"

UCLASS(BlueprintType)
class SOFFUMBERGOLAB_API ULidarVegetationMask : public UDataAsset {
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere,BlueprintReadWrite) int32 Width=0;
 UPROPERTY(EditAnywhere,BlueprintReadWrite) int32 Height=0;
 UPROPERTY(EditAnywhere,BlueprintReadWrite) double SpacingCm=50;
 UPROPERTY(EditAnywhere,BlueprintReadWrite) FVector OriginCm=FVector::ZeroVector;
 UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<uint8> Cells;
 UPROPERTY(EditAnywhere,BlueprintReadWrite) FString Provenance;
 uint8 At(const FVector& Position) const;
};

UCLASS(BlueprintType)
class SOFFUMBERGOLAB_API ULidarNativeGroundGrid : public UDataAsset {
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere) int32 Samples=0;
 UPROPERTY(EditAnywhere) double SpacingCm=50;
 UPROPERTY(EditAnywhere) FVector OriginCm=FVector::ZeroVector;
 UPROPERTY(EditAnywhere) double QuantumCm=1;
 UPROPERTY(EditAnywhere) TArray<uint16> Heights;
 UPROPERTY(EditAnywhere) FString Provenance;
 bool Project(const FVector& Position,FVector& OutPosition,double& OutUp) const;
};

UCLASS(BlueprintType,ClassGroup=(Procedural))
class SOFFUMBERGOLAB_API UPCGLidarVegetationSettings : public UPCGSettings {
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") TObjectPtr<ULidarVegetationMask> Mask;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") TObjectPtr<ULidarNativeGroundGrid> NativeGround;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") int32 RequiredClass=1;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") float MaxSlopeDegrees=40;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") float MinScale=0.8f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="LiDAR") float MaxScale=1.2f;
#if WITH_EDITOR
 virtual FName GetDefaultNodeName() const override { return TEXT("LidarVegetationMask"); }
 virtual FText GetDefaultNodeTitle() const override { return FText::FromString(TEXT("LiDAR + copertura OSM")); }
 virtual EPCGSettingsType GetType() const override { return EPCGSettingsType::Filter; }
#endif
 virtual bool UseSeed() const override {return true;}
protected:
 virtual TArray<FPCGPinProperties> InputPinProperties() const override {return DefaultPointInputPinProperties();}
 virtual TArray<FPCGPinProperties> OutputPinProperties() const override {return DefaultPointOutputPinProperties();}
 virtual FPCGElementPtr CreateElement() const override;
};

UCLASS()
class SOFFUMBERGOLAB_API ALidarProceduralArea : public AActor {
 GENERATED_BODY()
public:
 ALidarProceduralArea();
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<class UBoxComponent> Bounds;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<class UPCGComponent> Procedural;
};
