/* KdDebuggerEnabled_check @ 0x140239970 */

undefined1 FUN_140239970(void)

{
  short sVar1;
  int iVar2;
  ushort unaff_R12W;
  undefined1 local_18;
  
  FUN_1400016b0();
  sVar1 = 0;
  if (unaff_R12W != 0) {
    for (; (unaff_R12W >> sVar1 & 1) == 0; sVar1 = sVar1 + 1) {
    }
  }
  LOCK();
  iVar2 = *(int *)KdDebuggerEnabled_exref;
  if (iVar2 == 1) {
    *(undefined4 *)KdDebuggerEnabled_exref = 1;
    iVar2 = 1;
  }
  UNLOCK();
  FUN_1400016ca();
  local_18 = (undefined1)iVar2;
  return local_18;
}


