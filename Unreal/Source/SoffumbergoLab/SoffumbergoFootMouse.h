#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "SoffumbergoFootMouse.generated.h"

class ALabVehicle;
class UCameraComponent;
class USpringArmComponent;

/** Source-only walking prototype: an existing mouse mesh at mouse proportions.
 * Does not change the native Yaris, road, terrain, or mapped buildings.
 */
UCLASS()
class ASoffumbergoFootMouse : public ACharacter {
 GENERATED_BODY()
public:
 ASoffumbergoFootMouse();
 void SetParkedVehicle(ALabVehicle* InVehicle);
 /** AController::Possess may replace AActor::Owner, so link explicitly. */
 bool IsAssociatedWith(const ALabVehicle* InVehicle) const { return ParkedVehicle.Get()==InVehicle; }
 virtual void BeginPlay() override;
 virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
private:
 void WalkForward(float Value);
 void WalkRight(float Value);
 void Turn(float Value);
 void LookUp(float Value);
 void TryReenterVehicle();
 void QuitGame();
 UPROPERTY() TObjectPtr<USpringArmComponent> CameraArm;
 UPROPERTY() TObjectPtr<UCameraComponent> ThirdPersonCamera;
 UPROPERTY() TWeakObjectPtr<ALabVehicle> ParkedVehicle;
};
