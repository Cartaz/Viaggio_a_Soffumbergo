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
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "AssetRegistry/AssetRegistryModule.h"

UStaticMesh* ULidarTerrainLibrary::CreateCircuitMesh(const FString& JsonPath,const FString& AssetPath,const FString& MaterialPath) {
 if(!AssetPath.StartsWith(TEXT("/Game/World/Driving/")))return nullptr;
 if(auto* Existing=LoadObject<UStaticMesh>(nullptr,*AssetPath))return Existing;
 FString Text;TSharedPtr<FJsonObject> Data;
 if(!FFileHelper::LoadFileToString(Text,*JsonPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data))return nullptr;
 const auto& Points=Data->GetArrayField(TEXT("vertices_cm"));const auto& Faces=Data->GetArrayField(TEXT("triangles"));
 if(Points.IsEmpty()||Faces.IsEmpty())return nullptr;
 const TArray<TSharedPtr<FJsonValue>>* Convexes=nullptr;
 const bool HasConvexes=Data->TryGetArrayField(TEXT("collision_convexes_cm"),Convexes)&&Convexes&&!Convexes->IsEmpty();
 bool ClosedSurface=HasConvexes;
 bool ExplicitClosed=false;
 if(Data->TryGetBoolField(TEXT("closed_surface"),ExplicitClosed))ClosedSurface=ClosedSurface||ExplicitClosed;
 FMeshDescription Mesh;FStaticMeshAttributes Attributes(Mesh);Attributes.Register();
 FMeshDescriptionBuilder Builder;Builder.SetMeshDescription(&Mesh);Builder.EnablePolyGroups();Builder.SetNumUVLayers(1);
 const auto Group=Builder.AppendPolygonGroup(TEXT("Surface"));
 TArray<FVertexID> Vertices;TArray<FVector> Positions,Normals;
 for(const auto& V:Points){const auto& A=V->AsArray();if(A.Num()!=3)return nullptr;FVector P(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());if(P.ContainsNaN())return nullptr;Positions.Add(P);Vertices.Add(Builder.AppendVertex(P));}
 Normals.SetNumZeroed(Points.Num());
 TArray<FIntVector> Triangles;
 for(const auto& V:Faces) {
  const auto& A=V->AsArray();if(A.Num()!=3)return nullptr;
  const FIntVector F(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
  if(!Positions.IsValidIndex(F.X)||!Positions.IsValidIndex(F.Y)||!Positions.IsValidIndex(F.Z))return nullptr;
  const FVector N=FVector::CrossProduct(Positions[F.Y]-Positions[F.X],Positions[F.Z]-Positions[F.X]);
  if(N.SizeSquared()<1.e-8)return nullptr;
  Normals[F.X]+=N;Normals[F.Y]+=N;Normals[F.Z]+=N;
  // Source convex hulls use mathematical outward winding. Unreal's mesh
  // operations compute the geometric normal with cross(edge2, edge1).
  // Reverse the closed solids so their outward sides survive backface culling.
  Triangles.Add(ClosedSurface?FIntVector(F.X,F.Z,F.Y):F);
 }
 for(const auto& F:Triangles) {
  FVertexInstanceID Instances[3];const int32 Indices[]={F.X,F.Y,F.Z};
  // Closed rails and walls have hard edges. Averaging the eight corner
  // normals across their caps makes each flat side look diagonally folded.
  const FVector FaceNormal=FVector::CrossProduct(Positions[F.Z]-Positions[F.X],Positions[F.Y]-Positions[F.X]).GetSafeNormal();
  for(int32 I=0;I<3;++I){const int32 K=Indices[I];Instances[I]=Builder.AppendInstance(Vertices[K]);Builder.SetInstanceNormal(Instances[I],ClosedSurface?FaceNormal:Normals[K].GetSafeNormal());Builder.SetInstanceUV(Instances[I],FVector2D(Positions[K].X,Positions[K].Y)/400);}
  Builder.AppendTriangle(Instances[0],Instances[1],Instances[2],Group);
 }
 auto* Package=CreatePackage(*AssetPath);
 auto* Asset=NewObject<UStaticMesh>(Package,*FPackageName::GetLongPackageAssetName(AssetPath),RF_Public|RF_Standalone);
 Asset->GetStaticMaterials().Add(FStaticMaterial(LoadObject<UMaterialInterface>(nullptr,*MaterialPath),TEXT("Surface"),TEXT("Surface")));
 if(ClosedSurface) {
  Asset->SetNumSourceModels(1);
  // The editor build otherwise recomputes and smooths the explicit face normals.
  Asset->GetSourceModel(0).BuildSettings.bRecomputeNormals=false;
 }
 UStaticMesh::FBuildMeshDescriptionsParams Params;Params.bFastBuild=false;Params.bBuildSimpleCollision=false;
 const TArray<const FMeshDescription*> Descriptions{&Mesh};
 if(!Asset->BuildFromMeshDescriptions(Descriptions,Params))return nullptr;
 TArray<UStaticMesh*> ToFinish{Asset};FStaticMeshCompilingManager::Get().FinishCompilation(ToFinish);
 Asset->CreateBodySetup();auto* Body=Asset->GetBodySetup();
 if(HasConvexes) {
  // Closed structural solids use matching convex collision. Triangulated
  // double-sided closed shells can trap a dynamic chassis after contact.
  for(const auto& Value:*Convexes) {
   FKConvexElem Hull;
   for(const auto& Vertex:Value->AsArray()) {
    const auto& P=Vertex->AsArray();if(P.Num()!=3)return nullptr;
    Hull.VertexData.Add(FVector(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber()));
   }
   if(Hull.VertexData.Num()<4)return nullptr;
   Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
  }
 }
 Body->CollisionTraceFlag=HasConvexes?CTF_UseSimpleAndComplex:CTF_UseComplexAsSimple;
 Body->bDoubleSidedGeometry=!HasConvexes;
 Body->bNeverNeedsCookedCollisionData=false;Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();
 Asset->MarkPackageDirty();FAssetRegistryModule::AssetCreated(Asset);
 UE_LOG(LogTemp,Display,TEXT("CIRCUIT_MESH asset=%s vertices=%d triangles=%d collision_meshes=%d convex_solids=%d closed_surface=%d"),*AssetPath,Points.Num(),Faces.Num(),Body->TriMeshGeometries.Num(),Body->AggGeom.ConvexElems.Num(),ClosedSurface);
 return Asset;
}
