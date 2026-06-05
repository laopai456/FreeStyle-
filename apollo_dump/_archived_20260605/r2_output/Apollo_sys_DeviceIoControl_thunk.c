/* DeviceIoControl_thunk @ 0x140239a21 */

int FUN_140239a21(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  uint uVar2;
  undefined4 *puVar3;
  undefined4 *puVar4;
  int iVar5;
  longlong lVar6;
  undefined8 uVar7;
  int local_48;
  undefined8 local_18 [3];
  
  local_48 = -0x3fffffff;
  lVar6 = FUN_140001c4c(param_2);
  puVar3 = *(undefined4 **)(param_2 + 0x18);
  uVar1 = *(uint *)(lVar6 + 0x10);
  puVar4 = *(undefined4 **)(param_2 + 0x18);
  uVar2 = *(uint *)(lVar6 + 8);
  iVar5 = *(int *)(lVar6 + 0x18);
  if (iVar5 == 0x222404) {
    if (DAT_140004220 == 0) {
      DAT_140004220 = 1;
    }
    local_48 = 0;
  }
  else if (iVar5 == 0x222408) {
    if (DAT_140004220 != 0) {
      local_48 = 0;
    }
  }
  else if (iVar5 == 0x222410) {
    if ((DAT_140004220 != 0) && (uVar2 == 0x48)) {
      FUN_14023a326(puVar4);
      local_48 = 0;
    }
  }
  else if (iVar5 == 0x222418) {
    if ((((DAT_140004220 != 0) && (puVar3 != (undefined4 *)0x0)) && (uVar1 == 4)) &&
       ((puVar4 != (undefined4 *)0x0 && (uVar2 == 4)))) {
      local_18[0] = 0;
      uVar7 = FUN_14000101c(*puVar3);
      local_48 = PsLookupProcessByProcessId(uVar7,local_18);
      if (-1 < local_48) {
        *puVar4 = (int)local_18[0];
        ObfDereferenceObject(local_18[0]);
      }
    }
  }
  else if (iVar5 == 0x222420) {
    if (((uVar1 == 4) && (puVar3 != (undefined4 *)0x0)) &&
       (iVar5 = FUN_140001d48(*puVar3,puVar4,uVar2), iVar5 != 0)) {
      local_48 = 0;
    }
  }
  else if (iVar5 == 0x222440) {
    if ((uVar1 == uVar2) && (0xc < uVar1)) {
      local_48 = FUN_140001986(puVar3,uVar1);
    }
    else {
      local_48 = -0x3fffffff;
    }
  }
  *(ulonglong *)(param_2 + 0x38) = (ulonglong)uVar2;
  *(int *)(param_2 + 0x30) = local_48;
  IofCompleteRequest(param_2,0);
  return local_48;
}


