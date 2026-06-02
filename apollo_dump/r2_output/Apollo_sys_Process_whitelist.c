/* Process_whitelist @ 0x140001d48 */

undefined4 FUN_140001d48(undefined8 param_1,undefined8 param_2,undefined4 param_3)

{
  char cVar1;
  int iVar2;
  undefined4 local_24;
  undefined2 *local_20;
  undefined8 local_18;
  undefined8 local_10 [2];
  
  local_18 = 0;
  cVar1 = FUN_140001e54();
  if (cVar1 == '\0') {
    iVar2 = PsLookupProcessByProcessId(param_1,local_10);
    if (iVar2 == 0) {
      iVar2 = PsReferenceProcessFilePointer(local_10[0],&local_18);
      if (iVar2 == 0) {
        local_20 = (undefined2 *)0x0;
        iVar2 = IoQueryFileDosDeviceName(local_18,&local_20);
        if (iVar2 == 0) {
          RtlUnicodeToMultiByteN(param_2,param_3,&local_24,*(undefined8 *)(local_20 + 4),*local_20);
          ExFreePoolWithTag(local_20,0);
          ObfDereferenceObject(local_18);
          ObfDereferenceObject(local_10[0]);
        }
        else {
          ObfDereferenceObject(local_18);
          ObfDereferenceObject(local_10[0]);
          local_24 = 0;
        }
      }
      else {
        ObfDereferenceObject(local_10[0]);
        local_24 = 0;
      }
    }
    else {
      local_24 = 0;
    }
  }
  else {
    local_24 = 0;
  }
  return local_24;
}


