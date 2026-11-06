// Read-only triage of an existing Windows live GPU dump using installed DbgEng.
// No live process attachment, symbols download, registry or driver changes.
#include <Windows.h>
#include <DbgEng.h>
#include <DbgHelp.h>
#include <iostream>
#include <string>

static std::string Json(const char* value) {
 std::string out="\"";
 for(const char* p=value;*p;++p) {
  if(*p=='\\'||*p=='\"')out+='\\';
  if(*p=='\n')out+="\\n";else if(*p=='\r')out+="\\r";else out+=*p;
 }
 return out+'\"';
}

int wmain(int argc,wchar_t** argv) {
 if(argc!=2)return 2;
 IDebugClient4* client=nullptr;
 IDebugControl* control=nullptr;
 IDebugSymbols3* symbols=nullptr;
 HRESULT hr=DebugCreate(__uuidof(IDebugClient4),reinterpret_cast<void**>(&client));
 if(FAILED(hr)){std::cout<<"{\"error\":\"DebugCreate\",\"hresult\":"<<hr<<"}\n";return 3;}
 hr=client->QueryInterface(__uuidof(IDebugControl),reinterpret_cast<void**>(&control));
 if(SUCCEEDED(hr))hr=client->QueryInterface(__uuidof(IDebugSymbols3),reinterpret_cast<void**>(&symbols));
 if(SUCCEEDED(hr)) {
  symbols->SetSymbolPath("");
  symbols->SetSymbolOptions(SYMOPT_DEFERRED_LOADS|SYMOPT_FAIL_CRITICAL_ERRORS|SYMOPT_NO_PROMPTS);
  hr=client->OpenDumpFileWide(argv[1],0);
 }
 if(SUCCEEDED(hr))hr=control->WaitForEvent(DEBUG_WAIT_DEFAULT,30000);
 ULONG code=0;ULONG64 args[4]={};
 if(SUCCEEDED(hr))hr=control->ReadBugCheckData(&code,&args[0],&args[1],&args[2],&args[3]);
 if(FAILED(hr))std::cout<<"{\"error\":\"dump_open_or_header\",\"hresult\":"<<hr<<"}\n";
 else {
  ULONG index=DEBUG_ANY_ID;ULONG64 base=0;
  char image[2048]={};char name[2048]={};ULONG used=0;ULONG64 displacement=0;
  HRESULT module=symbols->GetModuleByOffset(args[1],0,&index,&base);
  if(SUCCEEDED(module))module=symbols->GetModuleNameString(DEBUG_MODNAME_IMAGE,index,base,image,sizeof(image),&used);
  HRESULT symbol=symbols->GetNameByOffset(args[1],name,sizeof(name),&used,&displacement);
  std::cout<<"{\"bug_check_code\":"<<code<<",\"responsible_module_resolved\":"<<(SUCCEEDED(module)?"true":"false")
   <<",\"responsible_module_image\":"<<Json(image)<<",\"responsible_module_symbol\":"<<Json(name)
   <<",\"module_lookup_hresult\":"<<module<<",\"symbol_lookup_hresult\":"<<symbol
   <<",\"symbol_downloads_requested\":false,\"read_only_dump_analysis\":true}\n";
 }
 if(symbols)symbols->Release();if(control)control->Release();client->Release();
 return FAILED(hr)?4:0;
}
