#include "LidarVegetation.h"
#include "PCGContext.h"
#include "PCGElement.h"
#include "Data/PCGBasePointData.h"
#include "PCGComponent.h"
#include "Components/BoxComponent.h"

ALidarProceduralArea::ALidarProceduralArea() {
 Bounds=CreateDefaultSubobject<UBoxComponent>(TEXT("GenerationBounds"));SetRootComponent(Bounds);
 Bounds->SetBoxExtent(FVector(12600,12600,10000));
 Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);Bounds->SetGenerateOverlapEvents(false);
 Procedural=CreateDefaultSubobject<UPCGComponent>(TEXT("PCGVegetation"));
 Procedural->GenerationTrigger=EPCGComponentGenerationTrigger::GenerateOnDemand;
}

uint8 ULidarVegetationMask::At(const FVector& Position) const {
 if(SpacingCm<=0||Width<=0||Height<=0||Cells.Num()!=Width*Height) return 0;
 const int X=FMath::RoundToInt((Position.X-OriginCm.X)/SpacingCm);
 const int Y=FMath::RoundToInt((Position.Y-OriginCm.Y)/SpacingCm);
 return X>=0&&X<Width&&Y>=0&&Y<Height ? Cells[Y*Width+X] : 0;
}

bool ULidarNativeGroundGrid::Project(const FVector& Position,FVector& OutPosition,double& OutUp) const {
 if(Samples<2||SpacingCm<=0||QuantumCm<=0||Heights.Num()!=Samples*Samples)return false;
 const double U=(Position.X-OriginCm.X)/SpacingCm,V=(Position.Y-OriginCm.Y)/SpacingCm;
 const int X=FMath::FloorToInt(U),Y=FMath::FloorToInt(V);
 if(X<0||Y<0||X>=Samples-1||Y>=Samples-1)return false;
 const double Fx=U-X,Fy=V-Y;
 const double A=Heights[Y*Samples+X],B=Heights[Y*Samples+X+1],C=Heights[(Y+1)*Samples+X],D=Heights[(Y+1)*Samples+X+1];
 // Match the native Landscape/Chaos diagonal, not PCG's bilinear cache.
 const double Dx=Fx>=Fy?B-A:D-C,Dy=Fx>=Fy?D-B:C-A;
 OutPosition=Position;OutPosition.Z=OriginCm.Z+(A+Dx*Fx+Dy*Fy)*QuantumCm;
 const double Gx=Dx*QuantumCm/SpacingCm,Gy=Dy*QuantumCm/SpacingCm;
 OutUp=1.0/FMath::Sqrt(1+Gx*Gx+Gy*Gy);return true;
}

class FLidarVegetationElement : public IPCGElement {
 virtual bool ExecuteInternal(FPCGContext* Context) const override {
  const auto* Settings=Context->GetInputSettings<UPCGLidarVegetationSettings>();
  if(!Settings||!Settings->Mask) {UE_LOG(LogTemp,Error,TEXT("LiDAR vegetation mask missing; no vegetation generated"));return true;}
  for(const auto& Input:Context->InputData.GetInputsByPin(TEXT("In"))) {
   const auto* Source=Cast<UPCGBasePointData>(Input.Data);
   if(!Source) continue;
   const auto Transforms=Source->GetConstTransformValueRange();
   const auto Seeds=Source->GetConstSeedValueRange();
   TArray<int32> Indices;
   const double MinUp=FMath::Cos(FMath::DegreesToRadians(Settings->MaxSlopeDegrees));
   for(int I=0;I<Source->GetNumPoints();++I) {
    FVector Position=Transforms[I].GetLocation();double Up=Transforms[I].GetUnitAxis(EAxis::Z).Z;
    if(Settings->NativeGround&&!Settings->NativeGround->Project(Position,Position,Up))continue;
    if(Settings->Mask->At(Position)==Settings->RequiredClass && Up>=MinUp) Indices.Add(I);
   }
   auto* Result=FPCGContext::NewPointData_AnyThread(Context);
   FPCGInitializeFromDataParams Params(Source);Params.bInheritSpatialData=false;
   Result->InitializeFromDataWithParams(Params);
   Result->SetNumPoints(Indices.Num(),false);
   Result->AllocateProperties(Source->GetAllocatedProperties()|EPCGPointNativeProperties::Transform);
   Result->CopyUnallocatedPropertiesFrom(Source);
   TArray<int32> WriteIndices;WriteIndices.Reserve(Indices.Num());
   for(int I=0;I<Indices.Num();++I) WriteIndices.Add(I);
   Source->CopyPointsTo(Result,Indices,WriteIndices);
   auto OutputTransforms=Result->GetTransformValueRange();
   for(int I=0;I<Indices.Num();++I) {
    FRandomStream Random(Settings->Seed^Seeds[Indices[I]]);
    FTransform T=OutputTransforms[I];
    if(Settings->NativeGround) {
     FVector Position;double Up;
     if(Settings->NativeGround->Project(T.GetLocation(),Position,Up))T.SetLocation(Position);
    }
    T.SetRotation(FRotator(0,Random.FRandRange(0,360),0).Quaternion());
    T.SetScale3D(FVector(Random.FRandRange(Settings->MinScale,Settings->MaxScale)));
    OutputTransforms[I]=T;
   }
   auto& Output=Context->OutputData.TaggedData.Add_GetRef(Input);Output.Data=Result;Output.Pin=TEXT("Out");
   UE_LOG(LogTemp,Display,TEXT("LIDAR_PCG_FILTER input=%d accepted=%d class=%d"),Source->GetNumPoints(),Indices.Num(),Settings->RequiredClass);
  }
  return true;
 }
 virtual bool SupportsBasePointDataInputs(FPCGContext*) const override {return true;}
};
FPCGElementPtr UPCGLidarVegetationSettings::CreateElement() const {return MakeShared<FLidarVegetationElement>();}
