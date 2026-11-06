#include "LabVehicle.h"
#include "Camera/CameraComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "HAL/PlatformTime.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

void ALabVehicle::TickInputCheck(float Delta) {
 InputCheckClock+=Delta;
 auto* View=GetWorld()->GetGameViewport();
 if(!View||!View->Viewport){InputCheckResults.Add(TEXT("viewport_available"),false);if(InputCheckClock>5)QuitGame();return;}
 if(InputInitialWindowMode<0)InputInitialWindowMode=int32(View->Viewport->GetWindowMode());
 struct FKeyStep {double Time;FKey Key;EInputEvent Event;};
 const FKeyStep Events[]={
  {3,EKeys::W,IE_Pressed},{4.2,EKeys::W,IE_Released},{4.2,EKeys::SpaceBar,IE_Pressed},
  {6.2,EKeys::SpaceBar,IE_Released},{6.2,EKeys::S,IE_Pressed},{7.4,EKeys::S,IE_Released},{7.4,EKeys::SpaceBar,IE_Pressed},
  {9.5,EKeys::A,IE_Pressed},{11,EKeys::A,IE_Released},{11,EKeys::D,IE_Pressed},{12.5,EKeys::D,IE_Released},
  {13,EKeys::C,IE_Pressed},{13.05,EKeys::C,IE_Released},{14,EKeys::C,IE_Pressed},{14.05,EKeys::C,IE_Released},
  {15,EKeys::C,IE_Pressed},{15.05,EKeys::C,IE_Released},{16,EKeys::R,IE_Pressed},{16.05,EKeys::R,IE_Released},
  {19,EKeys::F11,IE_Pressed},{19.1,EKeys::F11,IE_Released},{20.5,EKeys::F11,IE_Pressed},{20.6,EKeys::F11,IE_Released},
  {21.4,EKeys::Up,IE_Pressed},{21.65,EKeys::Up,IE_Released},
  {21.7,EKeys::Down,IE_Pressed},{21.95,EKeys::Down,IE_Released},
  {22,EKeys::Left,IE_Pressed},{22.25,EKeys::Left,IE_Released},
  {22.3,EKeys::Right,IE_Pressed},{22.55,EKeys::Right,IE_Released},
  {23,EKeys::Escape,IE_Pressed}
 };
 // Extra settling time for the fully loaded car on a real grade; retain the
 // same keys, forces and thresholds, requiring a sustained stationary interval.
 auto Scheduled=[](double Time){return Time+(Time>=6.2?1.:0.)+(Time>=19?1.:0.);};
 InputExpectedEvents=UE_ARRAY_COUNT(Events);
 while(InputEventIndex<UE_ARRAY_COUNT(Events)&&InputCheckClock>=Scheduled(Events[InputEventIndex].Time)) {
  const auto& E=Events[InputEventIndex++];
  if(E.Key==EKeys::Escape)bCompleted=true;
  // The stop must be proven before applying reverse. Inspect the accumulated
  // hold at this actual transition, not an arbitrary earlier sample time.
  if(E.Key==EKeys::S&&E.Event==IE_Pressed) {
   InputBrakeCheckClock=InputCheckClock;InputBrakeHoldAtCheck=InputBrakeStationarySeconds;
   InputCheckResults.Add(TEXT("space_brakes_and_stops"),InputBrakeHoldAtCheck>=.25);
  }
  View->InputKey(FInputKeyEventArgs(View->Viewport,IPlatformInputDeviceMapper::Get().GetDefaultInputDevice(),E.Key,E.Event,FPlatformTime::Cycles64()));
 }
 auto Check=[&](const TCHAR* Name,double Time,bool Value){if(InputCheckClock>=Time&&!InputCheckResults.Contains(Name))InputCheckResults.Add(Name,Value);};
 const double SignedSpeed=GetMesh()->GetPhysicsLinearVelocity().Dot(GetActorForwardVector())/100;
 auto* Movement=CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
 const double Angle=FMath::DegreesToRadians(Movement->Wheels[0]->GetSteerAngle());
 Check(TEXT("W_accelerates_forward"),4,Gas>.9&&SignedSpeed>.3);
 const bool Stationary=GetMesh()->GetPhysicsLinearVelocity().Size()<12;
 if(InputCheckClock>=4.2&&InputCheckClock<Scheduled(6.2))
  InputBrakeStationarySeconds=Braking>.9&&Stationary?InputBrakeStationarySeconds+Delta:0;
 Check(TEXT("S_accelerates_reverse"),Scheduled(7.2),Gas<-.9&&SignedSpeed<-.3);
 Check(TEXT("A_steers_left"),Scheduled(10.7),Steering<-.9&&Angle<-.4);
 Check(TEXT("D_steers_right"),Scheduled(12.3),Steering>.9&&Angle>.4);
 const TCHAR* CameraNames[]={TEXT("external"),TEXT("cabin"),TEXT("coffa")};
 for(int32 I=0;I<3;++I) {
  const int32 Expected=(I+1)%3;const FString Name=TEXT("C_camera_")+FString(CameraNames[Expected]);
  if(InputCheckClock>=Scheduled(13.5+I)&&!InputCheckResults.Contains(Name)) {
   int32 Active=0;for(const auto& Camera:Cameras)Active+=Camera->IsActive()?1:0;
   InputCheckResults.Add(Name,CameraIndex==Expected&&Cameras[Expected]->IsActive()&&Active==1);
   if(!FParse::Param(FCommandLine::Get(),TEXT("nullrhi"))){FString Folder=FPaths::ProjectSavedDir()/TEXT("Telemetry");FParse::Value(FCommandLine::Get(),TEXT("LabOutput="),Folder);FScreenshotRequest::RequestScreenshot(Folder/(RunId+TEXT("_camera_")+CameraNames[Expected]+TEXT(".png")),false,false);}
  }
 }
 Check(TEXT("R_returns_to_start"),Scheduled(17.5),ResetCount==1&&FVector::Dist2D(GetActorLocation(),RespawnTransform.GetLocation())<20);
 int32 Contacts=0;for(int32 I=0;I<Movement->GetNumWheels();++I)Contacts+=Movement->GetWheelState(I).bInContact?1:0;
 if(InputCheckClock>=Scheduled(16)&&InputCheckClock<Scheduled(20.5))
  InputResetStationarySeconds=ResetCount==1&&Contacts==4&&Stationary&&GetActorUpVector().Z>.9?InputResetStationarySeconds+Delta:0;
 // Evaluate on the same shifted schedule as the key sequence, before the
 // second F11. Record the value at the decision rather than the later total.
 if(InputCheckClock>=Scheduled(20.3)&&!InputCheckResults.Contains(TEXT("reset_settles_on_four_wheels"))) {
  InputResetCheckClock=InputCheckClock;InputResetHoldAtCheck=InputResetStationarySeconds;
  Check(TEXT("reset_settles_on_four_wheels"),Scheduled(20.3),InputResetHoldAtCheck>=.25);
 }
 Check(TEXT("F11_changes_window_mode"),Scheduled(20),int32(View->Viewport->GetWindowMode())!=InputInitialWindowMode);
 Check(TEXT("F11_restores_window_mode"),Scheduled(21.3),int32(View->Viewport->GetWindowMode())==InputInitialWindowMode);
 Check(TEXT("up_arrow_binding"),Scheduled(21.55),Gas>.9);
 Check(TEXT("down_arrow_binding"),Scheduled(21.85),Gas<-.9);
 Check(TEXT("left_arrow_binding"),Scheduled(22.15),Steering<-.9);
 Check(TEXT("right_arrow_binding"),Scheduled(22.45),Steering>.9);
 if(InputCheckClock>28){InputCheckResults.Add(TEXT("Escape_binding_timed_out"),false);QuitGame();}
}

