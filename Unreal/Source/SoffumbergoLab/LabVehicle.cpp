#include "LabVehicle.h"
#include "SoffumbergoFootMouse.h"
#include "SoffumbergoCompanionMouse.h"
#include "CircuitTerrainWorld.h"
#include "CircuitDrivePilot.h"
#include "EngineUtils.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InputComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Engine/PostProcessVolume.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/GameUserSettings.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Modules/ModuleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Physics/PhysicsInterfaceUtils.h"
#include "Chaos/ChaosEngineInterface.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Components/PoseableMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Kismet/KismetMathLibrary.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Misc/App.h"
#include "HAL/PlatformTime.h"
#include "Misc/EngineVersion.h"
#include "UObject/ConstructorHelpers.h"
#include "UnrealClient.h"
#include "HAL/IConsoleManager.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "HAL/PlatformMemory.h"
#include "DynamicRHI.h"
#include "RHIStats.h"
#include "TimerManager.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#if WITH_EDITOR
#include "StaticMeshCompiler.h"
#endif
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, SoffumbergoLab, "SoffumbergoLab");

static void WheelDefaults(UChaosVehicleWheel* W) {
 W->WheelRadius = 31.045f;
 W->WheelWidth = 19.5f;
 // 5.8.4 FillSuspensionSetup multiplies this value by 100; SI stiffness 32000 N/m.
 W->SpringRate = 320;
 W->SpringPreload = 0;
 W->SuspensionMaxRaise = 28;
 W->SuspensionMaxDrop = 15;
 // c/(2 sqrt(k*m_sprung)); estimate only, must reconcile actual corner masses.
 W->SuspensionDampingRatio = 0.5023f;
 // FillWheelSetup multiplies by 10000, whereas N -> kg*cm/s² is x100.
 W->CorneringStiffness = 420;
 W->FrictionForceMultiplier = 0.9f;
 W->MaxBrakeTorque = 16000.f * 0.31045f / 4.f;
 W->bABSEnabled = false;
 W->bTractionControlEnabled = false;
 W->bAffectedByHandbrake = false;
 W->WheelLoadRatio = 1;
 W->RollbarScaling = 0;
 W->SuspensionSmoothing = 0;
 W->ExternalTorqueCombineMethod = ETorqueCombineMethod::Override;
}
ULabFrontWheel::ULabFrontWheel() {
 WheelDefaults(this);
 bAffectedByEngine = true; bAffectedBySteering = true;
 MaxSteerAngle = FMath::RadiansToDegrees(0.52f);
}
ULabRearWheel::ULabRearWheel() {
 WheelDefaults(this);
 bAffectedByEngine = false; bAffectedBySteering = false;
 MaxSteerAngle = 0;
}
ALabVehicle::ALabVehicle() {
 PrimaryActorTick.bCanEverTick = true;
 PrimaryActorTick.TickGroup = TG_PrePhysics;
 auto* M = CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
 M->WheelSetups.SetNum(4);
 const TCHAR* Bones[] = {TEXT("wheel_FL"),TEXT("wheel_FR"),TEXT("wheel_RL"),TEXT("wheel_RR")};
 for (int32 I=0; I<4; ++I) {
  M->WheelSetups[I].WheelClass = I<2 ? ULabFrontWheel::StaticClass() : ULabRearWheel::StaticClass();
  M->WheelSetups[I].BoneName = Bones[I];
  M->WheelSetups[I].AdditionalOffset.Z = 2.955f;
 }
 M->DifferentialSetup.DifferentialType = EVehicleDifferential::FrontWheelDrive;
 M->SteeringSetup.SteeringType=ESteeringType::SingleAngle;
 M->SteeringSetup.SteeringCurve.GetRichCurve()->Reset();
 M->SteeringSetup.SteeringCurve.GetRichCurve()->AddKey(0,1);
 M->SteeringSetup.SteeringCurve.GetRichCurve()->AddKey(200,1);
 M->SteeringInputRate.RiseRate=M->SteeringInputRate.FallRate=0.9f/0.52f;
 // Chaos defaults to a squared controller response. Godot's experimental input is linear.
 M->SteeringInputRate.InputCurveFunction=EInputFunctionType::LinearFunction;
 M->SleepThreshold=0;
 M->ChassisWidth=174.5f;M->ChassisHeight=150;
 M->DragCoefficient=1.27f/(1.745f*1.5f);M->DownforceCoefficient=0;
 M->Mass = 1605;
 M->bEnableCenterOfMassOverride = true;
 M->CenterOfMassOverride = FVector(19.401869, -1.576604, 147.436137);
 // Deliberately explicit candidate map, not a Toyota e-CVT claim.
 M->EngineSetup.MaxTorque = 200;
 M->EngineSetup.MaxRPM = 6000;
 auto* Curve = M->EngineSetup.TorqueCurve.GetRichCurve();
 Curve->AddKey(0,1); Curve->AddKey(2500,1); Curve->AddKey(6000,0.4);
 M->TransmissionSetup.ForwardGearRatios = {1.0f};
 M->TransmissionSetup.FinalRatio = 10.0f;
 M->TransmissionSetup.bUseAutomaticGears = true;
 static ConstructorHelpers::FObjectFinder<USkeletalMesh> MeshAsset(TEXT("/Game/Imported/YarisChaos1.YarisChaos1"));
 if(MeshAsset.Succeeded()) GetMesh()->SetSkeletalMeshAsset(MeshAsset.Object);
 Visual=CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("YarisVisual"));
 Visual->SetupAttachment(GetMesh());
 Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 const TCHAR* Names[] = {TEXT("External"),TEXT("Cabin"),TEXT("Coffa")};
 const FVector Positions[] = {FVector(-1400,1000,700),FVector(60,-39,127),FVector(-150,0,650)};
 const FVector ExternalTarget(0,0,250);
 const FVector ExternalProbeAnchor(0,0,70);
 const FRotator ExternalArmRotation=(ExternalProbeAnchor-Positions[0]).Rotation();
 ExternalCameraArm=CreateDefaultSubobject<USpringArmComponent>(TEXT("ExternalCameraArm"));
 ExternalCameraArm->SetupAttachment(GetMesh());
 // Trace from the chassis rather than above its roof. An elevated trace can
 // clear a bank while that same bank completely hides the lower vehicle.
 ExternalCameraArm->SetRelativeLocation(ExternalProbeAnchor);
 ExternalCameraArm->SetRelativeRotation(ExternalArmRotation);
 ExternalCameraArm->TargetArmLength=(Positions[0]-ExternalProbeAnchor).Size();
 ExternalCameraArm->ProbeSize=30;
 ExternalCameraArm->ProbeChannel=ECC_Camera;
 ExternalCameraArm->bDoCollisionTest=true;
 ExternalCameraArm->bUsePawnControlRotation=false;
 ExternalCameraArm->bEnableCameraLag=false;
 ExternalCameraArm->bEnableCameraRotationLag=false;
 for (int32 I=0; I<3; ++I) {
  auto* Camera = CreateDefaultSubobject<UCameraComponent>(Names[I]);
  if(I==0){Camera->SetupAttachment(ExternalCameraArm,USpringArmComponent::SocketName);
   Camera->SetRelativeRotation((ExternalTarget-Positions[0]).Rotation()-ExternalArmRotation);}
  else {Camera->SetupAttachment(GetMesh());Camera->SetRelativeLocation(Positions[I]);}
  Camera->FieldOfView=FMath::RadiansToDegrees(2*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(75.f/2))*16.f/9));
  Camera->SetAutoActivate(I==0); Cameras.Add(Camera);
 }
}
void ALabVehicle::BeginPlay() {
 Super::BeginPlay();
 const bool Headless=FParse::Param(FCommandLine::Get(),TEXT("nullrhi"));
 const float FrameLimit=Headless?0.f:60.f;
 if(auto* Limit=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS")))Limit->Set(FrameLimit,ECVF_SetByCode);
 if(GEngine)if(auto* Settings=GEngine->GetGameUserSettings())Settings->SetFrameRateLimit(FrameLimit);
 bInputCheck=FParse::Param(FCommandLine::Get(),TEXT("LabInputCheck"));
 bOnFootSmokeTest=FParse::Param(FCommandLine::Get(),TEXT("LabOnFootSmokeTest"));
 bGeographicScene=GetWorld()->GetMapName().Contains(TEXT("ValleLiDAR"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoSoffumbergo"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"));
 for(TActorIterator<ACircuitTerrainWorld> It(GetWorld());It;++It){CircuitWorld=*It;AddTickPrerequisiteActor(CircuitWorld);break;}
 UPhysicsSettings::Get()->bSubstepping=false;
 UPhysicsSettings::Get()->bTickPhysicsAsync=false;
 FParse::Value(FCommandLine::Get(),TEXT("LabLoad="),LoadName);
 FParse::Value(FCommandLine::Get(),TEXT("LabBenchmark="),BenchmarkSeconds);
 FString Preset;
 if(FParse::Value(FCommandLine::Get(),TEXT("LabPreset="),Preset)) {
  const bool Balanced=Preset==TEXT("C");
  const bool Quality=Preset==TEXT("B")||Balanced;
  const TCHAR* Names[]={TEXT("r.VSync"),TEXT("t.MaxFPS"),TEXT("r.ScreenPercentage"),TEXT("r.DynamicRes.OperationMode"),TEXT("r.DynamicGlobalIlluminationMethod"),TEXT("r.ReflectionMethod")};
  const float Values[]={0,FrameLimit,100,0,Quality?1.f:0.f,Quality?1.f:0.f};
  for(int I=0;I<6;++I) if(auto* C=IConsoleManager::Get().FindConsoleVariable(Names[I])) C->Set(Values[I],ECVF_SetByCode);
  for(const TCHAR* Group:{TEXT("sg.ViewDistanceQuality"),TEXT("sg.ShadowQuality"),TEXT("sg.PostProcessQuality")})
   if(auto* C=IConsoleManager::Get().FindConsoleVariable(Group)) C->Set(Balanced?2:Quality?3:1,ECVF_SetByCode);
  // Native 3840x2160 input/output: reduce history supersampling, not scene resolution.
  if(Balanced) if(auto* History=IConsoleManager::Get().FindConsoleVariable(TEXT("r.TSR.History.ScreenPercentage"))) History->Set(100,ECVF_SetByCode);
 }
 FString PropertiesJson;
 if(FFileHelper::LoadFileToString(PropertiesJson,*(FPaths::ProjectContentDir()/TEXT("Data/mass_properties.json")))) {
  TSharedPtr<FJsonObject> Properties;
  if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PropertiesJson),Properties)&&Properties->HasField(LoadName)) {
   auto Part=Properties->GetObjectField(LoadName);
   VehicleMass=Part->GetNumberField(TEXT("mass_kg"));
   const auto& Com=Part->GetArrayField(TEXT("com_m"));
   CentreOfMassUE=FVector(-Com[2]->AsNumber(),Com[0]->AsNumber(),Com[1]->AsNumber())*100;
   const auto& Tensor=Part->GetArrayField(TEXT("inertia_kg_m2"));
   DiagonalInertiaUE=FVector(Tensor[2]->AsArray()[2]->AsNumber(),Tensor[0]->AsArray()[0]->AsNumber(),Tensor[1]->AsArray()[1]->AsNumber())*10000;
  }
 }
 auto* Asset = LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Imported/YarisChaos1.YarisChaos1"));
 if (!Asset) {
  UE_LOG(LogTemp,Error,TEXT("Missing imported Yaris: run bootstrap_unreal.py")); return;
 }
 GetMesh()->SetSimulatePhysics(false);
 GetMesh()->SetSkeletalMeshAsset(Asset);
 if(!bGeographicScene) SetActorLocation(FVector(0,0,20));
 RespawnTransform=GetActorTransform();
 Visual->SetSkinnedAssetAndUpdate(Asset);
 if(LoadName==TEXT("low")) {
  for(int32 I=0;I<Asset->GetMaterials().Num();++I) {
   FString Name=Asset->GetMaterials()[I].MaterialSlotName.ToString();
   if(Name.Contains(TEXT("oak"))||Name.Contains(TEXT("wood"))||Name.Contains(TEXT("rope"))||Name.Contains(TEXT("Rope"))||Name.Contains(TEXT("pirate"))||Name.Contains(TEXT("Pirate"))||Name.Contains(TEXT("brass"))||Name.Contains(TEXT("Forged"))) Visual->ShowMaterialSection(I,INDEX_NONE,false,0);
  }
 }
 GetMesh()->SetVisibility(false,false);
 const TCHAR* BoneNames[]={TEXT("wheel_FL"),TEXT("wheel_FR"),TEXT("wheel_RL"),TEXT("wheel_RR")};
 for(int I=0;I<4;++I) WheelReferences.Add(Visual->GetBoneTransformByName(BoneNames[I],EBoneSpaces::ComponentSpace));
 const TCHAR* CharacterPaths[]={TEXT("/Game/Imported/bernie.bernie"),TEXT("/Game/Imported/bianca.bianca")};
 const FVector CharacterPositions[]={FVector(20,-39.77,49),FVector(23,22,575.6)};
 for(int I=0;I<2;++I) if(!(I==1&&LoadName==TEXT("low"))) if(auto* Character=LoadObject<USkeletalMesh>(nullptr,CharacterPaths[I])) {
  auto* Component=NewObject<USkeletalMeshComponent>(this);
  Component->SetupAttachment(GetMesh()); Component->SetSkeletalMeshAsset(Character);
  Component->SetRelativeLocation(CharacterPositions[I]);
  Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
  Component->RegisterComponent(); Occupants.Add(Component);
 }
 // One rigid aggregate. Do not accept automatically generated wheel/body capsules.
 LabPhysicsAsset=NewObject<UPhysicsAsset>(this);
 auto* Body=NewObject<USkeletalBodySetup>(LabPhysicsAsset);
 const FTransform RootReference=Asset->GetRefSkeleton().GetRefBonePose()[0];
 UE_LOG(LogTemp,Display,TEXT("LAB_ROOT reference=%s component=%s wheel_FL=%s"),*RootReference.ToString(),*GetMesh()->GetComponentTransform().ToString(),*GetMesh()->GetBoneTransform(GetMesh()->GetBoneIndex(TEXT("wheel_FL"))).ToString());
 Body->BoneName=Asset->GetRefSkeleton().GetBoneName(0);
 Body->PhysicsType=PhysType_Simulated;
 FKBoxElem Chassis;
 Chassis.X=380; Chassis.Y=168; Chassis.Z=75;
 Chassis.SetTransform(FTransform(FVector(0,0,70))*RootReference.Inverse());
 Body->AggGeom.BoxElems.Add(Chassis);
 auto Cylinder=[&](float Radius,float Height,float CentreZ) {
  FKConvexElem Hull;
  for(int End=0;End<2;++End) for(int I=0;I<32;++I) {
   float Angle=2*PI*I/32;
   Hull.VertexData.Add(RootReference.InverseTransformPosition(FVector(Radius*FMath::Cos(Angle),Radius*FMath::Sin(Angle),CentreZ+(End?1:-1)*Height/2)));
  }
  Hull.UpdateElemBox(); Body->AggGeom.ConvexElems.Add(Hull);
 };
 if(LoadName!=TEXT("low")) {
  Cylinder(11.55f,631.6865f,339.1568f);
  Cylinder(64,30,560);
 }
 Body->CreatePhysicsMeshes();
 LabPhysicsAsset->SkeletalBodySetups.Add(Body);
 LabPhysicsAsset->UpdateBodySetupIndexMap(); LabPhysicsAsset->UpdateBoundsBodiesArray();
 GetMesh()->SetPhysicsAsset(LabPhysicsAsset,true);
 GetMesh()->SetCollisionProfileName(TEXT("Vehicle"));
 GetMesh()->SetSimulatePhysics(true);
 GetMesh()->SetEnableGravity(true);
 GetMesh()->SetLinearDamping(0);GetMesh()->SetAngularDamping(0);
 auto* Movement=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
 Movement->bEnableCenterOfMassOverride=false;
 Movement->Mass=VehicleMass;
 Movement->RecreatePhysicsState();
 if(auto* BI=GetMesh()->GetBodyInstance()) {
  FPhysicsCommand::ExecuteWrite(BI->GetPhysicsActor(),[&](const FPhysicsActorHandle& Actor) {
   FTransform COM(RootReference.GetRotation().Inverse(),RootReference.InverseTransformPosition(CentreOfMassUE));
   FPhysicsInterface::SetComLocalPose_AssumesLocked(Actor,COM);
   FPhysicsInterface::SetMass_AssumesLocked(Actor,VehicleMass);
   FPhysicsInterface::SetMassSpaceInertiaTensor_AssumesLocked(Actor,DiagonalInertiaUE);
  });
  UE_LOG(LogTemp,Display,TEXT("LAB_MASS mass=%g inertia_kgcm2=%s COM_world_cm=%s"),BI->GetBodyMass(),*BI->GetBodyInertiaTensor().ToString(),*GetMesh()->GetCenterOfMass().ToString());
 }
 bFinalAssetsLoaded=Occupants.Num()==2 && Asset->GetBounds().BoxExtent.Z*2>500 && Visual->IsVisible();
 if(bGeographicScene&&!bFinalAssetsLoaded) {
  UE_LOG(LogTemp,Error,TEXT("FINAL_ASSET_GUARD failed: Yaris/coffa/occupants incomplete"));
  return;
 }
 UE_LOG(LogTemp,Display,TEXT("FINAL_ASSET_GUARD loaded=%d occupants=%d height_cm=%g geographic=%d"),bFinalAssetsLoaded,Occupants.Num(),Asset->GetBounds().BoxExtent.Z*2,bGeographicScene);
 bReadyForSimulation = true;
 FString Profile;
 if (FParse::Value(FCommandLine::Get(),TEXT("LabTest="),RunId)) {
  FString Json;
  if (!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("Data/profiles.json")))) { bReadyForSimulation=false; return; }
  TSharedPtr<FJsonObject> Object;
  if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Object) || !Object->HasField(RunId)) { bReadyForSimulation=false; return; }
  auto Test = Object->GetObjectField(RunId);
  Duration = Test->GetNumberField(TEXT("duration_s"));
  for (const auto& Row : Test->GetArrayField(TEXT("keys"))) {
   TArray<double> Key;
   for (const auto& Value : Row->AsArray()) Key.Add(Value->AsNumber());
   InputKeys.Add(Key);
  }
 } else RunId = TEXT("manual");
 FString RequestedRun;
 if(FParse::Value(FCommandLine::Get(),TEXT("LabRunId="),RequestedRun)) RunId=RequestedRun;
 if(FParse::Param(FCommandLine::Get(),TEXT("CircuitAutoDrive"))){CircuitPilot=NewObject<UCircuitDrivePilot>(this);CircuitPilot->Initialize();}
 // Every rendered mode, including autopilot and diagnostic input profiles,
 // retains the user's 60 FPS limit. Only no-render physics runs are uncapped.
 UE_LOG(LogTemp,Display,TEXT("LAB_FRAME_LIMIT requested=%g headless=%d legacy_uncapped_flag_ignored=%d"),FrameLimit,Headless,FParse::Param(FCommandLine::Get(),TEXT("LabUncapped")));
 if(!Headless&&FParse::Param(FCommandLine::Get(),TEXT("LabStaticSky"))) {
  int32 Changed=0;
  for(TActorIterator<ASkyLight> It(GetWorld());It;++It) {
   auto* Light=It->GetLightComponent();Light->SetRealTimeCaptureEnabled(false);Light->RecaptureSky();++Changed;
  }
  UE_LOG(LogTemp,Display,TEXT("LAB_STATIC_SKY diagnostic_one_time_capture_lights=%d"),Changed);
 }
 StartedWall=LastWall=FPlatformTime::Seconds();
 if(BenchmarkSeconds>0) {
  GetVehicleMovement()->DestroyPhysicsState();
  GetMesh()->SetSimulatePhysics(false);
  if(!bGeographicScene) {SetActorLocation(FVector::ZeroVector);SetActorRotation(FRotator::ZeroRotator);}
 }
 FrameCsv=TEXT("elapsed_s,frame_ms,gpu_ms\n");
 Csv = TEXT("run_id,time_s,physics_hz,render_fps,x_m,y_m,z_m,qw,qx,qy,qz,vx_m_s,vy_m_s,vz_m_s,wx_rad_s,wy_rad_s,wz_rad_s,ax_m_s2,ay_m_s2,az_m_s2,roll_rad,pitch_rad,yaw_rad,throttle,brake,steering_input,steering_rad,FL_spring_proxy_N,FR_spring_proxy_N,RL_spring_proxy_N,RR_spring_proxy_N,FL_compression_m,FR_compression_m,RL_compression_m,RR_compression_m,FL_contact,FR_contact,RL_contact,RR_contact,FL_drive_torque_Nm,FR_drive_torque_Nm,RL_drive_torque_Nm,RR_drive_torque_Nm,FL_brake_torque_Nm,FR_brake_torque_Nm,RL_brake_torque_Nm,RR_brake_torque_Nm,body_awake,inverted\n");
}
void ALabVehicle::Throttle(float Value) { Gas=FMath::Clamp(Value,-1.f,1.f); }
void ALabVehicle::Brake(float Value) { Braking=FMath::Clamp(Value,0.f,1.f); }
void ALabVehicle::Steer(float Value) { Steering=FMath::Clamp(Value,-1.f,1.f); }
void ALabVehicle::CameraNext() {
 Cameras[CameraIndex]->Deactivate(); CameraIndex=(CameraIndex+1)%3; Cameras[CameraIndex]->Activate();
}
void ALabVehicle::ResetVehiclePose() {
 Gas=Braking=Steering=0;
 GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
 GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
 SetActorTransform(RespawnTransform,false,nullptr,ETeleportType::TeleportPhysics);
 PreviousVelocity=FVector::ZeroVector;++ResetCount;
}
void ALabVehicle::QuitGame() {if(bInputCheck)bInputQuitObserved=true;if(auto* PC=GetWorld()->GetFirstPlayerController()) PC->ConsoleCommand(TEXT("quit"));}
void ALabVehicle::TryExitOnFoot() {
 // The on-foot prototype is a manual, geographic-gameplay action. It must
 // never hijack automated native driving tests, benchmark runs or test inputs.
 if(!bGeographicScene||!bReadyForSimulation||bExploringOnFoot||
    bInputCheck||CircuitPilot||InputKeys.Num()||BenchmarkSeconds>0||
    bHoldingForTerrain) return;
 auto* PC=Cast<APlayerController>(GetController());
 if(!PC||GetMesh()->GetPhysicsLinearVelocity().Size()>25.f||
    GetMesh()->GetPhysicsAngularVelocityInRadians().Size()>0.25f) {
  UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_REJECT car moving or unpossessed"));
  return;
 }
 FCollisionQueryParams Query(SCENE_QUERY_STAT(SoffumbergoSafeExit),true);
 Query.AddIgnoredActor(this);
 // Driver's side first, passenger side fallback. Require a real walkable
 // ground hit plus space for the complete mouse capsule; never teleport the car.
 for(const float Side:{-1.f,1.f}) {
  const FVector SideCenter=GetActorLocation()+GetActorRightVector()*Side*175.f;
  FHitResult Floor;
  if(!GetWorld()->LineTraceSingleByChannel(Floor,SideCenter+FVector(0,0,180),
       SideCenter-FVector(0,0,360),ECC_Visibility,Query)||
       Floor.ImpactNormal.Z<0.72f||
       FMath::Abs(Floor.ImpactPoint.Z-GetActorLocation().Z)>180.f) continue;
  const FVector SpawnPoint=Floor.ImpactPoint+FVector(0,0,12.f);
  if(GetWorld()->OverlapBlockingTestByChannel(SpawnPoint,FQuat::Identity,
       ECC_Pawn,FCollisionShape::MakeCapsule(5.f,11.f),Query)) continue;
  FActorSpawnParameters Spawn;
  Spawn.Owner=this;
  Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
  auto* Explorer=GetWorld()->SpawnActor<ASoffumbergoFootMouse>(
       SpawnPoint,FRotator(0,GetActorRotation().Yaw,0),Spawn);
  if(!Explorer) continue;
  Explorer->SetParkedVehicle(this);
  // Find a second authentic surface position for Bianca. A failed candidate
  // never becomes a hidden or teleporting NPC.
  ASoffumbergoCompanionMouse* Bianca=nullptr;
  for(const float Rearward:{-95.f,95.f,-145.f}) {
   const FVector Candidate=SideCenter+GetActorForwardVector()*Rearward;
   FHitResult CompanionFloor;
   if(!GetWorld()->LineTraceSingleByChannel(CompanionFloor,Candidate+FVector(0,0,180),
       Candidate-FVector(0,0,360),ECC_Visibility,Query)||
       CompanionFloor.ImpactNormal.Z<0.72f||
       FMath::Abs(CompanionFloor.ImpactPoint.Z-GetActorLocation().Z)>180.f)continue;
   const FVector CompanionSpawn=CompanionFloor.ImpactPoint+FVector(0,0,12.f);
   if(FVector::Dist2D(CompanionSpawn,SpawnPoint)<35.f||
      GetWorld()->OverlapBlockingTestByChannel(CompanionSpawn,FQuat::Identity,
         ECC_Pawn,FCollisionShape::MakeCapsule(5.f,11.f),Query))continue;
   FActorSpawnParameters FriendSpawn;
   FriendSpawn.Owner=this;
   FriendSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
   Bianca=GetWorld()->SpawnActor<ASoffumbergoCompanionMouse>(
      CompanionSpawn,FRotator(0,GetActorRotation().Yaw,0),FriendSpawn);
   if(Bianca)break;
  }
  if(!Bianca) {
   Explorer->Destroy();
   UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_ON_FOOT_REJECT no safe ground for companion Bianca"));
   continue;
  }
  Bianca->Follow(Explorer);
  WalkingCompanion=Bianca;
  Gas=0;Braking=1;Steering=0;
  auto* M=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
  M->SetThrottleInput(0);M->SetSteeringInput(0);M->SetBrakeInput(1);
  for(int32 Wheel=0;Wheel<M->GetNumWheels();++Wheel) {
   M->SetDriveTorque(0,Wheel);
   M->SetBrakeTorque(5000,Wheel);
  }
  bExploringOnFoot=true;
  for(const auto& MouseInCar:Occupants)if(MouseInCar)MouseInCar->SetVisibility(false,true);
  PC->Possess(Explorer);
  if(PC->GetPawn()!=Explorer) {
   bExploringOnFoot=false;
   for(const auto& MouseInCar:Occupants)if(MouseInCar)MouseInCar->SetVisibility(true,true);
   if(auto* Friend=WalkingCompanion.Get())Friend->Destroy();
   WalkingCompanion.Reset();
   Explorer->Destroy();
   return;
  }
  PC->SetControlRotation(FRotator(-12.f,GetActorRotation().Yaw,0));
  UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_EXIT safe_ground=%s side=%g"),*Floor.ImpactPoint.ToString(),Side);
  return;
 }
 UE_LOG(LogTemp,Warning,TEXT("SOFFUMBERGO_ON_FOOT_REJECT no collision-free walkable ground next to parked Yaris"));
}

