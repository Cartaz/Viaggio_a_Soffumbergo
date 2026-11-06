#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "CircuitDrivePilot.generated.h"

struct FCircuitDrivePhase {
 FString Name;
 TArray<FVector> Points;
 TArray<double> Station;
 TArray<double> Yaws,Steers;
 double InitialSteer=0;
 int32 Direction=1;
 bool bManeuver=false;
};

/** Diagnostic driver: outputs the same throttle, brake and steering as input.
 * No vehicle transforms, velocities, balance forces or recoveries are assigned.
 */
UCLASS()
class UCircuitDrivePilot : public UObject {
 GENERATED_BODY()
public:
 bool Initialize();
 bool Control(class ALabVehicle* Vehicle,float Delta,float& Gas,float& Brake,float& Steering);
 void Save(const FString& Folder,const FString& RunId,int32 Resets,int32 TerrainWaits);
 bool Passed() const {return bFinished&&!bFailed;}
private:
 void Fail(const FString& Reason);
 void Advance();
 TArray<FCircuitDrivePhase> Phases;
 FString BuildId,Failure,ProgressCsv,ItinerarySHA1;
 int32 PhaseIndex=0,Segment=0,CompletedManeuvers=0;
 double Clock=0,Progress=0,PhaseStart=0,Pause=2,LastProgressTime=0,LastProgress=0;
 double Integral=0,LogClock=0,SampleClock=0,NoContact=0,MaxNoContact=0;
 double SurfaceClock=0,OffSurfaceTime=0,MaxOffSurfaceTime=0;
 int32 DriveSurfaceWheels=4;
 int32 TestStop=-1;
 double RearOffsetCm=123,WheelbaseCm=256;
 bool bLayoutMeasured=false;
 double MaxCrossTrack=0,DrivenMetres=0,LastStepMetres=0,DistanceLimit=0,SpeedLimit=7;
 FVector PreviousPosition=FVector::ZeroVector;
 bool bHavePrevious=false,bFailed=false,bFinished=false,bPartial=false;
 bool bTestDeparture=false;
};
