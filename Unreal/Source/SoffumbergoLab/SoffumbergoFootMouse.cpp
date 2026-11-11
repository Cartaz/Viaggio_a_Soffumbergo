#include "SoffumbergoFootMouse.h"
#include "LabVehicle.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "UObject/UObjectGlobals.h"

ASoffumbergoFootMouse::ASoffumbergoFootMouse() {
 PrimaryActorTick.bCanEverTick=false;
 // An actual mouse-sized capsule: do not extend limbs to reach the Yaris.
 GetCapsuleComponent()->InitCapsuleSize(5.f,11.f);
 GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
 GetCharacterMovement()->MaxWalkSpeed=85.f;
 GetCharacterMovement()->MaxAcceleration=260.f;
 GetCharacterMovement()->BrakingDecelerationWalking=400.f;
 GetCharacterMovement()->MaxStepHeight=3.f;
 GetCharacterMovement()->SetWalkableFloorAngle(45.f);
 GetCharacterMovement()->bOrientRotationToMovement=true;
 GetCharacterMovement()->RotationRate=FRotator(0.f,540.f,0.f);
 bUseControllerRotationYaw=false;
 GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 GetMesh()->SetRelativeLocation(FVector(0,0,-11.f));
 CameraArm=CreateDefaultSubobject<USpringArmComponent>(TEXT("MouseCameraArm"));
 CameraArm->SetupAttachment(GetCapsuleComponent());
 CameraArm->TargetArmLength=150.f;
 CameraArm->SetRelativeLocation(FVector(0,0,36.f));
 CameraArm->bUsePawnControlRotation=true;
 CameraArm->bDoCollisionTest=true;
 CameraArm->ProbeSize=8.f;
 ThirdPersonCamera=CreateDefaultSubobject<UCameraComponent>(TEXT("MouseThirdPersonCamera"));
 ThirdPersonCamera->SetupAttachment(CameraArm,USpringArmComponent::SocketName);
 ThirdPersonCamera->bUsePawnControlRotation=false;
 ThirdPersonCamera->FieldOfView=78.f;
}

void ASoffumbergoFootMouse::SetParkedVehicle(ALabVehicle* InVehicle) {
 ParkedVehicle=InVehicle;
}

void ASoffumbergoFootMouse::BeginPlay() {
 Super::BeginPlay();
 if(auto* Existing=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Imported/bernie.bernie"))) {
  GetMesh()->SetSkeletalMeshAsset(Existing);
  const FBoxSphereBounds VisualBounds=Existing->GetBounds();
  const double HalfHeight=VisualBounds.BoxExtent.Z;
  if(HalfHeight>0.1) {
   // Uniform scale preserves original anatomy, including eye size. Place the
   // true model bounds just above the capsule base, not its arbitrary asset pivot.
   const float Scale=FMath::Clamp(float(18.0/(2.0*HalfHeight)),0.0001f,2.f);
   GetMesh()->SetRelativeScale3D(FVector(Scale));
   GetMesh()->SetRelativeLocation(FVector(-VisualBounds.Origin.X*Scale,
     -VisualBounds.Origin.Y*Scale,-11.f-(VisualBounds.Origin.Z-HalfHeight)*Scale));
   UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_MOUSE_BOUNDS raw_origin=%s raw_extent=%s visual_scale=%g offset=%s"),
     *VisualBounds.Origin.ToString(),*VisualBounds.BoxExtent.ToString(),Scale,*GetMesh()->GetRelativeLocation().ToString());
  }
 } else {
  UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_ON_FOOT mouse visual asset absent; movement still available"));
 }
 UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_ENTER mouse_cm=22 walking_speed_cm_s=85"));
}

void ASoffumbergoFootMouse::WalkForward(float Value) {
 if(Controller&&FMath::Abs(Value)>KINDA_SMALL_NUMBER) {
  const FRotator View(0,Controller->GetControlRotation().Yaw,0);
  AddMovementInput(FRotationMatrix(View).GetUnitAxis(EAxis::X),Value);
 }
}
void ASoffumbergoFootMouse::WalkRight(float Value) {
 if(Controller&&FMath::Abs(Value)>KINDA_SMALL_NUMBER) {
  const FRotator View(0,Controller->GetControlRotation().Yaw,0);
  AddMovementInput(FRotationMatrix(View).GetUnitAxis(EAxis::Y),Value);
 }
}
void ASoffumbergoFootMouse::Turn(float Value) {AddControllerYawInput(Value);}
void ASoffumbergoFootMouse::LookUp(float Value) {AddControllerPitchInput(Value);}

void ASoffumbergoFootMouse::TryReenterVehicle() {
 if(ALabVehicle* Vehicle=ParkedVehicle.Get()) {
  Vehicle->CompleteOnFootReturn(this);
 }
}
void ASoffumbergoFootMouse::QuitGame() {
 if(auto* PC=Cast<APlayerController>(GetController())) PC->ConsoleCommand(TEXT("quit"));
}
void ASoffumbergoFootMouse::SetupPlayerInputComponent(UInputComponent* Input) {
 Super::SetupPlayerInputComponent(Input);
 Input->BindAxis("WalkForward",this,&ASoffumbergoFootMouse::WalkForward);
 Input->BindAxis("WalkRight",this,&ASoffumbergoFootMouse::WalkRight);
 Input->BindAxis("MouseLookYaw",this,&ASoffumbergoFootMouse::Turn);
 Input->BindAxis("MouseLookPitch",this,&ASoffumbergoFootMouse::LookUp);
 Input->BindAction("Interact",IE_Pressed,this,&ASoffumbergoFootMouse::TryReenterVehicle);
 Input->BindAction("Quit",IE_Pressed,this,&ASoffumbergoFootMouse::QuitGame);
}
