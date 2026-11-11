#include "SoffumbergoCompanionMouse.h"
#include "SoffumbergoFootMouse.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/UObjectGlobals.h"

ASoffumbergoCompanionMouse::ASoffumbergoCompanionMouse() {
 PrimaryActorTick.bCanEverTick=true;
 GetCapsuleComponent()->InitCapsuleSize(5.f,11.f);
 GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
 auto* Movement=GetCharacterMovement();
 Movement->bRunPhysicsWithNoController=true;
 Movement->MaxWalkSpeed=95.f;
 Movement->MaxAcceleration=300.f;
 Movement->BrakingDecelerationWalking=400.f;
 Movement->MaxStepHeight=3.f;
 Movement->SetWalkableFloorAngle(45.f);
 Movement->bOrientRotationToMovement=true;
 Movement->RotationRate=FRotator(0,480,0);
 bUseControllerRotationYaw=false;
 GetMesh()->SetRelativeLocation(FVector(0,0,-11.f));
 GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void ASoffumbergoCompanionMouse::Follow(ASoffumbergoFootMouse* InLeader) {
 Leader=InLeader;
}
void ASoffumbergoCompanionMouse::BeginPlay() {
 Super::BeginPlay();
 if(auto* Asset=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Imported/bianca.bianca"))) {
  GetMesh()->SetSkeletalMeshAsset(Asset);
  const FBoxSphereBounds VisualBounds=Asset->GetBounds();
  const double HalfHeight=VisualBounds.BoxExtent.Z;
  if(HalfHeight>0.1) {
   // Uniform scale; anchor the actual imported mesh bounds to capsule feet.
   const float UniformScale=FMath::Clamp(float(18.0/(2.0*HalfHeight)),0.0001f,2.f);
   GetMesh()->SetRelativeScale3D(FVector(UniformScale));
   GetMesh()->SetRelativeLocation(FVector(-VisualBounds.Origin.X*UniformScale,
      -VisualBounds.Origin.Y*UniformScale,-11.f-(VisualBounds.Origin.Z-HalfHeight)*UniformScale));
   UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_BIANCA_BOUNDS raw_origin=%s raw_extent=%s visual_scale=%g offset=%s"),
     *VisualBounds.Origin.ToString(),*VisualBounds.BoxExtent.ToString(),UniformScale,*GetMesh()->GetRelativeLocation().ToString());
  }
 } else {
  UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_COMPANION mesh Bianca missing; capsule logic still valid"));
 }
}
void ASoffumbergoCompanionMouse::Tick(float DeltaTime) {
 Super::Tick(DeltaTime);
 if(DeltaTime<=0)return;
 const auto* Mouse=Leader.Get();
 if(!IsValid(Mouse)) {
  if(!bReportedMissingLeader) {
   UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_COMPANION lost leader; stopping"));
   bReportedMissingLeader=true;
  }
  return;
 }
 // Follow using actual CharacterMovement and world collision; never SetActorLocation.
 // A short exclusion zone prevents overlap and constant jitter at mouse scale.
 FVector To=Mouse->GetActorLocation()-GetActorLocation();
 To.Z=0.f;
 const double Dist=To.Size();
 if(Dist>65.f) {
  // Keep walking even if the leader gets far away. Freezing at the warning
  // threshold made it impossible for Bianca ever to catch up again.
  GetCharacterMovement()->AddInputVector(To/Dist,true);
 }
 if(Dist>=500.f&&!bReportedMissingLeader) {
  UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_COMPANION too distant to follow without pathfinding"));
  bReportedMissingLeader=true;
 }
}
