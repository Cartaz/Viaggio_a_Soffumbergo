#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "SoffumbergoCompanionMouse.generated.h"

class ASoffumbergoFootMouse;

/** Local-only following companion. Never teleports through walls or leaves the
 * native Landscape to fake success. No NavigationMesh is assumed to exist.
 */
UCLASS()
class ASoffumbergoCompanionMouse : public ACharacter {
 GENERATED_BODY()
public:
 ASoffumbergoCompanionMouse();
 virtual void BeginPlay() override;
 virtual void Tick(float DeltaTime) override;
 void Follow(ASoffumbergoFootMouse* InLeader);
 bool HasLeader(const ASoffumbergoFootMouse* Expected) const {
  return Leader.Get()==Expected;
 }
private:
 UPROPERTY() TWeakObjectPtr<ASoffumbergoFootMouse> Leader;
 bool bReportedMissingLeader=false;
};