void ALabVehicle::CompleteOnFootReturn(ASoffumbergoFootMouse* Explorer) {
 if(!bExploringOnFoot||!IsValid(Explorer)||!Explorer->IsAssociatedWith(this))return;
 auto* PC=Cast<APlayerController>(Explorer->GetController());
 if(!PC||PC->GetPawn()!=Explorer)return;
 // Reentry is local; never teleport the pawn or the physics-driven Yaris.
 const auto* Bianca=WalkingCompanion.Get();
 if(!IsValid(Bianca)||!Bianca->HasLeader(Explorer)||
    FVector::Dist(Bianca->GetActorLocation(),GetActorLocation())>320.f||
    !Bianca->GetCharacterMovement()->IsMovingOnGround()||
    FVector::Dist(Explorer->GetActorLocation(),GetActorLocation())>300.f||
    GetMesh()->GetPhysicsLinearVelocity().Size()>50.f) {
  UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_REENTER_REJECT mouse or Bianca too far, airborne, or car moving"));
  return;
 }
 PC->Possess(this);
 if(PC->GetPawn()!=this)return;
 bExploringOnFoot=false;
 Gas=0;Braking=1;Steering=0;
 for(const auto& MouseInCar:Occupants)if(MouseInCar)MouseInCar->SetVisibility(true,true);
 if(auto* Friend=WalkingCompanion.Get())Friend->Destroy();
 WalkingCompanion.Reset();
 UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_REENTER successful with companion Bianca"));
 Explorer->Destroy();
}

