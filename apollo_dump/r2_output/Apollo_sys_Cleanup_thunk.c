/* Cleanup_thunk @ 0x14023a0dd */

void FUN_14023a0dd(longlong param_1)

{
  undefined1 local_18 [24];
  
  RtlInitUnicodeString(local_18,L"\\DosDevices\\ApolloProtect");
  IoDeleteSymbolicLink(local_18);
  IoDeleteDevice(*(undefined8 *)(param_1 + 8));
  return;
}


