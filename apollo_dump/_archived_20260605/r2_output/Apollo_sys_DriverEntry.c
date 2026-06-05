/* DriverEntry @ 0x140239e6a */

int FUN_140239e6a(longlong param_1)

{
  int iVar1;
  undefined8 local_30;
  undefined1 local_28 [16];
  undefined1 local_18 [24];
  
  FUN_1402399e8();
  RtlInitUnicodeString(local_28,L"\\Device\\ApolloProtect");
  iVar1 = IoCreateDevice(param_1,0,local_28,0x22,0,0,&local_30);
  if (-1 < iVar1) {
    RtlInitUnicodeString(local_18,L"\\DosDevices\\ApolloProtect");
    iVar1 = IoCreateSymbolicLink(local_18,local_28);
    if (iVar1 < 0) {
      IoDeleteDevice(local_30);
    }
    else {
      *(code **)(param_1 + 0x70) = FUN_1400017e0;
      *(code **)(param_1 + 0x80) = FUN_1400017e0;
      *(code **)(param_1 + 0x100) = FUN_1400017e0;
      *(code **)(param_1 + 0xe0) = thunk_FUN_140239a21;
      *(code **)(param_1 + 0x68) = thunk_FUN_14023a0dd;
      FUN_1402399e8();
      if (iVar1 != 0) {
        IoDeleteSymbolicLink(local_18);
      }
      iVar1 = 0;
    }
  }
  return iVar1;
}