void ALabVehicle::SaveInputCheck(const FString& Folder) {
 if(!bInputCheck)return;
 InputCheckResults.Add(TEXT("Escape_quit_binding"),bInputQuitObserved&&InputCheckClock<28);
 InputCheckResults.Add(TEXT("completed_key_sequence"),InputExpectedEvents>0&&InputEventIndex==InputExpectedEvents&&InputCheckClock>=25);
 auto R=MakeShared<FJsonObject>();auto Checks=MakeShared<FJsonObject>();bool Passed=true;
 for(const auto& Item:InputCheckResults){Checks->SetBoolField(Item.Key,Item.Value);Passed&=Item.Value;}
 R->SetObjectField(TEXT("checks"),Checks);R->SetBoolField(TEXT("passed"),Passed&&InputCheckResults.Num()>=18);
 R->SetStringField(TEXT("method"),TEXT("Key press/release events through the actual GameViewport input path and configured bindings; no direct calls to throttle, brake, steering, camera or reset handlers"));
 R->SetNumberField(TEXT("game_seconds"),InputCheckClock);R->SetNumberField(TEXT("key_events_sent"),InputEventIndex);
 R->SetNumberField(TEXT("minimum_stationary_hold_s"),.25);
 R->SetNumberField(TEXT("brake_stationary_hold_s"),InputBrakeStationarySeconds);
 R->SetNumberField(TEXT("brake_check_clock_s"),InputBrakeCheckClock);
 R->SetNumberField(TEXT("brake_stationary_hold_at_check_s"),InputBrakeHoldAtCheck);
 R->SetNumberField(TEXT("reset_stationary_hold_s"),InputResetStationarySeconds);
 R->SetNumberField(TEXT("reset_check_clock_s"),InputResetCheckClock);
 R->SetNumberField(TEXT("reset_stationary_hold_at_check_s"),InputResetHoldAtCheck);
 R->SetBoolField(TEXT("camera_visibility_reviewed"),false);R->SetBoolField(TEXT("full_lap_verified"),false);
 FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
 FFileHelper::SaveStringToFile(Json,*(Folder/(RunId+TEXT("_input.json"))),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
 UE_LOG(LogTemp,Display,TEXT("LAB_INPUT_CHECK %s"),*Json);
}
