#include "LidarTerrainLibrary.h"
#include "Landscape.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Modules/ModuleManager.h"
#include "LandscapeInfo.h"
#include "LandscapeEdit.h"
#include "EngineUtils.h"
#include "Serialization/JsonSerializer.h"
#include "Materials/MaterialInterface.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeComponent.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, SoffumbergoTerrainEditor);

ALandscape* ULidarTerrainLibrary::ImportLidarWorldTile(const FString& R16Path,const FString& HolesPath,FVector LocationCm,double ZScale) {
 constexpr int N=1009;
 TArray<uint8> Bytes,Holes;
 if(!FFileHelper::LoadFileToArray(Bytes,*R16Path)||Bytes.Num()!=N*N*2||
    !FFileHelper::LoadFileToArray(Holes,*HolesPath)||Holes.Num()!=N*N||ZScale<=0) return nullptr;
 UWorld* World=GEditor?GEditor->GetEditorWorldContext().World():nullptr;
 if(!World)return nullptr;
 TArray<uint16> Values;Values.SetNumUninitialized(N*N);
 for(int I=0;I<Values.Num();++I) Values[I]=uint16(Bytes[2*I])|(uint16(Bytes[2*I+1])<<8);
 auto* Terrain=World->SpawnActor<ALandscape>();
 Terrain->SetActorTransform(FTransform(FRotator::ZeroRotator,LocationCm,FVector(50,50,ZScale)));
 auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/World/Materials/M_LidarWorld.M_LidarWorld"));
 Terrain->LandscapeMaterial=Material;Terrain->LandscapeHoleMaterial=Material;
 TMap<FGuid,TArray<uint16>> HeightData;HeightData.Add(FGuid(),MoveTemp(Values));
 TMap<FGuid,TArray<FLandscapeImportLayerInfo>> Layers;
 FLandscapeImportLayerInfo Visibility;
 Visibility.LayerName=ALandscapeProxy::VisibilityLayer->GetLayerName();Visibility.LayerInfo=ALandscapeProxy::VisibilityLayer;Visibility.LayerData=MoveTemp(Holes);
 Layers.Add(FGuid(),{MoveTemp(Visibility)});
 Terrain->Import(FGuid::NewGuid(),0,0,N-1,N-1,2,63,HeightData,*R16Path,Layers,ELandscapeImportAlphamapType::Additive,TArrayView<const FLandscapeLayer>());
 Terrain->ForceUpdateLayersContent();
 Terrain->RecreateCollisionComponents();
 Terrain->MarkPackageDirty();return Terrain;
}