void ALabVehicle::TickOnFootSmoke(float Delta) {
 if(!bOnFootSmokeTest||bFootSmokeReported||Delta<=0)return;
 FootSmokeTime+=Delta;
 auto* PC=GetWorld()->GetFirstPlayerController();
 if(FootSmokeTime>=4.f&&!bFootSmokeExited&&
    FootSmokeTime-FootSmokeLastAttempt>=1.0f&&bReadyForSimulation) {
  FootSmokeLastAttempt=FootSmokeTime;
  TryExitOnFoot();
  if(PC)if(auto* Mouse=Cast<ASoffumbergoFootMouse>(PC->GetPawn())) {
   FootSmokeMouse=Mouse;
   FootSmokeStart=Mouse->GetActorLocation();
   if(auto* Friend=WalkingCompanion.Get()) {
    bFootSmokeCompanionSpawned=Friend->HasLeader(Mouse);
    FootSmokeCompanionStart=Friend->GetActorLocation();
   }
   FootSmokeVehicleStart=GetActorLocation();
   FootSmokeStartDistance=FVector::Dist(FootSmokeStart,FootSmokeVehicleStart);
   FootSmokeExitAt=FootSmokeTime;
   bFootSmokeExited=true;
  }
 }
 if(auto* Mouse=FootSmokeMouse.Get()) {
  const double WalkSeconds=FootSmokeTime-FootSmokeExitAt;
  if(WalkSeconds<1.5) {
   Mouse->AddMovementInput(GetActorForwardVector(),1.f);
   if(!bFootSmokeScreenshotRequested&&WalkSeconds>=0.65&&
      !FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) {
    FString ScreenshotFolder=FPaths::ProjectSavedDir();
    FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),ScreenshotFolder);
    IFileManager::Get().MakeDirectory(*ScreenshotFolder,true);
    const FString Screenshot=ScreenshotFolder/TEXT("on_foot_midwalk.png");
    FScreenshotRequest::RequestScreenshot(Screenshot,false,false);
    bFootSmokeScreenshotRequested=true;
    UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_SCREENSHOT requested=%s"),*Screenshot);
   }
   // Diagnostic second view: expose the following Bianca behind Bernie.
   // This changes no regular user camera and is disabled for NullRHI.
   const bool Rendering=!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"));
   if(Rendering&&PC&&WalkSeconds>=0.82&&!bFootSmokeReviewViewSet) {
    FootSmokePreviousView=PC->GetControlRotation();
    PC->SetControlRotation(FRotator(-17.f,FootSmokePreviousView.Yaw+145.f,0.f));
    bFootSmokeReviewViewSet=true;
   }
   if(Rendering&&PC&&WalkSeconds>=1.00&&bFootSmokeReviewViewSet&&
      !bFootSmokeReviewShotRequested) {
    FString Folder=FPaths::ProjectSavedDir();
    FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
    IFileManager::Get().MakeDirectory(*Folder,true);
    FScreenshotRequest::RequestScreenshot(Folder/TEXT("on_foot_companion_review.png"),false,false);
    bFootSmokeReviewShotRequested=true;
   }
   if(Rendering&&PC&&WalkSeconds>=1.28&&bFootSmokeReviewViewSet&&
      !bFootSmokeViewRestored) {
    PC->SetControlRotation(FootSmokePreviousView);
    bFootSmokeViewRestored=true;
   }
  } else if(!bFootSmokeReentered) {
   FootSmokeWalkDistance=FVector::Dist(FootSmokeStart,Mouse->GetActorLocation());
   bFootSmokeMoved=FootSmokeWalkDistance>10.f;
   bFootSmokeGrounded=Mouse->GetCharacterMovement()->IsMovingOnGround();
   if(auto* Friend=WalkingCompanion.Get()) {
    FootSmokeCompanionTravel=FVector::Dist(FootSmokeCompanionStart,Friend->GetActorLocation());
    bFootSmokeCompanionMoved=FootSmokeCompanionTravel>10.f;
    bFootSmokeCompanionGrounded=Friend->GetCharacterMovement()->IsMovingOnGround();
    bFootSmokeCompanionNearCar=FVector::Dist(Friend->GetActorLocation(),GetActorLocation())<320.f;
   }
   CompleteOnFootReturn(Mouse);
   bFootSmokeReentered=PC&&PC->GetPawn()==this;
  }
 }
 const bool Timeout=FootSmokeTime>=24.f;
 if(bFootSmokeReentered||Timeout) {
  bFootSmokeReported=true;
  auto Result=MakeShared<FJsonObject>();
  const bool Headless=FParse::Param(FCommandLine::Get(),TEXT("nullrhi"));
  Result->SetStringField(TEXT("scope"),Headless?TEXT("Native NullRHI on-foot transfer, movement and reentry; no rendering evidence"):TEXT("Native rendered on-foot transfer, movement and reentry; not a full game or 4K benchmark"));
  Result->SetBoolField(TEXT("nullrhi"),Headless);
  Result->SetBoolField(TEXT("screenshot_requested"),bFootSmokeScreenshotRequested);
  Result->SetBoolField(TEXT("bianca_review_screenshot_requested"),bFootSmokeReviewShotRequested);
  Result->SetBoolField(TEXT("diagnostic_view_restored"),Headless||bFootSmokeViewRestored);
  Result->SetStringField(TEXT("rhi"),GDynamicRHI?GDynamicRHI->GetName():TEXT("unavailable"));
  if(GetWorld()->GetGameViewport()&&GetWorld()->GetGameViewport()->Viewport) {
   const FIntPoint Size=GetWorld()->GetGameViewport()->Viewport->GetSizeXY();
   Result->SetNumberField(TEXT("viewport_width"),Size.X);
   Result->SetNumberField(TEXT("viewport_height"),Size.Y);
  }
  Result->SetBoolField(TEXT("entered"),bFootSmokeExited);
  Result->SetBoolField(TEXT("moved_more_than_10_cm"),bFootSmokeMoved);
  Result->SetBoolField(TEXT("reentered"),bFootSmokeReentered);
  Result->SetBoolField(TEXT("walking_on_ground"),bFootSmokeGrounded);
  Result->SetBoolField(TEXT("bianca_spawned"),bFootSmokeCompanionSpawned);
  Result->SetBoolField(TEXT("bianca_followed_more_than_10_cm"),bFootSmokeCompanionMoved);
  Result->SetBoolField(TEXT("bianca_walking_on_ground"),bFootSmokeCompanionGrounded);
  Result->SetBoolField(TEXT("bianca_near_parked_car"),bFootSmokeCompanionNearCar);
  Result->SetNumberField(TEXT("bianca_travel_cm"),FootSmokeCompanionTravel);
  Result->SetNumberField(TEXT("mouse_travel_cm"),FootSmokeWalkDistance);
  Result->SetNumberField(TEXT("parked_vehicle_displacement_cm"),bFootSmokeExited?FVector::Dist(FootSmokeVehicleStart,GetActorLocation()):-1.0);
  Result->SetBoolField(TEXT("passed"),bFootSmokeExited&&bFootSmokeMoved&&bFootSmokeGrounded&&
      bFootSmokeCompanionSpawned&&bFootSmokeCompanionMoved&&bFootSmokeCompanionGrounded&&
      bFootSmokeCompanionNearCar&&bFootSmokeReentered&&
      FVector::Dist(FootSmokeVehicleStart,GetActorLocation())<50.0);
  Result->SetNumberField(TEXT("mouse_egress_distance_cm"),FootSmokeStartDistance);
  Result->SetNumberField(TEXT("elapsed_s"),FootSmokeTime);
  FString Folder=FPaths::ProjectSavedDir();
  FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
  IFileManager::Get().MakeDirectory(*Folder,true);
  FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
  FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("on_foot_smoke.json")));
  UE_LOG(LogTemp,Display,TEXT("SOFFUMBERGO_ON_FOOT_SMOKE %s"),*Json);
  if(PC)PC->ConsoleCommand(TEXT("quit"));
 }
}

