#include "LidarTerrainLibrary.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "MeshDescriptionBuilder.h"
#include "StaticMeshCompiler.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/PackageName.h"
#include "AssetRegistry/AssetRegistryModule.h"

namespace {
struct FFoliageMesh {
 FMeshDescription Mesh;
 FMeshDescriptionBuilder Builder;
 FPolygonGroupID Bark,Leaf;
 FFoliageMesh() {
  FStaticMeshAttributes Attributes(Mesh);Attributes.Register();
  Builder.SetMeshDescription(&Mesh);Builder.EnablePolyGroups();Builder.SetNumUVLayers(1);
  Bark=Builder.AppendPolygonGroup(TEXT("Bark"));Leaf=Builder.AppendPolygonGroup(TEXT("Leaf"));
 }
 void Tri(FVector A,FVector B,FVector C,FPolygonGroupID Group) {
  const FVector Normal=FVector::CrossProduct(B-A,C-A).GetSafeNormal();
  const FVector Positions[]={A,B,C};FVertexInstanceID Instances[3];
  for(int I=0;I<3;++I) {
   Instances[I]=Builder.AppendInstance(Builder.AppendVertex(Positions[I]));
   Builder.SetInstanceNormal(Instances[I],Normal);
   Builder.SetInstanceUV(Instances[I],FVector2D(Positions[I].X,Positions[I].Z)/100);
  }
  Builder.AppendTriangle(Instances[0],Instances[1],Instances[2],Group);
 }
 void Tube(FVector A,FVector B,double R0,double R1,int Sides) {
  const FVector Axis=(B-A).GetSafeNormal();FVector U,V;Axis.FindBestAxisVectors(U,V);
  for(int I=0;I<Sides;++I) {
   const double P0=I*2*PI/Sides,P1=(I+1)*2*PI/Sides;
   const FVector N0=U*FMath::Cos(P0)+V*FMath::Sin(P0),N1=U*FMath::Cos(P1)+V*FMath::Sin(P1);
   const FVector A0=A+N0*R0,A1=A+N1*R0,B0=B+N0*R1,B1=B+N1*R1;
   Tri(A0,A1,B0,Bark);Tri(A1,B1,B0,Bark);
  }
 }
 void Blade(FVector Centre,FVector Direction,FVector Side,double Length,double Width) {
  const FVector Tip=Centre+Direction*Length;
  const FVector Mid=Centre+Direction*Length*0.48+FVector(0,0,Width*0.25);
  const FVector Left=Centre+Direction*Length*0.40+Side*Width;
  const FVector Right=Centre+Direction*Length*0.40-Side*Width;
  Tri(Centre,Left,Mid,Leaf);Tri(Left,Tip,Mid,Leaf);
  Tri(Centre,Mid,Right,Leaf);Tri(Mid,Tip,Right,Leaf);
 }
};
}