FString ULidarTerrainLibrary::VerifyLidarWorldTile(const FString& R16Path,const FString& HolesPath) {
 constexpr int N=1009;
 auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),false);
 UWorld* World=GEditor?GEditor->GetEditorWorldContext().World():nullptr;
 ALandscape* Terrain=nullptr;
 if(World) for(TActorIterator<ALandscape> It(World);It;++It) {Terrain=*It;break;}
 TArray<uint8> Bytes,Holes;
 if(Terrain&&FFileHelper::LoadFileToArray(Bytes,*R16Path)&&Bytes.Num()==N*N*2&&FFileHelper::LoadFileToArray(Holes,*HolesPath)&&Holes.Num()==N*N) {
  TArray<uint16> Readback;Readback.SetNumZeroed(N*N);
  FLandscapeEditDataInterface Edit(Terrain->GetLandscapeInfo(),false);
  Edit.GetHeightDataFast(0,0,N-1,N-1,Readback.GetData(),0);
  TArray<uint8> VisibilityReadback;VisibilityReadback.SetNumZeroed(N*N);
  Edit.GetWeightDataFast(ALandscapeProxy::VisibilityLayer,0,0,N-1,N-1,VisibilityReadback.GetData(),0);
  int Mismatch=0,VisibilityMismatch=0,ValidExpected=0,ValidHits=0,HoleExpected=0,HoleMisses=0;double MaxError=0;
  for(int I=0;I<Readback.Num();++I) if(Readback[I]!=(uint16(Bytes[I*2])|(uint16(Bytes[I*2+1])<<8))) ++Mismatch;
  for(int I=0;I<Holes.Num();++I) if(VisibilityReadback[I]!=Holes[I]) ++VisibilityMismatch;
  // Interior sample grid avoids ambiguity exactly on the outside triangle boundary.
  for(int R=0;R<17;++R) for(int C=0;C<17;++C) {
   const int X=4+C*62,Y=4+R*62,I=Y*N+X;
   const bool Valid=Holes[I]==0 && Holes[I+1]==0 && Holes[I+N]==0 && Holes[I+N+1]==0;
   const FVector Expected=Terrain->GetActorTransform().TransformPosition(FVector(X,Y,(int(Readback[I])-32768)/128.0));
   FHitResult Hit;FCollisionQueryParams Params;Params.bTraceComplex=false;
   // ECC_Visibility also sees Unreal's special editor-only heightfield, which
   // intentionally closes holes for the Landscape editing tools. Query the
   // physical WorldStatic shape used by the vehicle instead.
   const bool Found=World->LineTraceSingleByChannel(Hit,Expected+FVector(0,0,200000),Expected-FVector(0,0,200000),ECC_WorldStatic,Params)&&Hit.GetActor()==Terrain;
   if(Valid){++ValidExpected;if(Found){++ValidHits;MaxError=FMath::Max(MaxError,FMath::Abs(Hit.ImpactPoint.Z-Expected.Z));}}
   else if(Holes[I]==255&&Holes[I+1]==255&&Holes[I+N]==255&&Holes[I+N+1]==255){++HoleExpected;if(!Found)++HoleMisses;}
  }
  Report->SetNumberField(TEXT("height_mismatches"),Mismatch);Report->SetNumberField(TEXT("samples_read"),Readback.Num());
  Report->SetNumberField(TEXT("visibility_mismatches"),VisibilityMismatch);
  Report->SetNumberField(TEXT("valid_rays_expected"),ValidExpected);Report->SetNumberField(TEXT("valid_ray_hits"),ValidHits);
  Report->SetNumberField(TEXT("hole_rays_expected"),HoleExpected);Report->SetNumberField(TEXT("hole_ray_misses"),HoleMisses);
  Report->SetNumberField(TEXT("max_height_error_cm"),MaxError);
  // Chaos::FHeightField::BuildData recompresses each component to uint16 with
  // truncation. Its maximum additional error is one global R16 quantum;
  // add 1 mm for the scene-query conversion and report the measured value.
  const double CollisionToleranceCm=Terrain->GetActorScale3D().Z/128.0+0.1;
  Report->SetNumberField(TEXT("collision_tolerance_cm"),CollisionToleranceCm);
  Report->SetBoolField(TEXT("passed"),Mismatch==0&&VisibilityMismatch==0&&ValidExpected>0&&ValidHits==ValidExpected&&HoleMisses==HoleExpected&&MaxError<CollisionToleranceCm);
 }
 FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}

ALandscape* ULidarTerrainLibrary::ImportLidarLandscape(const FString& R16Path, int32 Samples, double XYScaleCm, double ZScale, double OffsetZCm) {
 // Deliberately accept only the verified first increment: 8x8 components, 63 quads.
 TArray<uint8> Bytes;
 if (Samples != 505 || XYScaleCm <= 0 || ZScale <= 0 ||
     !FFileHelper::LoadFileToArray(Bytes, *R16Path) || Bytes.Num() != Samples*Samples*2) {
  UE_LOG(LogTemp, Error, TEXT("Invalid LiDAR heightmap or dimensions"));
  return nullptr;
 }
 UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
 if (!World) return nullptr;
 TArray<uint16> Heights;
 Heights.SetNumUninitialized(Samples*Samples);
 for (int32 I=0; I<Heights.Num(); ++I) Heights[I] = uint16(Bytes[2*I]) | (uint16(Bytes[2*I+1]) << 8);
 ALandscape* Terrain = World->SpawnActor<ALandscape>();
 Terrain->SetActorLabel(TEXT("LiDAR_Valle_505_0p5m"));
 Terrain->SetActorTransform(FTransform(FRotator::ZeroRotator, FVector(0,0,OffsetZCm), FVector(XYScaleCm,XYScaleCm,ZScale)));
 TMap<FGuid,TArray<uint16>> HeightData;
 HeightData.Add(FGuid(), MoveTemp(Heights));
 TMap<FGuid,TArray<FLandscapeImportLayerInfo>> LayerData;
 LayerData.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
 Terrain->Import(FGuid::NewGuid(),0,0,Samples-1,Samples-1,1,63,HeightData,*R16Path,LayerData,ELandscapeImportAlphamapType::Additive,TArrayView<const FLandscapeLayer>());
 Terrain->MarkPackageDirty();
 UE_LOG(LogTemp, Display, TEXT("LIDAR_IMPORT samples=%d spacing_cm=%g"), Samples, XYScaleCm);
 return Terrain;
}

