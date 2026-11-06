#include "LidarTerrainLibrary.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "MeshDescriptionBuilder.h"
#include "StaticMeshCompiler.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/PackageName.h"
#include "Misc/FileHelper.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/JsonSerializer.h"
#include "AssetRegistry/AssetRegistryModule.h"

namespace {
bool ReadDistant(const FString& Path,TArray<FVector>& Points,TArray<FIntVector>& Faces) {
 TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*Path)||Bytes.Num()<16)return false;
 FMemoryReader Reader(Bytes,true);uint32 Magic=0,Version=0,NV=0,NT=0;
 Reader<<Magic<<Version<<NV<<NT;
 // SFD1, little endian, v1: header, float64 XYZ centimeters, uint32 triples.
 if(Magic!=0x31444653||Version!=1||NV==0||NT==0||NV>2000000||NT>4000000||
    int64(Bytes.Num())!=16+int64(NV)*24+int64(NT)*12)return false;
 Points.Reserve(NV);Faces.Reserve(NT);
 for(uint32 I=0;I<NV;++I){double X,Y,Z;Reader<<X<<Y<<Z;FVector P(X,Y,Z);if(P.ContainsNaN())return false;Points.Add(P);}
 for(uint32 I=0;I<NT;++I){uint32 A,B,C;Reader<<A<<B<<C;if(A>=NV||B>=NV||C>=NV)return false;
  const FVector N=FVector::CrossProduct(Points[B]-Points[A],Points[C]-Points[A]);
  if(N.ContainsNaN()||N.Z<=0)return false;Faces.Add(FIntVector(A,B,C));}
 return !Reader.IsError();
}
}

UStaticMesh* ULidarTerrainLibrary::CreateDistantTerrainMesh(const FString& BinaryPath,const FString& AssetPath,const FString& MaterialPath) {
 if(!AssetPath.StartsWith(TEXT("/Game/World/Distant/"))||!FPackageName::IsValidLongPackageName(AssetPath))return nullptr;
 if(LoadObject<UStaticMesh>(nullptr,*AssetPath))return nullptr; // Never overwrite/reuse an untracked package.
 TArray<FVector> P,N;TArray<FIntVector> Faces;if(!ReadDistant(BinaryPath,P,Faces))return nullptr;
 auto* Material=LoadObject<UMaterialInterface>(nullptr,*MaterialPath);if(!Material)return nullptr;
 FMeshDescription Mesh;FStaticMeshAttributes Attr(Mesh);Attr.Register();
 FMeshDescriptionBuilder B;B.SetMeshDescription(&Mesh);B.EnablePolyGroups();B.SetNumUVLayers(1);
 const auto Group=B.AppendPolygonGroup(TEXT("DistantTerrain"));TArray<FVertexID> IDs;
 for(const auto& Point:P)IDs.Add(B.AppendVertex(Point));
 N.SetNumZeroed(P.Num());for(const auto& F:Faces){const FVector Normal=FVector::CrossProduct(P[F.Y]-P[F.X],P[F.Z]-P[F.X]);N[F.X]+=Normal;N[F.Y]+=Normal;N[F.Z]+=Normal;}
 for(const auto& F:Faces){FVertexInstanceID V[3];const int32 Index[]={F.X,F.Z,F.Y};
  // Mathematical +Z input is reversed for Unreal front-face winding. The
  // normal remains the original upward area-weighted terrain normal.
  for(int32 I=0;I<3;++I){const int32 K=Index[I];V[I]=B.AppendInstance(IDs[K]);B.SetInstanceNormal(V[I],N[K].GetSafeNormal());B.SetInstanceUV(V[I],FVector2D(P[K].X,P[K].Y)/800);}
  B.AppendTriangle(V[0],V[1],V[2],Group);
 }
 auto* Package=CreatePackage(*AssetPath);
 auto* Asset=NewObject<UStaticMesh>(Package,*FPackageName::GetLongPackageAssetName(AssetPath),RF_Public|RF_Standalone);
 Asset->GetStaticMaterials().Add(FStaticMaterial(Material,TEXT("DistantTerrain"),TEXT("DistantTerrain")));
 Asset->SetNumSourceModels(1);auto& Settings=Asset->GetSourceModel(0).BuildSettings;
 Settings.bRecomputeNormals=false;Settings.bGenerateLightmapUVs=false;
 Asset->CreateBodySetup();auto* Body=Asset->GetBodySetup();
 Body->bNeverNeedsCookedCollisionData=true;Body->CollisionTraceFlag=CTF_UseSimpleAndComplex;
 Body->DefaultInstance.SetCollisionProfileName(TEXT("NoCollision"));Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
 UStaticMesh::FBuildMeshDescriptionsParams Params;Params.bFastBuild=false;Params.bBuildSimpleCollision=false;
 const TArray<const FMeshDescription*> Descriptions{&Mesh};
 if(!Asset->BuildFromMeshDescriptions(Descriptions,Params))return nullptr;
 TArray<UStaticMesh*> Pending{Asset};FStaticMeshCompilingManager::Get().FinishCompilation(Pending);
 Body->ClearPhysicsMeshes();Body->AggGeom.EmptyElements();
 Body->bNeverNeedsCookedCollisionData=true;
 Asset->MarkPackageDirty();FAssetRegistryModule::AssetCreated(Asset);
 UE_LOG(LogTemp,Display,TEXT("DISTANT_MESH_CREATED asset=%s vertices=%d triangles=%d no_collision=1"),*AssetPath,P.Num(),Faces.Num());
 return Asset;
}

