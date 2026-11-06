#pragma once
#include "CoreMinimal.h"
#include "Misc/FileHelper.h"
#include "Misc/SecureHash.h"

/** Identity of the actual bytes loaded, including data staged inside a pak. */
inline FString CircuitFileSHA1(const FString& Path) {
 TArray<uint8> Bytes;
 if(!FFileHelper::LoadFileToArray(Bytes,*Path))return FString();
 return FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num()).ToString().ToLower();
}