FString ULidarTerrainLibrary::VerifyLidarLandscape(const FString& R16Path, int32 Samples) {
 auto Report=MakeShared<FJsonObject>();
 Report->SetBoolField(TEXT("passed"),false);
 UWorld* World=GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
 ALandscape* Terrain=nullptr;
 if(World) for(TActorIterator<ALandscape> It(World); It; ++It) { Terrain=*It; break; }
 TArray<uint8> Bytes;
 if(Terrain && Samples==505 && FFileHelper::LoadFileToArray(Bytes,*R16Path) && Bytes.Num()==Samples*Samples*2) {
  TArray<uint16> Readback;
  Readback.SetNumZeroed(Samples*Samples);
  FLandscapeEditDataInterface Edit(Terrain->GetLandscapeInfo(),false);
  Edit.GetHeightDataFast(0,0,Samples-1,Samples-1,Readback.GetData(),0);
  int Mismatches=0;
  for(int I=0;I<Readback.Num();++I) if(Readback[I]!=(uint16(Bytes[2*I])|(uint16(Bytes[2*I+1])<<8))) ++Mismatches;
  int Hits=0;
  double MaximumError=0;
  TArray<TSharedPtr<FJsonValue>> Rows;
  for(int R=0;R<9;++R) for(int C=0;C<9;++C) {
   const int X=8+C*61,Y=8+R*61;
   const uint16 H=Readback[Y*Samples+X];
   const FVector Expected=Terrain->GetActorTransform().TransformPosition(FVector(X,Y,(int(H)-32768)/128.0));
   FHitResult Hit;
   FCollisionQueryParams Params; Params.bTraceComplex=false;
   const bool Found=World->LineTraceSingleByChannel(Hit,Expected+FVector(0,0,20000),Expected-FVector(0,0,20000),ECC_Visibility,Params);
   const bool Correct=Found&&Hit.GetActor()==Terrain;
   auto Row=MakeShared<FJsonObject>();
   Row->SetNumberField(TEXT("x_cm"),Expected.X);Row->SetNumberField(TEXT("y_cm"),Expected.Y);
   Row->SetBoolField(TEXT("landscape_hit"),Correct);
   if(Correct) {
    ++Hits;const double Error=FMath::Abs(Hit.ImpactPoint.Z-Expected.Z);MaximumError=FMath::Max(MaximumError,Error);
    Row->SetNumberField(TEXT("height_error_cm"),Error);
   }
   Rows.Add(MakeShared<FJsonValueObject>(Row));
  }
  Report->SetNumberField(TEXT("samples_read_back"),Readback.Num());
  Report->SetNumberField(TEXT("heightmap_mismatches"),Mismatches);
  Report->SetNumberField(TEXT("collision_ray_hits"),Hits);Report->SetNumberField(TEXT("collision_ray_expected"),81);
  Report->SetNumberField(TEXT("max_collision_height_error_cm"),MaximumError);
  Report->SetArrayField(TEXT("rays"),Rows);
  Report->SetBoolField(TEXT("passed"),Mismatches==0&&Hits==81&&MaximumError<0.1);
 }
 FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}