FString ULidarTerrainLibrary::VerifyDistantTerrainMesh(const FString& BinaryPath,const FString& AssetPath) {
 auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),false);
 TArray<FVector> P;TArray<FIntVector> Faces;auto* Asset=LoadObject<UStaticMesh>(nullptr,*AssetPath);
 if(Asset&&ReadDistant(BinaryPath,P,Faces))if(auto* M=Asset->GetMeshDescription(0)){
  FStaticMeshAttributes Attributes(*M);auto Positions=Attributes.GetVertexPositions();
  int32 VertexErrors=0,TriangleErrors=0;double MaxError=0;
  const bool Counts=M->Vertices().Num()==P.Num()&&M->Triangles().Num()==Faces.Num();
  if(Counts){for(const auto ID:M->Vertices().GetElementIDs()){
   const double E=(FVector(Positions[ID])-P[ID.GetValue()]).Size();MaxError=FMath::Max(MaxError,E);if(E>.01)++VertexErrors;}
   for(const auto ID:M->Triangles().GetElementIDs()){
    const auto V=M->GetTriangleVertices(ID);const auto& F=Faces[ID.GetValue()];
    if(V.Num()!=3||V[0].GetValue()!=F.X||V[1].GetValue()!=F.Z||V[2].GetValue()!=F.Y)++TriangleErrors;
   }
  }
  const auto* Body=Asset->GetBodySetup();const bool NoCollision=Body&&Body->bNeverNeedsCookedCollisionData&&
   Body->AggGeom.GetElementCount()==0&&Body->TriMeshGeometries.IsEmpty()&&Body->DefaultInstance.GetCollisionEnabled()==ECollisionEnabled::NoCollision;
  R->SetNumberField(TEXT("source_vertices"),P.Num());R->SetNumberField(TEXT("source_triangles"),Faces.Num());
  R->SetNumberField(TEXT("native_vertices"),M->Vertices().Num());R->SetNumberField(TEXT("native_triangles"),M->Triangles().Num());
  R->SetNumberField(TEXT("vertex_mismatches"),VertexErrors);R->SetNumberField(TEXT("triangle_mismatches"),TriangleErrors);
  R->SetNumberField(TEXT("max_vertex_float_storage_error_cm"),MaxError);R->SetBoolField(TEXT("no_collision_geometry"),NoCollision);
  R->SetBoolField(TEXT("passed"),Counts&&VertexErrors==0&&TriangleErrors==0&&NoCollision);
 }
 FString Output;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Output));return Output;
}