void ALabVehicle::SetupPlayerInputComponent(UInputComponent* Input) {
 Super::SetupPlayerInputComponent(Input);
 Input->BindAxis("Throttle",this,&ALabVehicle::Throttle);
 Input->BindAxis("Brake",this,&ALabVehicle::Brake);
 Input->BindAxis("Steering",this,&ALabVehicle::Steer);
 Input->BindAction("Camera",IE_Pressed,this,&ALabVehicle::CameraNext);
 Input->BindAction("Reset",IE_Pressed,this,&ALabVehicle::ResetVehiclePose);
 Input->BindAction("Interact",IE_Pressed,this,&ALabVehicle::TryExitOnFoot);
 Input->BindAction("Quit",IE_Pressed,this,&ALabVehicle::QuitGame);
}
void ALabVehicle::Tick(float Delta) {
 Super::Tick(Delta);
 TickOnFootSmoke(Delta);
 if(bExploringOnFoot) {
  // Preserve the parked Chaos chassis while its driver walks: no throttle,
  // no scripted pilot and no displacement/teleport shortcuts.
  auto* M=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
  Gas=0;Braking=1;Steering=0;
  M->SetThrottleInput(0);M->SetSteeringInput(0);M->SetBrakeInput(1);
  for(int32 Wheel=0;Wheel<M->GetNumWheels();++Wheel){
   M->SetDriveTorque(0,Wheel);
   M->SetBrakeTorque(5000,Wheel);
  }
  return;
 }
 if (!bReadyForSimulation || Delta<=0) return;
 if(CircuitWorld&&BenchmarkSeconds<=0) {
  if(!CircuitWorld->IsAreaReady(GetActorLocation())) {
   if(!bHoldingForTerrain){bHoldingForTerrain=true;++TerrainWaitEpisodes;}
   TerrainWaitSeconds+=Delta;
   GetMesh()->SetEnableGravity(false);
   GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
   GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
   auto* WaitingMovement=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
   WaitingMovement->SetThrottleInput(0);WaitingMovement->SetBrakeInput(1);
   for(int32 I=0;I<WaitingMovement->GetNumWheels();++I){WaitingMovement->SetDriveTorque(0,I);WaitingMovement->SetBrakeTorque(2000,I);}
   return; // Don't consume scripted inputs while waiting for physical support.
  }
  if(bHoldingForTerrain){bHoldingForTerrain=false;GetMesh()->SetEnableGravity(true);PreviousVelocity=FVector::ZeroVector;}
 }
 ++StepCount; PhysicsDelta=Delta;
 if(ExternalCameraArm&&ExternalCameraArm->IsCollisionFixApplied())++ExternalCameraRetractionSamples;
 if(bInputCheck)TickInputCheck(Delta);
 if (InputKeys.Num()) {
  auto Value=InputKeys.Last();
  for (int32 I=1; I<InputKeys.Num(); ++I) if (Elapsed<=InputKeys[I][0]) {
   float Alpha=FMath::Clamp((Elapsed-InputKeys[I-1][0])/(InputKeys[I][0]-InputKeys[I-1][0]),0.,1.);
   Value=InputKeys[I-1];
   for (int32 J=1;J<4;++J) Value[J]=FMath::Lerp(InputKeys[I-1][J],InputKeys[I][J],Alpha);
   break;
  }
  Gas=Value[1]; Braking=Value[2]; Steering=Value[3];
 }
 auto* M=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
 if(CircuitPilot&&CircuitPilot->Control(this,Delta,Gas,Braking,Steering)) {
  bCompleted=true;QuitGame();
 }
 // Retromarcia has enough torque for a hill; its speed is governed with brakes.
 if(Gas<0&&GetMesh()->GetPhysicsLinearVelocity().Dot(GetActorForwardVector())< -400)
  Braking=FMath::Max(Braking,FMath::Clamp((-GetMesh()->GetPhysicsLinearVelocity().Dot(GetActorForwardVector())/100-4)*.3f,0.f,1.f));
 if(Gas<-.01f&&!GetMesh()->IsAnyRigidBodyAwake())++SleepingReverseInputSamples;
 M->SetThrottleInput(Gas);
 M->SetBrakeInput(Braking); M->SetSteeringInput(Steering);
 // Reuse the experimental wheel force/power envelope, bypassing an invented gearbox map.
 const float SpeedForward=GetMesh()->GetPhysicsLinearVelocity().Dot(GetActorForwardVector())/100;
 const float Drive=Gas*FMath::Min(6500.f,60000.f/FMath::Max(FMath::Abs(SpeedForward),2.f));
 for(int I=0;BenchmarkSeconds<=0 && I<4 && I<M->GetNumWheels();++I) {
  M->SetDriveTorque(I<2?Drive*0.5f*0.31045f:0.f,I);
  M->SetBrakeTorque(Braking*16000.f*0.25f*0.31045f,I);
  FTransform Pose=WheelReferences[I];
  FVector Position=Pose.GetLocation(); Position.Z+=M->GetSuspensionOffset(I)+2.955f;
  Pose.SetLocation(Position);
  Pose.SetRotation(FRotator(M->Wheels[I]->GetRotationAngle(),M->Wheels[I]->GetSteerAngle(),0).Quaternion()*Pose.GetRotation());
  Visual->SetBoneTransformByName(M->WheelSetups[I].BoneName,Pose,EBoneSpaces::ComponentSpace);
 }
 FVector P=GetMesh()->GetComponentLocation()/100., V=GetMesh()->GetPhysicsLinearVelocity()/100.;
 // UE polar vectors reflect Y; axial angular vectors additionally flip handedness.
 FVector W=GetMesh()->GetPhysicsAngularVelocityInRadians(); W=FVector(-W.X,W.Y,-W.Z);
 P.Y=-P.Y; V.Y=-V.Y;
 FVector A=(V-PreviousVelocity)/Delta; PreviousVelocity=V;
 const double Now=FPlatformTime::Seconds();
 const double WallFps=FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))?0:1/FMath::Max(Now-LastWall,1e-6);
 if(BenchmarkSeconds>0||CircuitPilot||bInputCheck||InputKeys.Num()>0) {
  FrameCsv+=FString::Printf(TEXT("%.9g,%.9g,%.9g\n"),Now-StartedWall,(Now-LastWall)*1000,FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()));
  if(Now-LastMemorySample>1) {
   LastMemorySample=Now;PeakProcessMemory=FMath::Max(PeakProcessMemory,FPlatformMemory::GetStats().UsedPhysical);
   FTextureMemoryStats Stats;RHIGetTextureMemoryStats(Stats);TextureAllocation=Stats.StreamingMemorySize+Stats.NonStreamingMemorySize;
  }
 }
 LastWall=Now;
 SampleClock+=Delta;
 if (SampleClock>=0.05&&BenchmarkSeconds<=0) {
  SampleClock=FMath::Fmod(SampleClock,0.05);
  FQuat Q=GetMesh()->GetComponentQuat(); Q=FQuat(-Q.X,Q.Y,-Q.Z,Q.W);
  FVector X=GetActorForwardVector(),Y=GetActorRightVector(),Z=GetActorUpVector();
  X.Y=-X.Y; Y=FVector(-Y.X,Y.Y,-Y.Z); Z.Y=-Z.Y;
  double Roll=FMath::Atan2(Y.Z,Z.Z),Pitch=FMath::Asin(FMath::Clamp(-X.Z,-1.,1.)),Yaw=FMath::Atan2(X.Y,X.X);
  float ActualSteer=M->GetNumWheels()?FMath::DegreesToRadians(M->Wheels[0]->GetSteerAngle()):0;
  Csv+=FString::Printf(TEXT("%s,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g"),*RunId,Elapsed,1./Delta,WallFps,P.X,P.Y,P.Z,Q.W,Q.X,Q.Y,Q.Z,V.X,V.Y,V.Z,W.X,W.Y,W.Z,A.X,A.Y,A.Z,Roll,Pitch,Yaw,Gas,Braking,Steering,ActualSteer);
  for(int I=0;I<4;++I) Csv+=FString::Printf(TEXT(",%.9g"),M->GetWheelState(I).SpringForce*0.01f);
  for(int I=0;I<4;++I) Csv+=FString::Printf(TEXT(",%.9g"),(M->GetSuspensionOffset(I)+15.f)/100);
  for(int I=0;I<4;++I) Csv+=M->GetWheelState(I).bInContact?TEXT(",1"):TEXT(",0");
  for(int I=0;I<4;++I) Csv+=FString::Printf(TEXT(",%.9g"),M->GetWheelState(I).DriveTorque);
  for(int I=0;I<4;++I) Csv+=FString::Printf(TEXT(",%.9g"),M->GetWheelState(I).BrakeTorque);
  Csv+=GetMesh()->IsAnyRigidBodyAwake()?TEXT(",1"):TEXT(",0");
  Csv+=GetActorUpVector().Z<0?TEXT(",1"):TEXT(",0");
  Csv+=TEXT("\n");
 }
 Elapsed+=Delta;
 float CaptureAt=BenchmarkSeconds>0?65:8;FParse::Value(FCommandLine::Get(),TEXT("LabCaptureAt="),CaptureAt);
 if(!bCaptured&&Now-StartedWall>CaptureAt&&FParse::Param(FCommandLine::Get(),TEXT("LabCapture"))&&!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) {
  bCaptured=true;
  FString Folder=FPaths::ProjectDir()/TEXT("../private/screenshots");IFileManager::Get().MakeDirectory(*Folder,true);
  FScreenshotRequest::RequestScreenshot(Folder/(RunId+TEXT(".png")),false,false);
 }
 if(BenchmarkSeconds>0?Now-StartedWall>=BenchmarkSeconds:Duration>0&&Elapsed>=Duration) {
  bCompleted=true;GetWorld()->GetFirstPlayerController()->ConsoleCommand(TEXT("quit"));
 }
}
void ALabVehicle::EndPlay(const EEndPlayReason::Type Reason) {
 if(bReadyForSimulation) {
  FString Folder=FPaths::ProjectSavedDir()/TEXT("Telemetry");
  FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);
  IFileManager::Get().MakeDirectory(*Folder,true);
  SaveInputCheck(Folder);
  FFileHelper::SaveStringToFile(Csv,*(Folder/(RunId+TEXT(".csv"))));
  auto Meta=MakeShared<FJsonObject>();
  Meta->SetStringField(TEXT("run_id"),RunId);
  Meta->SetBoolField(TEXT("geographic_scene"),bGeographicScene);
  Meta->SetStringField(TEXT("road_world_build_id"),CircuitWorld?CircuitWorld->GetRoadBuildId():FString());
  Meta->SetStringField(TEXT("road_world_data_sha1"),CircuitWorld?CircuitWorld->GetDataSHA1():FString());
  Meta->SetNumberField(TEXT("terrain_wait_episodes"),TerrainWaitEpisodes);
  Meta->SetNumberField(TEXT("terrain_wait_seconds"),TerrainWaitSeconds);
  Meta->SetBoolField(TEXT("final_assets_loaded"),bFinalAssetsLoaded);
  Meta->SetNumberField(TEXT("user_resets"),ResetCount);
  Meta->SetNumberField(TEXT("sleeping_reverse_input_samples"),SleepingReverseInputSamples);
  Meta->SetBoolField(TEXT("external_camera_collision_enabled"),ExternalCameraArm&&ExternalCameraArm->bDoCollisionTest);
  Meta->SetNumberField(TEXT("external_camera_retraction_samples"),ExternalCameraRetractionSamples);
  if(ExternalCameraArm) {
   Meta->SetStringField(TEXT("external_camera_probe_anchor_local_cm"),*ExternalCameraArm->GetRelativeLocation().ToString());
   Meta->SetStringField(TEXT("external_camera_final_location_cm"),*Cameras[0]->GetComponentLocation().ToString());
   Meta->SetStringField(TEXT("external_camera_unfixed_location_cm"),*ExternalCameraArm->GetUnfixedCameraPosition().ToString());
  }
  Meta->SetStringField(TEXT("engine"),FEngineVersion::Current().ToString());
  Meta->SetStringField(TEXT("status"),bCompleted?TEXT("executed"):TEXT("interrupted_or_manual"));
  Meta->SetNumberField(TEXT("simulated_s"),Elapsed);Meta->SetNumberField(TEXT("wall_s"),FPlatformTime::Seconds()-StartedWall);
  Meta->SetNumberField(TEXT("world_ticks"),StepCount);Meta->SetNumberField(TEXT("world_dt_s"),PhysicsDelta);
  Meta->SetBoolField(TEXT("substepping"),false);Meta->SetBoolField(TEXT("async_physics"),false);
  Meta->SetBoolField(TEXT("constraint_suspension"),IConsoleManager::Get().FindConsoleVariable(TEXT("p.Vehicle.DisableConstraintSuspension"))->GetInt()==0);
  Meta->SetStringField(TEXT("steering_input_function"),CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement())->SteeringInputRate.InputCurveFunction==EInputFunctionType::LinearFunction?TEXT("linear"):TEXT("other"));
  Meta->SetNumberField(TEXT("mass_kg"),GetMesh()->GetBodyInstance()->GetBodyMass());
  Meta->SetBoolField(TEXT("mass_measurement_valid"),BenchmarkSeconds<=0);
  Meta->SetNumberField(TEXT("configured_aggregate_mass_kg"),VehicleMass);
  Meta->SetNumberField(TEXT("com_height_m"),CentreOfMassUE.Z/100);
  Meta->SetStringField(TEXT("load"),LoadName);
  Meta->SetStringField(TEXT("sample_phase"),TEXT("game thread before physics; previous completed state; synchronous physics"));
  Meta->SetStringField(TEXT("canonical"),TEXT("RH X forward Y left Z up; quaternion wxyz; Euler ZYX"));
  Meta->SetBoolField(TEXT("normal_load_available"),false);
  Meta->SetBoolField(TEXT("physics_disabled_for_graphics"),BenchmarkSeconds>0);
  Meta->SetStringField(TEXT("wheel_force_semantics"),TEXT("FWheelStatus.SpringForce converted /100; internal spring/tire-load proxy, not constraint reaction or measured vertical load"));
  if(CircuitPilot)CircuitPilot->Save(Folder,RunId,ResetCount,TerrainWaitEpisodes);
  if(BenchmarkSeconds>0||CircuitPilot||bInputCheck||InputKeys.Num()>0) {
   Meta->SetStringField(TEXT("RHI"),GDynamicRHI?GDynamicRHI->GetName():TEXT("unavailable"));
   auto Settings=MakeShared<FJsonObject>();
   for(const TCHAR* Name:{TEXT("r.ScreenPercentage"),TEXT("r.DynamicRes.OperationMode"),TEXT("r.DynamicGlobalIlluminationMethod"),TEXT("r.ReflectionMethod"),TEXT("sg.ViewDistanceQuality"),TEXT("sg.ShadowQuality"),TEXT("sg.PostProcessQuality"),TEXT("r.TSR.History.ScreenPercentage"),TEXT("r.AntiAliasingMethod"),TEXT("r.VSync"),TEXT("t.MaxFPS")})
    if(auto* C=IConsoleManager::Get().FindConsoleVariable(Name)) Settings->SetNumberField(Name,C->GetFloat());
   Meta->SetObjectField(TEXT("graphics_settings"),Settings);
  Meta->SetBoolField(TEXT("diagnostic_static_sky"),FParse::Param(FCommandLine::Get(),TEXT("LabStaticSky")));
  int32 SkyLights=0,RealtimeSkyLights=0;
  for(TActorIterator<ASkyLight> It(GetWorld());It;++It){++SkyLights;RealtimeSkyLights+=It->GetLightComponent()->IsRealTimeCaptureEnabled()?1:0;}
  Meta->SetNumberField(TEXT("sky_light_count"),SkyLights);Meta->SetNumberField(TEXT("realtime_sky_light_count"),RealtimeSkyLights);
  if(GEngine)if(auto* UserSettings=GEngine->GetGameUserSettings())Meta->SetNumberField(TEXT("user_settings_frame_rate_limit"),UserSettings->GetFrameRateLimit());
   if(GetWorld()->GetGameViewport()&&GetWorld()->GetGameViewport()->Viewport) {
    const FIntPoint Size=GetWorld()->GetGameViewport()->Viewport->GetSizeXY();
    Meta->SetNumberField(TEXT("viewport_width"),Size.X);Meta->SetNumberField(TEXT("viewport_height"),Size.Y);
   }
   FFileHelper::SaveStringToFile(FrameCsv,*(Folder/(RunId+TEXT("_frames.csv"))));
   Meta->SetNumberField(TEXT("process_peak_rss_bytes"),PeakProcessMemory);
   Meta->SetNumberField(TEXT("rhi_texture_allocation_bytes"),TextureAllocation);
   Meta->SetStringField(TEXT("vram_semantics"),TEXT("RHI allocated texture memory only, not total resident VRAM"));
  }
  FString Json;FJsonSerializer::Serialize(Meta,TJsonWriterFactory<>::Create(&Json));
  FFileHelper::SaveStringToFile(Json,*(Folder/(RunId+TEXT(".json"))));
  UE_LOG(LogTemp,Display,TEXT("BENCH_COMPLETE %s"),*Json);
 }
 Super::EndPlay(Reason);
}
void ALidarDrivingHUD::DrawHUD() {
 Super::DrawHUD();
 if(!Canvas||!GEngine)return;
 const float Scale=FMath::Clamp(Canvas->SizeX/1920.f,0.8f,2.f);
 const bool Terrain=GetWorld()->GetMapName().Contains(TEXT("ValleLiDAR"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoSoffumbergo"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"));
 const bool Driving=GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"));
 const bool Walking=Cast<ASoffumbergoFootMouse>(GetOwningPawn())!=nullptr;
 DrawText(Walking?TEXT("Esplorazione a piedi - prototipo"):Driving?TEXT("Viaggio a Soffumbergo - percorso in collaudo"):Terrain?TEXT("Valle di Soffumbergo - terreno di prova"):TEXT("Laboratorio di guida"),FLinearColor::White,24*Scale,20*Scale,GEngine->GetMediumFont(),Scale);
 DrawText(Walking?TEXT("WASD: cammina   Mouse: guarda   E: rientra vicino alla Yaris   Esc: esci"):TEXT("W/S: avanti/indietro   A/D: sterzo   Spazio: freno   C: vista   E: scendi da fermo   R: riparti   Esc: esci"),FLinearColor::White,24*Scale,53*Scale,GEngine->GetSmallFont(),1.2f*Scale);
 if(!Walking) if(const auto* Pawn=GetOwningPawn()) DrawText(FString::Printf(TEXT("%.0f km/h"),Pawn->GetVelocity().Size()*0.036),FLinearColor::White,24*Scale,82*Scale,GEngine->GetMediumFont(),Scale);
 if(Terrain) DrawText(Driving?TEXT("Percorso in collaudo. Ambiente ancora in costruzione."):TEXT("Strada e borgo in costruzione. Stai guidando sul terreno rilevato."),FLinearColor(1,0.82f,0.45f),24*Scale,Canvas->SizeY-48*Scale,GEngine->GetSmallFont(),1.2f*Scale);
 if(const auto* Pawn=GetOwningPawn())for(TActorIterator<ACircuitTerrainWorld> It(GetWorld());It;++It) {
  if(!It->IsAreaReady(Pawn->GetActorLocation()))DrawText(TEXT("Caricamento del terreno..."),FLinearColor::White,24*Scale,115*Scale,GEngine->GetMediumFont(),Scale);
  break;
 }
}
ALabGameMode::ALabGameMode() { DefaultPawnClass=(FParse::Param(FCommandLine::Get(),TEXT("CircuitTerrainSurvey"))||FParse::Param(FCommandLine::Get(),TEXT("CircuitRoadSurvey")))?nullptr:ALabVehicle::StaticClass();HUDClass=ALidarDrivingHUD::StaticClass(); }
AActor* ALabGameMode::ChoosePlayerStart_Implementation(AController* Player) {
 int32 TestStop=-1;
 if(GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"))&&FParse::Value(FCommandLine::Get(),TEXT("CircuitTestStop="),TestStop)&&TestStop>=0) {
  FString Json;TSharedPtr<FJsonObject> Data;
  if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("Data/circuit_itinerary.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Data)) {
   const auto& Stops=Data->GetArrayField(TEXT("stops"));
   if(Stops.IsValidIndex(TestStop))for(TActorIterator<APlayerStart> It(GetWorld());It;++It){
    const auto Stop=Stops[TestStop]->AsObject();const auto& P=Stop->GetArrayField(TEXT("position_cm"));
    FVector Position(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber());double Yaw=Stop->GetNumberField(TEXT("arrival_yaw_rad"));
    const bool Approach=FParse::Param(FCommandLine::Get(),TEXT("CircuitTestApproach"));
    if(Approach){const auto& Points=Data->GetArrayField(TEXT("points_cm"));const int32 Index=FMath::Max(0,Stop->GetIntegerField(TEXT("index"))-20);const auto& A=Points[Index]->AsArray();const auto& B=Points[Index+1]->AsArray();Position=FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());Yaw=FMath::Atan2(B[1]->AsNumber()-A[1]->AsNumber(),B[0]->AsNumber()-A[0]->AsNumber());}
    It->GetRootComponent()->SetMobility(EComponentMobility::Movable);const bool Set=It->SetActorLocationAndRotation(Position+FVector(0,0,45),FRotator(0,FMath::RadiansToDegrees(Yaw),0));
    UE_LOG(LogTemp,Display,TEXT("CIRCUIT_TEST_START stop=%d approach=%d applied=%d position=%s yaw=%g"),TestStop,Approach,Set,*It->GetActorLocation().ToString(),It->GetActorRotation().Yaw);return *It;
   }
  }
 }
 return Super::ChoosePlayerStart_Implementation(Player);
}
void ALabGameMode::BeginPlay() {
 Super::BeginPlay();
 if(GetWorld()->GetMapName().Contains(TEXT("ValleLiDAR"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoSoffumbergo"))||GetWorld()->GetMapName().Contains(TEXT("CircuitoGuidabile"))) {
  UE_LOG(LogTemp,Display,TEXT("LIDAR_GAME: using saved Landscape; synthetic laboratory disabled"));
  return;
 }
 UStaticMesh* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
 UMaterialInterface* LabGround=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Materials/LabGround.LabGround"));
 auto* Asphalt=NewObject<UPhysicalMaterial>(this);Asphalt->Friction=1;Asphalt->Restitution=0;
 auto Box=[&](FVector At,FVector Size,FRotator Rotation=FRotator::ZeroRotator) {
  auto* Actor=GetWorld()->SpawnActor<AStaticMeshActor>(At,Rotation);
  Actor->GetStaticMeshComponent()->SetStaticMesh(Cube);
  if(LabGround) Actor->GetStaticMeshComponent()->SetMaterial(0,LabGround);
  Actor->SetActorScale3D(Size/100.); Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
  Actor->GetStaticMeshComponent()->SetPhysMaterialOverride(Asphalt);
  return Actor;
 };
 Box(FVector(0,0,-20),FVector(200000,200000,40));
 // Separate obstacle lane; metric 20m circle has no steering/rollover triggers.
 FString TestName;FParse::Value(FCommandLine::Get(),TEXT("LabTest="),TestName);
 float LaneY=TestName==TEXT("T5")?0:1000;
 float RampDeg=FMath::RadiansToDegrees(0.16f);FParse::Value(FCommandLine::Get(),TEXT("LabRampDeg="),RampDeg);
 Box(FVector(4000,LaneY,144.5),FVector(2000,800,30),FRotator(RampDeg,0,0));
 for(int I=0;I<6;++I) Box(FVector(1200+I*150,LaneY,3),FVector(30,800,6));
 Box(FVector(800,LaneY-76,6),FVector(40,40,12));
 auto* Slippery=NewObject<UPhysicalMaterial>(this);Slippery->Friction=0.3f;
 Box(FVector(4000,-2000,0.5),FVector(3000,1000,1))->GetStaticMeshComponent()->SetPhysMaterialOverride(Slippery);
 for(int I=0;I<80;++I) {
  float Angle=I*2*PI/80;
  Box(FVector(2000*FMath::Cos(Angle),2000*FMath::Sin(Angle),0.5),FVector(15,30,1))->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 }
 auto* Sun=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,1000),FRotator(-40,-30,0));
 Cast<UDirectionalLightComponent>(Sun->GetLightComponent())->SetIntensity(50000);
 auto* Exposure=GetWorld()->SpawnActor<APostProcessVolume>();Exposure->bUnbound=true;
 Exposure->Settings.bOverride_AutoExposureMethod=true;Exposure->Settings.AutoExposureMethod=AEM_Manual;
 Exposure->Settings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Exposure->Settings.AutoExposureApplyPhysicalCameraExposure=false;
 Exposure->Settings.bOverride_AutoExposureBias=true;Exposure->Settings.AutoExposureBias=-13.f;
 GetWorld()->SpawnActor<ASkyAtmosphere>();
 auto* Sky=GetWorld()->SpawnActor<ASkyLight>();Sky->GetLightComponent()->SetRealTimeCaptureEnabled(true);
 if(!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))) {
  if(auto* Scenery=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Imported/CartoonScenery.CartoonScenery"))) {
   auto* SceneActor=GetWorld()->SpawnActor<AStaticMeshActor>();
   SceneActor->GetStaticMeshComponent()->SetStaticMesh(Scenery);
   SceneActor->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
  }
 }
 if(FParse::Param(FCommandLine::Get(),TEXT("LabTerrainCheck"))) {
 GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateLambda([this]() {
  auto Report=MakeShared<FJsonObject>();
  auto SaveReport=[Report]() {
   FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
   FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectDir()/TEXT("../results/unreal_terrain_check.json")));
   UE_LOG(LogTemp,Display,TEXT("TERRAIN_CHECK %s"),*Json);
  };
  auto* Terrain=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Imported/ValleCrop.ValleCrop"));
  if(Terrain) {
#if WITH_EDITOR
   // Fixed-time tests may finish before asynchronous static-mesh compilation does.
   TArray<UStaticMesh*> MeshesToFinish{Terrain};
   FStaticMeshCompilingManager::Get().FinishCompilation(MeshesToFinish);
#endif
   auto* Body=Terrain->GetBodySetup();
   Report->SetBoolField(TEXT("had_cooked_data_flag"),Body->bHasCookedCollisionData);
   Report->SetBoolField(TEXT("never_cook_flag"),Body->bNeverNeedsCookedCollisionData);
   Report->SetBoolField(TEXT("has_triangle_source"),Terrain->ContainsPhysicsTriMeshData(true));
   Body->CollisionTraceFlag=CTF_UseComplexAsSimple;Body->bDoubleSidedGeometry=true;
   Body->bHasCookedCollisionData=true;Body->bNeverNeedsCookedCollisionData=false;
   Body->InvalidatePhysicsData();
   Body->CreatePhysicsMeshesAsync(FOnAsyncPhysicsCookFinished::CreateLambda([this,Terrain,Report,SaveReport,Body](bool Success) {
   Report->SetBoolField(TEXT("async_collision_cook_success"),Success);
   Report->SetNumberField(TEXT("cooked_triangle_meshes"),Body->TriMeshGeometries.Num());
   Report->SetStringField(TEXT("collision_build_scale"),Body->BuildScale3D.ToString());
   if(Body->TriMeshGeometries.Num()) {
    auto ShapeBounds=Body->TriMeshGeometries[0]->BoundingBox();
    Report->SetStringField(TEXT("cooked_bounds_min_cm"),FVector(ShapeBounds.Min()).ToString());
    Report->SetStringField(TEXT("cooked_bounds_max_cm"),FVector(ShapeBounds.Max()).ToString());
   }
   FVector Origin(20000,20000,10000);
   auto* Actor=GetWorld()->SpawnActor<AStaticMeshActor>(Origin,FRotator::ZeroRotator);
   // This actor is spawned after BeginPlay: a Static component rejects SetStaticMesh.
   Actor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
   bool Assigned=Actor->GetStaticMeshComponent()->SetStaticMesh(Terrain);
   Report->SetBoolField(TEXT("mesh_assigned"),Assigned&&Actor->GetStaticMeshComponent()->GetStaticMesh()==Terrain);
   Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
   Actor->SetActorEnableCollision(true);
   Actor->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
   Actor->GetStaticMeshComponent()->SetCollisionResponseToAllChannels(ECR_Block);
   Actor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Static);
   Actor->GetStaticMeshComponent()->RecreatePhysicsState();
   Report->SetNumberField(TEXT("actor_x_cm"),Actor->GetActorLocation().X);
   Report->SetNumberField(TEXT("actor_y_cm"),Actor->GetActorLocation().Y);
   Report->SetNumberField(TEXT("actor_z_cm"),Actor->GetActorLocation().Z);
   // Scene queries must wait until the new body has entered the physics broadphase.
   FTimerHandle TerrainQueryDelay;
   GetWorld()->GetTimerManager().SetTimer(TerrainQueryDelay,FTimerDelegate::CreateLambda([this,Terrain,Report,SaveReport,Actor,Origin]() {
   auto* TerrainComponent=Actor->GetStaticMeshComponent();
   Report->SetBoolField(TEXT("component_registered"),TerrainComponent->IsRegistered());
   Report->SetBoolField(TEXT("physics_state_created"),TerrainComponent->IsPhysicsStateCreated());
   Report->SetBoolField(TEXT("valid_body_instance"),TerrainComponent->GetBodyInstance()->IsValidBodyInstance());
   FBox PhysicalBounds=TerrainComponent->GetBodyInstance()->GetBodyBounds();
   Report->SetStringField(TEXT("body_world_bounds_min_cm"),PhysicalBounds.Min.ToString());
   Report->SetStringField(TEXT("body_world_bounds_max_cm"),PhysicalBounds.Max.ToString());
   FHitResult CenterHit;FCollisionQueryParams CenterQuery;CenterQuery.bTraceComplex=true;
   bool CenterHitFound=false;
   if(PhysicalBounds.IsValid&&TerrainComponent->GetBodyInstance()->IsValidBodyInstance()) {
    auto Center=PhysicalBounds.GetCenter();
    CenterHitFound=TerrainComponent->LineTraceComponent(CenterHit,FVector(Center.X,Center.Y,PhysicalBounds.Max.Z+1000),FVector(Center.X,Center.Y,PhysicalBounds.Min.Z-1000),CenterQuery);
   }
   Report->SetBoolField(TEXT("body_center_ray_hit"),CenterHitFound);
   FString Data;TSharedPtr<FJsonObject> Samples;
   int Hits=0,ComponentHits=0,ReverseHits=0;double MaximumError=0,MinimumNormalZ=1;
   bool Loaded=FFileHelper::LoadFileToString(Data,*(FPaths::ProjectDir()/TEXT("../private/terrain/test_samples.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Data),Samples);
   Report->SetBoolField(TEXT("samples_loaded"),Loaded);
   if(Loaded) {
    Report->SetNumberField(TEXT("samples_read"),Samples->GetArrayField(TEXT("samples")).Num());
    for(const auto& Value:Samples->GetArrayField(TEXT("samples"))) {
     auto P=Value->AsObject();FVector Expected=Origin+FVector(P->GetNumberField(TEXT("x_cm")),P->GetNumberField(TEXT("y_cm")),P->GetNumberField(TEXT("z_cm")));
     FHitResult Hit;FCollisionQueryParams Query;Query.bTraceComplex=true;
     FHitResult Direct,Reverse;
     if(Actor->GetStaticMeshComponent()->LineTraceComponent(Direct,FVector(Expected.X,Expected.Y,20000),FVector(Expected.X,Expected.Y,5000),Query)) ++ComponentHits;
     if(GetWorld()->LineTraceSingleByChannel(Reverse,FVector(Expected.X,Expected.Y,5000),FVector(Expected.X,Expected.Y,20000),ECC_Visibility,Query)) ++ReverseHits;
     if(GetWorld()->LineTraceSingleByChannel(Hit,FVector(Expected.X,Expected.Y,20000),FVector(Expected.X,Expected.Y,5000),ECC_Visibility,Query)) {
      ++Hits;MaximumError=FMath::Max(MaximumError,FMath::Abs(Hit.ImpactPoint.Z-Expected.Z));MinimumNormalZ=FMath::Min(MinimumNormalZ,Hit.ImpactNormal.Z);
     }
    }
   }
   auto Bounds=Terrain->GetBounds();
   Report->SetNumberField(TEXT("ray_hits"),Hits);Report->SetNumberField(TEXT("ray_expected"),9);
   Report->SetNumberField(TEXT("component_ray_hits"),ComponentHits);Report->SetNumberField(TEXT("reverse_ray_hits"),ReverseHits);
   Report->SetBoolField(TEXT("actor_collision_enabled"),Actor->GetActorEnableCollision());
   Report->SetNumberField(TEXT("visibility_response"),Actor->GetStaticMeshComponent()->GetCollisionResponseToChannel(ECC_Visibility));
   Report->SetNumberField(TEXT("max_height_error_cm"),MaximumError);Report->SetNumberField(TEXT("minimum_up_normal_dot"),MinimumNormalZ);
   Report->SetNumberField(TEXT("extent_x_m"),Bounds.BoxExtent.X*2/100);Report->SetNumberField(TEXT("extent_y_m"),Bounds.BoxExtent.Y*2/100);
   Report->SetNumberField(TEXT("height_range_m"),Bounds.BoxExtent.Z*2/100);Report->SetNumberField(TEXT("render_lods"),Terrain->GetNumLODs());
   Report->SetBoolField(TEXT("passed"),Hits==9&&MaximumError<0.1&&MinimumNormalZ>0);
   Report->SetStringField(TEXT("axes"),TEXT("UE X east,Y south,Z up; original ellipsoidal datum retained"));
   Report->SetBoolField(TEXT("road_surface_verified"),false);
   SaveReport();
   }),0.1f,false);
   }));
  } else {Report->SetBoolField(TEXT("passed"),false);SaveReport();}
 }));
 }
}