UStaticMesh* ULidarTerrainLibrary::CreateProceduralFoliage(const FString& AssetPath,int32 Seed,int32 Kind,bool WithTrunkCollision) {
 if(!AssetPath.StartsWith(TEXT("/Game/Vegetation/"))||Kind<0||Kind>2) return nullptr;
 if(auto* Existing=LoadObject<UStaticMesh>(nullptr,*AssetPath)) return Existing;
 UPackage* Package=CreatePackage(*AssetPath);
 auto* Asset=NewObject<UStaticMesh>(Package,*FPackageName::GetLongPackageAssetName(AssetPath),RF_Public|RF_Standalone);
 auto* Bark=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Vegetation/M_Bark.M_Bark"));
 auto* Leaf=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Vegetation/M_Leaf.M_Leaf"));
 Asset->GetStaticMaterials().Add(FStaticMaterial(Bark,TEXT("Bark"),TEXT("Bark")));
 Asset->GetStaticMaterials().Add(FStaticMaterial(Leaf,TEXT("Leaf"),TEXT("Leaf")));
 TArray<TUniquePtr<FFoliageMesh>> Lods;
 TArray<FVector> TrunkPoints;
 for(int Lod=0;Lod<3;++Lod) {
  auto& M=*Lods.Add_GetRef(MakeUnique<FFoliageMesh>());
  FRandomStream Random(Seed);
  if(Kind==2) {
   const int Blades=Lod==0?36:Lod==1?18:8;
   for(int I=0;I<Blades;++I) {
    const double A=Random.FRandRange(0,2*PI),Radius=Random.FRandRange(0,22);
    const FVector Centre(FMath::Cos(A)*Radius,FMath::Sin(A)*Radius,0);
    const FVector Dir(FMath::Cos(A)*0.35,FMath::Sin(A)*0.35,1);
    M.Blade(Centre,Dir.GetSafeNormal(),FVector(-FMath::Sin(A),FMath::Cos(A),0),Random.FRandRange(22,55),Lod==2?5:2.5);
   }
  } else {
   const double Height=Kind==0?Random.FRandRange(850,1200):Random.FRandRange(110,190);
   const double Radius=Kind==0?Random.FRandRange(20,29):5;
   const FVector Lean(Random.FRandRange(-40,40),Random.FRandRange(-40,40),0);
   const int Sides=Lod==0?9:6;
   for(int I=0;I<8;++I) {
    double T0=I/8.0,T1=(I+1)/8.0;
    const FVector A=Lean*T0*T0+FVector(0,0,Height*T0),B=Lean*T1*T1+FVector(0,0,Height*T1);
    M.Tube(A,B,Radius*(1-T0*0.94),Radius*(1-T1*0.94),Sides);
    if(WithTrunkCollision&&Kind==0&&Lod==0) {
     // Envelope every endpoint of the exact visible trunk segments. Branches
     // and leaves remain outside this optional simple collision geometry.
     FVector U,V;(B-A).GetSafeNormal().FindBestAxisVectors(U,V);
     for(int J=0;J<Sides;++J) {
      const double Angle=J*2*PI/Sides;const FVector N=U*FMath::Cos(Angle)+V*FMath::Sin(Angle);
      TrunkPoints.Add(A+N*Radius*(1-T0*0.94));TrunkPoints.Add(B+N*Radius*(1-T1*0.94));
     }
    }
   }
   const int Branches=Kind==0?18:12;
   for(int I=0;I<Branches;++I) {
    const double A=I*2.39996323+Random.FRandRange(-0.2,0.2),T=0.32+I*0.56/Branches;
    const double Reach=Height*(Kind==0?0.34:0.40)*(1-0.45*(T-0.32));
    const FVector Start=Lean*T*T+FVector(0,0,Height*T);
    const FVector End=Start+FVector(FMath::Cos(A)*Reach,FMath::Sin(A)*Reach,Height*Random.FRandRange(0.08,0.19));
    const FVector Middle=FMath::Lerp(Start,End,0.52)+FVector(0,0,Height*0.025);
    M.Tube(Start,Middle,Radius*0.36,Radius*0.17,Sides);M.Tube(Middle,End,Radius*0.17,0.8,Sides);
    for(int J=0;J<4;++J) {
     const double S=0.45+J*0.18;
     const FVector Base=FMath::Lerp(Middle,End,S);
     const FVector TwigEnd=Base+FVector(FMath::Cos(A+(J%2?0.8:-0.8)),FMath::Sin(A+(J%2?0.8:-0.8)),0.6)*Height*0.105;
     M.Tube(Base,TwigEnd,Kind==0?2:0.6,0.3,Lod==0?5:3);
     FRandomStream Leaves(Seed+I*101+J*37);
     const int Count=Lod==0?90:Lod==1?30:10;
     const double Cluster=Height*(Kind==0?0.105:0.12);
     for(int K=0;K<Count;++K) {
      FVector P=Leaves.VRand();P*=FMath::Pow(Leaves.FRand(),1.0/3.0)*Cluster;
      P.Z*=0.7;
      const FVector Direction=(Leaves.VRand()+FVector(0,0,0.3)).GetSafeNormal();
      FVector Side,Other;Direction.FindBestAxisVectors(Side,Other);
      const double LeafLength=(Kind==0?20:12)*(Lod==0?1:Lod==1?1.5:2.5);
      M.Blade(TwigEnd+P,Direction,Side,LeafLength,LeafLength*0.32);
     }
    }
   }
  }
 }
 TArray<const FMeshDescription*> Descriptions;
 for(const auto& Lod:Lods) Descriptions.Add(&Lod->Mesh);
 UStaticMesh::FBuildMeshDescriptionsParams Params;Params.bFastBuild=false;Params.bBuildSimpleCollision=false;
 if(!Asset->BuildFromMeshDescriptions(Descriptions,Params)) return nullptr;
 if(!TrunkPoints.IsEmpty()) {
  TArray<UStaticMesh*> ToFinish{Asset};FStaticMeshCompilingManager::Get().FinishCompilation(ToFinish);
  Asset->CreateBodySetup();auto* Body=Asset->GetBodySetup();
  FKConvexElem Hull;Hull.VertexData=MoveTemp(TrunkPoints);Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(MoveTemp(Hull));
  Body->CollisionTraceFlag=CTF_UseSimpleAndComplex;Body->bDoubleSidedGeometry=false;
  Body->bNeverNeedsCookedCollisionData=false;Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();
 }
 Asset->MarkPackageDirty();FAssetRegistryModule::AssetCreated(Asset);
 UE_LOG(LogTemp,Display,TEXT("PROCEDURAL_FOLIAGE asset=%s seed=%d kind=%d LODs=3 trunk_collision=%d"),*AssetPath,Seed,Kind,WithTrunkCollision&&Kind==0);
 return Asset;
}

FString ULidarTerrainLibrary::InspectProceduralFoliage(const FString& AssetPath) {
 auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("loaded"),false);
 if(auto* Mesh=LoadObject<UStaticMesh>(nullptr,*AssetPath)) {
  TArray<UStaticMesh*> ToFinish{Mesh};FStaticMeshCompilingManager::Get().FinishCompilation(ToFinish);
  Result->SetBoolField(TEXT("loaded"),true);
  auto Array=[](const FVector& V) {return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};};
  const FBox Bounds=Mesh->GetBoundingBox();Result->SetArrayField(TEXT("min_cm"),Array(Bounds.Min));Result->SetArrayField(TEXT("max_cm"),Array(Bounds.Max));
  Result->SetNumberField(TEXT("source_lods"),Mesh->GetNumSourceModels());
  TArray<TSharedPtr<FJsonValue>> Hulls;
  if(const auto* Body=Mesh->GetBodySetup()) {
   Result->SetStringField(TEXT("collision_trace_mode"),UEnum::GetValueAsString(Body->CollisionTraceFlag.GetValue()));
   for(const auto& Hull:Body->AggGeom.ConvexElems) {
    TArray<TSharedPtr<FJsonValue>> Points;
    for(const auto& P:Hull.VertexData) Points.Add(MakeShared<FJsonValueArray>(Array(P)));
    Hulls.Add(MakeShared<FJsonValueArray>(Points));
   }
  }
  Result->SetArrayField(TEXT("convex_hulls_cm"),Hulls);
 }
 FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));return Text;
}
