#include "CircuitDrivePilot.h"
#include "CircuitDataSignature.h"
#include "LabVehicle.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace {
FVector ReadPoint(const TSharedPtr<FJsonValue>& V) {
 const auto& A=V->AsArray();return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A.Num()>2?A[2]->AsNumber():0);
}
void CompletePhase(FCircuitDrivePhase& P) {
 P.Station.Add(0);
 for(int32 I=1;I<P.Points.Num();++I)P.Station.Add(P.Station.Last()+FVector::Dist2D(P.Points[I],P.Points[I-1]));
}
FVector AtStation(const FCircuitDrivePhase& P,double S) {
 for(int32 I=1;I<P.Station.Num();++I)if(S<=P.Station[I])return FMath::Lerp(P.Points[I-1],P.Points[I],FMath::Clamp((S-P.Station[I-1])/FMath::Max(.001,P.Station[I]-P.Station[I-1]),0.,1.));
 return P.Points.Last();
}
}

bool UCircuitDrivePilot::Initialize() {
 FParse::Value(FCommandLine::Get(),TEXT("CircuitDistanceLimit="),DistanceLimit);
 FParse::Value(FCommandLine::Get(),TEXT("CircuitSpeed="),SpeedLimit);
 FParse::Value(FCommandLine::Get(),TEXT("CircuitTestStop="),TestStop);
 const bool ApproachTest=FParse::Param(FCommandLine::Get(),TEXT("CircuitTestApproach"));
 bTestDeparture=FParse::Param(FCommandLine::Get(),TEXT("CircuitTestDeparture"));
 FString Json;TSharedPtr<FJsonObject> Data;
 if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("Data/circuit_itinerary.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Data)){Fail(TEXT("missing_itinerary"));return false;}
 BuildId=Data->GetStringField(TEXT("build_id"));
 ItinerarySHA1=CircuitFileSHA1(FPaths::ProjectContentDir()/TEXT("Data/circuit_itinerary.json"));
 TArray<FVector> Route;for(const auto& V:Data->GetArrayField(TEXT("points_cm")))Route.Add(ReadPoint(V));
 const TArray<TSharedPtr<FJsonValue>>* Turns=nullptr;
 if(!Data->TryGetArrayField(TEXT("maneuvers"),Turns)||Turns->Num()!=3){Fail(TEXT("missing_three_maneuver_plans"));return false;}
 int32 Start=0,StopOrdinal=0,StartingPhase=-1;
 for(const auto& Value:*Turns) {
  const auto Turn=Value->AsObject();const int32 Stop=Turn->GetIntegerField(TEXT("index"));
  FCircuitDrivePhase Main;Main.Name=TEXT("Road_to_")+Turn->GetStringField(TEXT("name"));
  const int32 MainStart=(StopOrdinal==TestStop&&ApproachTest)?FMath::Max(Start,Stop-20):Start;
  for(int32 I=MainStart;I<=Stop;++I)Main.Points.Add(Route[I]);CompletePhase(Main);Phases.Add(MoveTemp(Main));
  if(StopOrdinal==TestStop)StartingPhase=Phases.Num()-(ApproachTest?1:0);++StopOrdinal;
  const auto& Poses=Turn->GetArrayField(TEXT("poses"));
  int32 First=0,Direction=Poses[1]->AsObject()->GetIntegerField(TEXT("direction"));
  auto AddTurnPhase=[&](int32 Last) {
   if(Last<=First)return;
   FCircuitDrivePhase P;P.Name=TEXT("Turn_")+Turn->GetStringField(TEXT("name"));P.Direction=Direction;P.bManeuver=true;
   P.InitialSteer=Poses[FMath::Min(First+1,Last)]->AsObject()->GetNumberField(TEXT("steering_rad"));
   for(int32 I=First;I<=Last;++I){const auto Pose=Poses[I]->AsObject();P.Points.Add(ReadPoint(Pose->GetField<EJson::Array>(TEXT("rear_cm"))));P.Yaws.Add(Pose->GetNumberField(TEXT("yaw_rad")));P.Steers.Add(Pose->GetNumberField(TEXT("steering_rad")));}
   CompletePhase(P);Phases.Add(MoveTemp(P));
  };
  for(int32 I=1;I<Poses.Num();++I) {
   const int32 Next=Poses[I]->AsObject()->GetIntegerField(TEXT("direction"));
   if(Next!=Direction){AddTurnPhase(I-1);First=I-1;Direction=Next;}
  }
  AddTurnPhase(Poses.Num()-1);Start=Stop;
 }
 FCircuitDrivePhase End;End.Name=TEXT("Road_to_finish");for(int32 I=Start;I<Route.Num();++I)End.Points.Add(Route[I]);CompletePhase(End);Phases.Add(MoveTemp(End));
 if(TestStop>=0){if(StartingPhase<0){Fail(TEXT("invalid_test_stop"));return false;}PhaseIndex=StartingPhase;bPartial=true;}
 ProgressCsv=TEXT("time_s,phase,phase_name,direction,x_cm,y_cm,z_cm,phase_station_m,driven_m,speed_m_s,target_m_s,cross_track_m,throttle,brake,steering,contacts,up_z,drive_surface_wheels,actual_yaw_rad,planned_yaw_rad,feedforward_steer_rad,lateral_error_m\n");
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_DRIVE initialized phases=%d build=%s route_m=%g"),Phases.Num(),*BuildId,Data->GetNumberField(TEXT("route_length_m")));
 return true;
}

void UCircuitDrivePilot::Fail(const FString& Reason){bFailed=true;Failure=Reason;UE_LOG(LogTemp,Error,TEXT("CIRCUIT_DRIVE failed phase=%d reason=%s"),PhaseIndex,*Reason);}
void UCircuitDrivePilot::Advance() {
 const bool WasTurn=Phases[PhaseIndex].bManeuver;
 ++PhaseIndex;
 if(WasTurn&&(PhaseIndex==Phases.Num()||!Phases[PhaseIndex].bManeuver)){++CompletedManeuvers;if(TestStop>=0&&!bTestDeparture)bFinished=true;}
 Progress=0;Segment=0;Integral=0;Pause=1.2;PhaseStart=LastProgressTime=Clock;LastProgress=0;
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_DRIVE phase=%d/%d driven_m=%g maneuvers=%d"),PhaseIndex,Phases.Num(),DrivenMetres,CompletedManeuvers);
 if(PhaseIndex==Phases.Num())bFinished=true;
}

bool UCircuitDrivePilot::Control(ALabVehicle* Vehicle,float Delta,float& Gas,float& Brake,float& Steering) {
 Clock+=Delta;Gas=0;Brake=1;Steering=0;
 if(bFailed||bFinished)return true;
 const FVector Root=Vehicle->GetActorLocation(),Forward=Vehicle->GetActorForwardVector(),Right=Vehicle->GetActorRightVector();
 const double Speed=Vehicle->GetMesh()->GetPhysicsLinearVelocity().Size()/100;
 if(bHavePrevious){LastStepMetres=FVector::Dist2D(Root,PreviousPosition)/100;DrivenMetres+=LastStepMetres;}PreviousPosition=Root;bHavePrevious=true;
 auto* Movement=CastChecked<UChaosWheeledVehicleMovementComponent>(Vehicle->GetVehicleMovement());
 if(!bLayoutMeasured) {
  const FTransform Transform=Vehicle->GetMesh()->GetComponentTransform();double Front=0,Back=0;
  for(int32 I=0;I<4;++I){const FVector P=Transform.InverseTransformPosition(Vehicle->GetMesh()->GetBoneLocation(Movement->WheelSetups[I].BoneName));if(I<2)Front+=P.X*.5;else Back+=P.X*.5;}
  RearOffsetCm=-Back;WheelbaseCm=Front-Back;bLayoutMeasured=true;
  UE_LOG(LogTemp,Display,TEXT("CIRCUIT_DRIVE wheel_layout wheelbase_cm=%g rear_offset_cm=%g"),WheelbaseCm,RearOffsetCm);
  if(WheelbaseCm<200||WheelbaseCm>320||RearOffsetCm<80||RearOffsetCm>180){Fail(TEXT("unexpected_wheel_layout"));return true;}
 }
 int32 Contacts=0;for(int32 I=0;I<Movement->GetNumWheels();++I)Contacts+=Movement->GetWheelState(I).bInContact?1:0;
 if(Clock>3) {
  NoContact=Contacts==0?NoContact+Delta:0;MaxNoContact=FMath::Max(MaxNoContact,NoContact);
  if(NoContact>.5){Fail(TEXT("airborne"));return true;}
  if(Vehicle->GetActorUpVector().Z<.35){Fail(TEXT("tipped"));return true;}
  SurfaceClock+=Delta;
  if(SurfaceClock>=.1) {
   DriveSurfaceWheels=0;FCollisionQueryParams Query;Query.AddIgnoredActor(Vehicle);
   for(int32 I=0;I<Movement->WheelSetups.Num();++I) {
    const FVector At=Vehicle->GetMesh()->GetBoneLocation(Movement->WheelSetups[I].BoneName);
    FHitResult Hit;
    if(Vehicle->GetWorld()->LineTraceSingleByChannel(Hit,At+FVector(0,0,80),At-FVector(0,0,200),ECC_WorldStatic,Query)&&Hit.GetActor()&&
       (Hit.GetActor()->ActorHasTag(TEXT("RoadSurface"))||Hit.GetActor()->ActorHasTag(TEXT("RoadShoulder"))))++DriveSurfaceWheels;
   }
   OffSurfaceTime=DriveSurfaceWheels<3?OffSurfaceTime+SurfaceClock:0;
   MaxOffSurfaceTime=FMath::Max(MaxOffSurfaceTime,OffSurfaceTime);SurfaceClock=0;
   if(OffSurfaceTime>.75){Fail(TEXT("left_built_driving_surface"));return true;}
  }
 }
 auto& P=Phases[PhaseIndex];
 constexpr double SteeringCap=.506145483;
 if(Pause>0) {Steering=FMath::Clamp(P.InitialSteer/SteeringCap,-1.,1.);if(Speed<.06)Pause-=Delta;return false;}
 const FVector Rear=Root-Forward*RearOffsetCm;
 const FVector Ref=P.bManeuver?Rear:Root;
 double Best=DBL_MAX,Along=Progress;FVector Closest=Ref;
 const int32 PreviousSegment=Segment;
 for(int32 I=FMath::Max(0,PreviousSegment-2);I<FMath::Min(P.Points.Num()-1,PreviousSegment+10);++I) {
  const FVector A=P.Points[I],D=P.Points[I+1]-A;const double Den=D.X*D.X+D.Y*D.Y;
  const double T=FMath::Clamp(((Ref.X-A.X)*D.X+(Ref.Y-A.Y)*D.Y)/FMath::Max(Den,.001),0.,1.);
  const FVector Q=A+D*T;const double Dist=FVector::DistSquared2D(Ref,Q);
  if(Dist<Best){Best=Dist;Along=P.Station[I]+(P.Station[I+1]-P.Station[I])*T;Segment=I;Closest=Q;}
 }
 Progress=FMath::Max(Progress,Along);const double Cross=FMath::Sqrt(Best)/100;MaxCrossTrack=FMath::Max(MaxCrossTrack,Cross);
 if(Progress>LastProgress+10){LastProgress=Progress;LastProgressTime=Clock;}
 if(Clock-LastProgressTime>30){Fail(TEXT("stalled"));return true;}
 // GIS vertices form sharp corners which the car rounds physically. Main-road
 // containment is checked at the four actual wheel positions against the built
 // asphalt/shoulders above, rather than rejecting a valid turn on a V-shaped axis.
 if(P.bManeuver&&Cross>1.1){Fail(TEXT("left_planned_maneuver"));return true;}
 const double Remaining=(P.Station.Last()-Progress)/100;
 const double LookAhead=P.bManeuver?75:Remaining<10?200:FMath::Clamp(700+Speed*25,700.,1000.);
 // Pure pursuit tracks from the rear axle. At a sharp corner the body origin
 // can project onto the outgoing segment while the rear axle is still on the
 // incoming one; using body progress then skips ahead and opens the turn.
 double TrackingStation=Progress;
 if(!P.bManeuver) {
  double RearBest=DBL_MAX;
  for(int32 I=FMath::Max(0,Segment-4);I<FMath::Min(P.Points.Num()-1,Segment+10);++I) {
   const FVector A=P.Points[I],D=P.Points[I+1]-A;
   const double T=FMath::Clamp(((Rear.X-A.X)*D.X+(Rear.Y-A.Y)*D.Y)/FMath::Max(D.SizeSquared2D(),.001),0.,1.);
   const double Dist=FVector::DistSquared2D(Rear,A+D*T);
   if(Dist<RearBest){RearBest=Dist;TrackingStation=FMath::Lerp(P.Station[I],P.Station[I+1],T);}
  }
 }
 const FVector Target=AtStation(P,TrackingStation+LookAhead);FVector To=Target-Rear;To.Z=0;
 double DesiredAngle=FMath::Clamp(FMath::Atan2(2*WheelbaseCm*To.Dot(Right),FMath::Max(To.SizeSquared2D(),100.)),-SteeringCap,SteeringCap);
 double PlannedYaw=0,FeedforwardSteer=0,LateralError=0;
 if(P.bManeuver) {
  const double Alpha=FMath::Clamp((Progress-P.Station[Segment])/FMath::Max(1.,P.Station[Segment+1]-P.Station[Segment]),0.,1.);
  const double Yaw=P.Yaws[Segment]+FMath::FindDeltaAngleRadians(P.Yaws[Segment],P.Yaws[Segment+1])*Alpha;
  const double HeadingError=FMath::FindDeltaAngleRadians(FMath::DegreesToRadians(Vehicle->GetActorRotation().Yaw),Yaw);
  PlannedYaw=Yaw;FeedforwardSteer=P.Steers[Segment+1];
  // Maneuver paths store planar points. Their placeholder Z=0 must not enter
  // steering feedback through chassis roll at this world's negative altitude.
  LateralError=((Closest.X-Ref.X)*Right.X+(Closest.Y-Ref.Y)*Right.Y)/100;
  DesiredAngle=FMath::Clamp(FeedforwardSteer+P.Direction*1.3*HeadingError+.35*LateralError,-SteeringCap,SteeringCap);
 }
 Steering=DesiredAngle/SteeringCap;
 double TargetSpeed=P.bManeuver?.45:SpeedLimit;
 if(!P.bManeuver&&Remaining<10)TargetSpeed=FMath::Min(TargetSpeed,.65);
 if(!P.bManeuver) {
  const double SteeringCurvature=FMath::Abs(FMath::Tan(DesiredAngle))/2.56;
  TargetSpeed=FMath::Min(TargetSpeed,FMath::Sqrt(1.6/FMath::Max(SteeringCurvature,.0001)));
  if(Cross>.5)TargetSpeed=FMath::Min(TargetSpeed,2.5);
 }
 if(!P.bManeuver) {
  for(int32 I=FMath::Max(1,Segment);I<FMath::Min(P.Points.Num()-1,Segment+18);++I) {
   const FVector A=P.Points[I]-P.Points[I-1],B=P.Points[I+1]-P.Points[I],C=P.Points[I+1]-P.Points[I-1];
   const double Den=A.Size2D()*B.Size2D()*C.Size2D();
   if(Den>1){const double Curvature=200*FMath::Abs(A.X*B.Y-A.Y*B.X)/Den;TargetSpeed=FMath::Min(TargetSpeed,FMath::Sqrt(1.6/FMath::Max(Curvature,.0001)));}
  }
 }
 TargetSpeed=FMath::Min(TargetSpeed,FMath::Sqrt(2*(P.bManeuver?.45:.8)*FMath::Max(0.,Remaining-.01)));
 if(Remaining<.025) {
  if(Speed<.06) {
   if(FVector::Dist2D(Ref,P.Points.Last())>25){Fail(TEXT("stop_position_missed"));return true;}
   Advance();
  }
  return bFinished;
 }
 const double SignedSpeed=Vehicle->GetMesh()->GetPhysicsLinearVelocity().Dot(Forward)*P.Direction/100;
 const double Error=TargetSpeed-SignedSpeed;Integral=FMath::Clamp(Integral+Error*Delta,-1.,1.);
 const double Feed=(1605*9.81*Forward.Z*P.Direction+120)/6500;
 const double Control=Feed+.42*Error+.12*Integral;
 Gas=P.Direction*FMath::Clamp(Control,0.,.85);Brake=FMath::Clamp(-Control*6500/16000,0.,1.);
 if(DistanceLimit>0&&DrivenMetres>=DistanceLimit){bPartial=true;bFinished=true;Brake=1;Gas=0;}
 SampleClock+=Delta;LogClock+=Delta;
 if(SampleClock>.1) {
  SampleClock=0;
  ProgressCsv+=FString::Printf(TEXT("%.6g,%d,%s,%d,%.9g,%.9g,%.9g,%.7g,%.7g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%d,%.6g,%d,%.9g,%.9g,%.9g,%.9g\n"),Clock,PhaseIndex,*P.Name,P.Direction,Root.X,Root.Y,Root.Z,Progress/100,DrivenMetres,Speed,TargetSpeed,Cross,Gas,Brake,Steering,Contacts,Vehicle->GetActorUpVector().Z,DriveSurfaceWheels,FMath::DegreesToRadians(Vehicle->GetActorRotation().Yaw),PlannedYaw,FeedforwardSteer,LateralError);
 }
 if(LogClock>20){LogClock=0;UE_LOG(LogTemp,Display,TEXT("CIRCUIT_DRIVE progress phase=%d name=%s stage_m=%g/%g driven_m=%g speed=%g cross=%g"),PhaseIndex,*P.Name,Progress/100,P.Station.Last()/100,DrivenMetres,Speed,Cross);}
 return bFailed||bFinished;
}

void UCircuitDrivePilot::Save(const FString& Folder,const FString& RunId,int32 Resets,int32 TerrainWaits) {
 auto R=MakeShared<FJsonObject>();
 R->SetBoolField(TEXT("passed"),Passed()&&!bPartial&&CompletedManeuvers==3&&Resets==0&&TerrainWaits<=1);
 R->SetBoolField(TEXT("finished"),bFinished);R->SetBoolField(TEXT("partial_diagnostic"),bPartial);R->SetBoolField(TEXT("failed"),bFailed);
 R->SetStringField(TEXT("failure"),Failure);R->SetStringField(TEXT("build_id"),BuildId);
 R->SetStringField(TEXT("itinerary_sha1"),ItinerarySHA1);
 R->SetNumberField(TEXT("phase"),PhaseIndex);R->SetNumberField(TEXT("expected_phases"),Phases.Num());
 R->SetNumberField(TEXT("maneuvers_completed"),CompletedManeuvers);R->SetNumberField(TEXT("driven_m"),DrivenMetres);R->SetNumberField(TEXT("game_seconds"),Clock);
 R->SetNumberField(TEXT("max_cross_track_m"),MaxCrossTrack);R->SetNumberField(TEXT("max_no_contact_seconds"),MaxNoContact);
 R->SetNumberField(TEXT("max_off_driving_surface_seconds"),MaxOffSurfaceTime);
 R->SetNumberField(TEXT("user_resets"),Resets);R->SetNumberField(TEXT("terrain_waits"),TerrainWaits);
 R->SetNumberField(TEXT("test_stop"),TestStop);R->SetNumberField(TEXT("wheelbase_cm"),WheelbaseCm);R->SetNumberField(TEXT("rear_axle_offset_cm"),RearOffsetCm);
 R->SetBoolField(TEXT("test_departure"),bTestDeparture);
 R->SetStringField(TEXT("method"),TEXT("Throttle, brake and steering inputs only; actual Chaos Yaris; no poses, velocity assignments or recovery from this driver"));
 FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
 FFileHelper::SaveStringToFile(Json,*(Folder/(RunId+TEXT("_drive.json"))));FFileHelper::SaveStringToFile(ProgressCsv,*(Folder/(RunId+TEXT("_drive.csv"))),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_DRIVE_RESULT %s"),*Json);
}
