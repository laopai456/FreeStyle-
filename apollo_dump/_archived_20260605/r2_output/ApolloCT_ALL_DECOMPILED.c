// ============================================
// Apollo.sys - ALL FUNCTIONS DECOMPILED
// Ghidra 12.0.1 headless decompilation
// ============================================

//── Ordinal_21  @0x00000000690064d0  (29B) ──

void __fastcall Ordinal_21(undefined4 param_1,int param_2)

{
  int unaff_EBX;
  int unaff_ESI;
  int unaff_EDI;
  undefined2 in_FS;
  
                    /* 0x64d0  21   */
  *(undefined2 *)((unaff_ESI - *(int *)(unaff_EDI + 0x37395cec)) + 0x5b0afe7e + unaff_EBX) = in_FS;
  *(char *)(param_2 + 0x7a) = *(char *)(param_2 + 0x7a) + '\x01';
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── Ordinal_10  @0x000000006901a230  (27B) ──

/* WARNING: Unable to track spacebase fully for stack */

void __fastcall Ordinal_10(int param_1,code *param_2)

{
  uint *puVar1;
  uint uVar2;
  code *pcVar4;
  undefined4 in_EAX;
  int iVar5;
  int unaff_EBX;
  uint unaff_ESI;
  int unaff_EDI;
  undefined2 in_SS;
  byte in_CF;
  char in_PF;
  char in_AF;
  char in_ZF;
  char in_SF;
  uint uVar3;
  
                    /* 0x1a230  10   */
  iVar5 = CONCAT22((short)((uint)in_EAX >> 0x10),
                   CONCAT11(in_SF << 7 | in_ZF << 6 | in_AF << 4 | in_PF << 2 | 2U | in_CF,
                            (char)in_EAX));
  puVar1 = (uint *)(unaff_EBX + -0xf);
  uVar2 = *puVar1;
  *puVar1 = *puVar1 << 1 | (uint)((int)uVar2 < 0);
  uVar3 = *puVar1;
  if (param_1 == 1) {
    *(undefined2 *)(iVar5 + -4) = in_SS;
    out((short)param_2,(char)((short)&stack0x00000000 / (short)(char)((uint)&stack0x00000000 >> 8)))
    ;
    pcVar4 = (code *)swi(4);
    if ((int)uVar2 < 0 != (int)uVar3 < 0) {
      (*pcVar4)();
    }
    *(uint *)(unaff_EDI + 0x75) = *(uint *)(unaff_EDI + 0x75) ^ unaff_ESI;
    return;
  }
  *(undefined4 *)(iVar5 + -4) = 0x6901a282;
  (*param_2)();
  return;
}



//── Ordinal_15  @0x000000006901a690  (16B) ──

void Ordinal_15(void)

{
  int in_EAX;
  int unaff_EBP;
  undefined4 unaff_EDI;
  
                    /* 0x1a690  15   */
  *(undefined4 *)(unaff_EBP + 0x3a6466b9) = unaff_EDI;
                    /* WARNING: Could not recover jumptable at 0x6901a69a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(in_EAX + 0x3f1c5ad0))();
  return;
}



//── FUN_6901c8e7  @0x000000006901c8e7  (9B) ──

void FUN_6901c8e7(void)

{
  return;
}



//── FUN_6941aaca  @0x000000006941aaca  (13B) ──

void __fastcall FUN_6941aaca(int param_1)

{
  *(undefined4 *)(&DAT_6941a903 + param_1) = 0x1a6;
  FUN_6941aaad();
  return;
}



//── FUN_6941aada  @0x000000006941aada  (17B) ──

void FUN_6941aada(void)

{
  return;
}



//── FUN_6941ab02  @0x000000006941ab02  (16B) ──

void FUN_6941ab02(void)

{
  int unaff_retaddr;
  
  *(undefined1 *)(unaff_retaddr + 0x1046) = 0xe9;
  FUN_6941aaca();
  return;
}



//── FUN_6941ab2a  @0x000000006941ab2a  (31B) ──

void FUN_6941ab2a(int *param_1,undefined4 param_2)

{
  int unaff_retaddr;
  
  *param_1 = unaff_retaddr + -0x17e8656b;
  *param_1 = *param_1 + 0x17e87bae;
  *(undefined4 *)*param_1 = param_2;
  thunk_FUN_6941ab02();
  return;
}



//── FUN_6941ab49  @0x000000006941ab49  (48B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6941ab49(void)

{
  undefined1 uVar1;
  byte extraout_AH;
  undefined2 extraout_DX;
  int unaff_EBP;
  undefined1 *unaff_EDI;
  
                    /* WARNING: Call to offcut address within same function */
  func_0x6941ab83();
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  uVar1 = in(extraout_DX);
  unaff_EDI[1] = uVar1;
  *(byte *)(unaff_EBP + 0x45af5c36) = *(byte *)(unaff_EBP + 0x45af5c36) & extraout_AH & 4;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6941abec  @0x000000006941abec  (20B) ──

void FUN_6941abec(uint param_1)

{
  if (0xae85b38b < param_1) {
    thunk_FUN_6941ab49();
    return;
  }
  thunk_FUN_6941ab49();
  return;
}



//── FUN_6941ad18  @0x000000006941ad18  (22B) ──

void FUN_6941ad18(void)

{
  bool in_OF;
  
  if (in_OF) {
    FUN_6941abec(0x6187096b);
    return;
  }
  FUN_6941abec(0x6187096b);
  return;
}



//── FUN_6941ada0  @0x000000006941ada0  (10B) ──

void FUN_6941ada0(void)

{
  FUN_6941adff();
  return;
}



//── FUN_6941add1  @0x000000006941add1  (15B) ──

void FUN_6941add1(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    FUN_6941ada0();
    return;
  }
  FUN_6941adff(0x9a566f49);
  return;
}



//── FUN_6941ae0c  @0x000000006941ae0c  (92B) ──

/* WARNING: Type propagation algorithm not settling */

void FUN_6941ae0c(void)

{
  char *pcVar1;
  undefined1 uVar2;
  undefined4 *puVar3;
  undefined4 *puVar4;
  char cVar5;
  int *piVar6;
  undefined2 extraout_CX;
  undefined2 uVar7;
  int unaff_EBX;
  int unaff_EBP;
  undefined1 *unaff_EDI;
  undefined2 in_DS;
  undefined2 in_GS;
  undefined6 uVar8;
  char acStack_deb1 [56904];
  undefined4 *puStack_69;
  undefined4 *apuStack_9 [2];
  
                    /* WARNING: Call to offcut address within same function */
  uVar8 = func_0x6941ae93();
  uVar7 = (undefined2)((uint6)uVar8 >> 0x20);
  apuStack_9[1] = (undefined4 *)(unaff_EBP + 2);
  uVar2 = in(uVar7);
  *unaff_EDI = uVar2;
  uVar2 = in(uVar7);
  unaff_EDI[1] = uVar2;
  *(undefined2 *)(unaff_EBP + -0x3dc83b41 + (int)apuStack_9[1]) = in_GS;
  puStack_69 = apuStack_9 + 1;
  puVar3 = apuStack_9 + 1;
  cVar5 = '\x18';
  puVar4 = apuStack_9[1];
  do {
    puVar4 = puVar4 + -1;
    puVar3 = puVar3 + -1;
    *puVar3 = *puVar4;
    cVar5 = cVar5 + -1;
  } while ('\0' < cVar5);
  piVar6 = (int *)(CONCAT31((int3)((uint)((int)uVar8 + -1) >> 8),DAT_debb2ba4) + 0x32a22640);
  segment(in_DS,(short)(unaff_EDI + 1) + 0xfe9);
  acStack_deb1[0] = acStack_deb1[0] + (char)acStack_deb1 * '\x03';
  pcVar1 = (char *)(CONCAT31((int3)((uint)(unaff_EBX + -1) >> 8),
                             (char)(unaff_EBX + -1) + (char)((ushort)extraout_CX >> 8)) + 0x47407c35
                   );
  *pcVar1 = *pcVar1 + (char)extraout_CX;
  *piVar6 = *piVar6 + 6;
  thunk_FUN_6941ab2a();
  return;
}



//── FUN_6941b2b7  @0x000000006941b2b7  (10B) ──

void FUN_6941b2b7(void)

{
  FUN_6941b33f();
  return;
}



//── FUN_6941b2e6  @0x000000006941b2e6  (10B) ──

void FUN_6941b2e6(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    FUN_6941b2b7();
    return;
  }
  FUN_6941b33f(0x99388ab0);
  return;
}



//── FUN_6941b33f  @0x000000006941b33f  (13B) ──

void FUN_6941b33f(void)

{
  bool in_PF;
  
  if (!in_PF) {
    thunk_FUN_6941b34c();
    return;
  }
  thunk_FUN_6941b34c();
  return;
}



//── FUN_6941b34c  @0x000000006941b34c  (38B) ──

void FUN_6941b34c(void)

{
  undefined1 uVar1;
  undefined2 extraout_DX;
  undefined1 *unaff_EDI;
  
                    /* WARNING: Call to offcut address within same function */
  func_0x6941b3df();
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  uVar1 = in(extraout_DX);
  unaff_EDI[1] = uVar1;
  return;
}



//── FUN_6941cdb0  @0x000000006941cdb0  (205B) ──

/* WARNING: Instruction at (ram,0x6941ce02) overlaps instruction at (ram,0x6941cdfe)
    */
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x6941ce0f) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6941cdb0(void)

{
  int *piVar1;
  code *pcVar2;
  byte *pbVar3;
  char cVar4;
  byte bVar5;
  short sVar6;
  uint uVar7;
  int *piVar8;
  int iVar9;
  undefined2 uVar15;
  undefined1 *puVar10;
  undefined1 *puVar11;
  undefined4 uVar12;
  undefined4 uVar13;
  undefined1 uVar17;
  int extraout_ECX;
  int iVar16;
  short sVar18;
  int iVar19;
  byte bVar20;
  int extraout_EDX;
  char *unaff_EBX;
  uint unaff_EBP;
  byte *unaff_ESI;
  int unaff_EDI;
  undefined2 in_ES;
  byte in_CF;
  bool bVar21;
  char in_AF;
  bool bVar22;
  bool bVar23;
  undefined8 uVar24;
  byte *pbStack_20;
  byte *pbStack_1c;
  uint uStack_18;
  int3 iVar14;
  
  uVar24 = thunk_FUN_6945e76c();
  iVar19 = (int)((ulonglong)uVar24 >> 0x20);
  sVar18 = (short)((ulonglong)uVar24 >> 0x20);
  pbStack_20 = (byte *)(unaff_EDI + -1);
  iVar16 = (int)uVar24 + 0x6093fa6b;
  iVar9 = iVar16 - (uint)in_CF;
  uVar15 = (undefined2)((uint)iVar9 >> 0x10);
  if (iVar9 == 0 || (SBORROW4((int)uVar24,-0x6093fa6b) != SBORROW4(iVar16,(uint)in_CF)) != iVar9 < 0
     ) {
    *unaff_ESI = *unaff_ESI + 0x71 + (unaff_ESI[0x8d338c9] < (byte)((uint)extraout_ECX >> 8));
    unaff_EBX[0x79] = unaff_EBX[0x79] + '\x10';
    sVar6 = (ushort)iVar9 + (ushort)unaff_ESI;
    piVar8 = (int *)CONCAT22(uVar15,sVar6);
    if (CARRY2((ushort)iVar9,(ushort)unaff_ESI) || sVar6 == 0) {
      piVar1 = (int *)((int)piVar8 + -0x52d368ad);
      iVar16 = *piVar1;
      *piVar1 = *piVar1 << 0x1d;
      bVar21 = iVar16 << 0x1c < 0;
      unaff_EBX = (char *)CONCAT22((short)((uint)unaff_EBX >> 0x10),CONCAT11(0x42,(char)unaff_EBX));
      iVar16 = *piVar8 * 0x51d17efb + -1;
      pbStack_1c = unaff_ESI;
      if (iVar16 == 0 || &stack0x00000000 == (undefined1 *)0xffffffff) goto code_r0x6941cde2;
      *unaff_EBX = *unaff_EBX << 1;
    }
    bVar22 = *unaff_ESI < *pbStack_20;
    if ((char)(*unaff_ESI - *pbStack_20) < '\0') {
      bVar22 = (byte)sVar6 < 0xeb;
    }
  }
  else {
    uVar7 = CONCAT22(uVar15,CONCAT11(0x3a,(char)iVar9)) + 1;
    bVar21 = CARRY4(unaff_EBP,uVar7);
    unaff_EBP = unaff_EBP + uVar7;
    pbStack_1c = unaff_ESI + 1;
    bVar5 = *unaff_ESI;
    iVar14 = (int3)(uVar7 >> 8);
    piVar8 = (int *)CONCAT31(iVar14,bVar5);
    pbVar3 = (byte *)((int)piVar8 * 2);
    bVar22 = *pbVar3 < bVar5 || (byte)(*pbVar3 - bVar5) < bVar21;
    *pbVar3 = (*pbVar3 - bVar5) - bVar21;
    iVar19 = (int)iVar14 >> 0x17;
    cVar4 = (char)(uVar7 >> 0x18);
    sVar18 = (short)cVar4 >> 7;
    if (extraout_ECX == 1) {
      in_AF = (uVar7 & 0x1000) != 0;
      bVar21 = (uVar7 & 0x100) != 0;
      iVar16 = 0;
code_r0x6941cde2:
      *(byte *)(iVar16 + 0x1a9b8860) = ~*(byte *)(iVar16 + 0x1a9b8860);
      uVar17 = (undefined1)((uint)iVar16 >> 8);
      bVar20 = (byte)((ushort)sVar18 >> 8);
      bVar5 = bVar20 - (byte)iVar16;
      out(0x74,(char)piVar8);
      uVar12 = in(CONCAT11(bVar5 - bVar21,(char)sVar18));
      *(undefined4 *)pbStack_20 = uVar12;
      *(uint *)(pbStack_1c + (bVar20 < (byte)iVar16 || bVar5 < bVar21) + unaff_EBP + 0x11e28717) =
           *(int *)(pbStack_1c + (bVar20 < (byte)iVar16 || bVar5 < bVar21) + unaff_EBP + 0x11e28717)
           + -0x35 + (uint)((int *)0x6104941d < piVar8);
      puVar10 = (undefined1 *)((int)piVar8 + 0x9efb6be2U & 0xa05136a0);
      bVar21 = &pbStack_20 < (undefined1 *)0xce27d48d;
      puVar11 = &stack0x31d82b53;
      bVar23 = (int)puVar11 < 0;
      bVar22 = puVar11 == (undefined1 *)0x0;
      bVar5 = POPCOUNT((uint)puVar11 & 0xff);
      while (iVar16 = CONCAT22((short)((uint)puVar11 >> 0x10),
                               CONCAT11(bVar23 << 7 | bVar22 << 6 | in_AF << 4 |
                                        ((bVar5 & 1) == 0) << 2 | 2U | bVar21,(char)puVar11)) +
                      -0x9e0137b + (uint)bVar21, -1 < iVar16) {
        puVar10 = puVar10 + 4;
        bVar21 = false;
        puVar11 = (undefined1 *)
                  CONCAT31((int3)(CONCAT22((short)((uint)iVar16 >> 0x10),
                                           CONCAT11(bRam3faf234f / 0x27,bRam3faf234f)) >> 8),
                           bRam3faf234f % 0x27);
        bVar23 = false;
        bVar22 = (ushort)puVar11 == 0;
        bVar5 = POPCOUNT((ushort)puVar11 & 0xff);
        swi(4);
      }
      *(undefined1 *)
       (CONCAT22((short)((uint)unaff_EBX >> 0x10),CONCAT11(uVar17,(char)unaff_EBX)) + -2) = uVar17;
      *(undefined1 **)(puVar10 + -4) = puVar10;
      pcVar2 = (code *)swi(3);
      uStack_18 = unaff_EBP;
      (*pcVar2)();
      return;
    }
    if (*pbVar3 != 0) {
      pcVar2 = (code *)swi(1);
      (*pcVar2)();
      return;
    }
    out((short)cVar4 >> 7,piVar8);
  }
  while( true ) {
    iVar16 = _DAT_9f689a06;
    in(0xc);
    uVar12 = in((short)iVar19);
    uVar13 = in(0x75);
    bVar5 = ((char)uVar13 + '\x11') -
            ((byte)uVar12 < 0xf7 ||
            (byte)((byte)uVar12 + 9) <
            (0x75 < (byte)unaff_EBP || CARRY1((byte)unaff_EBP + 0x8a,bVar22)));
    piVar8 = (int *)(CONCAT31((int3)((uint)uVar13 >> 8),bVar5 + 0x81) + -0x7d);
    _DAT_9f689a1a = in_ES;
    *piVar8 = *piVar8 + _DAT_9f689a02 + (uint)(0x7e < bVar5);
    _DAT_82dc35c6 = iVar16 * 0x41b2d747;
    FUN_69460104();
    unaff_EBP = iVar16 + 1;
    if (!SCARRY4(iVar16,1)) break;
    bVar22 = false;
    iVar19 = extraout_EDX;
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6941d35f  @0x000000006941d35f  (21B) ──

void FUN_6941d35f(void)

{
  byte extraout_CL;
  
  FUN_69470085();
  DAT_88791e88 = DAT_88791e88 >> (extraout_CL & 7) | DAT_88791e88 << 8 - (extraout_CL & 7);
  return;
}



//── FUN_6941da12  @0x000000006941da12  (150B) ──

undefined4 FUN_6941da12(int param_1,int param_2,uint param_3,uint param_4,uint param_5)

{
  uint *puVar1;
  uint uVar2;
  undefined4 uVar3;
  int iVar4;
  uint uVar5;
  uint uVar6;
  uint local_c;
  uint local_8;
  
  local_c = 0;
  if ((DAT_69422728 == 0) ||
     ((**(code **)(DAT_69422728 + 0x1c))(param_1 + param_2,param_3,0x40,&local_8),
     (local_8 & 0x101) == 0)) {
    uVar6 = 0;
    if (param_3 != 0) {
      uVar5 = 0;
      do {
        puVar1 = (uint *)(param_2 + param_1 + uVar6);
        uVar2 = *puVar1;
        *puVar1 = uVar5 + uVar2;
        uVar6 = uVar6 + 4;
        uVar5 = *puVar1 + param_4 ^ local_c ^ param_5;
        local_c = local_c + uVar5;
        param_4 = param_4 >> 1 | (uint)((param_4 & 1) != 0) << 0x1f;
        param_5 = param_5 << 2 | param_5 >> 0x1e;
        *puVar1 = uVar5;
        uVar5 = uVar2;
      } while (uVar6 < param_3);
    }
    iVar4 = FUN_6942e1c2();
    if (iVar4 != 0) {
      (**(code **)(iVar4 + 0x1c))(param_1 + param_2,param_3,local_8,&local_8);
    }
    uVar3 = 0;
  }
  else {
    uVar3 = 1;
  }
  return uVar3;
}



//── FUN_6941e0c4  @0x000000006941e0c4  (64B) ──

void FUN_6941e0c4(void)

{
  char *pcVar1;
  int iVar2;
  int unaff_EDI;
  undefined4 local_10;
  undefined4 local_c;
  undefined1 local_8;
  
  do {
    local_10 = 0x36343831;
    local_c = 0x31342d37;
    local_8 = 0;
    iVar2 = FUN_6941ad18(&local_10,0);
    pcVar1 = (char *)(unaff_EDI + 0x6a + iVar2);
    *pcVar1 = *pcVar1 << 3;
    FUN_6944d2b9();
    iVar2 = FUN_694309c5();
    (**(code **)(iVar2 + 0x44))(2000);
  } while( true );
}



//── FUN_6941e10a  @0x000000006941e10a  (54B) ──

void FUN_6941e10a(void)

{
  code *pcVar1;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  undefined1 local_8;
  
  local_14 = 0x656c6946;
  local_10 = 0x636e6f6d;
  local_c = 0x7373616c;
  local_8 = 0;
  FUN_6941ad18(&local_14,0);
  pcVar1 = (code *)swi(1);
  (*pcVar1)();
  return;
}



//── FUN_6941e157  @0x000000006941e157  (73B) ──

void FUN_6941e157(void)

{
  int iVar1;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  undefined2 local_8;
  
  do {
    local_14 = 0x33323834;
    local_10 = 0x3030302d;
    local_c = 0x32303030;
    local_8 = 0x39;
    iVar1 = FUN_6941ad18(&local_14,0);
    if (iVar1 != 0) {
      thunk_FUN_6944d2fd(3);
    }
    iVar1 = FUN_6943097e();
    (**(code **)(iVar1 + 0x44))(2000);
  } while( true );
}



//── FUN_6941e1a6  @0x000000006941e1a6  (67B) ──

void FUN_6941e1a6(void)

{
  ushort *puVar1;
  int iVar2;
  undefined1 *puVar3;
  byte bVar4;
  
  puVar3 = &stack0xfffffffc;
  bVar4 = &stack0xfffffffc < (undefined1 *)0xc;
  do {
    *(undefined4 *)(puVar3 + -0xc) = 0x6d676552;
    *(undefined4 *)(puVar3 + -8) = 0x6c636e6f;
    *(undefined4 *)(puVar3 + -4) = 0x737361;
    iVar2 = FUN_6941ad18(puVar3 + -0xc,0);
    puVar1 = (ushort *)(puVar3 + 0x6a0774c0);
    *puVar1 = *puVar1 + (ushort)bVar4 * (((ushort)iVar2 & 3) - (*puVar1 & 3));
    puVar3 = puVar3 + iVar2;
    bVar4 = (char)iVar2 + 0xf;
    bVar4 = CARRY1(bVar4,*(byte *)CONCAT31((int3)((uint)iVar2 >> 8),bVar4));
    iVar2 = FUN_69430985();
    (**(code **)(iVar2 + 0x44))(2000);
  } while( true );
}



//── FUN_694200b8  @0x00000000694200b8  (37B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_694200b8(undefined4 param_1,undefined4 *param_2,undefined4 *param_3)

{
  code *pcVar1;
  uint uVar2;
  int extraout_EDX;
  int unaff_ESI;
  int unaff_EDI;
  byte in_CF;
  undefined2 in_stack_0000001c;
  undefined4 in_stack_00000024;
  
  FUN_694900c9();
  *(int *)(unaff_ESI + 0x13e08111) = *(int *)(unaff_ESI + 0x13e08111) + extraout_EDX + (uint)in_CF;
  *(char *)(unaff_EDI + -0x35) = *(char *)(unaff_EDI + -0x35) + -1;
  pcVar1 = (code *)swi(0x29);
  uVar2 = (*pcVar1)();
  out(in_stack_0000001c,in_stack_00000024);
  if ((int)(uVar2 | *(uint *)(uVar2 + 0x6b807116)) < 1) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  *param_2 = *param_3;
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_69420f1c  @0x0000000069420f1c  (651B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_69420f1c(int *param_1,int param_2,undefined4 param_3)

{
  undefined4 *puVar1;
  char *pcVar2;
  int *piVar3;
  undefined4 *puVar4;
  int iVar5;
  undefined4 uVar6;
  undefined4 extraout_ECX;
  int iVar7;
  undefined4 *unaff_EDI;
  undefined2 in_ES;
  undefined2 in_CS;
  undefined2 in_SS;
  undefined2 in_DS;
  undefined2 in_FS;
  undefined2 in_GS;
  char cVar8;
  byte in_AF;
  byte in_TF;
  byte in_IF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined8 uVar9;
  undefined4 uStack_35c;
  undefined4 uStack_358;
  undefined1 *puStack_34;
  int *piStack_30;
  undefined4 *puStack_2c;
  undefined4 *puStack_28;
  int *local_1c;
  undefined4 local_18;
  int *local_14;
  undefined4 local_10;
  int local_c;
  char local_5;
  
  puVar4 = *(undefined4 **)(param_2 + 8);
  puStack_28 = (undefined4 *)0x69420f31;
  FUN_6944c6c9();
  puStack_28 = unaff_EDI + 1;
  piVar3 = puVar4 + 1;
  *unaff_EDI = *puVar4;
  local_5 = '\0';
  local_10 = 1;
  puVar1 = (undefined4 *)(param_2 + 0x10);
  if (*piVar3 != -2) {
    puStack_2c = (undefined4 *)0x69420f55;
    thunk_FUN_6944f559();
  }
  puStack_2c = (undefined4 *)0x69420f65;
  FUN_6944f523();
  iVar7 = param_2;
  if ((*(byte *)(param_1 + 1) & 0x66) == 0) {
    *(int ***)(param_2 + -4) = &local_1c;
    iVar7 = *(int *)(param_2 + 0xc);
    local_1c = param_1;
    local_18 = param_3;
    if (iVar7 != -2) {
      do {
        local_14 = puVar4 + iVar7 * 3 + 5;
        local_c = *local_14;
        if (puVar4[iVar7 * 3 + 6] != 0) {
          puStack_2c = (undefined4 *)0x69420faa;
          iVar5 = FUN_6944f5e2();
          local_5 = '\x01';
          if (iVar5 < 0) {
            local_10 = 0;
            goto LAB_69420fc4;
          }
          if (0 < iVar5) {
            if ((*param_1 == -0x1f928c9d) && (DAT_69422af4 != (code *)0x0)) {
              puStack_2c = &DAT_69422af4;
              piStack_30 = (int *)0x69421019;
              iVar5 = FUN_6944f7c5();
              if (iVar5 != 0) {
                puStack_2c = (undefined4 *)0x1;
                piStack_30 = param_1;
                puStack_34 = (undefined1 *)0x6942102c;
                (*DAT_69422af4)();
              }
            }
            puStack_2c = (undefined4 *)0x6942103a;
            FUN_6944f602();
            if (*(int *)(param_2 + 0xc) != iVar7) {
              puStack_2c = (undefined4 *)&DAT_6942259c;
              puStack_34 = (undefined1 *)0x69421051;
              puStack_28 = puVar1;
              thunk_FUN_6944f722();
            }
            *(int *)(param_2 + 0xc) = local_c;
            if (*piVar3 != -2) {
              puStack_2c = (undefined4 *)0x6942106e;
              thunk_FUN_6944f640();
            }
            puStack_2c = (undefined4 *)0x6942107e;
            FUN_6944f620();
            puStack_2c = (undefined4 *)0x6942108b;
            FUN_6944f66b();
            goto LAB_6942108b;
          }
        }
        iVar7 = local_c;
      } while (local_c != -2);
      if (local_5 != '\0') {
LAB_69420fc4:
        if (*piVar3 != -2) {
          puStack_2c = (undefined4 *)0x69420fd8;
          thunk_FUN_6944f59a();
        }
        puStack_2c = (undefined4 *)0x69420fe8;
        thunk_FUN_6944f91c();
      }
    }
  }
  else {
LAB_6942108b:
    if (*(int *)(iVar7 + 0xc) != -2) {
      puStack_2c = (undefined4 *)&DAT_6942259c;
      puStack_34 = (undefined1 *)0x694210a6;
      piStack_30 = puVar1;
      thunk_FUN_6944f67d();
      puStack_34 = (undefined1 *)0x694210ab;
      uVar9 = FUN_6944f64e();
      _DAT_694228cc = (undefined4)((ulonglong)uVar9 >> 0x20);
      _DAT_694228d4 = (undefined4)uVar9;
      _DAT_694228e4 =
           (uint)(in_NT & 1) * 0x4000 | (uint)SBORROW4((int)&puStack_34,0x328) * 0x800 |
           (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 |
           (uint)((int)&uStack_35c < 0) * 0x80 |
           (uint)(&stack0x00000000 == (undefined1 *)0x35c) * 0x40 | (uint)(in_AF & 1) * 0x10 |
           (uint)((POPCOUNT((uint)&uStack_35c & 0xff) & 1U) == 0) * 4 |
           (uint)(&puStack_34 < (undefined1 *)0x328) | (uint)(in_ID & 1) * 0x200000 |
           (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
           (uint)(in_AC & 1) * 0x40000;
      DAT_694228dc = piStack_30;
      _DAT_694228e8 = &puStack_2c;
      _DAT_69422824 = 0x10001;
      _DAT_694227d8 = piStack_30;
      _DAT_694227cc = 0xc0000409;
      _DAT_694227d0 = 1;
      _DAT_694228b0 = in_GS;
      _DAT_694228b4 = in_FS;
      _DAT_694228b8 = in_ES;
      _DAT_694228bc = in_DS;
      _DAT_694228c0 = puVar1;
      _DAT_694228c4 = piVar3;
      _DAT_694228c8 = iVar7;
      _DAT_694228d0 = extraout_ECX;
      _DAT_694228d8 = &stack0xfffffffc;
      _DAT_694228e0 = in_CS;
      _DAT_694228ec = in_SS;
      puStack_34 = &stack0xfffffffc;
      uStack_35c = FUN_6944c83b();
      uStack_358 = FUN_6944c78c();
      thunk_FUN_6941b2e6();
      pcVar2 = (char *)((int)&DAT_6942281c + iVar7);
      cVar8 = *pcVar2 < '\0';
      *pcVar2 = *pcVar2 << 1;
      thunk_FUN_6944f6ef(1);
      uVar6 = FUN_694235db(0);
      pcVar2 = (char *)CONCAT31(CONCAT21((short)((uint)uVar6 >> 0x10),(byte)uVar6 / 0x68),-cVar8);
      *pcVar2 = *pcVar2 + -cVar8;
      if (DAT_6942281c == 0) {
        thunk_FUN_6944f6d2(1,&puStack_34,0xe8694216);
      }
      thunk_FUN_69423d30(0xc0000409);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
  }
  return local_10;
}



//── FUN_6942357c  @0x000000006942357c  (14B) ──

void FUN_6942357c(void)

{
  FUN_6942379c();
  return;
}



//── FUN_694235db  @0x00000000694235db  (10B) ──

void FUN_694235db(void)

{
  bool in_OF;
  
  if (!in_OF) {
    FUN_6942357c(0x33581f63);
    return;
  }
  FUN_6942357c(0x33581f63);
  return;
}



//── FUN_694235ee  @0x00000000694235ee  (31B) ──

void FUN_694235ee(void)

{
  byte *pbVar1;
  uint *puVar2;
  undefined1 uVar3;
  uint uVar4;
  int extraout_ECX;
  uint *extraout_EDX;
  int unaff_ESI;
  undefined1 *unaff_EDI;
  
                    /* WARNING: Call to offcut address within same function */
  func_0x69423600();
  uVar4 = *extraout_EDX;
  uVar3 = in((short)extraout_EDX);
  *unaff_EDI = uVar3;
  uVar3 = in((short)extraout_EDX);
  unaff_EDI[1] = uVar3;
  pbVar1 = (byte *)((unaff_ESI - 1U ^ uVar4) + 0x1bcb20d2);
  *pbVar1 = *pbVar1 & (byte)((uint)extraout_EDX >> 8);
  puVar2 = (uint *)(extraout_ECX + -0x79c5f418);
  *puVar2 = *puVar2 << 1 | (uint)((int)*puVar2 < 0);
  FUN_694235ee();
  return;
}



//── FUN_69423654  @0x0000000069423654  (11B) ──

void FUN_69423654(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    FUN_694235ee();
    return;
  }
  FUN_694235ee();
  return;
}



//── FUN_6942379c  @0x000000006942379c  (16B) ──

void FUN_6942379c(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    thunk_FUN_69423654();
    return;
  }
  thunk_FUN_69423654();
  return;
}



//── FUN_69423b0c  @0x0000000069423b0c  (18B) ──

void FUN_69423b0c(void)

{
  FUN_69423cd6();
  return;
}



//── FUN_69423b71  @0x0000000069423b71  (14B) ──

void FUN_69423b71(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_69423c4e();
    return;
  }
  FUN_69423c4e();
  return;
}



//── FUN_69423c4e  @0x0000000069423c4e  (20B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69423c4e(void)

{
  undefined1 uVar1;
  code *pcVar2;
  undefined2 extraout_DX;
  undefined1 *unaff_EDI;
  
                    /* WARNING: Call to offcut address within same function */
  func_0x69423c60();
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  uVar1 = in(extraout_DX);
  unaff_EDI[1] = uVar1;
  pcVar2 = (code *)swi(0xfe);
  (*pcVar2)();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69423d30  @0x0000000069423d30  (17B) ──

void FUN_69423d30(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_69423b0c();
    return;
  }
  FUN_69423cd6(0xe03ecfba);
  return;
}



//── FUN_6942715a  @0x000000006942715a  (120B) ──

void FUN_6942715a(void)

{
  undefined2 in_AX;
  bool in_ZF;
  undefined8 in_stack_00000010;
  undefined2 local_4;
  undefined1 local_2;
  undefined1 uStack_1;
  
  local_4 = SUB42(&local_4,0);
  local_2 = (undefined1)in_AX;
  uStack_1 = (undefined1)((ushort)in_AX >> 8);
  if (!in_ZF) {
    FUN_69427250();
    return;
  }
  local_4 = (undefined2)((ulonglong)in_stack_00000010 >> 0x18);
  FUN_694272dd();
  return;
}



//── FUN_69427218  @0x0000000069427218  (13B) ──

void FUN_69427218(undefined8 param_1)

{
  uint *puVar1;
  int *piVar2;
  code *pcVar3;
  uint uVar4;
  int extraout_ECX;
  int extraout_EDX;
  uint unaff_ESI;
  int unaff_EDI;
  byte bVar5;
  undefined1 uStack_1;
  
  uVar4 = (uint)_uStack_1 >> 8;
  _uStack_1 = CONCAT31((int3)uVar4,(char)((ulonglong)param_1 >> 0x20));
  FUN_6942715a((short)_uStack_1);
  puVar1 = (uint *)(unaff_EDI + 0x66);
  bVar5 = CARRY4(*puVar1,unaff_ESI);
  *puVar1 = *puVar1 + unaff_ESI;
  FUN_694275dc((short)((ulonglong)param_1 >> 0x18));
  piVar2 = (int *)(extraout_EDX + -0x168c6393 + extraout_ECX);
  *piVar2 = *piVar2 + extraout_EDX + (uint)bVar5;
  pcVar3 = (code *)swi(1);
  (*pcVar3)();
  return;
}



//── FUN_6942722d  @0x000000006942722d  (13B) ──

void FUN_6942722d(void)

{
  FUN_694272dd();
  return;
}



//── FUN_69427250  @0x0000000069427250  (11B) ──

void FUN_69427250(void)

{
  FUN_6942722d();
  return;
}



//── FUN_69427262  @0x0000000069427262  (24B) ──

void FUN_69427262(void)

{
  FUN_694272ba();
  return;
}



//── FUN_69427292  @0x0000000069427292  (27B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69427292(void)

{
  FUN_69427262();
  FUN_69427342();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_694272ba  @0x00000000694272ba  (14B) ──

void FUN_694272ba(void)

{
  FUN_694274b4();
  return;
}



//── FUN_6942730f  @0x000000006942730f  (17B) ──

void FUN_6942730f(void)

{
  FUN_69427218();
  return;
}



//── FUN_6942731f  @0x000000006942731f  (14B) ──

void FUN_6942731f(void)

{
  FUN_6942746e();
  return;
}



//── FUN_69427342  @0x0000000069427342  (9B) ──

void FUN_69427342(void)

{
  FUN_6942731f();
  return;
}



//── FUN_69427363  @0x0000000069427363  (10B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69427363(void)

{
  FUN_69427342();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69427385  @0x0000000069427385  (22B) ──

void FUN_69427385(void)

{
  FUN_69427407();
  return;
}



//── FUN_694273f0  @0x00000000694273f0  (9B) ──

void FUN_694273f0(undefined4 param_1,undefined8 param_2)

{
  bool in_CF;
  bool in_ZF;
  undefined2 uStack_2;
  
  if (!in_CF && !in_ZF) {
    FUN_69427385();
    return;
  }
  uStack_2 = (undefined2)((ulonglong)param_2 >> 0x28);
  param_1._1_2_ = uStack_2;
  FUN_6942743f();
  return;
}



//── FUN_6942743f  @0x000000006942743f  (26B) ──

void FUN_6942743f(void)

{
  int *piVar1;
  code *pcVar2;
  int extraout_ECX;
  int extraout_EDX;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  ushort uStack00000007;
  undefined1 uStack00000009;
  undefined2 local_4;
  
  local_4 = (ushort)(in_NT & 1) * 0x4000 | (ushort)(in_OF & 1) * 0x800 | (ushort)(in_IF & 1) * 0x200
            | (ushort)(in_TF & 1) * 0x100 | (ushort)(in_SF & 1) * 0x80 | (ushort)(in_ZF & 1) * 0x40
            | (ushort)(in_AF & 1) * 0x10 | (ushort)(in_PF & 1) * 4 | (ushort)(in_CF & 1);
  uStack00000007 = local_4;
  if (!(bool)in_CF) {
    uStack00000009 = 0;
    FUN_69427517();
    return;
  }
  uStack00000009 = 0;
  FUN_694275dc();
  piVar1 = (int *)(extraout_EDX + -0x168c6393 + extraout_ECX);
  *piVar1 = *piVar1 + extraout_EDX + (uint)in_CF;
  pcVar2 = (code *)swi(1);
  (*pcVar2)();
  return;
}



//── FUN_6942746e  @0x000000006942746e  (80B) ──

void FUN_6942746e(void)

{
  undefined4 in_stack_00000010;
  undefined4 in_stack_00000014;
  undefined2 uStack0000001c;
  undefined2 uStack0000001e;
  
  LOCK();
  UNLOCK();
  uStack0000001e = (undefined2)((uint)in_stack_00000014 >> 0x10);
  uStack0000001c = CONCAT11((char)((uint)in_stack_00000010 >> 8),(char)in_stack_00000014);
  FUN_694273f0();
  return;
}



//── FUN_694274b4  @0x00000000694274b4  (20B) ──

void FUN_694274b4(void)

{
  FUN_694272f2();
  return;
}



//── FUN_69427517  @0x0000000069427517  (11B) ──

void FUN_69427517(void)

{
  int *piVar1;
  code *pcVar2;
  int extraout_ECX;
  int extraout_EDX;
  byte in_CF;
  
  FUN_694275dc();
  piVar1 = (int *)(extraout_EDX + -0x168c6393 + extraout_ECX);
  *piVar1 = *piVar1 + extraout_EDX + (uint)in_CF;
  pcVar2 = (code *)swi(1);
  (*pcVar2)();
  return;
}



//── FUN_6942753a  @0x000000006942753a  (84B) ──

void FUN_6942753a(undefined4 param_1)

{
  uint *puVar1;
  int *piVar2;
  code *pcVar3;
  int extraout_ECX;
  int extraout_EDX;
  undefined4 unaff_EBX;
  uint unaff_ESI;
  int unaff_EDI;
  byte bVar4;
  char in_SF;
  char in_OF;
  undefined2 uStack_a;
  undefined2 local_8;
  undefined1 local_6;
  undefined1 uStack_5;
  undefined1 uStack_4;
  undefined1 uStack_3;
  undefined1 uStack_2;
  undefined1 uStack_1;
  
  uStack_2 = (undefined1)unaff_EBX;
  uStack_1 = (undefined1)((uint)unaff_EBX >> 8);
  local_6 = SUB41(&uStack_2,0);
  uStack_3 = (undefined1)((uint)&uStack_2 >> 0x18);
  uStack_a = (undefined2)unaff_ESI;
  uStack_5 = (undefined1)unaff_ESI;
  local_8 = (undefined2)(CONCAT13(uStack_2,CONCAT12(uStack_3,uStack_a)) >> 0x10);
  uStack_4 = SUB41(&uStack_a,0);
  uStack_3 = (undefined1)((uint)&uStack_a >> 8);
  if (in_OF == in_SF) {
    FUN_6942730f();
    return;
  }
  local_6 = (undefined1)((uint)unaff_EDI >> 0x18);
  uStack_3 = (undefined1)param_1;
  uStack_2 = (undefined1)((uint)param_1 >> 8);
  uStack_1 = (undefined1)((uint)param_1 >> 0x10);
  local_8 = (undefined2)((uint)unaff_EDI >> 8);
  uStack_5 = (undefined1)param_1;
  uStack_a = (undefined2)
             (CONCAT13(uStack_2,CONCAT12((undefined1)param_1,CONCAT11(local_6,(undefined1)param_1)))
             >> 0x10);
  uStack_4 = local_6;
  FUN_6942715a(CONCAT11(local_6,(undefined1)param_1));
  puVar1 = (uint *)(unaff_EDI + 0x66);
  bVar4 = CARRY4(*puVar1,unaff_ESI);
  *puVar1 = *puVar1 + unaff_ESI;
  uStack_a = CONCAT11(uStack_5,local_6);
  FUN_694275dc();
  piVar2 = (int *)(extraout_EDX + -0x168c6393 + extraout_ECX);
  *piVar2 = *piVar2 + extraout_EDX + (uint)bVar4;
  pcVar3 = (code *)swi(1);
  (*pcVar3)();
  return;
}



//── FUN_69427595  @0x0000000069427595  (10B) ──

void FUN_69427595(void)

{
  FUN_694276de();
  return;
}



//── FUN_694275b6  @0x00000000694275b6  (20B) ──

void FUN_694275b6(void)

{
  FUN_69427707();
  FUN_694276de();
  return;
}



//── FUN_694275dc  @0x00000000694275dc  (186B) ──

void FUN_694275dc(void)

{
  FUN_69427590();
  return;
}



//── FUN_694276de  @0x00000000694276de  (19B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_694276de(void)

{
  char in_CF;
  bool in_SF;
  int in_stack_00000010;
  undefined1 in_stack_00000014;
  undefined1 in_stack_0000001c;
  undefined2 in_stack_00000020;
  undefined2 uStack00000025;
  undefined1 uStack00000027;
  undefined1 uStack00000029;
  undefined1 uStack0000002a;
  
  uStack00000029 = in_stack_0000001c;
  uStack0000002a = (undefined1)((uint)in_stack_00000010 >> 8);
  uStack00000027 = in_stack_00000014;
  if (!in_SF) {
    uStack00000025 = in_stack_00000020;
    FUN_69427754();
    return;
  }
  uStack00000025 = in_stack_00000020;
  FUN_6942775e();
  (&SUB_12e78012)[in_stack_00000010] = (byte)(&SUB_12e78012)[in_stack_00000010] >> 1 | in_CF << 7;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69427707  @0x0000000069427707  (62B) ──

/* WARNING: Instruction at (ram,0x69427740) overlaps instruction at (ram,0x6942773c)
    */

void FUN_69427707(void)

{
  undefined4 uVar1;
  int extraout_EDX;
  undefined4 *unaff_EDI;
  undefined1 in_PF;
  
  LOCK();
  UNLOCK();
  FUN_69427595();
  if ((bool)in_PF) {
    *(int *)(extraout_EDX + -3) = *(int *)(extraout_EDX + -3) + 1;
  }
  uVar1 = in((short)extraout_EDX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_69427754  @0x0000000069427754  (10B) ──

void FUN_69427754(void)

{
  FUN_6942777d();
  return;
}



//── FUN_6942775e  @0x000000006942775e  (9B) ──

void FUN_6942775e(void)

{
  FUN_69427a63();
  return;
}



//── FUN_6942777d  @0x000000006942777d  (9B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6942777d(void)

{
  int unaff_EBX;
  char in_CF;
  
  FUN_6942775e();
  (&SUB_12e78012)[unaff_EBX] = (byte)(&SUB_12e78012)[unaff_EBX] >> 1 | in_CF << 7;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_694277b3  @0x00000000694277b3  (26B) ──

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_694277b3(void)

{
  undefined2 extraout_DX;
  
  FUN_6942753a();
  in(extraout_DX);
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_694277d1  @0x00000000694277d1  (25B) ──

void FUN_694277d1(void)

{
  FUN_69427968();
  return;
}



//── FUN_69427838  @0x0000000069427838  (11B) ──

void FUN_69427838(void)

{
  FUN_694278de();
  return;
}



//── FUN_69427858  @0x0000000069427858  (27B) ──

void FUN_69427858(void)

{
  FUN_69427819();
  return;
}



//── FUN_694278de  @0x00000000694278de  (92B) ──

/* WARNING: Removing unreachable block (ram,0x6942794a) */

void FUN_694278de(undefined4 param_1,uint param_2,undefined4 param_3,uint *param_4,
                 undefined4 param_5,undefined4 param_6,undefined1 param_7,undefined1 param_8,
                 undefined4 param_9)

{
  char *pcVar1;
  undefined1 uVar2;
  uint uVar3;
  bool in_ZF;
  undefined8 uVar4;
  undefined2 unaff_retaddr;
  undefined2 unaff_retaddr_00;
  undefined1 uStack0000001d;
  undefined2 uStack0000001e;
  undefined1 uStack00000021;
  undefined2 uStack00000022;
  uint *puStack00000059;
  undefined1 uStack_1;
  
  uVar2 = param_7;
  uStack00000021 = (undefined1)unaff_retaddr;
  param_3._2_2_ = SUB42(param_4,0);
  puStack00000059 = param_4;
  param_7 = SUB41(&param_7,0);
  uStack0000001d = (undefined1)((uint)&param_7 >> 8);
  uStack0000001e = (undefined2)((uint)&param_7 >> 0x10);
  uStack_1 = (undefined1)((ushort)unaff_retaddr_00 >> 8);
  param_9._1_1_ = uVar2;
  param_3._0_2_ = param_3._2_2_;
  if (in_ZF) {
    param_9._3_1_ = (undefined1)((uint)param_4 >> 0x18);
    uStack00000022 = (undefined2)(CONCAT22(unaff_retaddr_00,unaff_retaddr) >> 8);
    uStack0000001d = 0x3c;
    uStack0000001e = 0x427a;
    param_8 = 0x69;
    param_9._0_1_ = uStack_1;
    uVar4 = FUN_694279ec();
    uStack0000001e = (undefined2)((ulonglong)uVar4 >> 0x28);
    param_8 = (undefined1)((ulonglong)uVar4 >> 0x38);
    uVar3 = *param_4;
    *param_4 = *param_4 + param_2;
    pcVar1 = (char *)((uint)uVar4 - 0x71);
    *pcVar1 = (*pcVar1 - (char)((ulonglong)uVar4 >> 8)) - CARRY4(uVar3,param_2);
    uVar3 = (uint)uVar4 & 0xffffff0e;
    param_7 = (undefined1)(uVar3 >> 0x10);
    uStack0000001d = (undefined1)(uVar3 >> 0x18);
    param_3._0_2_ = (undefined2)((uint)&stack0x0000001e >> 0x10);
    FUN_69427b33();
    return;
  }
  uStack00000022 = CONCAT11(param_9._2_1_,uVar2);
  FUN_69427936();
  return;
}



//── FUN_69427968  @0x0000000069427968  (63B) ──

void FUN_69427968(undefined1 param_1,undefined4 param_2)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  bool in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined1 uStack00000015;
  undefined1 uStack00000016;
  undefined1 uStack00000017;
  undefined1 uStack00000018;
  undefined1 uStack00000019;
  undefined1 uStack0000001a;
  byte bStack0000001b;
  byte in_stack_0000001c;
  byte bStack0000001d;
  byte bStack0000001e;
  byte bStack0000001f;
  ushort in_stack_00000020;
  undefined1 uStack00000022;
  
  uStack00000019 = in_stack_0000001c;
  uStack00000022 = in_stack_0000001c;
  bStack0000001e =
       (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) | (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10)
       | (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) | (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
  bStack0000001f = 0;
  uStack00000018 = param_1;
  uStack00000016 = SUB41(&stack0x00000016,0);
  uStack00000017 = (undefined1)((uint)&stack0x00000016 >> 8);
  uStack0000001a = SUB41(&stack0x0000001a,0);
  bStack0000001b = (byte)((uint)&stack0x0000001a >> 8);
  in_stack_0000001c = (byte)((uint)&stack0x0000001a >> 0x10);
  bStack0000001d = (byte)((uint)&stack0x0000001a >> 0x18);
  if (!in_SF) {
    FUN_69427858();
    return;
  }
  bStack0000001f =
       (in_ZF & 1) * '@' | 0x80 | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' | in_CF & 1;
  in_stack_00000020 =
       (ushort)((uint)(in_NT & 1) * 0x4000 >> 8) | (ushort)((uint)(in_OF & 1) * 0x800 >> 8) |
       (ushort)((uint)(in_IF & 1) * 0x200 >> 8) | (ushort)((uint)(in_TF & 1) * 0x100 >> 8) |
       (ushort)(in_ID & 1) * 0x2000 | (ushort)(in_VIP & 1) * 0x1000 | (ushort)(in_VIF & 1) * 0x800 |
       (ushort)(in_AC & 1) * 0x400;
  uStack00000022 = 0;
  in_stack_0000001c =
       (byte)((uint)(in_NT & 1) * 0x4000 >> 8) | (byte)((uint)(in_OF & 1) * 0x800 >> 8) |
       (byte)((uint)(in_IF & 1) * 0x200 >> 8) | (byte)((uint)(in_TF & 1) * 0x100 >> 8);
  bStack0000001b =
       (in_ZF & 1) * '@' | 0x80 | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' | in_CF & 1;
  bStack0000001d =
       (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) | (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10)
       | (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) | (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
  bStack0000001e = 0;
  uStack00000017 = 0x80;
  uStack00000018 = 0x78;
  uStack00000019 = 0x42;
  uStack0000001a = 0x69;
  uStack00000015 = FUN_69427838();
  uStack00000017 = (undefined1)param_2;
  uStack00000019 = (undefined1)((uint)param_2 >> 0x10);
  uStack0000001a = (undefined1)((uint)param_2 >> 0x18);
  uStack00000016 = uStack00000019;
  uStack00000018 = uStack00000015;
  FUN_69427936();
  return;
}



//── FUN_694279b7  @0x00000000694279b7  (9B) ──

void __fastcall FUN_694279b7(undefined4 param_1,undefined4 param_2)

{
  uint uVar1;
  int iVar2;
  uint *unaff_EBX;
  uint unaff_EBP;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined1 uStack00000008;
  
  uStack00000008 = (undefined1)((uint)param_2 >> 8);
  if (in_ZF || in_OF != in_SF) {
    iVar2 = FUN_694279ec();
    uVar1 = *unaff_EBX;
    *unaff_EBX = *unaff_EBX + unaff_EBP;
    *(char *)(iVar2 + -0x71) =
         (*(char *)(iVar2 + -0x71) - (char)((uint)iVar2 >> 8)) - CARRY4(uVar1,unaff_EBP);
    FUN_69427b33();
    return;
  }
  FUN_69427a33();
  return;
}



//── FUN_694279c8  @0x00000000694279c8  (17B) ──

void FUN_694279c8(void)

{
  FUN_69427d19();
  return;
}



//── FUN_694279ec  @0x00000000694279ec  (47B) ──

void FUN_694279ec(void)

{
  FUN_694279c8();
  return;
}



//── FUN_69427a33  @0x0000000069427a33  (26B) ──

void FUN_69427a33(void)

{
  uint uVar1;
  int iVar2;
  uint *unaff_EBX;
  uint unaff_EBP;
  
  iVar2 = FUN_694279ec();
  uVar1 = *unaff_EBX;
  *unaff_EBX = *unaff_EBX + unaff_EBP;
  *(char *)(iVar2 + -0x71) =
       (*(char *)(iVar2 + -0x71) - (char)((uint)iVar2 >> 8)) - CARRY4(uVar1,unaff_EBP);
  FUN_69427b33();
  return;
}



//── FUN_69427a63  @0x0000000069427a63  (85B) ──

void FUN_69427a63(void)

{
  code *pcVar1;
  undefined1 uVar2;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined1 *unaff_retaddr;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined8 in_stack_00000020;
  
  LOCK();
  UNLOCK();
  uStack0000001c = (undefined1)((ulonglong)in_stack_00000020 >> 0x10);
  uStack0000001d = (undefined1)((ulonglong)in_stack_00000020 >> 0x18);
  uStack0000001e = (undefined1)((ulonglong)in_stack_00000020 >> 0x20);
  uStack0000001f = (undefined1)((ulonglong)in_stack_00000020 >> 0x28);
  if (!in_ZF && in_OF == in_SF) {
    FUN_694277ff();
    return;
  }
  uVar2 = FUN_694277d1();
  *unaff_retaddr = uVar2;
  pcVar1 = (code *)swi(0x3c);
  (*pcVar1)();
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_69427acc  @0x0000000069427acc  (17B) ──

void FUN_69427acc(void)

{
  thunk_FUN_69427b10();
  return;
}



//── FUN_69427b10  @0x0000000069427b10  (15B) ──

void FUN_69427b10(void)

{
  undefined4 in_stack_00000014;
  undefined4 in_stack_00000018;
  undefined2 uStack0000001e;
  
  uStack0000001e =
       CONCAT11((char)((uint)in_stack_00000014 >> 8),(char)((uint)in_stack_00000018 >> 8));
  FUN_69427bf1();
  return;
}



//── FUN_69427b33  @0x0000000069427b33  (18B) ──

/* WARNING: Instruction at (ram,0x69427b40) overlaps instruction at (ram,0x69427b3c)
    */

void FUN_69427b33(void)

{
  undefined4 uVar1;
  undefined2 extraout_DX;
  undefined4 *unaff_EDI;
  undefined2 uStack00000018;
  
  uStack00000018 = SUB42(unaff_EDI,0);
  FUN_69427acc();
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_69427b6e  @0x0000000069427b6e  (11B) ──

void FUN_69427b6e(void)

{
  FUN_69427af2();
  return;
}



//── FUN_69427ba5  @0x0000000069427ba5  (22B) ──

void FUN_69427ba5(void)

{
  undefined2 uStack00000035;
  
  uStack00000035 = SUB42(&stack0x00000000,0);
  FUN_69427c4e();
  return;
}



//── FUN_69427bcf  @0x0000000069427bcf  (14B) ──

void FUN_69427bcf(void)

{
  undefined2 uStack00000035;
  
  uStack00000035 = SUB42(&stack0x00000000,0);
  FUN_69427c98();
  return;
}



//── FUN_69427bf1  @0x0000000069427bf1  (67B) ──

void FUN_69427bf1(void)

{
  bool in_CF;
  undefined2 uStack00000039;
  
  uStack00000039 = SUB42(&stack0x00000002,0);
  if (!in_CF) {
    FUN_69427ba5();
    return;
  }
  FUN_69427bcf();
  return;
}



//── FUN_69427c7b  @0x0000000069427c7b  (40B) ──

void FUN_69427c7b(void)

{
  FUN_69427cf6();
  return;
}



//── FUN_69427c98  @0x0000000069427c98  (13B) ──

undefined1 FUN_69427c98(void)

{
  undefined1 *unaff_ESI;
  
  FUN_69427c30();
  return *unaff_ESI;
}



//── FUN_69427cf6  @0x0000000069427cf6  (10B) ──

void FUN_69427cf6(void)

{
  undefined1 *puStack0000000c;
  
  puStack0000000c = &stack0x00000020;
  FUN_69427f7f();
  return;
}



//── FUN_69427d19  @0x0000000069427d19  (30B) ──

void FUN_69427d19(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_69427b8d();
    return;
  }
  FUN_69427b33();
  return;
}



//── FUN_69427d4d  @0x0000000069427d4d  (12B) ──

void FUN_69427d4d(void)

{
  undefined1 in_AH;
  undefined4 unaff_retaddr;
  undefined2 uStack00000004;
  undefined2 uStack00000006;
  
  uStack00000006 = (undefined2)((uint)unaff_retaddr >> 0x10);
  uStack00000004 = CONCAT11(in_AH,(char)unaff_retaddr);
  FUN_69427e6e();
  return;
}



//── FUN_69427d7b  @0x0000000069427d7b  (25B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69427d7b(void)

{
  undefined1 uVar1;
  undefined1 *extraout_ECX;
  undefined1 uStack00000004;
  
  uStack00000004 = 0x69;
  uVar1 = FUN_69427d5b();
  *extraout_ECX = uVar1;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69427daa  @0x0000000069427daa  (120B) ──

void FUN_69427daa(undefined4 param_1,undefined4 param_2)

{
  ushort *extraout_EDX;
  byte in_CF;
  undefined1 *puStack0000000c;
  undefined4 in_stack_00000018;
  undefined1 in_stack_00000020;
  undefined4 in_stack_0000009c;
  
  LOCK();
  UNLOCK();
  LOCK();
  UNLOCK();
  puStack0000000c = (undefined1 *)in_stack_00000018;
  FUN_69427e34();
  *extraout_EDX = *extraout_EDX + (ushort)in_CF * (((ushort)extraout_EDX & 3) - (*extraout_EDX & 3))
  ;
  puStack0000000c = &stack0x00000020;
  FUN_69427f11();
  in_stack_0000009c = param_2;
  FUN_69427ef1();
  return;
}



//── FUN_69427e34  @0x0000000069427e34  (36B) ──

void FUN_69427e34(void)

{
  FUN_69427eb6();
  return;
}



//── FUN_69427e6e  @0x0000000069427e6e  (12B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69427e6e(void)

{
  undefined1 uVar1;
  undefined1 *extraout_ECX;
  
  uVar1 = FUN_69427d5b();
  *extraout_ECX = uVar1;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69427e99  @0x0000000069427e99  (12B) ──

void FUN_69427e99(void)

{
  FUN_69427fdb();
  return;
}



//── FUN_69427eb6  @0x0000000069427eb6  (38B) ──

void FUN_69427eb6(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_69427e93();
    return;
  }
  FUN_69427f11();
  FUN_69427ef1();
  return;
}



//── FUN_69427ef1  @0x0000000069427ef1  (13B) ──

void __fastcall FUN_69427ef1(undefined2 param_1)

{
  FUN_69427fe0(param_1);
  return;
}



//── FUN_69427f11  @0x0000000069427f11  (93B) ──

void FUN_69427f11(void)

{
  bool in_PF;
  
  if (in_PF) {
    FUN_69427e99();
    return;
  }
  FUN_69427ef1();
  return;
}



//── FUN_69427f7f  @0x0000000069427f7f  (39B) ──

void FUN_69427f7f(void)

{
  bool in_PF;
  
  if (in_PF) {
    FUN_69427d7b();
    return;
  }
  FUN_69427d4d();
  return;
}



//── FUN_69427fe0  @0x0000000069427fe0  (545B) ──

void __fastcall FUN_69427fe0(undefined4 param_1,undefined1 param_2)

{
  undefined1 uStack0000003f;
  
  uStack0000003f = param_2;
  FUN_6942a764();
  return;
}



//── FUN_6942847e  @0x000000006942847e  (12B) ──

void __fastcall FUN_6942847e(undefined4 param_1,undefined2 param_2)

{
  if ((POPCOUNT(-(char)((ushort)param_2 >> 8)) & 1U) == 0) {
    FUN_69428525();
    return;
  }
  FUN_694284dd();
  return;
}



//── FUN_6942848a  @0x000000006942848a  (9B) ──

void FUN_6942848a(void)

{
  FUN_694284bf();
  return;
}



//── FUN_694284ab  @0x00000000694284ab  (9B) ──

void FUN_694284ab(void)

{
  FUN_6942847e();
  return;
}



//── FUN_694284dd  @0x00000000694284dd  (27B) ──

/* WARNING: Removing unreachable block (ram,0x69428508) */

void FUN_694284dd(void)

{
  thunk_FUN_694285d6();
  return;
}



//── FUN_69428525  @0x0000000069428525  (10B) ──

void FUN_69428525(void)

{
  FUN_6942848a();
  return;
}



//── FUN_6942852f  @0x000000006942852f  (20B) ──

void FUN_6942852f(void)

{
  FUN_69428597();
  return;
}



//── FUN_6942855d  @0x000000006942855d  (11B) ──

void FUN_6942855d(void)

{
  FUN_694284ab();
  return;
}



//── FUN_69428597  @0x0000000069428597  (16B) ──

void FUN_69428597(void)

{
  FUN_694285e4();
  return;
}



//── FUN_694285d6  @0x00000000694285d6  (10B) ──

void FUN_694285d6(void)

{
  FUN_69428597();
  return;
}



//── FUN_69428627  @0x0000000069428627  (14B) ──

void FUN_69428627(void)

{
  FUN_6942860a();
  return;
}



//── FUN_6942864d  @0x000000006942864d  (55B) ──

/* WARNING: Instruction at (ram,0x6942866f) overlaps instruction at (ram,0x6942866d)
    */

void FUN_6942864d(void)

{
  char *pcVar1;
  char cVar2;
  code *pcVar3;
  uint uVar4;
  undefined1 *unaff_ESI;
  uint unaff_EDI;
  undefined6 uVar5;
  
  uVar5 = FUN_69428627();
  out(*unaff_ESI,(short)((uint6)uVar5 >> 0x20));
  uVar4 = (uint)uVar5 | unaff_EDI;
  DAT_a15237a7 = DAT_a15237a7 + (char)(uVar4 >> 8);
  pcVar3 = (code *)swi(4);
  if (SBORROW4(*(int *)(unaff_EDI - 6),unaff_EDI)) {
    uVar4 = (*pcVar3)();
  }
  pcVar1 = unaff_ESI + 0x67;
  cVar2 = *pcVar1;
  *pcVar1 = *pcVar1 << 1;
  if (cVar2 < '\0' || (char)uVar4 == '>') {
    FUN_6942847e();
    return;
  }
  FUN_6942855d();
  return;
}



//── FUN_69428686  @0x0000000069428686  (30B) ──

void FUN_69428686(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    FUN_6942847e();
    return;
  }
  FUN_6942855d();
  return;
}



//── FUN_694286c9  @0x00000000694286c9  (17B) ──

void FUN_694286c9(void)

{
  short sVar1;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  uint uStack00000099;
  
  uStack00000099 =
       (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
       (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
       (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1) |
       (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
       (uint)(in_AC & 1) * 0x40000;
  for (sVar1 = 0xf; 0x6d74U >> sVar1 == 0; sVar1 = sVar1 + -1) {
  }
  FUN_69428686();
  return;
}



//── FUN_6942904a  @0x000000006942904a  (13B) ──

void FUN_6942904a(void)

{
  FUN_694286c9();
  return;
}



//── FUN_69429db2  @0x0000000069429db2  (21B) ──

void __fastcall
FUN_69429db2(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4,
            undefined4 param_5,undefined4 param_6,undefined4 param_7)

{
  short sVar1;
  undefined1 unaff_BL;
  undefined4 unaff_ESI;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  uint uStack000000a7;
  
  param_6 = param_5;
  param_5._3_1_ = (undefined1)((uint)param_7 >> 0x18);
  param_4._3_1_ = (char)&param_5 + '\x03';
  param_3._0_2_ = CONCAT11(unaff_BL,(char)unaff_ESI);
  param_4._2_1_ = (undefined1)((uint)param_2 >> 8);
  param_3._2_1_ = (undefined1)((uint)unaff_ESI >> 0x10);
  param_3._3_1_ = (undefined1)((uint)unaff_ESI >> 0x18);
  uStack000000a7 =
       (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
       (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
       (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1) |
       (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
       (uint)(in_AC & 1) * 0x40000;
  for (sVar1 = 0xf; 0x6d74U >> sVar1 == 0; sVar1 = sVar1 + -1) {
  }
  FUN_69428686();
  return;
}



//── FUN_6942a764  @0x000000006942a764  (30B) ──

void FUN_6942a764(void)

{
  bool in_CF;
  
  if (!in_CF) {
    FUN_69429db2();
    return;
  }
  FUN_6942904a();
  return;
}



//── FUN_6942e1c2  @0x000000006942e1c2  (14B) ──

void FUN_6942e1c2(void)

{
  bool in_CF;
  
  if (in_CF) {
                    /* WARNING: Subroutine does not return */
    thunk_FUN_694277b3();
  }
                    /* WARNING: Subroutine does not return */
  FUN_694277b3(0x1d10d934);
}



//── FUN_6942e388  @0x000000006942e388  (10B) ──

void FUN_6942e388(void)

{
  FUN_6942e464();
  return;
}



//── FUN_6942e464  @0x000000006942e464  (9B) ──

void FUN_6942e464(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_69430985  @0x0000000069430985  (10B) ──

void FUN_69430985(void)

{
  FUN_69430a3d();
  return;
}



//── FUN_69430a92  @0x0000000069430a92  (10B) ──

void FUN_69430a92(void)

{
  FUN_69430c2a();
  return;
}



//── FUN_69430ad0  @0x0000000069430ad0  (10B) ──

void FUN_69430ad0(void)

{
  FUN_69430b9c();
  return;
}



//── FUN_69430bc8  @0x0000000069430bc8  (10B) ──

void FUN_69430bc8(void)

{
  FUN_69433fd2();
  return;
}



//── FUN_69430c2a  @0x0000000069430c2a  (11B) ──

void FUN_69430c2a(void)

{
  bool in_CF;
  
  if (in_CF) {
                    /* WARNING: Subroutine does not return */
    thunk_FUN_694277b3();
  }
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_69433f9a  @0x0000000069433f9a  (10B) ──

void FUN_69433f9a(void)

{
  FUN_6943406e();
  return;
}



//── FUN_69433fb2  @0x0000000069433fb2  (15B) ──

void FUN_69433fb2(void)

{
  FUN_6943424f();
  return;
}



//── FUN_69433fd2  @0x0000000069433fd2  (11B) ──

void FUN_69433fd2(void)

{
  bool in_PF;
  
  if (in_PF) {
                    /* WARNING: Subroutine does not return */
    thunk_FUN_694277b3();
  }
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_6943406e  @0x000000006943406e  (9B) ──

void FUN_6943406e(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_6943424f  @0x000000006943424f  (11B) ──

void FUN_6943424f(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_69444c10  @0x0000000069444c10  (12B) ──

void FUN_69444c10(void)

{
  FUN_69444c77();
  return;
}



//── FUN_69444c91  @0x0000000069444c91  (16B) ──

void FUN_69444c91(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3(0x1d125681);
}



//── FUN_69444d37  @0x0000000069444d37  (10B) ──

void FUN_69444d37(void)

{
  FUN_69444ded();
  return;
}



//── FUN_69444d77  @0x0000000069444d77  (10B) ──

void FUN_69444d77(void)

{
  FUN_69444e80();
  return;
}



//── FUN_6944c6c9  @0x000000006944c6c9  (10B) ──

void FUN_6944c6c9(void)

{
  FUN_6944c8c6();
  return;
}



//── FUN_6944c78c  @0x000000006944c78c  (12B) ──

void FUN_6944c78c(void)

{
  FUN_6944c80e();
  return;
}



//── FUN_6944c7b3  @0x000000006944c7b3  (9B) ──

void FUN_6944c7b3(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_6944c83b  @0x000000006944c83b  (10B) ──

void FUN_6944c83b(void)

{
  FUN_6944c7b3();
  return;
}



//── FUN_6944c8c6  @0x000000006944c8c6  (11B) ──

void FUN_6944c8c6(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
                    /* WARNING: Subroutine does not return */
    thunk_FUN_694277b3();
  }
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_6944d471  @0x000000006944d471  (11B) ──

void FUN_6944d471(void)

{
  return;
}



//── FUN_6944eeb0  @0x000000006944eeb0  (11B) ──

void FUN_6944eeb0(void)

{
  return;
}



//── FUN_6944eee4  @0x000000006944eee4  (11B) ──

void FUN_6944eee4(void)

{
  return;
}



//── FUN_6944f523  @0x000000006944f523  (11B) ──

void FUN_6944f523(void)

{
  return;
}



//── FUN_6944f620  @0x000000006944f620  (11B) ──

void FUN_6944f620(void)

{
  return;
}



//── FUN_6944f72f  @0x000000006944f72f  (11B) ──

void FUN_6944f72f(void)

{
  return;
}



//── FUN_6944f7c5  @0x000000006944f7c5  (11B) ──

void FUN_6944f7c5(void)

{
  return;
}



//── FUN_6944f7d3  @0x000000006944f7d3  (11B) ──

void FUN_6944f7d3(void)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  ushort uVar1;
  undefined4 uStack0000001c;
  
  uVar1 = (ushort)(in_NT & 1) * 0x4000 | (ushort)(in_OF & 1) * 0x800 | (ushort)(in_IF & 1) * 0x200 |
          (ushort)(in_TF & 1) * 0x100 | (ushort)(in_SF & 1) * 0x80 | (ushort)(in_ZF & 1) * 0x40 |
          (ushort)(in_AF & 1) * 0x10 | (ushort)(in_PF & 1) * 4 | (ushort)(in_CF & 1);
  uStack0000001c = CONCAT22(uVar1,uVar1);
  FUN_6944f8c4();
  return;
}



//── FUN_6944f7f2  @0x000000006944f7f2  (21B) ──

void FUN_6944f7f2(void)

{
  FUN_6944f7d3();
  return;
}



//── FUN_6944f820  @0x000000006944f820  (35B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6944f83a) overlaps instruction at (ram,0x6944f839)
    */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: This function may have set the stack pointer */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6944f820(void)

{
  int *piVar1;
  byte bVar2;
  byte extraout_CL;
  undefined2 uVar3;
  int unaff_EBX;
  undefined4 *unaff_ESI;
  int unaff_EDI;
  undefined2 in_SS;
  byte in_SF;
  bool bVar4;
  undefined6 uVar5;
  
  FUN_6944f7f2();
  piVar1 = (int *)(unaff_EBX + 0x224648d);
  bVar2 = extraout_CL & 0x1f;
  _DAT_bd5dba4b = in_SS;
  *piVar1 = *piVar1 << bVar2;
  bVar4 = (bool)(bVar2 == 0 & in_SF | (bVar2 != 0 && *piVar1 < 0));
  _DAT_bd5dba47 = 0x6944f839;
  uVar5 = FUN_6944f871();
  uVar3 = (undefined2)((uint6)uVar5 >> 0x20);
  if (bVar4) {
    out(*unaff_ESI,uVar3);
    out(uVar3,(int)uVar5);
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
                    /* WARNING: Could not recover jumptable at 0x6944f83a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(unaff_EDI + 10))();
  return;
}



//── FUN_6944f84f  @0x000000006944f84f  (15B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6944f83a) overlaps instruction at (ram,0x6944f839)
    */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: This function may have set the stack pointer */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6944f84f(void)

{
  int *piVar1;
  byte bVar2;
  byte extraout_CL;
  undefined2 uVar3;
  int unaff_EBX;
  undefined4 *unaff_ESI;
  int unaff_EDI;
  undefined2 in_SS;
  bool in_CF;
  bool in_ZF;
  bool bVar4;
  byte in_SF;
  undefined6 uVar5;
  
  if (!in_CF && !in_ZF) {
    thunk_FUN_6944f820();
    return;
  }
  FUN_6944f7f2();
  piVar1 = (int *)(unaff_EBX + 0x224648d);
  bVar2 = extraout_CL & 0x1f;
  _DAT_bd5dba4b = in_SS;
  *piVar1 = *piVar1 << bVar2;
  bVar4 = (bool)(bVar2 == 0 & in_SF | (bVar2 != 0 && *piVar1 < 0));
  _DAT_bd5dba47 = 0x6944f839;
  uVar5 = FUN_6944f871();
  uVar3 = (undefined2)((uint6)uVar5 >> 0x20);
  if (bVar4) {
    out(*unaff_ESI,uVar3);
    out(uVar3,(int)uVar5);
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
                    /* WARNING: Could not recover jumptable at 0x6944f83a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(unaff_EDI + 10))();
  return;
}



//── FUN_6944f871  @0x000000006944f871  (11B) ──

void FUN_6944f871(void)

{
  FUN_6944f95b();
  return;
}



//── FUN_6944f8c4  @0x000000006944f8c4  (64B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6944f83a) overlaps instruction at (ram,0x6944f839)
    */

void FUN_6944f8c4(void)

{
  undefined2 uVar1;
  undefined4 *unaff_ESI;
  int unaff_EDI;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined6 uVar2;
  undefined1 uStack00000004;
  
  uStack00000004 = (undefined1)((uint)&stack0x00000002 >> 8);
  if (in_ZF || in_OF != in_SF) {
    FUN_6944f891();
    return;
  }
  uVar2 = FUN_6944f871();
  uVar1 = (undefined2)((uint6)uVar2 >> 0x20);
  if ((bool)in_SF) {
    out(*unaff_ESI,uVar1);
    out(uVar1,(int)uVar2);
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
                    /* WARNING: Could not recover jumptable at 0x6944f83a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(unaff_EDI + 10))();
  return;
}



//── FUN_6944f937  @0x000000006944f937  (13B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6944f83a) overlaps instruction at (ram,0x6944f839)
    */
/* WARNING (jumptable): Unable to track spacebase fully for stack */
/* WARNING: Unable to track spacebase fully for stack */

void FUN_6944f937(void)

{
  uint uVar1;
  uint uVar3;
  uint uVar4;
  undefined1 extraout_CL;
  undefined2 uVar5;
  undefined4 *puVar6;
  undefined2 unaff_BX;
  undefined4 unaff_EBP;
  undefined4 *unaff_ESI;
  uint *puVar7;
  uint *unaff_EDI;
  byte in_AF;
  undefined1 in_ZF;
  undefined1 in_SF;
  byte in_TF;
  byte in_IF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined8 uVar8;
  undefined6 uVar9;
  uint uVar2;
  
  uVar8 = FUN_6944f9e0();
  puVar6 = (undefined4 *)((ulonglong)uVar8 >> 0x20);
  uVar4 = (uint)uVar8;
  puVar7 = unaff_EDI;
  if (!(bool)in_ZF) {
    *(undefined1 *)((int)unaff_EDI + -0x5adb6bae) = 0;
    puVar7 = unaff_EDI + 1;
    uVar1 = *unaff_EDI;
    uVar2 = *unaff_EDI;
    uVar3 = uVar4 - *unaff_EDI;
    in_SF = (int)uVar3 < 0;
    *puVar6 = unaff_ESI;
    puVar6[-1] = 0x669c05b1;
    *(undefined4 *)((int)puVar6 + 1) = puVar6[-1];
    *(undefined2 *)puVar6 = unaff_BX;
    *puVar6 = unaff_EBP;
    puVar6[-1] = (uint)(in_NT & 1) * 0x4000 | (uint)SBORROW4(uVar4,uVar2) * 0x800 |
                 (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 | (uint)(byte)in_SF * 0x80 |
                 (uint)(uVar3 == 0) * 0x40 | (uint)(in_AF & 1) * 0x10 |
                 (uint)((POPCOUNT(uVar3 & 0xff) & 1U) == 0) * 4 | (uint)(uVar4 < uVar1) |
                 (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
                 (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000;
    *puVar6 = puVar6[-1];
    *(undefined2 *)((int)puVar6 + -2) = *(undefined2 *)((int)puVar6 + 3);
    *(undefined1 *)((int)puVar6 + 2) = extraout_CL;
    *(undefined4 *)((int)puVar6 + -6) = *(undefined4 *)((int)puVar6 + -2);
    *(undefined2 *)(puVar6 + -2) = *(undefined2 *)((int)puVar6 + -2);
    *(undefined2 *)((int)puVar6 + -10) = *(undefined2 *)((int)puVar6 + 1);
    puVar6[-2] = unaff_ESI;
    *(short *)((int)puVar6 + 5) = (short)((ulonglong)uVar8 >> 0x20) + 4;
    if (uVar3 == 0 || (int)uVar4 < (int)uVar2) {
      FUN_6944f891();
      return;
    }
  }
  uVar9 = FUN_6944f871();
  uVar5 = (undefined2)((uint6)uVar9 >> 0x20);
  if (!(bool)in_SF) {
                    /* WARNING: Could not recover jumptable at 0x6944f83a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    (**(code **)((int)puVar7 + 10))();
    return;
  }
  out(*unaff_ESI,uVar5);
  out(uVar5,(int)uVar9);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6944f95b  @0x000000006944f95b  (85B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6944f83a) overlaps instruction at (ram,0x6944f839)
    */
/* WARNING (jumptable): Unable to track spacebase fully for stack */
/* WARNING: Unable to track spacebase fully for stack */

void FUN_6944f95b(undefined4 *param_1,undefined4 param_2,undefined4 param_3,undefined2 param_4)

{
  uint uVar1;
  uint uVar3;
  byte bVar4;
  uint uVar5;
  undefined1 extraout_CL;
  undefined2 uVar6;
  undefined4 *puVar7;
  uint *puVar8;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  bool in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined8 uVar9;
  undefined6 uVar10;
  uint *unaff_retaddr;
  short sStack0000001a;
  byte bStack0000001c;
  byte bStack0000001d;
  byte bStack0000001e;
  byte bStack0000001f;
  uint uVar2;
  
  bStack0000001d =
       (byte)((uint)(in_NT & 1) * 0x4000 >> 8) | (byte)((uint)(in_OF & 1) * 0x800 >> 8) |
       (byte)((uint)(in_IF & 1) * 0x200 >> 8) | (byte)((uint)(in_TF & 1) * 0x100 >> 8);
  bStack0000001f = bStack0000001d;
  bStack0000001c =
       in_SF * -0x80 | (in_ZF & 1U) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' | in_CF & 1;
  bVar4 = bStack0000001c;
  bStack0000001e =
       (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) | (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10)
       | (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) | (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
  if (!in_ZF && in_OF == in_SF) {
    bStack0000001f = 0;
    FUN_6944f937();
    return;
  }
  sStack0000001a = 0xf8ae;
  bStack0000001c = 0x44;
  bStack0000001d = 0x69;
  bStack0000001e = bVar4;
  uVar9 = FUN_6944f9e0();
  puVar7 = (undefined4 *)((ulonglong)uVar9 >> 0x20);
  uVar5 = (uint)uVar9;
  puVar8 = unaff_retaddr;
  if (!in_ZF) {
    sStack0000001a = (short)((ulonglong)uVar9 >> 0x20);
    bStack0000001c = (byte)((ulonglong)uVar9 >> 0x30);
    bStack0000001d = (byte)((ulonglong)uVar9 >> 0x38);
    *(undefined1 *)((int)unaff_retaddr + -0x5adb6bae) = 0;
    puVar8 = unaff_retaddr + 1;
    uVar1 = *unaff_retaddr;
    uVar2 = *unaff_retaddr;
    uVar3 = uVar5 - *unaff_retaddr;
    in_SF = (int)uVar3 < 0;
    *puVar7 = param_1;
    puVar7[-1] = 0x669c05b1;
    *(undefined4 *)((int)puVar7 + 1) = puVar7[-1];
    *(undefined2 *)puVar7 = param_4;
    *puVar7 = param_2;
    puVar7[-1] = (uint)(in_NT & 1) * 0x4000 | (uint)SBORROW4(uVar5,uVar2) * 0x800 |
                 (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 | (uint)in_SF * 0x80 |
                 (uint)(uVar3 == 0) * 0x40 | (uint)(in_AF & 1) * 0x10 |
                 (uint)((POPCOUNT(uVar3 & 0xff) & 1U) == 0) * 4 | (uint)(uVar5 < uVar1) |
                 (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
                 (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000;
    *puVar7 = puVar7[-1];
    *(undefined2 *)((int)puVar7 + -2) = *(undefined2 *)((int)puVar7 + 3);
    *(undefined1 *)((int)puVar7 + 2) = extraout_CL;
    *(undefined4 *)((int)puVar7 + -6) = *(undefined4 *)((int)puVar7 + -2);
    *(undefined2 *)(puVar7 + -2) = *(undefined2 *)((int)puVar7 + -2);
    *(undefined2 *)((int)puVar7 + -10) = *(undefined2 *)((int)puVar7 + 1);
    puVar7[-2] = param_1;
    *(short *)((int)puVar7 + 5) = sStack0000001a + 4;
    if (uVar3 == 0 || (int)uVar5 < (int)uVar2) {
      FUN_6944f891();
      return;
    }
  }
  sStack0000001a = 0xf839;
  bStack0000001c = 0x44;
  bStack0000001d = 0x69;
  uVar10 = FUN_6944f871();
  uVar6 = (undefined2)((uint6)uVar10 >> 0x20);
  if (!(bool)in_SF) {
                    /* WARNING: Could not recover jumptable at 0x6944f83a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    (**(code **)((int)puVar8 + 10))();
    return;
  }
  out(*param_1,uVar6);
  out(uVar6,(int)uVar10);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6944f99e  @0x000000006944f99e  (47B) ──

void FUN_6944f99e(void)

{
  undefined1 *puStack0000000c;
  
  puStack0000000c = &stack0x00000020;
  FUN_6944fc39();
  return;
}



//── FUN_6944f9e0  @0x000000006944f9e0  (15B) ──

void FUN_6944f9e0(void)

{
  FUN_6944f99e();
  return;
}



//── FUN_6944fa1c  @0x000000006944fa1c  (55B) ──

/* WARNING: Removing unreachable block (ram,0x6944fa49) */

void FUN_6944fa1c(void)

{
  code *pcVar1;
  
  FUN_6944faf5();
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_6944fa9c  @0x000000006944fa9c  (19B) ──

void FUN_6944fa9c(void)

{
  FUN_6944fa1c();
  return;
}



//── FUN_6944faf5  @0x000000006944faf5  (65B) ──

void FUN_6944faf5(void)

{
  FUN_6944fad7();
  return;
}



//── FUN_6944fb56  @0x000000006944fb56  (13B) ──

void FUN_6944fb56(void)

{
  FUN_6944fb34();
  return;
}



//── FUN_6944fb6c  @0x000000006944fb6c  (23B) ──

void FUN_6944fb6c(void)

{
  FUN_6944fb39();
  return;
}



//── FUN_6944fbf4  @0x000000006944fbf4  (10B) ──

void FUN_6944fbf4(void)

{
  FUN_6944fd3b();
  return;
}



//── FUN_6944fc39  @0x000000006944fc39  (17B) ──

void __fastcall FUN_6944fc39(undefined4 param_1,undefined1 param_2)

{
  bool in_SF;
  undefined1 uStack00000007;
  
  uStack00000007 = param_2;
  if (!in_SF) {
    FUN_6944fa9c();
    return;
  }
  FUN_6944fa1c();
  return;
}



//── FUN_6944fc72  @0x000000006944fc72  (15B) ──

void __fastcall FUN_6944fc72(undefined4 param_1,undefined4 param_2)

{
  int unaff_EBP;
  
  *(undefined4 *)(unaff_EBP + -4) = param_2;
  FUN_6944fcbf();
  return;
}



//── FUN_6944fc9a  @0x000000006944fc9a  (13B) ──

void FUN_6944fc9a(void)

{
  int unaff_EBP;
  
  if (*(int *)(unaff_EBP + 8) == 0) {
    FUN_6944fc4b();
    return;
  }
  FUN_6944fcb0();
  return;
}



//── FUN_6944fcb0  @0x000000006944fcb0  (14B) ──

void FUN_6944fcb0(void)

{
  undefined4 in_EAX;
  int unaff_EBP;
  
  *(undefined4 *)(unaff_EBP + -8) = in_EAX;
  FUN_6944fc72();
  return;
}



//── FUN_6944fcf5  @0x000000006944fcf5  (15B) ──

void FUN_6944fcf5(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    thunk_FUN_69450010();
    return;
  }
  FUN_6944fd55();
  return;
}



//── FUN_6944fd16  @0x000000006944fd16  (16B) ──

void FUN_6944fd16(void)

{
  int unaff_EBP;
  
  if (*(int *)(unaff_EBP + 8) == 0) {
    FUN_6944fc4b();
    return;
  }
  FUN_6944fcb0();
  return;
}



//── FUN_6944fd3b  @0x000000006944fd3b  (27B) ──

void FUN_6944fd3b(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_6944fd16();
    return;
  }
  FUN_6944fc9a();
  return;
}



//── FUN_6944fd55  @0x000000006944fd55  (54B) ──

void FUN_6944fd55(void)

{
  int unaff_EBP;
  
  if (*(uint *)(unaff_EBP + 8) == 0) {
    thunk_FUN_6944fe07();
    return;
  }
  *(undefined4 *)(unaff_EBP + -4) = *(undefined4 *)(unaff_EBP + 8);
  if ((POPCOUNT(*(uint *)(unaff_EBP + 8) & 0xff) & 1U) == 0) {
    FUN_6944fe90();
    return;
  }
  FUN_6944ff2e();
  return;
}



//── FUN_6944fdc4  @0x000000006944fdc4  (10B) ──

void FUN_6944fdc4(void)

{
  FUN_6944fd55();
  return;
}



//── FUN_6944fe07  @0x000000006944fe07  (12B) ──

void FUN_6944fe07(void)

{
  FUN_694500a1();
  return;
}



//── FUN_6944fe6f  @0x000000006944fe6f  (12B) ──

/* WARNING: Control flow encountered bad instruction data */

void __fastcall FUN_6944fe6f(undefined4 param_1)

{
  byte *pbVar1;
  byte extraout_CL;
  undefined1 uVar2;
  undefined1 extraout_CH;
  byte extraout_DL;
  int unaff_ESI;
  uint *unaff_EDI;
  char in_CF;
  bool bVar3;
  undefined1 in_ZF;
  char in_SF;
  char in_OF;
  
  uVar2 = (undefined1)((uint)param_1 >> 8);
  if (!(bool)in_ZF && in_OF == in_SF) {
    FUN_6944ff47();
    return;
  }
  while( true ) {
    FUN_6944ffb8(uVar2);
    bVar3 = in_CF == '\0';
    if (!bVar3 && !(bool)in_ZF) break;
    pbVar1 = (byte *)(unaff_ESI + 0x759e6304);
    in_CF = CARRY1(*pbVar1,extraout_DL) || CARRY1(*pbVar1 + extraout_DL,bVar3);
    *pbVar1 = *pbVar1 + extraout_DL + bVar3;
    in_ZF = *pbVar1 == 0;
    uVar2 = extraout_CH;
  }
  in(0x17);
  *unaff_EDI = *unaff_EDI >> (extraout_CL & 0x1f) | *unaff_EDI << 0x20 - (extraout_CL & 0x1f);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6944fe90  @0x000000006944fe90  (10B) ──

void FUN_6944fe90(void)

{
  FUN_6944fe5c();
  return;
}



//── FUN_6944fe9c  @0x000000006944fe9c  (14B) ──

void FUN_6944fe9c(void)

{
  char *pcVar1;
  
  pcVar1 = (char *)FUN_6944fed5();
  *pcVar1 = *pcVar1 + (char)pcVar1;
  FUN_6944fe6f();
  return;
}



//── FUN_6944febf  @0x000000006944febf  (18B) ──

void FUN_6944febf(void)

{
  FUN_6944fe5c();
  return;
}



//── FUN_6944fed5  @0x000000006944fed5  (70B) ──

void FUN_6944fed5(void)

{
  FUN_6944fe6f();
  return;
}



//── FUN_6944ff2e  @0x000000006944ff2e  (10B) ──

void FUN_6944ff2e(void)

{
  FUN_6944febf();
  return;
}



//── FUN_6944ffb8  @0x000000006944ffb8  (51B) ──

void FUN_6944ffb8(void)

{
  LOCK();
  UNLOCK();
  FUN_69453c3a();
  return;
}



//── FUN_69450029  @0x0000000069450029  (9B) ──

void FUN_69450029(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_6944fe07();
    return;
  }
  FUN_6945006d();
  return;
}



//── FUN_69450060  @0x0000000069450060  (9B) ──

void FUN_69450060(void)

{
  FUN_69450029();
  return;
}



//── FUN_694500a1  @0x00000000694500a1  (18B) ──

void __fastcall FUN_694500a1(undefined4 param_1,undefined2 param_2)

{
  byte in_AL;
  bool in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined1 uVar1;
  ushort uVar2;
  
  if (in_CF) {
    uVar2 = (ushort)in_AL;
    uVar1 = (undefined1)((ushort)param_2 >> 8);
    FUN_694500b6(CONCAT13((char)param_2,
                          (uint3)(in_NT & 1) * 0x4000 | (uint3)(in_OF & 1) * 0x800 |
                          (uint3)(in_IF & 1) * 0x200 | (uint3)(in_TF & 1) * 0x100 |
                          (uint3)(in_SF & 1) * 0x80 | (uint3)(in_ZF & 1) * 0x40 |
                          (uint3)(in_AF & 1) * 0x10 | (uint3)(in_PF & 1) * 4 | 1 |
                          (uint3)(in_ID & 1) * 0x200000 | (uint3)(in_VIP & 1) * 0x100000 |
                          (uint3)(in_VIF & 1) * 0x80000 | (uint3)(in_AC & 1) * 0x40000),uVar1,uVar2)
    ;
    FUN_694504aa(uVar1,uVar2);
    return;
  }
  FUN_69450100();
  return;
}



//── FUN_694500b6  @0x00000000694500b6  (20B) ──

void FUN_694500b6(void)

{
  LOCK();
  UNLOCK();
  FUN_69450124();
  return;
}



//── FUN_694500e2  @0x00000000694500e2  (16B) ──

void __fastcall FUN_694500e2(undefined4 param_1,undefined1 param_2)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  
  FUN_694500b6(CONCAT13(param_2,(uint3)(in_NT & 1) * 0x4000 | (uint3)(in_OF & 1) * 0x800 |
                                (uint3)(in_IF & 1) * 0x200 | (uint3)(in_TF & 1) * 0x100 |
                                (uint3)(in_SF & 1) * 0x80 | (uint3)(in_ZF & 1) * 0x40 |
                                (uint3)(in_AF & 1) * 0x10 | (uint3)(in_PF & 1) * 4 |
                                (uint3)(in_CF & 1) | (uint3)(in_ID & 1) * 0x200000 |
                                (uint3)(in_VIP & 1) * 0x100000 | (uint3)(in_VIF & 1) * 0x80000 |
                                (uint3)(in_AC & 1) * 0x40000));
  FUN_694504aa();
  return;
}



//── FUN_69450100  @0x0000000069450100  (9B) ──

void FUN_69450100(void)

{
  FUN_69450082();
  return;
}



//── FUN_69450181  @0x0000000069450181  (54B) ──

void FUN_69450181(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_69450060();
    return;
  }
  if (!in_ZF) {
    FUN_6944fe07();
    return;
  }
  FUN_6945006d();
  return;
}



//── FUN_69450191  @0x0000000069450191  (26B) ──

void FUN_69450191(void)

{
  undefined1 in_ZF;
  char in_SF;
  char in_OF;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  byte bStack00000004;
  undefined1 uStack00000005;
  undefined2 uStack00000006;
  
  bStack00000004 = 0;
  uStack00000005 = (undefined1)((uint)&stack0x00000000 >> 8);
  uStack00000006 = (undefined2)((uint)&stack0x00000000 >> 0x10);
  thunk_FUN_694501ba();
  bStack00000004 =
       (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) | (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10)
       | (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) | (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
  uStack00000005 = 0;
  if ((bool)in_ZF || in_OF != in_SF) {
    FUN_694502d3();
    return;
  }
  FUN_6945036c();
  return;
}



//── FUN_6945019b  @0x000000006945019b  (10B) ──

void FUN_6945019b(void)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  
  FUN_6945025a((uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
               (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
               (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1) |
               (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
               (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000);
  return;
}



//── FUN_694501ba  @0x00000000694501ba  (92B) ──

void FUN_694501ba(void)

{
  undefined2 unaff_SI;
  
  FUN_6945019b(unaff_SI);
  return;
}



//── FUN_6945025a  @0x000000006945025a  (54B) ──

void FUN_6945025a(void)

{
  undefined1 unaff_BL;
  byte in_CF;
  bool in_PF;
  byte in_AF;
  bool in_ZF;
  char in_SF;
  char in_OF;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  byte bStack00000020;
  ushort uStack00000022;
  undefined4 uStack00000024;
  undefined4 uStack00000028;
  
  if (in_PF) {
    bStack00000020 =
         in_SF * -0x80 | (in_ZF & 1U) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1U) * '\x04' |
         in_CF & 1;
    uStack00000022 =
         (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8 |
         (ushort)(in_AC & 1) * 4;
    _bStack00000020 = CONCAT11(unaff_BL,bStack00000020);
  }
  else {
    bStack00000020 =
         in_SF * -0x80 | (in_ZF & 1U) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1U) * '\x04' |
         in_CF & 1;
    uStack00000022 =
         (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8 |
         (ushort)(in_AC & 1) * 4;
    _bStack00000020 = CONCAT11(unaff_BL,bStack00000020);
  }
  uStack00000024 = _bStack00000020;
  uStack00000028 = _bStack00000020;
  if (in_ZF || in_OF != in_SF) {
    FUN_694502d3();
    return;
  }
  FUN_6945036c();
  return;
}



//── FUN_694502d3  @0x00000000694502d3  (10B) ──

void FUN_694502d3(void)

{
  return;
}



//── FUN_6945038a  @0x000000006945038a  (101B) ──

void FUN_6945038a(void)

{
  FUN_69450181();
  return;
}



//── FUN_694507eb  @0x00000000694507eb  (31B) ──

void FUN_694507eb(void)

{
  byte bVar1;
  undefined2 extraout_var;
  char *pcVar2;
  
  FUN_6945038a();
  bVar1 = in(199);
  DAT_4c000000 = bVar1 % 0;
  pcVar2 = (char *)(CONCAT31((int3)(CONCAT22(extraout_var,CONCAT11(bVar1 / 0,bVar1)) >> 8),
                             DAT_4c000000) & 0xffffffff);
  *pcVar2 = *pcVar2 + DAT_4c000000;
  return;
}



//── FUN_6945259b  @0x000000006945259b  (62B) ──

char * FUN_6945259b(char *param_1)

{
  char cVar1;
  char *local_8;
  
  local_8 = param_1;
  do {
    cVar1 = *local_8;
    local_8 = local_8 + 1;
  } while (cVar1 != '\0');
  return local_8 + (-1 - (int)param_1);
}



//── FUN_69453c3a  @0x0000000069453c3a  (52B) ──

void FUN_69453c3a(void)

{
  byte bVar1;
  undefined2 extraout_var;
  char *pcVar2;
  bool in_PF;
  
  if (in_PF) {
    FUN_694507eb();
    return;
  }
  FUN_6945038a();
  bVar1 = in(199);
  DAT_4c000000 = bVar1 % 0;
  pcVar2 = (char *)(CONCAT31((int3)(CONCAT22(extraout_var,CONCAT11(bVar1 / 0,bVar1)) >> 8),
                             DAT_4c000000) & 0xffffffff);
  *pcVar2 = *pcVar2 + DAT_4c000000;
  return;
}



//── FUN_6945da0b  @0x000000006945da0b  (75B) ──

void FUN_6945da0b(undefined4 *param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4,
                 undefined4 param_5)

{
  param_1[1] = 0;
  *param_1 = 0;
  param_1[2] = param_2;
  param_1[3] = param_3;
  param_1[4] = param_4;
  param_1[5] = param_5;
  return;
}



//── FUN_6945e76c  @0x000000006945e76c  (27B) ──

void FUN_6945e76c(void)

{
  FUN_6945e971();
  return;
}



//── FUN_69460104  @0x0000000069460104  (37B) ──

void FUN_69460104(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_694704d2  @0x00000000694704d2  (16B) ──

void FUN_694704d2(void)

{
  bool in_SF;
  
  if (!in_SF) {
                    /* WARNING: Subroutine does not return */
    thunk_FUN_694277b3();
  }
                    /* WARNING: Subroutine does not return */
  FUN_694277b3(0x1d14fa6b);
}



//── FUN_694780b3  @0x00000000694780b3  (10B) ──

void FUN_694780b3(void)

{
  FUN_6942e381();
  FUN_694780e0();
  return;
}



//── FUN_694780e0  @0x00000000694780e0  (10B) ──

void FUN_694780e0(void)

{
  FUN_6942e388();
  FUN_69478120();
  return;
}



//── FUN_694780ef  @0x00000000694780ef  (17B) ──

void FUN_694780ef(void)

{
  FUN_69478145();
  FUN_6947a049();
  return;
}



//── FUN_69478145  @0x0000000069478145  (66B) ──

void __fastcall FUN_69478145(undefined4 param_1)

{
  FUN_69478487((char)((uint)param_1 >> 0x18));
  return;
}



//── FUN_694783a2  @0x00000000694783a2  (34B) ──

void FUN_694783a2(void)

{
  code *pcVar1;
  char *extraout_EDX;
  undefined4 unaff_EBX;
  undefined4 unaff_EBP;
  undefined4 *unaff_ESI;
  undefined4 *unaff_EDI;
  bool in_ZF;
  undefined1 uStack00000007;
  undefined2 uStack00000008;
  
  uStack00000007 = (undefined1)((uint)unaff_EBP >> 8);
  uStack00000008 = (undefined2)((uint)unaff_EBP >> 0x10);
  if (in_ZF) {
    FUN_6947846a();
    return;
  }
  uStack00000007 = (undefined1)((uint)unaff_EBX >> 8);
  uStack00000008 = (undefined2)((uint)unaff_EBX >> 0x10);
  thunk_FUN_694784bc();
  *extraout_EDX = *extraout_EDX + -0x70;
  *unaff_EDI = *unaff_ESI;
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_69478449  @0x0000000069478449  (16B) ──

void FUN_69478449(void)

{
  FUN_69478768();
  return;
}



//── FUN_6947846a  @0x000000006947846a  (24B) ──

void FUN_6947846a(void)

{
  code *pcVar1;
  char *extraout_EDX;
  undefined4 *unaff_ESI;
  undefined4 *unaff_EDI;
  
  thunk_FUN_694784bc();
  *extraout_EDX = *extraout_EDX + -0x70;
  *unaff_EDI = *unaff_ESI;
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_69478487  @0x0000000069478487  (28B) ──

void FUN_69478487(undefined4 param_1,undefined8 param_2)

{
  code *pcVar1;
  undefined1 uVar2;
  char *extraout_EDX;
  undefined4 *unaff_ESI;
  undefined4 *unaff_EDI;
  undefined2 in_CS;
  bool in_CF;
  bool in_ZF;
  
  param_1._0_1_ = (undefined1)((ulonglong)param_2 >> 0x28);
  if (!in_CF) {
    FUN_694783a2();
    return;
  }
  if (in_ZF) {
    FUN_6947846a();
    return;
  }
  param_1._0_1_ = 0x84;
  uVar2 = (char)((ushort)in_CS >> 8);
  thunk_FUN_694784bc();
  param_1._0_1_ = uVar2;
  *extraout_EDX = *extraout_EDX + -0x70;
  *unaff_EDI = *unaff_ESI;
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_694784bc  @0x00000000694784bc  (19B) ──

void FUN_694784bc(void)

{
  FUN_69478449();
  return;
}



//── FUN_69478718  @0x0000000069478718  (32B) ──

void FUN_69478718(void)

{
  uint uVar1;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  bool in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  uint uVar2;
  undefined2 uStack0000001a;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  byte bStack0000001e;
  undefined1 uStack0000001f;
  uint in_stack_00000020;
  
  uStack0000001a = SUB42(&stack0x0000001a,0);
  uVar1 = (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
          (uint)(in_TF & 1) * 0x100;
  uVar2 = uVar1 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 | (uint)(in_AF & 1) * 0x10 |
          (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1);
  bStack0000001e =
       (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) | (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10)
       | (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) | (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
  uStack0000001c = (undefined1)uVar2;
  uStack0000001d = (undefined1)(uVar1 >> 8);
  uStack0000001f = 0;
  if (!in_SF) {
    FUN_69478889();
    return;
  }
  in_stack_00000020 = (uint)CONCAT12(bStack0000001e,(short)uVar2);
  FUN_6947873f();
  return;
}



//── FUN_6947873f  @0x000000006947873f  (39B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6947874b) overlaps instruction at (ram,0x69478748)
    */

void FUN_6947873f(void)

{
  char *pcVar1;
  char extraout_DL;
  undefined1 in_SF;
  undefined2 unaff_retaddr;
  undefined1 uStack_1;
  
  while( true ) {
    uStack_1 = (undefined1)((ushort)unaff_retaddr >> 8);
    pcVar1 = (char *)thunk_FUN_694787f9(uStack_1,(char)unaff_retaddr);
    if ((bool)in_SF) break;
    *pcVar1 = *pcVar1 + (char)pcVar1;
    in_SF = *pcVar1 < '\0';
  }
  *pcVar1 = extraout_DL + -0x15;
  in((short)pcVar1);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69478768  @0x0000000069478768  (16B) ──

void FUN_69478768(void)

{
  FUN_69478718();
  return;
}



//── FUN_694787d6  @0x00000000694787d6  (12B) ──

void FUN_694787d6(void)

{
  FUN_6947883f();
  return;
}



//── FUN_694787f9  @0x00000000694787f9  (18B) ──

void FUN_694787f9(void)

{
  LOCK();
  UNLOCK();
  FUN_694787d6();
  return;
}



//── FUN_6947883f  @0x000000006947883f  (52B) ──

void FUN_6947883f(void)

{
  undefined4 in_stack_00000028;
  undefined4 in_stack_00000038;
  undefined2 uStack0000003e;
  undefined2 uStack00000040;
  
  uStack0000003e = CONCAT11((char)((uint)in_stack_00000028 >> 0x18),in_stack_00000038._2_1_);
  uStack00000040 = uStack0000003e;
  FUN_69478a64();
  return;
}



//── FUN_69478889  @0x0000000069478889  (21B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6947874b) overlaps instruction at (ram,0x69478748)
    */

void FUN_69478889(undefined4 param_1,undefined1 param_2)

{
  char *pcVar1;
  char extraout_DL;
  undefined1 in_SF;
  undefined4 unaff_retaddr;
  
  param_1._2_1_ = (undefined1)((uint)unaff_retaddr >> 0x10);
  param_1._3_1_ = (undefined1)((uint)unaff_retaddr >> 0x18);
  param_1._0_1_ = param_1._3_1_;
  param_1._1_1_ = param_2;
  while( true ) {
    pcVar1 = (char *)thunk_FUN_694787f9();
    if ((bool)in_SF) break;
    *pcVar1 = *pcVar1 + (char)pcVar1;
    in_SF = *pcVar1 < '\0';
  }
  *pcVar1 = extraout_DL + -0x15;
  in((short)pcVar1);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_694788a5  @0x00000000694788a5  (13B) ──

void FUN_694788a5(void)

{
  int in_EAX;
  int iVar1;
  int unaff_EBP;
  
  (**(code **)(in_EAX + 0x48))();
  (**(code **)(in_EAX + 0x10))();
  iVar1 = *(int *)(unaff_EBP + 8);
  thunk_FUN_6944cc60();
  iVar1 = FUN_6942e4e1(iVar1 + -0x1e000000);
  (**(code **)(iVar1 + 0x40))();
  FUN_694780e0();
  return;
}



//── FUN_694788ca  @0x00000000694788ca  (59B) ──

void FUN_694788ca(void)

{
  FUN_694788a5();
  return;
}



//── FUN_69478a64  @0x0000000069478a64  (26B) ──

void FUN_69478a64(void)

{
  int iVar1;
  undefined1 extraout_var;
  int in_EAX;
  undefined4 unaff_EDI;
  bool in_CF;
  bool in_ZF;
  undefined1 uStack00000007;
  undefined1 uStack00000009;
  undefined1 uStack0000000a;
  undefined1 uStack0000000b;
  
  if (in_CF || in_ZF) {
    FUN_694788ca();
    return;
  }
  uStack00000009 = (undefined1)((uint)unaff_EDI >> 8);
  uStack0000000a = (undefined1)((uint)unaff_EDI >> 0x10);
  uStack0000000b = (undefined1)((uint)unaff_EDI >> 0x18);
  uStack00000007 = 0x69;
  (**(code **)(in_EAX + 0x48))();
  uStack00000007 = extraout_var;
  (**(code **)(in_EAX + 0x10))();
  thunk_FUN_6944cc60();
  iVar1 = FUN_6942e4e1();
  (**(code **)(iVar1 + 0x40))();
  FUN_694780e0();
  return;
}



//── FUN_6947a049  @0x000000006947a049  (20B) ──

void FUN_6947a049(void)

{
  int in_EAX;
  int unaff_EBP;
  int unaff_EDI;
  
  **(int **)(unaff_EBP + 0x10) = in_EAX + unaff_EDI;
  FUN_6947a028();
  return;
}



//── FUN_6947a081  @0x000000006947a081  (9B) ──

void FUN_6947a081(void)

{
  FUN_6947a0d5();
  return;
}



//── FUN_6947a09f  @0x000000006947a09f  (28B) ──

void FUN_6947a09f(void)

{
  FUN_6947a109();
  return;
}



//── FUN_6947a0d5  @0x000000006947a0d5  (41B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6947a0d5(void)

{
  byte *pbVar1;
  char cVar2;
  char cVar3;
  uint uVar4;
  uint extraout_ECX;
  int iVar5;
  int unaff_EBX;
  int unaff_EBP;
  int unaff_EDI;
  uint *puVar6;
  char in_CF;
  undefined8 uVar7;
  
  uVar7 = FUN_6947a198();
  cVar2 = *(char *)(unaff_EDI + 0x68916207);
  pbVar1 = (byte *)((int)uVar7 + -0x2a);
  *pbVar1 = *pbVar1 << 1 | *pbVar1 >> 7;
  uVar4 = (int)uVar7 + 1;
  cVar3 = *(char *)(unaff_EBX + (uVar4 & 0xff));
  puVar6 = (uint *)(unaff_EDI + 1);
  iVar5 = CONCAT31((int3)((ulonglong)uVar7 >> 0x28),
                   (char)((ulonglong)uVar7 >> 0x20) + cVar2 + in_CF & (byte)extraout_ECX);
  uVar4 = CONCAT31((int3)(uVar4 >> 8),cVar3) ^ 0xf6;
  if (cVar3 == -10) {
    *puVar6 = *puVar6 >> 0x1e | *puVar6 << 2;
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  if ((ushort)iVar5 <= (ushort)uVar4) {
    FUN_6947a049();
    return;
  }
  **(int **)(unaff_EBP + 0x10) = ((uVar4 - iVar5 & extraout_ECX) - 1) + (int)puVar6;
  FUN_6947a028();
  return;
}



//── FUN_6947a140  @0x000000006947a140  (36B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6947a140(void)

{
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined2 unaff_retaddr;
  undefined4 in_stack_00000010;
  undefined4 uStack0000001c;
  undefined4 uStack00000020;
  undefined4 uStack00000040;
  
  uStack00000040 = in_stack_00000010;
  uStack00000020 =
       CONCAT22((ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8
                | (ushort)(in_AC & 1) * 4,unaff_retaddr);
  uStack0000001c = 0x6947a22f;
  func_0x6947a1e6();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6947a198  @0x000000006947a198  (11B) ──

void FUN_6947a198(void)

{
  FUN_6947a140();
  return;
}



//── FUN_6947d90c  @0x000000006947d90c  (23B) ──

void __fastcall FUN_6947d90c(undefined4 param_1)

{
  FUN_694309ff(param_1);
  FUN_6947da44();
  return;
}



//── FUN_6947d9c4  @0x000000006947d9c4  (62B) ──

undefined4 FUN_6947d9c4(undefined1 *param_1,undefined4 param_2)

{
  undefined4 uVar1;
  bool in_PF;
  undefined1 *unaff_retaddr;
  undefined4 uStack00000018;
  undefined1 uStack0000001f;
  undefined1 in_stack_00000020;
  
  uStack0000001f = (undefined1)((uint)param_2 >> 0x18);
  if (in_PF) {
    uStack00000018 = CONCAT22((short)unaff_retaddr,CONCAT11(in_stack_00000020,uStack0000001f));
    FUN_6947dacf();
    *unaff_retaddr = *param_1;
    return 0x36;
  }
  uStack00000018 = CONCAT22((short)unaff_retaddr,CONCAT11(in_stack_00000020,uStack0000001f));
  uVar1 = FUN_6947da02();
  return uVar1;
}



//── FUN_6947da02  @0x000000006947da02  (13B) ──

undefined4 FUN_6947da02(void)

{
  undefined1 *unaff_ESI;
  undefined1 *unaff_EDI;
  
  FUN_6947dacf();
  *unaff_EDI = *unaff_ESI;
  return 0x36;
}



//── FUN_6947da22  @0x000000006947da22  (18B) ──

void FUN_6947da22(void)

{
  FUN_6947d9c4();
  return;
}



//── FUN_6947da44  @0x000000006947da44  (37B) ──

undefined4 FUN_6947da44(undefined1 param_1)

{
  undefined1 uVar1;
  undefined2 extraout_DX;
  undefined4 *unaff_ESI;
  undefined1 *unaff_EDI;
  undefined4 unaff_retaddr;
  
  uVar1 = FUN_6947da22();
  out(*unaff_ESI,extraout_DX);
  out(0x74,uVar1);
  FUN_6947dacf(CONCAT22((short)unaff_EDI,CONCAT11(param_1,(char)((uint)unaff_retaddr >> 0x18))));
  *unaff_EDI = *(undefined1 *)(unaff_ESI + 1);
  return 0x36;
}



//── FUN_6947daa9  @0x000000006947daa9  (15B) ──

void FUN_6947daa9(void)

{
  FUN_6947da8c();
  return;
}



//── FUN_6947dacf  @0x000000006947dacf  (192B) ──

void __fastcall FUN_6947dacf(undefined4 param_1,undefined1 param_2)

{
  undefined4 in_EAX;
  undefined4 unaff_EBX;
  undefined4 unaff_ESI;
  undefined4 unaff_EDI;
  undefined1 uStack_13;
  undefined2 local_12;
  undefined2 uStack_e;
  undefined2 uStack_c;
  undefined1 local_a;
  undefined1 uStack_9;
  undefined1 uStack_8;
  undefined2 uStack_6;
  undefined2 uStack_4;
  undefined2 uStack_2;
  
  uStack_2 = (undefined2)((uint)in_EAX >> 0x10);
  uStack_e = (undefined2)((uint)unaff_EBX >> 0x10);
  local_12 = (undefined2)((uint)&stack0x00000000 >> 0x10);
  uStack_4 = (undefined2)((uint)unaff_EDI >> 0x10);
  uStack_13 = (undefined1)((uint)unaff_ESI >> 0x18);
  uStack_8 = (undefined1)((uint)unaff_ESI >> 8);
  uStack_6 = CONCAT11(uStack_13,param_2);
  uStack_c = local_12;
  local_a = SUB41(&uStack_e,0);
  uStack_9 = (undefined1)((uint)&uStack_e >> 8);
  FUN_6947daa9();
  return;
}



//── FUN_6947db6e  @0x000000006947db6e  (38B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x6947dc32) overlaps instruction at (ram,0x6947dc30)
    */

void FUN_6947db6e(void)

{
  uint *puVar1;
  undefined1 uVar2;
  uint uVar3;
  bool bVar4;
  code *pcVar5;
  byte bVar6;
  char cVar7;
  int *extraout_ECX;
  undefined2 extraout_DX;
  undefined1 *unaff_EDI;
  undefined1 *puVar8;
  byte in_ZF;
  byte in_SF;
  bool bVar9;
  
LAB_6947dbea:
  cVar7 = FUN_6947dbc4();
  puVar1 = (uint *)(extraout_ECX + 8);
  uVar3 = *puVar1;
  *puVar1 = *puVar1 << 1 | (uint)((int)uVar3 < 0);
  bVar6 = (byte)extraout_ECX & 0x1f;
  *extraout_ECX = *extraout_ECX >> bVar6;
  bVar9 = bVar6 != 1 && (int)uVar3 < 0 != (int)*puVar1 < 0;
  bVar4 = ((uint)extraout_ECX & 0x1f) != 0;
  bVar6 = !bVar4 & in_SF;
  in_ZF = !bVar4 & in_ZF | (bVar4 && *extraout_ECX == 0);
  if (extraout_ECX == (int *)0x1 || (bool)in_ZF != false) goto code_r0x6947dbf7;
  in_SF = false;
  if ((bool)(bVar6 | (bVar4 && *extraout_ECX < 0))) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  goto LAB_6947dc09;
code_r0x6947dbf7:
  in_SF = 0;
  in_ZF = 0;
  puVar8 = unaff_EDI + (uint)(((uint)&stack0x00000000 & 0x400) != 0) * -2 + 1;
  uVar2 = in(extraout_DX);
  *unaff_EDI = uVar2;
  unaff_EDI = puVar8;
  if (((uint)&stack0x00000000 & 0x800) != 0) {
    pcVar5 = (code *)swi(4);
    cVar7 = (*pcVar5)();
    bVar9 = SCARRY4((int)&stack0x00000000,1);
    in_SF = (int)&stack0x00000001 < 0;
    in_ZF = &stack0x00000000 == (undefined1 *)0xffffffff;
LAB_6947dc09:
    if (!(bool)in_ZF && bVar9 == (bool)in_SF) {
      if (bVar9 == (bool)in_SF) {
                    /* WARNING: Bad instruction - Truncating control flow here */
        halt_baddata();
      }
      in_SF = (char)(cVar7 + '$') < '\0';
      in_ZF = cVar7 == -0x24;
    }
  }
  goto LAB_6947dbea;
}



//── FUN_6947dbc4  @0x000000006947dbc4  (10B) ──

void FUN_6947dbc4(void)

{
  FUN_6947dc4d();
  return;
}



//── FUN_6947dc0b  @0x000000006947dc0b  (68B) ──

/* WARNING: Instruction at (ram,0x6947dc0c) overlaps instruction at (ram,0x6947dc0b)
    */
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x6947dc9b) */

void FUN_6947dc0b(uint param_1)

{
  uint *puVar1;
  undefined1 uVar2;
  uint uVar3;
  code *pcVar4;
  byte bVar5;
  byte bVar6;
  undefined4 uVar7;
  short extraout_var;
  int iVar8;
  int *extraout_ECX;
  byte *extraout_ECX_00;
  int unaff_EBX;
  uint unaff_ESI;
  undefined1 *puVar9;
  undefined1 *unaff_EDI;
  undefined2 in_DS;
  byte in_AF;
  byte bVar10;
  byte in_TF;
  byte in_IF;
  bool bVar11;
  bool bVar12;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined6 uVar13;
  undefined4 uStack00000026;
  uint uStack0000002a;
  undefined1 uStack_22;
  int iStack_21;
  undefined2 uStack_1c;
  undefined4 uStack_c;
  undefined1 uStack_8;
  undefined2 uStack_7;
  undefined1 uStack_5;
  undefined1 uStack_4;
  undefined1 uStack_3;
  undefined2 uStack_2;
  
  do {
    uStack_4 = 0x14;
    uStack_3 = 0xdc;
    uStack_2 = 0x6947;
    bVar6 = FUN_6947db6e();
    *extraout_ECX_00 = *extraout_ECX_00 | 0x99;
    if (extraout_ECX_00 != (byte *)0x1) {
      bVar6 = bVar6 & 0x10;
      param_1 = (uint)(in_NT & 1) * 0x4000 | (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 |
                (uint)(bVar6 == 0) * 0x40 | (uint)(in_AF & 1) * 0x10 |
                (uint)(POPCOUNT(bVar6) == '\0') * 4 | (uint)(in_ID & 1) * 0x200000 |
                (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
                (uint)(in_AC & 1) * 0x40000;
      uStack0000002a =
           (uint)(in_NT & 1) * 0x4000 | (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 |
           (uint)(bVar6 == 0) * 0x40 | (uint)(in_AF & 1) * 0x10 |
           (uint)(POPCOUNT(bVar6) == '\0') * 4 | (uint)(in_ID & 1) * 0x200000 |
           (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
           (uint)(in_AC & 1) * 0x40000;
      uStack00000026 = 0x6947dcc6;
      func_0x6947dd3b();
      uStack00000026 = CONCAT22(uStack00000026._2_2_,in_DS);
      out(*(undefined4 *)(unaff_ESI & *(uint *)(unaff_EBX + -0x6408da2a)),extraout_var >> 0xf);
      FUN_6947dd50();
      return;
    }
  } while (-1 < (int)&param_1);
  if ((POPCOUNT((uint)&param_1 & 0xff) & 1U) != 0) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  uVar7 = 0x3fb8492e;
  DAT_8f66b401 = 0x2e;
code_r0x6947dc32:
  bVar6 = (char)((char)uVar7 + '$') < '\0';
  bVar10 = (char)uVar7 == -0x24;
  puVar9 = unaff_EDI;
  do {
    uStack_4 = 0xef;
    uStack_3 = 0xdb;
    uStack_2 = 0x6947;
    uVar13 = FUN_6947dbc4();
    uVar7 = (undefined4)uVar13;
    puVar1 = (uint *)(extraout_ECX + 8);
    uVar3 = *puVar1;
    *puVar1 = *puVar1 << 1 | (uint)((int)uVar3 < 0);
    bVar5 = (byte)extraout_ECX & 0x1f;
    *extraout_ECX = *extraout_ECX >> bVar5;
    bVar11 = bVar5 != 1 && (int)uVar3 < 0 != (int)*puVar1 < 0;
    bVar12 = ((uint)extraout_ECX & 0x1f) != 0;
    bVar5 = !bVar12 & bVar6;
    bVar10 = !bVar12 & bVar10 | (bVar12 && *extraout_ECX == 0);
    if ((int)extraout_ECX + -1 == 0 || (bool)bVar10 != false) {
      bVar12 = ((uint)&uStack_22 & 0x800) != 0;
      bVar6 = ((uint)&uStack_22 & 0x80) != 0;
      bVar10 = ((uint)&uStack_22 & 0x40) != 0;
      unaff_EDI = puVar9 + (uint)(((uint)&uStack_22 & 0x400) != 0) * -2 + 1;
      uVar2 = in((short)((uint6)uVar13 >> 0x20));
      *puVar9 = uVar2;
      uVar7 = 0x8eeb7bf0;
      iVar8 = (int)extraout_ECX + -1;
      if (bVar12 != (bool)bVar6) {
        pcVar4 = (code *)swi(4);
        if (bVar12) {
          uVar7 = (*pcVar4)();
        }
        bVar11 = SCARRY4((int)&uStack_22,1);
        bVar6 = (int)&iStack_21 < 0;
        bVar10 = &stack0x00000000 == (undefined1 *)0x21;
        goto LAB_6947dc09;
      }
    }
    else {
      bVar6 = false;
      unaff_EDI = puVar9;
      if ((bool)(bVar5 | (bVar12 && *extraout_ECX < 0))) {
        halt_baddata();
      }
LAB_6947dc09:
      iVar8 = iStack_21;
      if (!(bool)bVar10 && bVar11 == (bool)bVar6) break;
    }
    uStack_8 = (undefined1)((uint)iVar8 >> 8);
    uStack_7 = (undefined2)((uint)iVar8 >> 0x10);
    uStack_1c = (undefined2)unaff_ESI;
    uStack_c = CONCAT13(uStack_4,CONCAT12(uStack_5,uStack_7));
    puVar9 = unaff_EDI;
  } while( true );
  if (bVar11 == (bool)bVar6) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  goto code_r0x6947dc32;
}



//── FUN_6947dc4d  @0x000000006947dc4d  (12B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_6947dc4d(uint param_1,undefined4 param_2,undefined8 param_3,undefined4 param_4,
                 undefined4 param_5)

{
  short extraout_var;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  char in_SF;
  byte in_TF;
  byte in_IF;
  bool in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined4 unaff_retaddr;
  byte bStack00000020;
  byte bStack00000021;
  ushort uStack00000022;
  
  param_2._2_1_ = (undefined1)unaff_retaddr;
  param_2._3_1_ = (undefined1)((uint)unaff_retaddr >> 8);
  param_2._0_1_ = (undefined1)((ulonglong)param_3 >> 0x28);
  param_2._1_1_ = (undefined1)((ulonglong)param_3 >> 0x30);
  bStack00000020 = (byte)param_5;
  bStack00000021 = (byte)((uint)param_5 >> 8);
  if (in_OF) {
    FUN_6947dceb();
    return;
  }
  bStack00000021 =
       (byte)((uint)(in_NT & 1) * 0x4000 >> 8) | (byte)((uint)(in_IF & 1) * 0x200 >> 8) |
       (byte)((uint)(in_TF & 1) * 0x100 >> 8);
  bStack00000020 =
       in_SF * -0x80 | (in_ZF & 1) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' | in_CF & 1;
  uStack00000022 =
       (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8 |
       (ushort)(in_AC & 1) * 4;
  func_0x6947dd3b();
  out(*(undefined4 *)(param_1 & *(uint *)((int)((ulonglong)param_3 >> 0x20) + -0x6408da2a)),
      extraout_var >> 0xf);
  FUN_6947dd50();
  return;
}



//── FUN_6947dc9d  @0x000000006947dc9d  (25B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_6947dc9d(void)

{
  short extraout_var;
  int unaff_EBX;
  uint unaff_ESI;
  
  func_0x6947dd3b();
  out(*(undefined4 *)(unaff_ESI & *(uint *)(unaff_EBX + -0x6408da2a)),extraout_var >> 0xf);
  FUN_6947dd50();
  return;
}



//── FUN_6947dcdd  @0x000000006947dcdd  (11B) ──

void FUN_6947dcdd(void)

{
  FUN_6947dc0b();
  return;
}



//── FUN_6947dcf5  @0x000000006947dcf5  (60B) ──

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x6947dd9c) */
/* WARNING: Removing unreachable block (ram,0x6947dde0) */
/* WARNING: Removing unreachable block (ram,0x6947dda1) */

undefined4 FUN_6947dcf5(void)

{
  short extraout_var;
  int iVar1;
  undefined4 uVar2;
  char extraout_DL;
  int unaff_EBX;
  int *piVar3;
  int *piVar4;
  char *unaff_EBP;
  uint unaff_ESI;
  int unaff_EDI;
  uint uVar6;
  undefined2 in_DS;
  bool bVar7;
  bool bVar8;
  byte in_TF;
  byte in_IF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined1 *puVar5;
  
  puVar5 = &stack0x0000000f;
  while( true ) {
    piVar4 = (int *)(puVar5 + -4);
    *(undefined4 *)(puVar5 + -4) = 0x6947dd24;
    iVar1 = FUN_69430a45();
    *unaff_EBP = *unaff_EBP + (char)unaff_EBP;
    *(char *)(iVar1 + 0x1be88919) = *(char *)(iVar1 + 0x1be88919) + extraout_DL;
    bVar8 = ((uint)unaff_EBP & 0x1000) != 0;
    piVar4[-1] = unaff_EBX;
    if ((POPCOUNT(((uint)unaff_EBP | 0x97641d8d) & 0xff) & 1U) == 0) {
      piVar3 = piVar4 + -2;
                    /* WARNING: Call to offcut address within same function */
      piVar4[-2] = 0x6947dcc6;
      func_0x6947dd3b();
      uVar6 = *(uint *)(unaff_EBX + -0x6408da2a);
      *(undefined2 *)((int)piVar3 + -4) = in_DS;
      out(*(undefined4 *)(unaff_ESI & uVar6),extraout_var >> 0xf);
      uVar2 = FUN_6947dd50();
      return uVar2;
    }
    uVar6 = unaff_EDI - 1;
    bVar7 = (POPCOUNT(uVar6 & 0xff) & 1U) == 0;
    piVar4[-1] = (uint)(in_NT & 1) * 0x4000 | (uint)SBORROW4(unaff_EDI,1) * 0x800 |
                 (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 |
                 (uint)((int)uVar6 < 0) * 0x80 | (uint)(uVar6 == 0) * 0x40 | (uint)bVar8 * 0x10 |
                 (uint)bVar7 * 4 | (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
                 (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000;
    LOCK();
    *(char *)((int)piVar4 + -2) = (char)unaff_EBX;
    UNLOCK();
    unaff_ESI = piVar4[1];
    unaff_EBP = (char *)piVar4[2];
    unaff_EBX = piVar4[4];
    uVar2 = piVar4[7];
    piVar4[7] = (int)(piVar4 + 8);
    piVar4[6] = *(undefined4 *)((int)piVar4 + 0x1e);
    *(short *)(piVar4 + 7) = (short)piVar4[6];
    *(uint *)((int)piVar4 + 0x16) =
         (uint)(in_NT & 1) * 0x4000 | (uint)SBORROW4(unaff_EDI,1) * 0x800 |
         (uint)(in_IF & 1) * 0x200 | (uint)(in_TF & 1) * 0x100 | (uint)((int)uVar6 < 0) * 0x80 |
         (uint)(uVar6 == 0) * 0x40 | (uint)bVar8 * 0x10 | (uint)bVar7 * 4 |
         (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000
         | (uint)(in_AC & 1) * 0x40000;
    *(undefined4 *)((int)piVar4 + 0x12) = *(undefined4 *)((int)piVar4 + 0x1a);
    *(undefined4 *)((int)piVar4 + 0xe) = uVar2;
    if (0 < unaff_EDI) break;
    puVar5 = (undefined1 *)((int)piVar4 + 0x36);
    unaff_EDI = *piVar4;
  }
  uVar2 = FUN_6947dcf5();
  return uVar2;
}



//── FUN_6947dd50  @0x000000006947dd50  (91B) ──

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x6947dd9c) */
/* WARNING: Removing unreachable block (ram,0x6947dde0) */
/* WARNING: Removing unreachable block (ram,0x6947dda1) */

undefined4
FUN_6947dd50(uint param_1,char *param_2,undefined4 param_3,undefined4 param_4,undefined4 param_5,
            undefined4 param_6,undefined4 param_7,undefined2 param_8)

{
  byte bVar1;
  int iVar2;
  undefined2 uVar3;
  byte in_AL;
  char cVar4;
  short extraout_var;
  int iVar5;
  undefined4 uVar6;
  char extraout_DL;
  uint uVar7;
  byte in_CF;
  bool bVar8;
  byte in_AF;
  bool bVar9;
  bool bVar10;
  byte in_TF;
  byte in_IF;
  bool bVar11;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  int unaff_retaddr;
  undefined8 in_stack_00000030;
  
  bVar1 = in_AL + 0x24;
  bVar8 = 0xdb < in_AL || CARRY1(bVar1,in_CF);
  bVar11 = SCARRY1(in_AL,'$') != SCARRY1(bVar1,in_CF);
  cVar4 = bVar1 + in_CF;
  bVar10 = cVar4 < '\0';
  bVar9 = cVar4 == '\0';
  bVar1 = POPCOUNT(cVar4);
  while( true ) {
    uVar3 = param_7._2_2_;
    LOCK();
    UNLOCK();
    iVar2 = CONCAT22(param_4._2_2_,(undefined2)param_4);
    param_7._2_2_ = (undefined2)((uint)&param_8 >> 0x10);
    param_6._2_2_ = param_8;
    param_5._2_2_ =
         (ushort)(in_NT & 1) * 0x4000 | (ushort)bVar11 * 0x800 | (ushort)(in_IF & 1) * 0x200 |
         (ushort)(in_TF & 1) * 0x100 | (ushort)bVar10 * 0x80 | (ushort)bVar9 * 0x40 |
         (ushort)(in_AF & 1) * 0x10 | (ushort)((bVar1 & 1) == 0) * 4 | (ushort)bVar8;
    param_6._0_2_ =
         (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8 |
         (ushort)(in_AC & 1) * 4;
    param_4._2_2_ = param_8;
    param_5._0_2_ = param_7._2_2_;
    param_3._2_2_ = (undefined2)param_7;
    param_4._0_2_ = uVar3;
    if (bVar11 == bVar10) {
      uVar6 = FUN_6947dcf5();
      return uVar6;
    }
    in_stack_00000030._2_4_ = 0x6947dd24;
    iVar5 = FUN_69430a45();
    *param_2 = *param_2 + (char)param_2;
    *(char *)(iVar5 + 0x1be88919) = *(char *)(iVar5 + 0x1be88919) + extraout_DL;
    in_AF = ((uint)param_2 & 0x1000) != 0;
    bVar8 = false;
    if ((POPCOUNT(((uint)param_2 | 0x97641d8d) & 0xff) & 1U) == 0) break;
    bVar11 = SBORROW4(unaff_retaddr,1);
    uVar7 = unaff_retaddr - 1;
    bVar10 = (int)uVar7 < 0;
    bVar9 = uVar7 == 0;
    bVar1 = POPCOUNT(uVar7 & 0xff);
    param_7._0_2_ = param_7._2_2_;
  }
                    /* WARNING: Call to offcut address within same function */
  func_0x6947dd3b(iVar2);
  out(*(undefined4 *)(param_1 & *(uint *)(iVar2 + -0x6408da2a)),extraout_var >> 0xf);
  uVar6 = FUN_6947dd50();
  return uVar6;
}



//── FUN_6947ddea  @0x000000006947ddea  (16B) ──

void FUN_6947ddea(void)

{
  FUN_6947dc0b();
  return;
}



//── FUN_6947de25  @0x000000006947de25  (68B) ──

void FUN_6947de25(void)

{
  bool in_PF;
  
  if (in_PF) {
    FUN_6947df81();
    return;
  }
  FUN_6947dff9();
  return;
}



//── FUN_6947df06  @0x000000006947df06  (20B) ──

void FUN_6947df06(void)

{
  int unaff_ESI;
  int unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_6947de1e();
    return;
  }
  if (unaff_ESI + unaff_EDI != 0) {
    if ((POPCOUNT(unaff_ESI + unaff_EDI & 0xff) & 1U) == 0) {
      FUN_6947df81();
      return;
    }
    FUN_6947dff9();
    return;
  }
  FUN_6947de25();
  return;
}



//── FUN_6947df20  @0x000000006947df20  (24B) ──

void FUN_6947df20(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_6947dfca();
    return;
  }
  FUN_6947dfca();
  return;
}



//── FUN_6947df5d  @0x000000006947df5d  (12B) ──

void FUN_6947df5d(void)

{
  thunk_FUN_6944d3c3();
  FUN_6947e9ce();
  return;
}



//── FUN_6947df81  @0x000000006947df81  (33B) ──

void FUN_6947df81(void)

{
  int unaff_EBP;
  
  if (*(int *)(unaff_EBP + 0x10) != 0) {
    FUN_6947df20();
    return;
  }
  FUN_6947e9f1(0);
  return;
}



//── FUN_6947dfca  @0x000000006947dfca  (18B) ──

void FUN_6947dfca(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined1 uStack0000001f;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_6947e00b();
    return;
  }
  if (in_OF != in_SF) {
    FUN_6947e16a();
    return;
  }
  uStack0000001f = 0;
  FUN_6947e134();
  return;
}



//── FUN_6947dff9  @0x000000006947dff9  (13B) ──

void FUN_6947dff9(void)

{
  FUN_6947df81();
  return;
}



//── FUN_6947e00b  @0x000000006947e00b  (126B) ──

void FUN_6947e00b(void)

{
  FUN_6947dfdc();
  return;
}



//── FUN_6947e106  @0x000000006947e106  (10B) ──

void FUN_6947e106(void)

{
  int in_EAX;
  
  if (in_EAX != 0) {
    FUN_6947e149();
    return;
  }
  FUN_6947e9f1(0);
  return;
}



//── FUN_6947e124  @0x000000006947e124  (14B) ──

void FUN_6947e124(void)

{
  FUN_6947df06();
  return;
}



//── FUN_6947e134  @0x000000006947e134  (14B) ──

void FUN_6947e134(void)

{
  int in_EAX;
  int iVar1;
  
  iVar1 = FUN_69430a4d(*(undefined4 *)(in_EAX + 0x54));
  (**(code **)(iVar1 + 0x1c))();
  FUN_6947e106();
  return;
}



//── FUN_6947e149  @0x000000006947e149  (10B) ──

void FUN_6947e149(void)

{
  FUN_69430a92();
  FUN_6947e1c0();
  return;
}



//── FUN_6947e16a  @0x000000006947e16a  (10B) ──

void FUN_6947e16a(void)

{
  undefined4 uStack0000003f;
  
  uStack0000003f = 0x40;
  FUN_6947e134();
  return;
}



//── FUN_6947e192  @0x000000006947e192  (9B) ──

void FUN_6947e192(void)

{
  int unaff_EBP;
  
  FUN_6947e175(unaff_EBP + 8);
  return;
}



//── FUN_6947e1a1  @0x000000006947e1a1  (11B) ──

void FUN_6947e1a1(void)

{
  FUN_6947e279();
  return;
}



//── FUN_6947e1c0  @0x000000006947e1c0  (12B) ──

void FUN_6947e1c0(void)

{
  undefined4 in_EAX;
  int unaff_EBP;
  
  *(undefined4 *)(unaff_EBP + 0x10) = in_EAX;
  FUN_6947e192();
  return;
}



//── FUN_6947e1e8  @0x000000006947e1e8  (37B) ──

void FUN_6947e1e8(undefined2 param_1)

{
  undefined2 extraout_var;
  undefined1 uStack00000006;
  undefined1 uStack00000007;
  undefined1 uStack00000009;
  
  FUN_6947e21f();
  uStack00000009 = (undefined1)((ushort)param_1 >> 8);
  uStack00000006 = (undefined1)extraout_var;
  uStack00000007 = (undefined1)((ushort)extraout_var >> 8);
  FUN_6947e319();
  return;
}



//── FUN_6947e21f  @0x000000006947e21f  (13B) ──

void FUN_6947e21f(void)

{
  FUN_6947e3a2();
  return;
}



//── FUN_6947e242  @0x000000006947e242  (31B) ──

void FUN_6947e242(void)

{
  FUN_6947e1e8();
  return;
}



//── FUN_6947e279  @0x000000006947e279  (31B) ──

void FUN_6947e279(void)

{
  FUN_6947e242();
  return;
}



//── FUN_6947e2af  @0x000000006947e2af  (13B) ──

void FUN_6947e2af(void)

{
  FUN_6947e124();
  return;
}



//── FUN_6947e2d7  @0x000000006947e2d7  (25B) ──

void FUN_6947e2d7(void)

{
  FUN_6947df06();
  return;
}



//── FUN_6947e319  @0x000000006947e319  (20B) ──

/* WARNING: Instruction at (ram,0x6947e371) overlaps instruction at (ram,0x6947e370)
    */

void FUN_6947e319(void)

{
  byte bVar1;
  uint uVar3;
  uint uVar4;
  int extraout_ECX;
  char extraout_DL;
  int unaff_EDI;
  int iVar5;
  char in_CF;
  bool in_ZF;
  byte *pbVar2;
  
  iVar5 = unaff_EDI;
  if ((bool)in_CF || in_ZF) {
    while( true ) {
      uVar3 = thunk_FUN_6947e5c0();
      if (extraout_ECX != 0) break;
      uVar4 = uVar3 >> 8 & 0xff;
      bVar1 = (byte)uVar3;
      pbVar2 = (byte *)CONCAT22((short)(uVar3 >> 0x10),(ushort)bVar1);
      *(char *)(iVar5 + 0x2b4cde4f) = *(char *)(iVar5 + 0x2b4cde4f) + extraout_DL + in_CF;
      out(0x61,bVar1);
      *(uint *)(uVar4 + 0xe8242474) = uVar4;
      in_CF = CARRY1(*pbVar2,bVar1);
      *pbVar2 = *pbVar2 + bVar1;
      iVar5 = iVar5 + -1;
    }
    FUN_6947e474((short)((uint)unaff_EDI >> 0x10));
    return;
  }
  FUN_6947e36c();
  return;
}



//── FUN_6947e33f  @0x000000006947e33f  (9B) ──

void FUN_6947e33f(void)

{
  undefined1 in_AH;
  undefined4 unaff_retaddr;
  undefined3 uStack00000004;
  undefined1 uStack00000007;
  
  uStack00000007 = (undefined1)((uint)unaff_retaddr >> 0x18);
  uStack00000004 = CONCAT12(in_AH,(short)unaff_retaddr);
  FUN_6947e309();
  return;
}



//── FUN_6947e36c  @0x000000006947e36c  (32B) ──

/* WARNING: Instruction at (ram,0x6947e371) overlaps instruction at (ram,0x6947e370)
    */

void FUN_6947e36c(void)

{
  byte bVar1;
  uint uVar3;
  uint uVar4;
  int extraout_ECX;
  char extraout_DL;
  int unaff_EDI;
  char in_CF;
  byte *pbVar2;
  
  while( true ) {
    uVar3 = thunk_FUN_6947e5c0();
    if (extraout_ECX != 0) break;
    uVar4 = uVar3 >> 8 & 0xff;
    bVar1 = (byte)uVar3;
    pbVar2 = (byte *)CONCAT22((short)(uVar3 >> 0x10),(ushort)bVar1);
    *(char *)(unaff_EDI + 0x2b4cde4f) = *(char *)(unaff_EDI + 0x2b4cde4f) + extraout_DL + in_CF;
    out(0x61,bVar1);
    *(uint *)(uVar4 + 0xe8242474) = uVar4;
    in_CF = CARRY1(*pbVar2,bVar1);
    *pbVar2 = *pbVar2 + bVar1;
    unaff_EDI = unaff_EDI + -1;
  }
  FUN_6947e474();
  return;
}



//── FUN_6947e3a2  @0x000000006947e3a2  (73B) ──

void FUN_6947e3a2(undefined2 param_1,undefined4 param_2,undefined4 param_3,undefined2 param_4,
                 undefined4 param_5,undefined2 param_6,undefined4 param_7,undefined1 param_8)

{
  char in_SF;
  char in_OF;
  undefined1 uStack0000001b;
  undefined1 uStack00000021;
  undefined2 uStack00000022;
  undefined1 uStack00000024;
  undefined1 uStack00000025;
  undefined1 uStack00000026;
  undefined1 uStack00000027;
  
  uStack0000001b = (undefined1)((uint)param_7 >> 8);
  param_3._2_2_ = param_4;
  param_3._0_2_ = (undefined2)((uint)((int)&param_7 + 2) >> 0x10);
  param_5._1_1_ = (undefined1)param_1;
  param_5._2_1_ = (undefined1)((ushort)param_1 >> 8);
  uStack00000021 = SUB41(&param_8,0);
  uStack00000022 = (undefined2)((uint)&param_8 >> 8);
  uStack00000024 = (undefined1)((uint)&param_8 >> 0x18);
  param_7._2_2_ = param_6;
  if (in_OF != in_SF) {
    FUN_6947e33f();
    return;
  }
  uStack00000027 = (undefined1)((uint)&param_8 >> 0x10);
  uStack00000022 = (undefined2)param_7;
  uStack00000024 = (undefined1)((uint)param_7 >> 0x10);
  uStack00000025 = (undefined1)((uint)param_7 >> 0x18);
  param_8 = uStack00000025;
  uStack00000021 = uStack0000001b;
  uStack00000026 = uStack0000001b;
  FUN_6947e319();
  return;
}



//── FUN_6947e411  @0x000000006947e411  (98B) ──

void FUN_6947e411(undefined2 param_1)

{
  bool in_CF;
  undefined4 uStack0000000c;
  
  uStack0000000c = CONCAT22(param_1,(short)&stack0x00000020);
  if (!in_CF) {
    FUN_6947e2d7();
    return;
  }
  FUN_6947e2af();
  return;
}



//── FUN_6947e474  @0x000000006947e474  (47B) ──

void FUN_6947e474(void)

{
  undefined2 unaff_BX;
  bool in_CF;
  undefined1 uStack00000006;
  
  uStack00000006 = (undefined1)((ushort)unaff_BX >> 8);
  if (!in_CF) {
    FUN_6947e74c();
    return;
  }
  FUN_6947e74c();
  return;
}



//── FUN_6947e56b  @0x000000006947e56b  (13B) ──

void FUN_6947e56b(void)

{
  FUN_6947e62c();
  return;
}



//── FUN_6947e5c0  @0x000000006947e5c0  (102B) ──

void FUN_6947e5c0(void)

{
  LOCK();
  UNLOCK();
  LOCK();
  UNLOCK();
  func_0x6947e4e8();
  FUN_6947e474();
  return;
}



//── FUN_6947e62c  @0x000000006947e62c  (62B) ──

void FUN_6947e62c(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined1 param_4)

{
  int extraout_EDX;
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined4 uStack00000018;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined1 uStack00000020;
  undefined1 uStack00000021;
  undefined1 uStack00000022;
  undefined3 uStack00000023;
  
  uStack00000018 =
       CONCAT13(param_4,(uint3)(in_NT & 1) * 0x4000 | (uint3)(in_OF & 1) * 0x800 |
                        (uint3)(in_IF & 1) * 0x200 | (uint3)(in_TF & 1) * 0x100 |
                        (uint3)(in_SF & 1) * 0x80 | (uint3)(in_ZF & 1) * 0x40 |
                        (uint3)(in_AF & 1) * 0x10 | (uint3)(in_PF & 1) * 4 | (uint3)(in_CF & 1) |
                        (uint3)(in_ID & 1) * 0x200000 | (uint3)(in_VIP & 1) * 0x100000 |
                        (uint3)(in_VIF & 1) * 0x80000 | (uint3)(in_AC & 1) * 0x40000);
  uStack0000001c = 0x6a;
  uStack0000001d = 0xe6;
  uStack0000001e = 0x47;
  uStack0000001f = 0x69;
  FUN_6947e6e3();
  *(undefined4 *)(extraout_EDX + 0x66) = param_1;
  uStack0000001c = (undefined1)_uStack00000022;
  uStack0000001d = (undefined1)((uint)_uStack00000022 >> 8);
  uStack0000001e = (undefined1)((uint)_uStack00000022 >> 0x10);
  uStack0000001f = SUB41(&stack0x0000001c,0);
  uStack00000020 = (undefined1)((uint)&stack0x0000001c >> 8);
  uStack00000021 = (undefined1)((uint)&stack0x0000001c >> 0x10);
  uStack00000022 = (undefined1)((uint)&stack0x0000001c >> 0x18);
  FUN_6947e6c4();
  return;
}



//── FUN_6947e6a5  @0x000000006947e6a5  (10B) ──

void FUN_6947e6a5(void)

{
  FUN_6947e786();
  return;
}



//── FUN_6947e6e3  @0x000000006947e6e3  (21B) ──

void FUN_6947e6e3(void)

{
  bool in_CF;
  
  if (!in_CF) {
    FUN_6947e68d();
    return;
  }
  FUN_6947e6c4();
  return;
}



//── FUN_6947e72b  @0x000000006947e72b  (13B) ──

void FUN_6947e72b(void)

{
  FUN_6947e6a5();
  return;
}



//── FUN_6947e74c  @0x000000006947e74c  (38B) ──

void FUN_6947e74c(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uVar3;
  undefined2 uVar4;
  undefined1 extraout_DL;
  int unaff_EBX;
  byte in_AF;
  undefined1 *puStack00000005;
  
  uVar4 = FUN_6947e56b();
  in_AF = 9 < ((byte)uVar4 & 0xf) | in_AF;
  uVar3 = in(CONCAT11(0x24,extraout_DL));
  bVar2 = (byte)(CONCAT11((char)((ushort)uVar4 >> 8) + in_AF,uVar3) /
                (ushort)*(byte *)(unaff_EBX + -0xb));
  bVar1 = bVar2 - 9;
  if ((char)(bVar1 + in_AF) < '\0') {
    FUN_6947efa1();
    return;
  }
  if (bVar2 < 9 && !CARRY1(bVar1,in_AF)) {
    FUN_6947e68d();
    return;
  }
  puStack00000005 = &stack0x00000002;
  FUN_6947e6c4();
  return;
}



//── FUN_6947e786  @0x000000006947e786  (11B) ──

void FUN_6947e786(void)

{
  bool in_OF;
  
  if (!in_OF) {
    FUN_6947efa1();
    return;
  }
  FUN_6947efa1();
  return;
}



//── FUN_6947e7be  @0x000000006947e7be  (10B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Type propagation algorithm not settling */

void __fastcall FUN_6947e7be(undefined4 param_1,undefined4 param_2)

{
  undefined2 extraout_DX;
  undefined2 unaff_BP;
  undefined1 *unaff_ESI;
  undefined1 *unaff_EDI;
  undefined1 in_OF;
  undefined2 uVar1;
  undefined1 uStack00000004;
  
  uStack00000004 = (undefined1)((ushort)unaff_BP >> 8);
  uVar1 = (undefined2)((uint)param_2 >> 8);
  do {
    thunk_FUN_6947e7fe(uVar1);
    while ((bool)in_OF) {
      in_OF = SCARRY4((int)unaff_EDI,(int)unaff_ESI);
      unaff_EDI = unaff_EDI + (int)unaff_ESI;
      if ((bool)in_OF == (int)unaff_EDI < 0) {
        out(*unaff_ESI,extraout_DX);
        unaff_ESI[0x32] = unaff_ESI[0x32];
                    /* WARNING: Bad instruction - Truncating control flow here */
        halt_baddata();
      }
    }
  } while( true );
}



//── FUN_6947e7e4  @0x000000006947e7e4  (55B) ──

void FUN_6947e7e4(void)

{
  FUN_6947e7be();
  return;
}



//── FUN_6947e7fe  @0x000000006947e7fe  (13B) ──

void FUN_6947e7fe(void)

{
  FUN_6947e839();
  return;
}



//── FUN_6947e839  @0x000000006947e839  (39B) ──

void FUN_6947e839(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)

{
  undefined2 uStack0000001a;
  undefined2 uStack0000001c;
  undefined2 uStack0000001e;
  
  uStack0000001e = (undefined2)((uint)param_4 >> 0x10);
  uStack0000001a = (undefined2)param_2;
  uStack0000001c = (undefined2)((uint)param_2 >> 0x10);
  FUN_6947e935();
  return;
}



//── FUN_6947e8af  @0x000000006947e8af  (12B) ──

void FUN_6947e8af(void)

{
  FUN_6947e7e4();
  return;
}



//── FUN_6947e8c8  @0x000000006947e8c8  (42B) ──

void FUN_6947e8c8(void)

{
  int iVar1;
  int unaff_EBP;
  
  FUN_6944d337();
  iVar1 = FUN_69430ad0();
  *(undefined4 *)(iVar1 + 0x50) = *(undefined4 *)(unaff_EBP + 0x10);
  FUN_69430bc8();
  FUN_6947e979();
  return;
}



//── FUN_6947e935  @0x000000006947e935  (51B) ──

void FUN_6947e935(void)

{
  int iVar1;
  int unaff_EBP;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined4 uStack00000012;
  undefined4 uStack00000022;
  undefined4 uStack00000026;
  undefined4 uStack0000002a;
  int iStack0000002e;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_6947e8c8();
    return;
  }
  uStack00000012 = 0x6947e8cd;
  FUN_6944d337();
  uStack00000012 = 0x6947e8e9;
  iVar1 = FUN_69430ad0();
  *(undefined4 *)(iVar1 + 0x50) = *(undefined4 *)(unaff_EBP + 0x10);
  iStack0000002e = unaff_EBP + -4;
  uStack0000002a = *(undefined4 *)(unaff_EBP + -4);
  uStack00000026 = *(undefined4 *)(iVar1 + 0x54);
  uStack00000022 = 0x6947e8fa;
  FUN_69430bc8();
  FUN_6947e979();
  return;
}



//── FUN_6947e979  @0x000000006947e979  (9B) ──

void FUN_6947e979(void)

{
  int in_EAX;
  
  (**(code **)(in_EAX + 0x1c))();
  FUN_6947ea83();
  return;
}



//── FUN_6947e9f1  @0x000000006947e9f1  (14B) ──

void FUN_6947e9f1(void)

{
  int unaff_EBP;
  
  FUN_6947df5d(1,unaff_EBP + 8);
  return;
}



//── FUN_6947efa1  @0x000000006947efa1  (14B) ──

void FUN_6947efa1(void)

{
  int extraout_EDX;
  
  FUN_6947eabf();
  if (extraout_EDX + 1 < 0) {
    FUN_6947efec();
    return;
  }
  FUN_6947efcb();
  FUN_6947f0a1();
  return;
}



//── FUN_6947efcb  @0x000000006947efcb  (9B) ──

void FUN_6947efcb(void)

{
  FUN_6947f011();
  return;
}



//── FUN_6947efec  @0x000000006947efec  (16B) ──

void FUN_6947efec(void)

{
  FUN_6947efcb();
  FUN_6947f0a1();
  return;
}



//── FUN_6947f011  @0x000000006947f011  (43B) ──

void FUN_6947f011(void)

{
  undefined4 unaff_retaddr;
  undefined2 uStack0000001a;
  undefined2 uStack0000001d;
  
  uStack0000001d = (undefined2)((uint)unaff_retaddr >> 8);
  uStack0000001a = uStack0000001d;
  FUN_6947f462();
  return;
}



//── FUN_6947f06d  @0x000000006947f06d  (40B) ──

void FUN_6947f06d(void)

{
  undefined2 unaff_BP;
  
  FUN_6947f0c7(unaff_BP);
  return;
}



//── FUN_6947f0a1  @0x000000006947f0a1  (23B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6947f0a1(void)

{
  FUN_6947f06d();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6947f109  @0x000000006947f109  (12B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6947f109(void)

{
  undefined2 unaff_BX;
  undefined1 unaff_retaddr;
  undefined2 uStack00000004;
  
  uStack00000004 = (undefined2)CONCAT21(unaff_BX,unaff_retaddr);
  FUN_6947f06d();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6947f133  @0x000000006947f133  (57B) ──

void FUN_6947f133(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_6947f201();
    return;
  }
  FUN_6947f201();
  return;
}



//── FUN_6947f1f5  @0x000000006947f1f5  (10B) ──

void FUN_6947f1f5(void)

{
  FUN_6947f133();
  return;
}



//── FUN_6947f201  @0x000000006947f201  (28B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_6947f201(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  uint uVar3;
  undefined2 uVar4;
  uint *unaff_ESI;
  undefined1 *unaff_EDI;
  undefined1 in_OF;
  undefined6 uVar5;
  
  uVar5 = FUN_6947f1d8();
  uVar4 = (undefined2)((uint6)uVar5 >> 0x20);
  uVar2 = in(99);
  do {
  } while ((bool)in_OF);
  uVar1 = in(uVar4);
  *unaff_EDI = uVar1;
  uVar3 = CONCAT31((int3)((uint6)uVar5 >> 8),uVar2) | *unaff_ESI;
  unaff_ESI[uVar3] = unaff_ESI[uVar3] + 0x488e7314;
  out(uVar4,uVar3);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_6947f220  @0x000000006947f220  (17B) ──

void FUN_6947f220(void)

{
  FUN_6947f2d7();
  return;
}



//── FUN_6947f247  @0x000000006947f247  (11B) ──

void FUN_6947f247(void)

{
  bool in_CF;
  bool in_PF;
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_6947f3ba();
    return;
  }
  if (!in_CF) {
    if (!in_PF) {
      FUN_6947f201();
      return;
    }
    FUN_6947f201();
    return;
  }
  FUN_6947f1f5();
  return;
}



//── FUN_6947f25d  @0x000000006947f25d  (26B) ──

void FUN_6947f25d(void)

{
  FUN_6947f37f();
  return;
}



//── FUN_6947f2d7  @0x000000006947f2d7  (99B) ──

void FUN_6947f2d7(void)

{
  bool in_PF;
  undefined1 *puStack0000000c;
  undefined1 in_stack_00000020;
  
  puStack0000000c = &stack0x00000020;
  if (in_PF) {
    FUN_6947f25d();
    return;
  }
  FUN_6947f33f();
  return;
}



//── FUN_6947f33f  @0x000000006947f33f  (26B) ──

void FUN_6947f33f(void)

{
  code *pcVar1;
  undefined4 *unaff_ESI;
  undefined4 *unaff_EDI;
  
  FUN_6947f35e();
  *unaff_EDI = *unaff_ESI;
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_6947f3ba  @0x000000006947f3ba  (35B) ──

void FUN_6947f3ba(void)

{
  bool in_CF;
  bool in_PF;
  
  if (in_CF) {
    FUN_6947f1f5();
    return;
  }
  if (!in_PF) {
    FUN_6947f201();
    return;
  }
  FUN_6947f201();
  return;
}



//── FUN_6947f3e4  @0x000000006947f3e4  (34B) ──

void FUN_6947f3e4(void)

{
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  undefined1 uStack0000001b;
  undefined1 uStack0000001c;
  ushort uStack0000001d;
  undefined1 uStack0000001f;
  undefined1 in_stack_00000020;
  
  uStack0000001d =
       (ushort)((uint)(in_NT & 1) * 0x4000 >> 8) | (ushort)((uint)(in_OF & 1) * 0x800 >> 8) |
       (ushort)((uint)(in_IF & 1) * 0x200 >> 8) | (ushort)((uint)(in_TF & 1) * 0x100 >> 8) |
       (ushort)(in_ID & 1) * 0x2000 | (ushort)(in_VIP & 1) * 0x1000 | (ushort)(in_VIF & 1) * 0x800 |
       (ushort)(in_AC & 1) * 0x400;
  uStack0000001f = 0;
  uStack0000001b = 0;
  uStack0000001c = in_stack_00000020;
  FUN_6947f445();
  return;
}



//── FUN_6947f41f  @0x000000006947f41f  (29B) ──

void FUN_6947f41f(void)

{
  bool in_OF;
  
  if (in_OF) {
    FUN_6947f109();
    return;
  }
  FUN_6947f0a1();
  return;
}



//── FUN_6947f445  @0x000000006947f445  (10B) ──

void FUN_6947f445(void)

{
  FUN_6947f6ac();
  return;
}



//── FUN_6947f462  @0x000000006947f462  (23B) ──

void FUN_6947f462(void)

{
  FUN_6947f41f();
  return;
}



//── FUN_6947f4b9  @0x000000006947f4b9  (20B) ──

/* WARNING: Removing unreachable block (ram,0x6947f598) */

void FUN_6947f4b9(undefined1 param_1)

{
  int extraout_ECX;
  undefined4 extraout_ECX_00;
  int unaff_EBP;
  undefined4 unaff_EDI;
  byte in_CF;
  bool bVar1;
  undefined1 uStack00000005;
  undefined2 uStack00000006;
  undefined1 uStack00000011;
  undefined2 uStack00000012;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  int iStack00000020;
  
  FUN_6947f4c5();
  *(uint *)(extraout_ECX + -0x37) = *(uint *)(extraout_ECX + -0x37) >> 1 | (uint)in_CF << 0x1f;
  bVar1 = true;
  param_1 = SUB41(&param_1,0);
  uStack00000005 = (undefined1)((uint)&param_1 >> 8);
  uStack00000006 = (undefined2)((uint)&param_1 >> 0x10);
  iStack00000020 = 0x6947f5f9;
  FUN_6944d3a6();
  iStack00000020 = unaff_EBP + -0x68;
  uStack0000001e = (undefined1)((uint)extraout_ECX_00 >> 0x10);
  uStack0000001f = (undefined1)((uint)extraout_ECX_00 >> 0x18);
  uStack00000011 = (undefined1)((uint)&stack0x00000024 >> 8);
  uStack00000012 = (undefined2)((uint)&stack0x00000024 >> 0x10);
  param_1 = (undefined1)unaff_EDI;
  uStack00000005 = (undefined1)((uint)unaff_EDI >> 8);
  uStack00000006 = (undefined2)((uint)unaff_EDI >> 0x10);
  if (!bVar1) {
    uStack00000011 = (undefined1)((uint)&stack0x00000024 >> 0x10);
    FUN_6947f773((short)unaff_EDI,(char)extraout_ECX_00);
    return;
  }
  FUN_6947f799((char)extraout_ECX_00);
  return;
}



//── FUN_6947f4c5  @0x000000006947f4c5  (245B) ──

void FUN_6947f4c5(void)

{
  undefined4 extraout_ECX;
  int unaff_EBP;
  undefined2 unaff_DI;
  undefined1 in_PF;
  undefined1 uStack0000000d;
  undefined2 uStack0000000e;
  undefined1 uStack0000001a;
  undefined1 uStack0000001b;
  int iStack0000001c;
  
  iStack0000001c = 0x6947f5f9;
  FUN_6944d3a6();
  iStack0000001c = unaff_EBP + -0x68;
  uStack0000001a = (undefined1)((uint)extraout_ECX >> 0x10);
  uStack0000001b = (undefined1)((uint)extraout_ECX >> 0x18);
  uStack0000000d = (undefined1)((uint)&stack0x00000020 >> 8);
  uStack0000000e = (undefined2)((uint)&stack0x00000020 >> 0x10);
  if ((bool)in_PF) {
    FUN_6947f799((char)extraout_ECX,uStack0000001b);
    return;
  }
  uStack0000000d = (undefined1)((uint)&stack0x00000020 >> 0x10);
  FUN_6947f773(unaff_DI,(char)extraout_ECX);
  return;
}



//── FUN_6947f6ac  @0x000000006947f6ac  (45B) ──

/* WARNING: Removing unreachable block (ram,0x6947f598) */

void __fastcall FUN_6947f6ac(undefined4 param_1,undefined1 param_2)

{
  undefined1 uVar1;
  int extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined2 extraout_DX;
  undefined4 extraout_EDX;
  int unaff_EBP;
  undefined4 unaff_EDI;
  byte in_CF;
  bool bVar2;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined1 *puStack00000021;
  undefined2 uStack00000025;
  undefined1 uStack00000027;
  undefined1 uStack00000029;
  undefined1 uStack0000002a;
  undefined4 in_stack_0000002c;
  undefined1 in_stack_00000030;
  undefined1 uStack00000035;
  undefined1 uStack00000036;
  undefined2 uStack00000037;
  undefined1 uStack00000041;
  undefined1 uStack00000042;
  undefined2 uStack00000043;
  undefined1 uStack00000045;
  undefined2 uStack00000046;
  undefined4 uStack00000048;
  undefined2 uStack0000004d;
  undefined1 uStack0000004f;
  undefined1 uStack00000050;
  undefined1 uStack00000051;
  
  uStack00000048 = CONCAT13(in_stack_00000030,(int3)((uint)in_stack_0000002c >> 8));
  uStack00000027 = param_2;
  if (!in_ZF && in_OF == in_SF) {
    FUN_6947f4b9();
    return;
  }
  FUN_6947f4c5();
  *(uint *)(extraout_ECX + -0x37) = *(uint *)(extraout_ECX + -0x37) >> 1 | (uint)in_CF << 0x1f;
  bVar2 = true;
  uStack00000035 = SUB41(&stack0x00000035,0);
  uStack00000036 = (undefined1)((uint)&stack0x00000035 >> 8);
  uStack00000037 = (undefined2)((uint)&stack0x00000035 >> 0x10);
  uStack00000029 = (undefined1)extraout_DX;
  uStack0000002a = (undefined1)((ushort)extraout_DX >> 8);
  uStack00000027 = 0x88;
  uStack00000025 = (undefined2)unaff_EDI;
  _uStack00000051 = 0x6947f5f9;
  puStack00000021 = &stack0x00000035;
  FUN_6944d3a6();
  _uStack00000051 = unaff_EBP + -0x68;
  uStack0000004d = (undefined2)extraout_ECX_00;
  uStack0000004f = (undefined1)((uint)extraout_ECX_00 >> 0x10);
  uStack00000050 = (undefined1)((uint)extraout_ECX_00 >> 0x18);
  uStack00000045 = 0xf3;
  uStack00000046 = 0x8808;
  uStack00000048 = CONCAT31((int3)extraout_EDX,0x2c);
  uStack00000041 = SUB41(&stack0x00000055,0);
  uStack00000042 = (undefined1)((uint)&stack0x00000055 >> 8);
  uVar1 = uStack00000042;
  uStack00000043 = (undefined2)((uint)&stack0x00000055 >> 0x10);
  uStack00000035 = (undefined1)unaff_EDI;
  uStack00000036 = (undefined1)((uint)unaff_EDI >> 8);
  uStack00000037 = (undefined2)((uint)unaff_EDI >> 0x10);
  if (!bVar2) {
    uStack00000042 = (undefined1)((uint)&stack0x00000055 >> 0x10);
    uStack00000029 = uStack00000050;
    uStack0000002a = uStack00000051;
    uStack00000027 = uStack0000004f;
    uStack00000041 = uVar1;
    FUN_6947f773();
    return;
  }
  FUN_6947f799();
  return;
}



//── FUN_6947f6d9  @0x000000006947f6d9  (44B) ──

void __fastcall FUN_6947f6d9(undefined4 param_1,undefined1 param_2)

{
  undefined4 uVar1;
  byte extraout_CL;
  undefined2 extraout_DX;
  int unaff_EBX;
  undefined4 *unaff_EDI;
  undefined1 uStack00000017;
  
  uStack00000017 = param_2;
  thunk_FUN_6947f7a7();
  FUN_6947fce1();
  *(int *)(unaff_EBX + -0xd) = *(int *)(unaff_EBX + -0xd) << (extraout_CL & 0x1f);
  in(0x6e);
  in(extraout_DX);
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_6947f773  @0x000000006947f773  (16B) ──

void __fastcall FUN_6947f773(undefined4 param_1,undefined1 param_2)

{
  undefined4 uVar1;
  byte extraout_CL;
  undefined2 extraout_DX;
  int unaff_EBX;
  undefined4 *unaff_EDI;
  bool in_ZF;
  char in_SF;
  char in_OF;
  undefined1 uStack00000013;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_6947f6d9();
    return;
  }
  uStack00000013 = param_2;
  thunk_FUN_6947f7a7();
  FUN_6947fce1();
  *(int *)(unaff_EBX + -0xd) = *(int *)(unaff_EBX + -0xd) << (extraout_CL & 0x1f);
  in(0x6e);
  in(extraout_DX);
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_6947f799  @0x000000006947f799  (14B) ──

void FUN_6947f799(void)

{
  FUN_6947f773();
  return;
}



//── FUN_6947f7a7  @0x000000006947f7a7  (92B) ──

void FUN_6947f7a7(void)

{
  undefined4 uVar1;
  byte extraout_CL;
  undefined2 extraout_DX;
  int unaff_EBX;
  undefined4 *unaff_EDI;
  bool in_SF;
  
  LOCK();
  UNLOCK();
  if (in_SF) {
    FUN_6947f753();
    return;
  }
  FUN_6947fce1();
  *(int *)(unaff_EBX + -0xd) = *(int *)(unaff_EBX + -0xd) << (extraout_CL & 0x1f);
  in(0x6e);
  in(extraout_DX);
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_6947f835  @0x000000006947f835  (31B) ──

void FUN_6947f835(void)

{
  undefined2 uVar1;
  undefined4 in_stack_00000018;
  undefined4 uStack0000001c;
  
  uVar1 = CONCAT11((char)((uint)&stack0x00000020 >> 8),(char)((uint)in_stack_00000018 >> 8));
  uStack0000001c = CONCAT22(uVar1,uVar1);
  FUN_6947fa0e();
  return;
}



//── FUN_6947f866  @0x000000006947f866  (21B) ──

void FUN_6947f866(void)

{
  LOCK();
  UNLOCK();
  FUN_6947f835();
  return;
}



//── FUN_6947f894  @0x000000006947f894  (31B) ──

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6947f894(void)

{
  int unaff_EBP;
  
  FUN_6947f866();
  _DAT_30c1a6dd = (_DAT_30c1a6dd - unaff_EBP) - 1;
  if ((POPCOUNT(_DAT_30c1a6dd & 0xff) & 1U) != 0) {
    FUN_6947ff72();
    return;
  }
  FUN_6947fcc4();
  return;
}



//── FUN_6947f8d2  @0x000000006947f8d2  (17B) ──

void FUN_6947f8d2(void)

{
  FUN_6947f981(0x10);
  return;
}



//── FUN_6947f8e5  @0x000000006947f8e5  (16B) ──

void FUN_6947f8e5(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_69433f9a();
    FUN_6947f945();
    return;
  }
  FUN_6947fe69();
  return;
}



//── FUN_6947f90e  @0x000000006947f90e  (23B) ──

void FUN_6947f90e(void)

{
  undefined4 uStack00000056;
  
  uStack00000056 = 0x6947f9dc;
  thunk_FUN_6944d405();
  FUN_6947f8d2();
  return;
}



//── FUN_6947f945  @0x000000006947f945  (39B) ──

void FUN_6947f945(void)

{
  (*DAT_69422724)();
  thunk_FUN_6947f9a9();
  FUN_6947fa36();
  FUN_6947fa95();
  return;
}



//── FUN_6947f981  @0x000000006947f981  (16B) ──

void FUN_6947f981(void)

{
  thunk_FUN_6944d40b();
  FUN_6947f8e5();
  return;
}



//── FUN_6947f9a9  @0x000000006947f9a9  (19B) ──

void FUN_6947f9a9(void)

{
  FUN_6947fc11();
  return;
}



//── FUN_6947fa36  @0x000000006947fa36  (93B) ──

void FUN_6947fa36(void)

{
  bool in_CF;
  
  LOCK();
  UNLOCK();
  if (!in_CF) {
    FUN_6947fab4();
    return;
  }
  FUN_6947fa95();
  return;
}



//── FUN_6947fab4  @0x000000006947fab4  (18B) ──

void FUN_6947fab4(void)

{
  undefined2 unaff_DI;
  undefined4 unaff_retaddr;
  undefined1 uStack00000006;
  undefined1 uStack00000007;
  undefined3 uStack00000008;
  
  uStack00000006 = (undefined1)unaff_DI;
  uStack00000008 = (undefined3)((uint)unaff_retaddr >> 8);
  uStack00000007 = (undefined1)((ushort)unaff_DI >> 8);
  FUN_6947fbc6();
  return;
}



//── FUN_6947fadc  @0x000000006947fadc  (10B) ──

void FUN_6947fadc(void)

{
  FUN_6947fb42();
  return;
}



//── FUN_6947fb25  @0x000000006947fb25  (17B) ──

void FUN_6947fb25(void)

{
  FUN_6947fb7b();
  return;
}



//── FUN_6947fb42  @0x000000006947fb42  (23B) ──

void FUN_6947fb42(void)

{
  int *unaff_ESI;
  
  thunk_FUN_6947fb04();
  *unaff_ESI = *unaff_ESI + -0x19f10c6c;
  FUN_6947fcc4();
  return;
}



//── FUN_6947fb7b  @0x000000006947fb7b  (50B) ──

void FUN_6947fb7b(void)

{
  uint uStack00000018;
  undefined8 in_stack_0000001c;
  
  in_stack_0000001c._3_4_ = in_stack_0000001c._3_4_ & 0xffffff00;
  uStack00000018 = in_stack_0000001c._3_4_;
  FUN_6947fbe7();
  return;
}



//── FUN_6947fbc6  @0x000000006947fbc6  (13B) ──

void FUN_6947fbc6(void)

{
  int *unaff_ESI;
  
  thunk_FUN_6947fb04();
  *unaff_ESI = *unaff_ESI + -0x19f10c6c;
  FUN_6947fcc4();
  return;
}



//── FUN_6947fbe7  @0x000000006947fbe7  (35B) ──

void FUN_6947fbe7(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_6947ff72();
    return;
  }
  FUN_6947fcc4();
  return;
}



//── FUN_6947fc11  @0x000000006947fc11  (110B) ──

void FUN_6947fc11(undefined2 param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4,
                 undefined4 param_5,undefined1 param_6)

{
  bool in_ZF;
  undefined1 uStack0000001c;
  undefined2 uStack0000001d;
  undefined1 uStack0000001f;
  undefined2 uStack00000020;
  undefined4 uStack00000022;
  
  uStack0000001f = (undefined1)((uint)param_4 >> 0x18);
  param_5._2_2_ = param_1;
  uStack0000001c = param_6;
  uStack00000020 = (undefined2)param_4;
  if (in_ZF) {
    uStack0000001d = param_5._2_2_;
    FUN_6947fafe();
    return;
  }
  uStack0000001c = (undefined1)param_2;
  uStack0000001d = (undefined2)((uint)param_2 >> 8);
  uStack0000001f = (undefined1)((uint)param_2 >> 0x18);
  FUN_6947fa36();
  uStack00000022 = CONCAT22(uStack0000001d,CONCAT11(uStack0000001c,0x69));
  FUN_6947fa95();
  return;
}



//── FUN_6947fcc4  @0x000000006947fcc4  (26B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_6947fcc4(void)

{
  code *pcVar1;
  
  FUN_6947fe1e();
  pcVar1 = (code *)swi(0x3c);
  (*pcVar1)();
  return;
}



//── FUN_6947fce1  @0x000000006947fce1  (98B) ──

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6947fce1(void)

{
  int unaff_EBP;
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_6947f894();
    return;
  }
  FUN_6947f866();
  _DAT_30c1a6dd = (_DAT_30c1a6dd - unaff_EBP) - 1;
  if ((POPCOUNT(_DAT_30c1a6dd & 0xff) & 1U) != 0) {
    FUN_6947ff72();
    return;
  }
  FUN_6947fcc4();
  return;
}



//── FUN_6947fd43  @0x000000006947fd43  (15B) ──

void FUN_6947fd43(void)

{
  FUN_6947fd6f();
  return;
}



//── FUN_6947fd6f  @0x000000006947fd6f  (74B) ──

void FUN_6947fd6f(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_6947fdfe();
    return;
  }
  FUN_6947fdd0();
  return;
}



//── FUN_6947fdd0  @0x000000006947fdd0  (9B) ──

void FUN_6947fdd0(void)

{
  FUN_6947feb3();
  return;
}



//── FUN_6947fdfe  @0x000000006947fdfe  (13B) ──

void FUN_6947fdfe(void)

{
  undefined4 uStack00000005;
  
  uStack00000005 = 0x6947febd;
  FUN_69433fb2();
  FUN_6947fe8b();
  return;
}



//── FUN_6947fe1e  @0x000000006947fe1e  (67B) ──

void FUN_6947fe1e(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    FUN_6947fd6f();
    return;
  }
  FUN_6947fd43();
  return;
}



//── FUN_6947fe8b  @0x000000006947fe8b  (13B) ──

void FUN_6947fe8b(void)

{
  FUN_6944d471();
  FUN_6947ea89();
  return;
}



//── FUN_6947feb3  @0x000000006947feb3  (12B) ──

void FUN_6947feb3(void)

{
  undefined4 uStack00000004;
  
  uStack00000004 = 0x6947febd;
  FUN_69433fb2();
  FUN_6947fe8b();
  return;
}



//── FUN_6947ff72  @0x000000006947ff72  (12B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_6947ff72(void)

{
  code *pcVar1;
  
  FUN_6947fe1e();
  pcVar1 = (code *)swi(0x3c);
  (*pcVar1)();
  return;
}



//── FUN_69485dac  @0x0000000069485dac  (32B) ──

void FUN_69485dac(void)

{
                    /* WARNING: Subroutine does not return */
  FUN_694277b3();
}



//── FUN_694900c9  @0x00000000694900c9  (214B) ──

void FUN_694900c9(undefined4 param_1,undefined4 param_2,uint param_3)

{
  byte *pbVar1;
  char cVar2;
  bool bVar3;
  byte bVar4;
  bool bVar5;
  uint uVar6;
  byte bVar7;
  uint extraout_ECX;
  byte bVar8;
  byte bVar9;
  byte bVar10;
  char *pcVar11;
  undefined1 auStack_2b8 [88];
  char acStack_260 [16];
  char acStack_250 [592];
  
  FUN_69444be2(0x14c);
  thunk_FUN_6944ef0a(acStack_250,param_3);
  uVar6 = 0;
  do {
    acStack_250[uVar6] = acStack_250[uVar6] - *(char *)(uVar6 + 0x14c + param_3);
    uVar6 = uVar6 + 1;
  } while (uVar6 < 0x14c);
  FUN_6944eeb0(auStack_2b8);
  FUN_6944eeda(auStack_2b8,acStack_250,0x14c);
  thunk_FUN_6944ef38(auStack_2b8);
  pcVar11 = acStack_260;
  bVar8 = 0xfffffd67 < param_3;
  bVar10 = SCARRY4(param_3,0x298);
  FUN_6949035b(pcVar11,0x10);
  do {
    pbVar1 = (byte *)(pcVar11 + 0x27);
    bVar7 = (byte)extraout_ECX;
    *pbVar1 = *pbVar1 << (bVar7 & 7) | *pbVar1 >> 8 - (bVar7 & 7);
    bVar3 = (extraout_ECX & 0x1f) != 0;
    bVar9 = !bVar3 & bVar8 | (bVar3 && (*pbVar1 & 1) != 0);
    bVar3 = (bVar7 & 0x1f) == 1;
    bVar4 = !bVar3 & bVar10;
    bVar7 = bVar7 & 0x1f;
    cVar2 = *pcVar11;
    *pcVar11 = *pcVar11 << bVar7;
    bVar5 = (extraout_ECX & 0x1f) != 0;
    bVar8 = !bVar5 & bVar9 | (bVar5 && (char)(cVar2 << bVar7 - 1) < '\0');
    bVar10 = 1;
  } while ((bool)(bVar7 != 1 & (bVar4 | bVar3 & (bVar9 ^ (char)*pbVar1 < '\0')) |
                 bVar7 == 1 & (bVar8 ^ *pcVar11 < '\0')));
  FUN_694904e0();
  return;
}



//── FUN_6949035b  @0x000000006949035b  (30B) ──

void FUN_6949035b(void)

{
  undefined1 *local_24;
  
  local_24 = (undefined1 *)&local_24;
  LOCK();
  UNLOCK();
  FUN_694904e0();
  return;
}



//── FUN_694903dd  @0x00000000694903dd  (37B) ──

void FUN_694903dd(void)

{
  FUN_6949048f();
  return;
}



//── FUN_69490414  @0x0000000069490414  (51B) ──

void FUN_69490414(void)

{
  FUN_694903dd();
  return;
}



//── FUN_6949048f  @0x000000006949048f  (36B) ──

void FUN_6949048f(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_69490674();
    return;
  }
  FUN_69490521();
  return;
}



//── FUN_694904e0  @0x00000000694904e0  (64B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_694904e0(void)

{
  bool in_PF;
  undefined2 uStack0000000e;
  undefined2 uStack00000010;
  
  _uStack0000000e = &stack0x00000022;
  if (in_PF) {
    _uStack0000000e = &stack0x00000022;
    FUN_69490453();
    return;
  }
  FUN_69490414();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69490521  @0x0000000069490521  (22B) ──

void FUN_69490521(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  undefined2 uStack_2;
  
  param_2 = CONCAT22((short)((uint)_uStack_2 >> 0x10),param_3._1_2_);
  FUN_69490622();
  return;
}



//── FUN_69490655  @0x0000000069490655  (46B) ──

/* WARNING: Instruction at (ram,0x69490709) overlaps instruction at (ram,0x69490708)
    */

void FUN_69490655(void)

{
  code *pcVar1;
  int iVar2;
  int extraout_ECX;
  int extraout_ECX_00;
  undefined1 extraout_DL;
  int unaff_EDI;
  undefined1 in_CS;
  
  FUN_6949077b();
  *(char *)(unaff_EDI + -0x28a442ae) = *(char *)(unaff_EDI + -0x28a442ae) << 7;
  if (extraout_ECX != 0) {
    FUN_6949063f(extraout_DL);
    return;
  }
  pcVar1 = (code *)swi(0x5d);
  (*pcVar1)();
  iVar2 = func_0x25d6b323(in_CS);
  if ((iVar2 + 0x770868e1 != 0) &&
     (*(int *)(iVar2 + -0xf572cb) = *(int *)(iVar2 + -0xf572cb) + extraout_ECX_00,
     (byte)((byte)(iVar2 + 0x770868e1) | 0x24) == 0)) {
    FUN_694908dc();
    return;
  }
  FUN_694908a0();
  return;
}



//── FUN_69490674  @0x0000000069490674  (10B) ──

void FUN_69490674(void)

{
  FUN_6949063f();
  return;
}



//── FUN_69490681  @0x0000000069490681  (83B) ──

void FUN_69490681(void)

{
  bool in_ZF;
  bool in_SF;
  
  if (!in_SF) {
    FUN_6949085e();
    return;
  }
  if (!in_ZF) {
    FUN_694908a0();
    return;
  }
  FUN_694908dc();
  return;
}



//── FUN_69490726  @0x0000000069490726  (20B) ──

void FUN_69490726(void)

{
  FUN_69490681();
  return;
}



//── FUN_6949074d  @0x000000006949074d  (23B) ──

void FUN_6949074d(void)

{
  FUN_69490726();
  return;
}



//── FUN_6949077b  @0x000000006949077b  (51B) ──

void FUN_6949077b(void)

{
  FUN_6949074d();
  return;
}



//── FUN_6949085e  @0x000000006949085e  (11B) ──

void FUN_6949085e(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_694908a0();
    return;
  }
  FUN_694908dc();
  return;
}



//── FUN_694908a0  @0x00000000694908a0  (21B) ──

void FUN_694908a0(void)

{
  int iVar1;
  
  iVar1 = thunk_FUN_6944ef15();
  if (iVar1 == 0) {
    FUN_69490974();
    return;
  }
  FUN_69494108();
  return;
}



//── FUN_694908b9  @0x00000000694908b9  (14B) ──

void FUN_694908b9(void)

{
  FUN_694908f0();
  FUN_69490951();
  return;
}



//── FUN_694908dc  @0x00000000694908dc  (9B) ──

void FUN_694908dc(void)

{
  FUN_6949086a();
  return;
}



//── FUN_694908f0  @0x00000000694908f0  (90B) ──

void FUN_694908f0(void)

{
  bool in_OF;
  undefined4 in_stack_00000003;
  undefined1 local_4;
  undefined1 uStack_3;
  undefined1 local_2;
  undefined1 uStack_1;
  
  local_4 = (undefined1)in_stack_00000003;
  uStack_3 = (undefined1)((uint)in_stack_00000003 >> 8);
  local_2 = (undefined1)((uint)in_stack_00000003 >> 0x10);
  uStack_1 = (undefined1)((uint)in_stack_00000003 >> 0x18);
  if (in_OF) {
    FUN_6949098d();
    return;
  }
  uStack_3 = SUB41(&local_4,0);
  local_2 = (undefined1)((uint)&local_4 >> 8);
  uStack_1 = (undefined1)((uint)&local_4 >> 0x10);
  FUN_69490951();
  return;
}



//── FUN_69490951  @0x0000000069490951  (10B) ──

void FUN_69490951(void)

{
  FUN_694909b1();
  return;
}



//── FUN_69490974  @0x0000000069490974  (25B) ──

void FUN_69490974(void)

{
  undefined4 in_stack_000000a8;
  
  FUN_6944eee4(in_stack_000000a8);
  FUN_69444c10();
  FUN_694908b9();
  return;
}



//── FUN_6949098d  @0x000000006949098d  (17B) ──

void FUN_6949098d(void)

{
  FUN_69490acd();
  return;
}



//── FUN_694909b1  @0x00000000694909b1  (13B) ──

void FUN_694909b1(void)

{
  FUN_69490acd();
  return;
}



//── FUN_694909fe  @0x00000000694909fe  (20B) ──

void FUN_694909fe(void)

{
  FUN_69490aa9();
  FUN_69490add();
  return;
}



//── FUN_69490a4e  @0x0000000069490a4e  (9B) ──

void FUN_69490a4e(void)

{
  FUN_69490a31();
  return;
}



//── FUN_69490a70  @0x0000000069490a70  (34B) ──

void FUN_69490a70(void)

{
  undefined4 in_stack_00000018;
  undefined2 uStack0000001c;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined1 in_stack_00000020;
  
  uStack0000001e = (undefined1)in_stack_00000018;
  uStack0000001f = (undefined1)((uint)in_stack_00000018 >> 8);
  uStack0000001c = CONCAT11(in_stack_00000020,uStack0000001f);
  FUN_69490a4e();
  return;
}



//── FUN_69490aa9  @0x0000000069490aa9  (11B) ──

void FUN_69490aa9(void)

{
  FUN_69490a70();
  return;
}



//── FUN_69490acd  @0x0000000069490acd  (15B) ──

void FUN_69490acd(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_694909fe();
    return;
  }
  FUN_69490aa9();
  FUN_69490add();
  return;
}



//── FUN_69490add  @0x0000000069490add  (19B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x69490ae6) overlaps instruction at (ram,0x69490ae4)
    */

void FUN_69490add(void)

{
  char extraout_DL;
  undefined4 unaff_EBX;
  int unaff_ESI;
  undefined4 unaff_EDI;
  char in_CF;
  bool in_ZF;
  undefined1 uStack_1d;
  
  uStack_1d = (undefined1)((uint)unaff_EDI >> 0x18);
  if (in_ZF) {
    FUN_69490b34();
    return;
  }
  while( true ) {
    FUN_69490ba8();
    *(char *)(unaff_ESI + -0x3829ef1f) = *(char *)(unaff_ESI + -0x3829ef1f) + extraout_DL + in_CF;
    in(0x83);
    if (&stack0x00000000 != (undefined1 *)0x1c && -2 < (int)&uStack_1d) break;
    uStack_1d = (undefined1)((uint)&stack0xffffffe4 >> 0x18);
    in_CF = '\0';
  }
  if ((int)&stack0xffffffe4 < 0) {
    uStack_1d = (undefined1)((uint)unaff_EBX >> 8);
    FUN_69490acd();
    return;
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69490b19  @0x0000000069490b19  (27B) ──

void FUN_69490b19(void)

{
  FUN_69490add();
  return;
}



//── FUN_69490b78  @0x0000000069490b78  (24B) ──

void FUN_69490b78(void)

{
  LOCK();
  UNLOCK();
  FUN_69490b5b();
  return;
}



//── FUN_69490ba8  @0x0000000069490ba8  (30B) ──

void FUN_69490ba8(void)

{
  FUN_69490b78();
  return;
}



//── FUN_69490eb7  @0x0000000069490eb7  (38B) ──

void FUN_69490eb7(void)

{
  undefined1 in_stack_00000018;
  undefined4 in_stack_0000001c;
  undefined1 uStack00000020;
  undefined1 uStack00000021;
  undefined1 uStack00000022;
  undefined1 uStack00000023;
  undefined1 in_stack_00000024;
  
  uStack00000023 = 0;
  uStack00000021 = in_stack_00000024;
  uStack00000022 = in_stack_00000018;
  uStack00000020 = (undefined1)((uint)in_stack_0000001c >> 0x18);
  FUN_6949107b();
  return;
}



//── FUN_69490ef8  @0x0000000069490ef8  (15B) ──

void FUN_69490ef8(void)

{
  FUN_69490f34();
  return;
}



//── FUN_69490f20  @0x0000000069490f20  (17B) ──

void FUN_69490f20(void)

{
  FUN_69490f34();
  return;
}



//── FUN_69490f34  @0x0000000069490f34  (96B) ──

void FUN_69490f34(void)

{
  int in_EAX;
  undefined4 uVar1;
  uint *puVar2;
  int unaff_EBX;
  
  uVar1 = (**(code **)(in_EAX + 0x3c))(0x11);
  (**(code **)(in_EAX + 0x70))(uVar1);
  FUN_69444c89();
  FUN_6944ef1b();
                    /* WARNING: Call to offcut address within same function */
  puVar2 = (uint *)func_0x69490fe9();
  *puVar2 = *puVar2 | 0xd5d18e27;
  *(int *)(unaff_EBX + 0x60) = *(int *)(unaff_EBX + 0x60) << 1;
  FUN_69491056();
  return;
}



//── FUN_69491010  @0x0000000069491010  (10B) ──

void FUN_69491010(void)

{
  FUN_69490f20();
  return;
}



//── FUN_69491033  @0x0000000069491033  (34B) ──

void FUN_69491033(void)

{
  bool in_SF;
  
  if (!in_SF) {
    FUN_69491010();
    return;
  }
  FUN_69490ef8();
  return;
}



//── FUN_69491056  @0x0000000069491056  (15B) ──

void FUN_69491056(void)

{
  FUN_694911c6();
  return;
}



//── FUN_6949107b  @0x000000006949107b  (13B) ──

void __fastcall FUN_6949107b(undefined1 param_1)

{
  undefined3 unaff_retaddr;
  undefined4 uStack00000004;
  
  uStack00000004 = CONCAT13(param_1,unaff_retaddr);
  FUN_69491033();
  return;
}



//── FUN_69491137  @0x0000000069491137  (13B) ──

void FUN_69491137(void)

{
  code *pcVar1;
  
  FUN_69491149();
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_69491149  @0x0000000069491149  (43B) ──

void FUN_69491149(void)

{
  FUN_6949120c();
  return;
}



//── FUN_6949116e  @0x000000006949116e  (21B) ──

void FUN_6949116e(void)

{
  code *pcVar1;
  
  FUN_69491149();
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_694911c6  @0x00000000694911c6  (48B) ──

void FUN_694911c6(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_69491137();
    return;
  }
  FUN_6949116e();
  return;
}



//── FUN_6949120c  @0x000000006949120c  (44B) ──

/* WARNING: Removing unreachable block (ram,0x694911f1) */

void FUN_6949120c(void)

{
  uint *puVar1;
  uint *puVar2;
  uint uVar3;
  uint uVar4;
  code *pcVar5;
  byte extraout_CL;
  bool bVar6;
  char in_SF;
  char in_OF;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  unkbyte10 extraout_ST1;
  undefined8 uVar7;
  int in_stack_00000020;
  int in_stack_00000024;
  int in_stack_00000028;
  int in_stack_00000030;
  undefined4 in_stack_00000034;
  ushort uStack00000038;
  undefined2 uStack0000003a;
  undefined1 uStack0000003c;
  undefined1 uStack0000003d;
  undefined1 uStack0000003e;
  undefined1 uStack0000003f;
  undefined1 uStack00000040;
  undefined1 uStack00000041;
  
  LOCK();
  UNLOCK();
  uStack0000003d = (undefined1)((uint)in_stack_00000034 >> 8);
  uStack0000003a = (undefined2)((uint)in_stack_00000034 >> 8);
  uStack0000003c = (undefined1)in_stack_00000034;
  uStack00000038 =
       (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 | (ushort)(in_VIF & 1) * 8 |
       (ushort)(in_AC & 1) * 4;
  uStack0000003e = uStack00000040;
  uStack0000003f = uStack00000041;
  if (in_OF != in_SF) {
    FUN_6949133b();
    return;
  }
  uStack0000003c = (undefined1)in_stack_00000028;
  uStack0000003d = (undefined1)((uint)in_stack_00000028 >> 8);
  uStack00000038 = 0x11b0;
  uStack0000003a = 0x6949;
  uVar7 = FUN_694912ba();
  puVar2 = (uint *)(in_stack_00000020 + 4);
  uStack0000003a = (undefined2)((ulonglong)uVar7 >> 0x10);
  uStack00000038 = CONCAT11(0xd3,(char)uVar7);
  if ((byte)((uint)in_stack_00000030 >> 8) <= *(byte *)(in_stack_00000020 + 0x2344d658)) {
    puVar1 = (uint *)(in_stack_00000030 + 0x66);
    *puVar1 = (int)*puVar1 >> 0x17;
    uVar3 = *puVar1;
    bVar6 = (*puVar2 & 1) != 0;
    *puVar2 = *puVar2 >> 1 | (uint)bVar6 << 0x1f;
    uVar4 = *(uint *)(in_stack_00000020 + -0x36);
    *(uint *)(in_stack_00000020 + -0x36) = uVar4 << 5 | (uint)(CONCAT14(bVar6,uVar4) >> 0x1c);
    if ((POPCOUNT(uVar3 & 0xff) & 1U) == 0) {
      uStack0000003e = 0xd3;
      uStack00000038 = CONCAT11(0xd3,uStack0000003d);
      uStack0000003a =
           (undefined2)(CONCAT13(uStack00000040,CONCAT12(uStack0000003f,uStack00000038)) >> 0x10);
      FUN_6949116e();
      return;
    }
    *(unkbyte10 *)(in_stack_00000024 + 0x3cb8a34d) = extraout_ST1;
    *(char *)(in_stack_00000028 + -0x382a6fbc) =
         *(char *)(in_stack_00000028 + -0x382a6fbc) << (extraout_CL & 0x1f);
                    /* WARNING: Subroutine does not return */
    FUN_694277b3();
  }
  uStack00000038 = 0x119a;
  uStack0000003a = 0x6949;
  FUN_69491149();
  pcVar5 = (code *)swi(3);
  (*pcVar5)();
  return;
}



//── FUN_69491292  @0x0000000069491292  (10B) ──

void FUN_69491292(void)

{
  FUN_69491312();
  return;
}



//── FUN_6949129c  @0x000000006949129c  (9B) ──

void FUN_6949129c(void)

{
  FUN_6949136e();
  return;
}



//── FUN_694912ba  @0x00000000694912ba  (102B) ──

void __fastcall FUN_694912ba(undefined4 param_1,undefined4 param_2)

{
  undefined4 unaff_EBX;
  bool in_OF;
  undefined1 unaff_retaddr;
  undefined4 uStack_8;
  undefined1 local_4;
  undefined2 local_3;
  undefined1 uStack_1;
  
  uStack_1 = (undefined1)((uint)unaff_EBX >> 0x18);
  uStack_8 = CONCAT13(unaff_retaddr,(int3)((uint)unaff_EBX >> 8));
  local_3 = SUB42(&uStack_8,0);
  local_4 = (undefined1)((uint)param_2 >> 8);
  if (!in_OF) {
    FUN_69491292();
    return;
  }
  FUN_6949129c();
  return;
}



//── FUN_69491312  @0x0000000069491312  (14B) ──

void FUN_69491312(void)

{
  undefined4 uStack00000008;
  
  uStack00000008 = 0x6949137b;
  FUN_69444c91();
  FUN_69491346();
  return;
}



//── FUN_69491346  @0x0000000069491346  (17B) ──

void FUN_69491346(void)

{
  FUN_69444d01();
  thunk_FUN_6944f15a();
  FUN_69444d37();
  FUN_694913a1();
  return;
}



//── FUN_6949136e  @0x000000006949136e  (16B) ──

void FUN_6949136e(void)

{
  undefined4 uStack00000008;
  
  uStack00000008 = 0x6949137b;
  FUN_69444c91();
  FUN_69491346();
  return;
}



//── FUN_694913a1  @0x00000000694913a1  (67B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Removing unreachable block (ram,0x694913b4) */
/* WARNING: Removing unreachable block (ram,0x694911f1) */

void FUN_694913a1(undefined4 param_1)

{
  uint *puVar1;
  uint *puVar2;
  uint uVar3;
  code *pcVar4;
  int iVar5;
  uint uVar6;
  byte extraout_CL;
  byte extraout_DL;
  int unaff_EBX;
  int unaff_EBP;
  int unaff_ESI;
  int *unaff_EDI;
  bool bVar7;
  unkbyte10 extraout_ST1;
  undefined1 uStack0000000a;
  undefined1 uStack0000000b;
  
  iVar5 = FUN_69444d77();
  (**(code **)(iVar5 + 0xa0))();
  uVar6 = FUN_69444e55();
  swi(4);
  if (!CARRY1(extraout_DL,*(byte *)((int)unaff_EDI + 0x68916207))) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  uStack0000000a = (undefined1)((uint)param_1 >> 0x10);
  uStack0000000b = (undefined1)((uint)param_1 >> 0x18);
  if ((int)(uVar6 & 0xffffffeb) < *unaff_EDI) {
    FUN_6949133b();
    return;
  }
  uStack0000000a = (undefined1)unaff_EBP;
  uStack0000000b = (undefined1)((uint)unaff_EBP >> 8);
  FUN_694912ba();
  puVar2 = (uint *)(unaff_EDI + 2);
  if (*(byte *)(unaff_EDI + 0x8d13597) < (byte)((uint)unaff_EBX >> 8)) {
    FUN_69491149();
    pcVar4 = (code *)swi(3);
    (*pcVar4)();
    return;
  }
  puVar1 = (uint *)(unaff_EBX + 0x66);
  *puVar1 = (int)*puVar1 >> 0x17;
  uVar6 = *puVar1;
  bVar7 = (*puVar2 & 1) != 0;
  *puVar2 = *puVar2 >> 1 | (uint)bVar7 << 0x1f;
  uVar3 = *(uint *)((int)unaff_EDI + -0x32);
  *(uint *)((int)unaff_EDI + -0x32) = uVar3 << 5 | (uint)(CONCAT14(bVar7,uVar3) >> 0x1c);
  if ((POPCOUNT(uVar6 & 0xff) & 1U) != 0) {
    *(unkbyte10 *)(unaff_ESI + 0x3cb8a34d) = extraout_ST1;
    *(char *)(unaff_EBP + -0x382a6fbc) = *(char *)(unaff_EBP + -0x382a6fbc) << (extraout_CL & 0x1f);
                    /* WARNING: Subroutine does not return */
    FUN_694277b3(0x1d1703eb);
  }
  FUN_6949116e();
  return;
}



//── FUN_69494108  @0x0000000069494108  (14B) ──

undefined4 FUN_69494108(void)

{
  return 0;
}



//── FUN_69497ffd  @0x0000000069497ffd  (72B) ──

undefined4 FUN_69497ffd(undefined4 param_1,short *param_2)

{
  undefined4 uVar1;
  
  if (*param_2 != 0x5a4d) {
    return 0;
  }
  uVar1 = FUN_6949851b();
  return uVar1;
}



//── FUN_69498146  @0x0000000069498146  (15B) ──

void FUN_69498146(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF != in_SF) {
    thunk_FUN_694987a1();
    return;
  }
  FUN_694987a1();
  return;
}



//── FUN_6949851b  @0x000000006949851b  (23B) ──

undefined4 FUN_6949851b(void)

{
  undefined4 uVar1;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_69498167();
    return uVar1;
  }
  return 0;
}



//── FUN_694987a1  @0x00000000694987a1  (180B) ──

void FUN_694987a1(int param_1)

{
  uint uVar1;
  int iVar2;
  void *local_14;
  code *pcStack_10;
  undefined *local_c;
  undefined4 local_8;
  
  local_8 = 0xfffffffe;
  local_c = &DAT_6942170c;
  pcStack_10 = FUN_69420f1c;
  local_14 = ExceptionList;
  uVar1 = FUN_6944c6be();
  local_c = (undefined *)((uint)local_c ^ uVar1);
  ExceptionList = &local_14;
  local_8 = 0;
  iVar2 = thunk_FUN_6944f4d4(&DAT_6941a54c);
  if (iVar2 != 0) {
    iVar2 = thunk_FUN_6944f4e1(&DAT_6941a54c,param_1 + -0x6941a54c);
    if (iVar2 != 0) {
      local_8 = 0xfffffffe;
      FUN_69498e5c();
      return;
    }
  }
  local_8 = 0xfffffffe;
  ExceptionList = local_14;
  FUN_69498b57();
  return;
}



//── FUN_69498b57  @0x0000000069498b57  (24B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_69498b57(void)

{
  code *pcVar1;
  bool in_ZF;
  
  if (in_ZF) {
    thunk_FUN_69498ba2();
    pcVar1 = (code *)swi(3);
    (*pcVar1)();
    return;
  }
  FUN_69498c0c();
  return;
}



//── FUN_69498b7e  @0x0000000069498b7e  (11B) ──

void FUN_69498b7e(void)

{
  FUN_69498bc6();
  return;
}



//── FUN_69498bc6  @0x0000000069498bc6  (68B) ──

void FUN_69498bc6(void)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  char in_SF;
  undefined2 in_stack_00000010;
  undefined2 uStack0000001c;
  
  uStack0000001c =
       (undefined2)
       CONCAT21(in_stack_00000010,
                in_SF * -0x80 | (in_ZF & 1) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' |
                in_CF & 1);
  _uStack0000001c = CONCAT22(uStack0000001c,uStack0000001c);
  FUN_69498c4f();
  return;
}



//── FUN_69498c0c  @0x0000000069498c0c  (22B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_69498c0c(void)

{
  code *pcVar1;
  
  thunk_FUN_69498ba2();
  pcVar1 = (code *)swi(3);
  (*pcVar1)();
  return;
}



//── FUN_69498c4f  @0x0000000069498c4f  (22B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69498c4f(void)

{
  undefined2 in_AX;
  bool in_SF;
  undefined4 in_stack_00000002;
  undefined1 uStack00000009;
  undefined1 uStack0000000a;
  undefined2 uStack0000000b;
  
  uStack00000009 = (undefined1)in_stack_00000002;
  uStack0000000a = (undefined1)((uint)in_stack_00000002 >> 8);
  uStack0000000b = (undefined2)((uint)in_stack_00000002 >> 0x10);
  if (in_SF) {
    FUN_69498cf8();
    return;
  }
  uStack00000009 = (undefined1)((ushort)in_AX >> 8);
  FUN_69498c69();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69498c69  @0x0000000069498c69  (23B) ──

void FUN_69498c69(void)

{
  FUN_69498cb8();
  return;
}



//── FUN_69498c98  @0x0000000069498c98  (9B) ──

void FUN_69498c98(void)

{
  FUN_69498dc6();
  return;
}



//── FUN_69498cb8  @0x0000000069498cb8  (42B) ──

void FUN_69498cb8(void)

{
  FUN_69498d2f();
  return;
}



//── FUN_69498cf8  @0x0000000069498cf8  (9B) ──

void FUN_69498cf8(void)

{
  FUN_69498c86();
  return;
}



//── FUN_69498d06  @0x0000000069498d06  (21B) ──

void FUN_69498d06(void)

{
  undefined2 unaff_retaddr;
  undefined1 uStack0000000a;
  
  uStack0000000a = (undefined1)((ushort)unaff_retaddr >> 8);
  FUN_69498e22();
  return;
}



//── FUN_69498d2f  @0x0000000069498d2f  (24B) ──

void FUN_69498d2f(void)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  uint uVar1;
  undefined4 uStack00000036;
  uint uStack0000003a;
  undefined2 uStack0000003e;
  undefined2 uStack00000040;
  undefined2 uStack00000042;
  undefined2 in_stack_00000044;
  
  uVar1 = (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
          (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
          (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1);
  uStack0000003a =
       uVar1 | (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
       (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000;
  uStack00000040 = (undefined2)uVar1;
  uStack00000042 = (undefined2)(uStack0000003a >> 0x10);
  uStack0000003e = uStack00000040;
  uStack00000036 = CONCAT22(in_stack_00000044,uStack00000042);
  FUN_69498d06();
  return;
}



//── FUN_69498da6  @0x0000000069498da6  (12B) ──

void FUN_69498da6(void)

{
  FUN_69498e3c();
  return;
}



//── FUN_69498dc6  @0x0000000069498dc6  (23B) ──

void FUN_69498dc6(void)

{
  uint *puVar1;
  uint uVar2;
  undefined1 in_AL;
  uint uVar4;
  int extraout_ECX;
  undefined1 unaff_BL;
  int unaff_ESI;
  undefined2 unaff_DI;
  undefined2 in_CS;
  byte in_CF;
  bool in_PF;
  undefined2 uVar5;
  uint uVar3;
  
  if (in_PF) {
    FUN_69498e04((short)(CONCAT12(in_AL,unaff_DI) >> 8));
    return;
  }
  uVar5 = 0x6949;
  FUN_69498da6(CONCAT13(unaff_BL,(int3)((uint)&stack0x00000000 >> 8)),0,
               (short)(CONCAT12(in_AL,unaff_DI) >> 8));
  uVar4 = func_0x12e78012(CONCAT22(uVar5,in_CS));
  puVar1 = (uint *)(extraout_ECX + -0x6169ec20);
  uVar2 = *puVar1;
  uVar3 = *puVar1;
  *puVar1 = uVar3 + uVar4 + (uint)in_CF;
  *(char *)(unaff_ESI + -0x4868ef1f) =
       *(char *)(unaff_ESI + -0x4868ef1f) + (char)uVar4 +
       (CARRY4(uVar2,uVar4) || CARRY4(uVar3 + uVar4,(uint)in_CF));
  if (0x7fffffff < uVar4) {
    FUN_69498c98();
    return;
  }
  FUN_69498dc6(0x824648d);
  return;
}



//── FUN_69498e04  @0x0000000069498e04  (29B) ──

void FUN_69498e04(void)

{
  uint *puVar1;
  uint uVar2;
  uint uVar4;
  int extraout_ECX;
  int unaff_ESI;
  undefined2 in_CS;
  byte in_CF;
  undefined2 uVar5;
  uint uVar3;
  
  uVar5 = 0x6949;
  FUN_69498da6();
  uVar4 = func_0x12e78012(CONCAT22(uVar5,in_CS));
  puVar1 = (uint *)(extraout_ECX + -0x6169ec20);
  uVar2 = *puVar1;
  uVar3 = *puVar1;
  *puVar1 = uVar3 + uVar4 + (uint)in_CF;
  *(char *)(unaff_ESI + -0x4868ef1f) =
       *(char *)(unaff_ESI + -0x4868ef1f) + (char)uVar4 +
       (CARRY4(uVar2,uVar4) || CARRY4(uVar3 + uVar4,(uint)in_CF));
  if (0x7fffffff < uVar4) {
    FUN_69498c98();
    return;
  }
  FUN_69498dc6(0x824648d);
  return;
}



//── FUN_69498e22  @0x0000000069498e22  (19B) ──

void FUN_69498e22(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_69498c98();
    return;
  }
  FUN_69498dc6();
  return;
}



//── FUN_69498e5c  @0x0000000069498e5c  (18B) ──

void FUN_69498e5c(void)

{
  int unaff_EBP;
  
  ExceptionList = *(void **)(unaff_EBP + -0x10);
  FUN_69498b34();
  return;
}



//── FUN_69498e7a  @0x0000000069498e7a  (47B) ──

void FUN_69498e7a(void)

{
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  
  FUN_69498fb1((byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) |
               (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10) |
               (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) |
               (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10));
  return;
}



//── FUN_69498ebe  @0x0000000069498ebe  (29B) ──

void FUN_69498ebe(void)

{
  FUN_69498e7a();
  return;
}



//── FUN_69498f66  @0x0000000069498f66  (11B) ──

void FUN_69498f66(void)

{
  FUN_69498efd();
  return;
}



//── FUN_69498f8a  @0x0000000069498f8a  (9B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69498f8a(void)

{
  code *pcVar1;
  int unaff_EBX;
  
  FUN_69498f66();
  pcVar1 = (code *)swi(4);
  if (SBORROW4(unaff_EBX,1)) {
    (*pcVar1)();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69498f93  @0x0000000069498f93  (28B) ──

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unable to track spacebase fully for stack */

void FUN_69498f93(void)

{
  undefined4 uVar1;
  code *pcVar2;
  int extraout_ECX;
  int iVar3;
  int unaff_EBX;
  undefined4 *unaff_EBP;
  undefined4 *puVar4;
  undefined4 uVar5;
  int unaff_ESI;
  ushort *puVar6;
  int unaff_EDI;
  byte in_CF;
  bool bVar7;
  undefined2 in_FPUControlWord;
  undefined8 uVar8;
  
  uVar8 = FUN_69498fca();
  puVar6 = (ushort *)(unaff_ESI + -1);
  *(byte *)(unaff_ESI + 0x30) = *(byte *)(unaff_ESI + 0x30) | in_CF >> 1;
  puVar4 = (undefined4 *)*unaff_EBP;
  *(undefined2 *)((int)uVar8 + 0x59d88f4b) = in_FPUControlWord;
  uVar5 = *puVar4;
  bVar7 = (byte)uVar8 < *(byte *)(unaff_EDI + 1);
  uVar1 = in((short)((ulonglong)uVar8 >> 0x20));
  *(undefined4 *)(unaff_EDI + 2) = uVar1;
  *puVar6 = *puVar6 + (ushort)bVar7 * (((ushort)uVar8 & 3) - (*puVar6 & 3));
  iVar3 = ((extraout_ECX + -1) - *(int *)(unaff_EDI + 0x6c)) - (uint)!bVar7;
  *puVar4 = *(undefined4 *)((int)puVar4 + 9);
  *(int *)((int)puVar4 + 6) = (int)uVar8;
  *(int *)((int)puVar4 + 2) = iVar3;
  *(int *)((int)puVar4 + -2) = (int)((ulonglong)uVar8 >> 0x20);
  *(int *)((int)puVar4 + -6) = unaff_EBX;
  *(int *)((int)puVar4 + -10) = (int)puVar4 + 10;
  *(undefined4 *)((int)puVar4 + -0xe) = uVar5;
  *(ushort **)((int)puVar4 + -0x12) = puVar6;
  *(int *)((int)puVar4 + -0x16) = unaff_EDI + 6;
  if (-1 < iVar3) {
    FUN_69498f8a();
    return;
  }
  *(undefined4 *)((int)puVar4 + -0x1a) = *(undefined4 *)((int)puVar4 + 0x19);
  *(undefined4 *)((int)puVar4 + -0x1e) = 0x69498df0;
  FUN_69498f66();
  pcVar2 = (code *)swi(4);
  if (SBORROW4(unaff_EBX,1)) {
    (*pcVar2)();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69498fb1  @0x0000000069498fb1  (22B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_69498fb1(void)

{
  code *pcVar1;
  int unaff_EBX;
  bool in_SF;
  
  if (!in_SF) {
    FUN_69498f8a();
    return;
  }
  FUN_69498f66();
  pcVar1 = (code *)swi(4);
  if (SBORROW4(unaff_EBX,1)) {
    (*pcVar1)();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_69498fca  @0x0000000069498fca  (9B) ──

void FUN_69498fca(void)

{
  FUN_69499071();
  return;
}



//── FUN_69499071  @0x0000000069499071  (90B) ──

void FUN_69499071(void)

{
  bool in_CF;
  bool in_ZF;
  undefined4 unaff_retaddr;
  undefined2 uStack0000000c;
  undefined2 uStack0000000e;
  undefined2 uStack_2;
  
  uStack0000000e = (undefined2)((uint)&stack0x00000020 >> 0x10);
  uStack_2 = (undefined2)((uint)unaff_retaddr >> 0x10);
  uStack0000000c = uStack_2;
  if (!in_CF && !in_ZF) {
    FUN_69498f47();
    return;
  }
  FUN_69499052();
  return;
}



//── FUN_69499c10  @0x0000000069499c10  (16B) ──

void FUN_69499c10(void)

{
  bool in_PF;
  
  if (!in_PF) {
    FUN_6949a1b9();
    return;
  }
  FUN_6949a1b9();
  return;
}



//── FUN_69499c90  @0x0000000069499c90  (11B) ──

void FUN_69499c90(void)

{
  FUN_69499d6f();
  return;
}



//── FUN_69499caf  @0x0000000069499caf  (21B) ──

void FUN_69499caf(void)

{
  int unaff_ESI;
  int unaff_EDI;
  float10 fVar1;
  
  fVar1 = (float10)FUN_69499c90();
  *(short *)(unaff_EDI + 0x7c) = (short)ROUND(fVar1);
  *(byte *)(unaff_ESI + -0x71) = *(byte *)(unaff_ESI + -0x71) & 0x44;
  FUN_69499d4f();
  return;
}



//── FUN_69499d2a  @0x0000000069499d2a  (16B) ──

void FUN_69499d2a(void)

{
  FUN_69499e30();
  return;
}



//── FUN_69499d4f  @0x0000000069499d4f  (11B) ──

void FUN_69499d4f(void)

{
  FUN_69499ef3();
  return;
}



//── FUN_69499d6f  @0x0000000069499d6f  (80B) ──

void FUN_69499d6f(undefined4 param_1)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  bool in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  uint uStack00000008;
  undefined4 uStack0000000c;
  undefined4 uStack00000010;
  uint uStack00000014;
  undefined1 uStack00000018;
  undefined2 uStack00000019;
  byte bStack0000001b;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined8 in_stack_00000020;
  
  uStack00000010 = param_1;
  uStack00000018 = (undefined1)param_1;
  uStack00000019 = (undefined2)((uint)param_1 >> 8);
  uStack00000008 =
       (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
       (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
       (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1) |
       (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 | (uint)(in_VIF & 1) * 0x80000 |
       (uint)(in_AC & 1) * 0x40000;
  uStack00000014._1_3_ = (undefined3)(uStack00000008 >> 8);
  uStack0000000c = CONCAT13(uStack00000018,uStack00000014._1_3_);
  bStack0000001b =
       in_SF * -0x80 | (in_ZF & 1U) * '@' | (in_AF & 1) * '\x10' | (in_PF & 1) * '\x04' | in_CF & 1;
  uStack0000001c = (undefined1)((ulonglong)in_stack_00000020 >> 0x10);
  uStack0000001d = (undefined1)((ulonglong)in_stack_00000020 >> 0x18);
  uStack0000001e = (undefined1)((ulonglong)in_stack_00000020 >> 0x20);
  uStack0000001f = (undefined1)((ulonglong)in_stack_00000020 >> 0x28);
  uStack00000014 = uStack00000008;
  if (in_ZF || in_OF != in_SF) {
    FUN_69499d2a();
    return;
  }
  uStack0000001f = uStack0000001c;
  FUN_69499d4f();
  return;
}



//── FUN_69499dc5  @0x0000000069499dc5  (82B) ──

void FUN_69499dc5(void)

{
  FUN_69499e89();
  return;
}



//── FUN_69499e30  @0x0000000069499e30  (14B) ──

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: This function may have set the stack pointer */

void FUN_69499e30(void)

{
  int *piVar1;
  int iVar2;
  char cVar3;
  code *pcVar4;
  undefined4 unaff_EBX;
  undefined4 *puVar5;
  undefined1 *puVar6;
  undefined4 *unaff_EBP;
  int unaff_ESI;
  undefined1 uStack0000001e;
  undefined4 uStack_6;
  
  uStack0000001e = (undefined1)((uint)unaff_EBX >> 8);
  FUN_69499dc5();
  puVar5 = (undefined4 *)&stack0xfffffffe;
  cVar3 = '\x19';
  do {
    unaff_EBP = unaff_EBP + -1;
    puVar5 = puVar5 + -1;
    *puVar5 = *unaff_EBP;
    cVar3 = cVar3 + -1;
  } while ('\0' < cVar3);
  puVar6 = (undefined1 *)0xeb8c1e98;
  pcVar4 = (code *)swi(0x72);
  (*pcVar4)();
  piVar1 = (int *)(unaff_ESI + 8);
  iVar2 = *piVar1;
  *piVar1 = *piVar1 + -0x33;
  pcVar4 = (code *)swi(4);
  if (SCARRY4(iVar2,-0x33)) {
    (*pcVar4)();
  }
  *(undefined1 **)(puVar6 + 0x10) = &stack0xfffffffe;
  FUN_6949a916();
  return;
}



//── FUN_69499e58  @0x0000000069499e58  (27B) ──

void FUN_69499e58(void)

{
  LOCK();
  UNLOCK();
  FUN_6949a916();
  return;
}



//── FUN_69499e89  @0x0000000069499e89  (86B) ──

void __fastcall FUN_69499e89(undefined4 param_1,undefined4 param_2)

{
  undefined4 uStack00000018;
  
  uStack00000018 = param_2;
  FUN_69499e58();
  return;
}



//── FUN_69499ef3  @0x0000000069499ef3  (79B) ──

/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: This function may have set the stack pointer */

void FUN_69499ef3(void)

{
  int *piVar1;
  int iVar2;
  char cVar3;
  code *pcVar4;
  undefined4 unaff_EBX;
  undefined4 *puVar5;
  undefined1 *puVar6;
  undefined4 *unaff_EBP;
  int unaff_ESI;
  undefined1 uStack0000001e;
  undefined4 uStack_6;
  
  uStack0000001e = (undefined1)((uint)unaff_EBX >> 8);
  FUN_69499dc5();
  puVar5 = (undefined4 *)&stack0xfffffffe;
  cVar3 = '\x19';
  do {
    unaff_EBP = unaff_EBP + -1;
    puVar5 = puVar5 + -1;
    *puVar5 = *unaff_EBP;
    cVar3 = cVar3 + -1;
  } while ('\0' < cVar3);
  puVar6 = (undefined1 *)0xeb8c1e98;
  pcVar4 = (code *)swi(0x72);
  (*pcVar4)();
  piVar1 = (int *)(unaff_ESI + 8);
  iVar2 = *piVar1;
  *piVar1 = *piVar1 + -0x33;
  pcVar4 = (code *)swi(4);
  if (SCARRY4(iVar2,-0x33)) {
    (*pcVar4)();
  }
  *(undefined1 **)(puVar6 + 0x10) = &stack0xfffffffe;
  FUN_6949a916();
  return;
}



//── FUN_69499f3a  @0x0000000069499f3a  (143B) ──

void FUN_69499f3a(void)

{
  bool in_SF;
  char in_OF;
  undefined1 unaff_retaddr;
  
  if (!in_SF) {
    FUN_6949a07e();
    return;
  }
  if (in_OF == '\x01') {
    FUN_6949a040();
    return;
  }
  FUN_6949a08e(unaff_retaddr);
  return;
}



//── FUN_6949a07e  @0x000000006949a07e  (14B) ──

void FUN_6949a07e(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_6949a040();
    return;
  }
  FUN_6949a08e();
  return;
}



//── FUN_6949a08e  @0x000000006949a08e  (9B) ──

void FUN_6949a08e(void)

{
  FUN_6949a5a3();
  return;
}



//── FUN_6949a40c  @0x000000006949a40c  (17B) ──

void __fastcall FUN_6949a40c(undefined4 param_1)

{
  thunk_FUN_6941add1(param_1,&DAT_694212f2);
  return;
}



//── FUN_6949a5a3  @0x000000006949a5a3  (11B) ──

void FUN_6949a5a3(void)

{
  FUN_6949a040();
  return;
}



//── FUN_6949a916  @0x000000006949a916  (169B) ──

undefined8 FUN_6949a916(void)

{
  byte extraout_CL;
  undefined8 uVar1;
  int iStack00000014;
  byte bStack00000018;
  undefined2 uStack00000020;
  undefined2 uStack00000022;
  undefined4 in_stack_00000024;
  undefined2 in_stack_00000028;
  undefined4 uStack0000003c;
  int iStack0000004e;
  
  iStack00000014 = _bStack00000018;
  uStack00000020 = (undefined2)in_stack_00000024;
  uStack00000022 = (undefined2)((uint)in_stack_00000024 >> 0x10);
  uStack0000003c = CONCAT22(in_stack_00000028,in_stack_00000028);
  iStack0000004e = iStack00000014;
  uVar1 = FUN_69499f3a();
  return CONCAT44(CONCAT31((int3)((ulonglong)uVar1 >> 0x28),
                           (byte)((ulonglong)uVar1 >> 0x20) & extraout_CL),
                  CONCAT22((short)((ulonglong)uVar1 >> 0x10),
                           CONCAT11((byte)((ulonglong)uVar1 >> 8) ^ bStack00000018,
                                    *(undefined1 *)(_bStack00000018 + ((uint)uVar1 & 0xff)))));
}



//── FUN_696b0012  @0x00000000696b0012  (15B) ──

void FUN_696b0012(void)

{
  FUN_6941da12();
  FUN_696b00c6();
  return;
}



//── FUN_696b0035  @0x00000000696b0035  (38B) ──

void FUN_696b0035(void)

{
  code *unaff_retaddr;
  
  if (unaff_retaddr == FUN_696b0144) {
    FUN_6941da12();
    FUN_696b0088();
    return;
  }
  FUN_696b0012();
  return;
}



//── FUN_696b005c  @0x00000000696b005c  (23B) ──

void FUN_696b005c(void)

{
  int unaff_retaddr;
  
  if ((POPCOUNT(unaff_retaddr + 0x9694fffdU & 0xff) & 1U) != 0) {
    FUN_6941da12();
    FUN_696b00a9();
    return;
  }
  FUN_696b00fd();
  return;
}



//── FUN_696b0088  @0x00000000696b0088  (19B) ──

void FUN_696b0088(void)

{
  thunk_FUN_696b005c();
  return;
}



//── FUN_696b00c6  @0x00000000696b00c6  (12B) ──

void FUN_696b00c6(void)

{
  FUN_696b0088(0x5af141bb);
  return;
}



//── FUN_696b00d6  @0x00000000696b00d6  (10B) ──

void FUN_696b00d6(void)

{
  thunk_FUN_696b00e0();
  return;
}



//── FUN_696b00e0  @0x00000000696b00e0  (16B) ──

void FUN_696b00e0(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    FUN_696b01d6();
    return;
  }
  FUN_696b014b();
  return;
}



//── FUN_696b00fd  @0x00000000696b00fd  (20B) ──

void FUN_696b00fd(void)

{
  FUN_6941da12();
  thunk_FUN_696b00e0();
  return;
}



//── FUN_696b014b  @0x00000000696b014b  (10B) ──

void FUN_696b014b(void)

{
  FUN_696b018f();
  return;
}



//── FUN_696b0165  @0x00000000696b0165  (33B) ──

void FUN_696b0165(void)

{
  bool in_SF;
  
  if (in_SF) {
    FUN_696b082f();
    return;
  }
  FUN_696b0f99();
  return;
}



//── FUN_696b018f  @0x00000000696b018f  (13B) ──

void FUN_696b018f(void)

{
  FUN_6941ecf1();
  thunk_FUN_696b0165();
  return;
}



//── FUN_696b01d6  @0x00000000696b01d6  (27B) ──

void FUN_696b01d6(void)

{
  int unaff_EBX;
  
  FUN_6941ecf1(unaff_EBX + -0x6b0026);
  thunk_FUN_696b0165();
  return;
}



//── FUN_696b0204  @0x00000000696b0204  (15B) ──

void FUN_696b0204(void)

{
  thunk_FUN_696b0144(0x39ffc);
  return;
}



//── FUN_696b0256  @0x00000000696b0256  (16B) ──

void FUN_696b0256(void)

{
  FUN_696b032f();
  return;
}



//── FUN_696b0291  @0x00000000696b0291  (145B) ──

void FUN_696b0291(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (in_ZF || in_OF != in_SF) {
    FUN_696b0256();
    return;
  }
  FUN_696b0308();
  return;
}



//── FUN_696b0308  @0x00000000696b0308  (17B) ──

void FUN_696b0308(void)

{
  bool in_SF;
  
  if (!in_SF) {
    FUN_696b0372();
    return;
  }
  FUN_696b0352();
  return;
}



//── FUN_696b032f  @0x00000000696b032f  (13B) ──

void FUN_696b032f(void)

{
  undefined2 uStack00000012;
  undefined2 in_stack_00000014;
  
  uStack00000012 = in_stack_00000014;
  FUN_696b0308();
  return;
}



//── FUN_696b0352  @0x00000000696b0352  (10B) ──

void FUN_696b0352(void)

{
  FUN_696b03c3();
  return;
}



//── FUN_696b03a3  @0x00000000696b03a3  (11B) ──

/* WARNING: Control flow encountered bad instruction data */

void __fastcall FUN_696b03a3(undefined4 param_1,undefined3 param_2)

{
  undefined1 uVar1;
  uint uVar2;
  undefined1 uVar3;
  undefined2 in_AX;
  byte extraout_CL;
  int iVar4;
  int unaff_EBX;
  uint unaff_EBP;
  int *unaff_ESI;
  int unaff_EDI;
  undefined1 in_CF;
  bool in_ZF;
  float10 extraout_ST0;
  undefined8 uVar5;
  undefined4 uStack00000005;
  undefined2 uStack0000001a;
  undefined1 uStack0000001e;
  undefined2 uStackY_1b;
  
  if (in_ZF) {
    FUN_696b04e2();
    return;
  }
  uStack00000005 = CONCAT22((short)param_2,in_AX);
  uStack0000001e = (undefined1)((uint)unaff_EBX >> 8);
  uStackY_1b = (undefined2)CONCAT31(param_2,(char)((uint)unaff_EBX >> 0x18));
  uStack0000001a = uStackY_1b;
  uVar5 = FUN_696b041a((short)((uint3)param_2 >> 8));
  if ((bool)in_CF || in_ZF) {
    uVar3 = *(undefined1 *)(unaff_EBX + ((uint)uVar5 & 0xff));
    iVar4 = CONCAT31((int3)((ulonglong)uVar5 >> 0x28),(byte)((ulonglong)uVar5 >> 0x20) & extraout_CL
                    );
    *unaff_ESI = *unaff_ESI - iVar4;
    uVar2 = *(uint *)((int)unaff_ESI + -99);
    uVar1 = in((short)iVar4);
    *(undefined1 *)(unaff_EDI + 1) = uVar1;
    *(longlong *)((unaff_EBP | uVar2) + 0x14) = (longlong)extraout_ST0;
    out(0xd,CONCAT31((int3)((ulonglong)uVar5 >> 8),uVar3));
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_696b03c3  @0x00000000696b03c3  (59B) ──

void __fastcall FUN_696b03c3(undefined4 param_1)

{
  FUN_696b03a3(param_1);
  return;
}



//── FUN_696b0490  @0x00000000696b0490  (10B) ──

void FUN_696b0490(void)

{
  FUN_696b0439();
  return;
}



//── FUN_696b04ba  @0x00000000696b04ba  (15B) ──

void FUN_696b04ba(void)

{
  undefined1 in_stack_00000014;
  undefined2 uStack00000020;
  undefined2 uStack00000022;
  
  uStack00000022 = (undefined2)((uint)&stack0x00000020 >> 0x10);
  uStack00000020 = CONCAT11(in_stack_00000014,(char)&stack0x00000020);
  FUN_696b049c();
  return;
}



//── FUN_696b04f0  @0x00000000696b04f0  (37B) ──

void FUN_696b04f0(void)

{
  undefined1 in_AL;
  undefined2 uStack00000004;
  undefined2 uStack00000006;
  
  uStack00000006 = SUB42(&stack0x00000006,0);
  uStack00000004 = CONCAT11((char)((uint)&stack0x00000006 >> 8),in_AL);
  FUN_696b06ad();
  return;
}



//── FUN_696b051d  @0x00000000696b051d  (51B) ──

void FUN_696b051d(void)

{
  thunk_FUN_696b0291();
  FUN_696b05b0();
  return;
}



//── FUN_696b056d  @0x00000000696b056d  (49B) ──

void FUN_696b056d(void)

{
  FUN_696b060d();
  return;
}



//── FUN_696b058c  @0x00000000696b058c  (11B) ──

int FUN_696b058c(void)

{
  int iVar1;
  
  iVar1 = FUN_696b056d();
  return iVar1 + 0x21c83b43;
}



//── FUN_696b05b0  @0x00000000696b05b0  (11B) ──

int FUN_696b05b0(void)

{
  int iVar1;
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    iVar1 = FUN_696b058c();
    return iVar1;
  }
  iVar1 = FUN_696b056d();
  return iVar1 + 0x21c83b43;
}



//── FUN_696b060d  @0x00000000696b060d  (29B) ──

void FUN_696b060d(undefined4 param_1,undefined2 param_2,undefined4 param_3,undefined4 param_4,
                 undefined4 param_5,undefined4 param_6,undefined4 param_7,undefined2 param_8)

{
  undefined4 unaff_retaddr;
  
  param_3._1_1_ = (undefined1)((uint)&param_8 >> 8);
  param_3._2_2_ = (undefined2)((uint)&param_8 >> 0x10);
  param_7._0_1_ = (undefined1)((uint)unaff_retaddr >> 8);
  param_3._0_1_ = (undefined1)param_7;
  param_1._3_1_ = (undefined1)((uint)&param_8 >> 0x10);
  param_1._1_2_ = param_2;
  param_1._0_1_ = (undefined1)((ushort)param_8 >> 8);
  param_7._0_1_ = (undefined1)((uint)param_4 >> 0x18);
  param_7._1_1_ = (undefined1)param_5;
  param_7._2_1_ = (undefined1)((uint)param_5 >> 8);
  FUN_696b0669();
  return;
}



//── FUN_696b0642  @0x00000000696b0642  (25B) ──

void FUN_696b0642(void)

{
  FUN_696b05b0();
  return;
}



//── FUN_696b0669  @0x00000000696b0669  (43B) ──

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_696b0669(void)

{
  uint *puVar1;
  uint uVar2;
  undefined4 uVar3;
  undefined8 uVar4;
  undefined1 extraout_CL;
  int iVar5;
  int unaff_EBP;
  undefined1 in_CF;
  char in_SF;
  char in_OF;
  undefined8 uVar6;
  undefined1 uStack00000006;
  undefined2 uStack00000007;
  undefined1 uStack00000009;
  undefined1 uStack0000000a;
  undefined8 in_stack_00000010;
  undefined2 uStack0000001b;
  undefined2 uStack0000001d;
  undefined4 in_stack_00000020;
  
  uVar4 = in_stack_00000010;
  uStack00000006 = 0x7b;
  uStack00000007 = 0x6b06;
  uStack00000009 = 0x69;
                    /* WARNING: Call to offcut address within same function */
  uVar6 = func_0x696b068e();
  iVar5 = (int)((ulonglong)uVar6 >> 0x20);
  _DAT_2ed3b426 = (undefined4)uVar6;
  puVar1 = (uint *)(iVar5 + 0x18e98e18);
  uVar2 = *puVar1;
  *puVar1 = uVar2 << 0x1a | (uint)(CONCAT14(in_CF,uVar2) >> 7);
  uVar3 = *(undefined4 *)(iVar5 + -0x73 + unaff_EBP * 8);
  uStack00000006 = (undefined1)uVar3;
  uStack00000007 = (undefined2)((uint)uVar3 >> 8);
  uStack00000009 = (undefined1)((uint)uVar3 >> 0x18);
  if (in_OF == in_SF) {
    FUN_696b06da();
    return;
  }
  uStack00000009 = (undefined1)in_stack_00000010;
  uStack0000000a = (undefined1)((ulonglong)in_stack_00000010 >> 8);
  uStack00000007 = (undefined2)unaff_EBP;
  uStack00000006 = (undefined1)((uint)in_stack_00000020 >> 0x18);
  in_stack_00000010._2_4_ = CONCAT31(in_stack_00000010._3_3_,extraout_CL);
  uStack0000001b = (undefined2)in_stack_00000010._2_4_;
  uStack0000001d = (undefined2)((ulonglong)uVar4 >> 0x20);
  FUN_696b0669();
  return;
}



//── FUN_696b06ad  @0x00000000696b06ad  (40B) ──

void FUN_696b06ad(undefined2 param_1)

{
  bool in_SF;
  undefined2 uStack0000003a;
  
  if (!in_SF) {
    FUN_696b0642();
    return;
  }
  uStack0000003a = param_1;
  FUN_696b05b0();
  return;
}



//── FUN_696b06da  @0x00000000696b06da  (16B) ──

void FUN_696b06da(void)

{
  FUN_696b0809();
  return;
}



//── entry  @0x00000000696b06ff  (28B) ──

void entry(void)

{
  undefined1 uVar1;
  undefined4 uVar2;
  byte *pbVar3;
  int extraout_ECX;
  undefined2 uVar4;
  undefined4 *unaff_ESI;
  undefined4 *unaff_EDI;
  undefined6 uVar5;
  short sStack0000002b;
  
  uVar5 = FUN_696b0718();
  uVar4 = (undefined2)((uint6)uVar5 >> 0x20);
  if (SCARRY4(extraout_ECX,1)) {
    uVar2 = in(uVar4);
    *unaff_EDI = uVar2;
    do {
                    /* WARNING: Do nothing block with infinite loop */
    } while( true );
  }
  uVar1 = in(uVar4);
  *(undefined1 *)unaff_EDI = uVar1;
  uVar1 = in(uVar4);
  *(undefined1 *)((int)unaff_EDI + 1) = uVar1;
  out(*unaff_ESI,uVar4);
  pbVar3 = (byte *)((int)uVar5 + 1);
  if (CARRY1((byte)pbVar3,*pbVar3)) {
    FUN_696b051d();
    return;
  }
  thunk_FUN_696b0291();
  sStack0000002b = (short)(undefined1 *)((int)unaff_EDI + 1) + 1;
  FUN_696b05b0();
  return;
}



//── FUN_696b0718  @0x00000000696b0718  (12B) ──

void FUN_696b0718(void)

{
  bool in_CF;
  
  if (in_CF) {
    FUN_696b051d();
    return;
  }
  thunk_FUN_696b0291();
  FUN_696b05b0();
  return;
}



//── FUN_696b0786  @0x00000000696b0786  (9B) ──

uint __fastcall FUN_696b0786(undefined4 param_1,undefined4 param_2)

{
  uint uVar1;
  bool in_CF;
  bool in_ZF;
  undefined4 uStack00000069;
  
  if (in_CF || in_ZF) {
    uVar1 = FUN_696b0765();
    return uVar1;
  }
  uStack00000069 = param_2;
  uVar1 = FUN_696b083c();
  return uVar1 & 0xc79160fe;
}



//── FUN_696b0791  @0x00000000696b0791  (10B) ──

uint __fastcall FUN_696b0791(undefined4 param_1,undefined4 param_2)

{
  uint uVar1;
  undefined4 uStack00000067;
  
  uStack00000067 = param_2;
  uVar1 = FUN_696b083c();
  return uVar1 & 0xc79160fe;
}



//── FUN_696b07bd  @0x00000000696b07bd  (54B) ──

void FUN_696b07bd(void)

{
  FUN_696b0786();
  return;
}



//── FUN_696b0809  @0x00000000696b0809  (38B) ──

void FUN_696b0809(void)

{
  FUN_696b07bd();
  return;
}



//── FUN_696b082f  @0x00000000696b082f  (13B) ──

void FUN_696b082f(void)

{
  undefined4 in_EAX;
  int unaff_EBX;
  
  *(undefined4 *)(&DAT_6903d24c + unaff_EBX) = in_EAX;
  FUN_696b00b4();
  return;
}



//── FUN_696b083c  @0x00000000696b083c  (129B) ──

void FUN_696b083c(void)

{
  uint uVar1;
  int extraout_ECX;
  char extraout_DH;
  int unaff_EBX;
  undefined4 unaff_EBP;
  undefined2 uStack00000007;
  undefined2 local_e;
  undefined1 uStack_c;
  undefined1 uStack_b;
  undefined2 uStack_a;
  undefined1 *local_8;
  undefined1 uStack_4;
  undefined1 uStack_3;
  undefined1 uStack_2;
  undefined1 uStack_1;
  
  uStack_a = (undefined2)((uint)unaff_EBP >> 0x10);
  local_8 = (undefined1 *)&local_e;
  local_e = SUB42(&local_e,0);
  uStack_c = (undefined1)((uint)&local_e >> 0x10);
  uStack_b = (undefined1)((uint)&local_e >> 0x18);
  uStack_4 = 0xa0;
  uStack_3 = 8;
  uStack_2 = 0x6b;
  uStack_1 = 0x69;
  uVar1 = func_0x696b0743();
  *(char *)(unaff_EBX + 0x5cb54623) = *(char *)(unaff_EBX + 0x5cb54623) - extraout_DH;
  uStack00000007 =
       (undefined2)
       CONCAT31((int3)(uVar1 >> 8),
                ((char)uVar1 - *(char *)(extraout_ECX + 0x7ef11aef)) - (uVar1 < 0xbf4c25b5));
  FUN_696b0ec1();
  return;
}



//── FUN_696b08ff  @0x00000000696b08ff  (14B) ──

void FUN_696b08ff(void)

{
  undefined4 in_EAX;
  int unaff_EBX;
  
  *(undefined4 *)(&DAT_6903d24c + unaff_EBX) = in_EAX;
  FUN_696b00b4();
  return;
}



//── FUN_696b093e  @0x00000000696b093e  (12B) ──

void FUN_696b093e(undefined4 param_1,undefined8 param_2)

{
  int extraout_ECX;
  bool in_PF;
  undefined1 uStack_2;
  undefined1 uStack_1;
  
  uStack_2 = (undefined1)((ulonglong)param_2 >> 0x20);
  uStack_1 = (undefined1)((ulonglong)param_2 >> 0x28);
  if (in_PF) {
    FUN_696b09f8();
    return;
  }
  FUN_696b09c0((char)((uint)&uStack_2 >> 8));
  in(0x60);
  *(byte *)(extraout_ECX + 0xe848f60) = ~*(byte *)(extraout_ECX + 0xe848f60);
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_696b0962  @0x00000000696b0962  (75B) ──

/* WARNING: Instruction at (ram,0x696b098d) overlaps instruction at (ram,0x696b098c)
    */
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_696b0962(undefined4 param_1,undefined2 param_2)

{
  uint *puVar1;
  undefined1 uVar2;
  uint uVar3;
  byte bVar4;
  uint uVar5;
  byte extraout_CH;
  int extraout_ECX;
  uint uVar6;
  undefined4 unaff_EBX;
  int unaff_EBP;
  undefined1 *unaff_ESI;
  int unaff_EDI;
  undefined1 in_OF;
  undefined8 uVar7;
  undefined4 uStack0000006a;
  undefined2 uStack_6;
  undefined4 uStack_4;
  
  uStack_4 = param_1;
  uStack_6 = 0x696b;
  uVar7 = FUN_696b093e();
  uVar6 = (uint)((ulonglong)uVar7 >> 0x20);
  if ((bool)in_OF) {
    uVar5 = CONCAT22((short)((ulonglong)uVar7 >> 0x10),
                     (ushort)(byte)((char)uVar7 + (char)((ulonglong)uVar7 >> 8) * '$'));
    uVar3 = uVar5 & 0xeb0d55ff;
    _DAT_d3b426a8 = uVar5;
  }
  else {
    puVar1 = (uint *)((uint)uVar7 - 0x4a);
    *puVar1 = *puVar1 ^ 0x1d7ae467;
    in((short)((ulonglong)uVar7 >> 0x20));
    uVar3 = uVar6 - *(uint *)(&SUB_12e78012 + uVar6);
    in((short)uVar3);
    uVar5 = (uint)uVar7 & 0xffffff00;
    if (uVar6 < *(uint *)(&SUB_12e78012 + uVar6)) {
      LOCK();
      uVar2 = *(undefined1 *)(unaff_EBP + -0x68);
      *(undefined1 *)(unaff_EBP + -0x68) = (char)(uVar3 >> 8);
      UNLOCK();
      in(CONCAT11(uVar2,(char)uVar3));
      goto code_r0x696b09ac;
    }
  }
  if (uVar3 != 0) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  if (unaff_EDI == 0) {
    unaff_EBX = 0x44b5d23c;
    bVar4 = (byte)uRam00000000 & extraout_CH;
    uStack_4 = CONCAT13(extraout_CH,(undefined3)uStack_4);
    uRam00000000 = CONCAT31((int3)(uVar5 >> 8),*unaff_ESI);
    if ((POPCOUNT(bVar4) & 1U) != 0) {
      uStack_6 = param_2;
      uStack0000006a = 0x44b5d23c;
      FUN_696b09c0((char)((uint)&uStack_6 >> 8));
      in(0x60);
      *(byte *)(extraout_ECX + 0xe848f60) = ~*(byte *)(extraout_ECX + 0xe848f60);
      do {
                    /* WARNING: Do nothing block with infinite loop */
      } while( true );
    }
  }
code_r0x696b09ac:
  uStack_6 = param_2;
  uStack0000006a = unaff_EBX;
  FUN_696b09f8();
  return;
}



//── FUN_696b09c0  @0x00000000696b09c0  (17B) ──

void FUN_696b09c0(void)

{
  FUN_696b0a51();
  return;
}



//── FUN_696b09f8  @0x00000000696b09f8  (21B) ──

void FUN_696b09f8(void)

{
  int extraout_ECX;
  
  FUN_696b09c0();
  in(0x60);
  *(byte *)(extraout_ECX + 0xe848f60) = ~*(byte *)(extraout_ECX + 0xe848f60);
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_696b0a51  @0x00000000696b0a51  (71B) ──

void FUN_696b0a51(void)

{
  undefined2 uStack0000000c;
  undefined2 in_stack_00000010;
  
  uStack0000000c = in_stack_00000010;
  FUN_696b0c46();
  return;
}



//── FUN_696b0ad5  @0x00000000696b0ad5  (97B) ──

/* WARNING: Instruction at (ram,0x696b0989) overlaps instruction at (ram,0x696b0988)
    */
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_696b0ad5(void)

{
  uint *puVar1;
  undefined1 uVar2;
  uint uVar3;
  byte bVar4;
  uint uVar5;
  byte extraout_CH;
  int extraout_ECX;
  uint uVar6;
  undefined4 unaff_EBX;
  int unaff_EBP;
  undefined1 *unaff_ESI;
  int unaff_EDI;
  bool in_CF;
  undefined1 in_OF;
  undefined8 uVar7;
  undefined1 uStack0000000a;
  undefined4 uStack0000006f;
  
  if (in_CF) {
    FUN_696b0962();
    return;
  }
  uVar7 = FUN_696b093e();
  uVar6 = (uint)((ulonglong)uVar7 >> 0x20);
  if ((bool)in_OF) {
    uVar5 = CONCAT22((short)((ulonglong)uVar7 >> 0x10),
                     (ushort)(byte)((char)uVar7 + (char)((ulonglong)uVar7 >> 8) * '$'));
    uVar3 = uVar5 & 0xeb0d55ff;
    _DAT_d3b426a8 = uVar5;
  }
  else {
    puVar1 = (uint *)((uint)uVar7 - 0x4a);
    *puVar1 = *puVar1 ^ 0x1d7ae467;
    in((short)((ulonglong)uVar7 >> 0x20));
    uVar3 = uVar6 - *(uint *)(&SUB_12e78012 + uVar6);
    in((short)uVar3);
    uVar5 = (uint)uVar7 & 0xffffff00;
    if (uVar6 < *(uint *)(&SUB_12e78012 + uVar6)) {
      LOCK();
      uVar2 = *(undefined1 *)(unaff_EBP + -0x68);
      *(undefined1 *)(unaff_EBP + -0x68) = (char)(uVar3 >> 8);
      UNLOCK();
      in(CONCAT11(uVar2,(char)uVar3));
      goto code_r0x696b09ac;
    }
  }
  if (uVar3 != 0) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  if (unaff_EDI == 0) {
    unaff_EBX = 0x44b5d23c;
    bVar4 = (byte)uRam00000000 & extraout_CH;
    uRam00000000 = CONCAT31((int3)(uVar5 >> 8),*unaff_ESI);
    if ((POPCOUNT(bVar4) & 1U) != 0) {
      uStack0000000a = 0xd2;
      uStack0000006f = 0x44b5d23c;
      FUN_696b09c0();
      in(0x60);
      *(byte *)(extraout_ECX + 0xe848f60) = ~*(byte *)(extraout_ECX + 0xe848f60);
      do {
                    /* WARNING: Do nothing block with infinite loop */
      } while( true );
    }
  }
code_r0x696b09ac:
  uStack0000000a = (undefined1)((uint)unaff_EBX >> 8);
  uStack0000006f = unaff_EBX;
  FUN_696b09f8();
  return;
}



//── FUN_696b0b3d  @0x00000000696b0b3d  (127B) ──

void FUN_696b0b3d(void)

{
  byte *pbVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  bool bVar5;
  bool bVar6;
  byte bVar7;
  byte bVar8;
  uint uVar9;
  int extraout_ECX;
  char *extraout_EDX;
  byte in_CF;
  undefined1 in_PF;
  
  while( true ) {
    if (!(bool)in_PF) break;
    FUN_696b0c29();
    uVar9 = in(0x25);
    bVar2 = *(byte *)(extraout_ECX + 0x52e512e7);
    bVar4 = (byte)extraout_ECX + *(byte *)(extraout_ECX + 0x52e512e7);
    pbVar1 = (byte *)(CONCAT31((int3)((uint)extraout_ECX >> 8),bVar4 + in_CF) + 0x27);
    bVar7 = (byte)uVar9 & 7;
    *pbVar1 = *pbVar1 << bVar7 | *pbVar1 >> 8 - bVar7;
    bVar5 = (uVar9 & 0x1f) != 0;
    bVar7 = *pbVar1;
    bVar8 = (byte)uVar9 & 0x1f;
    cVar3 = *extraout_EDX;
    *extraout_EDX = *extraout_EDX >> bVar8;
    bVar6 = (uVar9 & 0x1f) != 0;
    in_CF = !bVar6 && (!bVar5 && (CARRY1((byte)extraout_ECX,bVar2) || CARRY1(bVar4,in_CF)) ||
                      bVar5 && (bVar7 & 1) != 0) || bVar6 && (cVar3 >> bVar8 - 1 & 1U) != 0;
    in_PF = (POPCOUNT(uVar9 - 1 & 0xff) & 1U) == 0;
  }
  FUN_696b0c59();
  return;
}



//── FUN_696b0b66  @0x00000000696b0b66  (21B) ──

void FUN_696b0b66(void)

{
  undefined4 uVar1;
  undefined2 extraout_DX;
  int *unaff_EBX;
  undefined4 *unaff_EDI;
  
  FUN_696b0b3d();
  *unaff_EBX = *unaff_EBX + 0x77;
  uVar1 = in(extraout_DX);
  *unaff_EDI = uVar1;
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



//── FUN_696b0c29  @0x00000000696b0c29  (9B) ──

void FUN_696b0c29(void)

{
  FUN_696b0e15();
  return;
}



//── FUN_696b0c59  @0x00000000696b0c59  (9B) ──

void FUN_696b0c59(void)

{
  byte *pbVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  bool bVar5;
  bool bVar6;
  byte bVar7;
  byte bVar8;
  uint uVar9;
  int extraout_ECX;
  char *extraout_EDX;
  byte in_CF;
  
  do {
    FUN_696b0c29();
    uVar9 = in(0x25);
    bVar2 = *(byte *)(extraout_ECX + 0x52e512e7);
    bVar4 = (byte)extraout_ECX + *(byte *)(extraout_ECX + 0x52e512e7);
    pbVar1 = (byte *)(CONCAT31((int3)((uint)extraout_ECX >> 8),bVar4 + in_CF) + 0x27);
    bVar7 = (byte)uVar9 & 7;
    *pbVar1 = *pbVar1 << bVar7 | *pbVar1 >> 8 - bVar7;
    bVar5 = (uVar9 & 0x1f) != 0;
    bVar7 = *pbVar1;
    bVar8 = (byte)uVar9 & 0x1f;
    cVar3 = *extraout_EDX;
    *extraout_EDX = *extraout_EDX >> bVar8;
    bVar6 = (uVar9 & 0x1f) != 0;
    in_CF = !bVar6 && (!bVar5 && (CARRY1((byte)extraout_ECX,bVar2) || CARRY1(bVar4,in_CF)) ||
                      bVar5 && (bVar7 & 1) != 0) || bVar6 && (cVar3 >> bVar8 - 1 & 1U) != 0;
  } while ((POPCOUNT(uVar9 - 1 & 0xff) & 1U) == 0);
  FUN_696b0c59();
  return;
}



//── FUN_696b0c71  @0x00000000696b0c71  (13B) ──

void FUN_696b0c71(void)

{
  FUN_696b0d06();
  return;
}



//── FUN_696b0c94  @0x00000000696b0c94  (37B) ──

void FUN_696b0c94(void)

{
  FUN_696b0c71();
  return;
}



//── FUN_696b0d36  @0x00000000696b0d36  (20B) ──

/* WARNING: Instruction at (ram,0x696b0c79) overlaps instruction at (ram,0x696b0c78)
    */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x696b0ca7) */
/* WARNING: Removing unreachable block (ram,0x696b0c81) */
/* WARNING: Removing unreachable block (ram,0x696b0c28) */
/* WARNING: Removing unreachable block (ram,0x696b0c8b) */

undefined8 FUN_696b0d36(void)

{
  int *piVar1;
  char cVar2;
  undefined1 uVar3;
  uint uVar4;
  int extraout_ECX;
  undefined2 uVar5;
  int unaff_EBX;
  undefined4 *puVar6;
  undefined4 *unaff_EBP;
  undefined4 *unaff_ESI;
  undefined2 in_DS;
  int in_GS_OFFSET;
  undefined1 in_CF;
  char in_AF;
  undefined1 in_ZF;
  undefined8 uVar7;
  undefined1 uStack00000007;
  undefined4 auStack_3982 [3671];
  undefined1 *puStack_24;
  undefined4 uStack_8;
  
  uVar7 = FUN_696b0dec();
  uVar3 = in(0x6e);
  if (!(bool)in_CF && !(bool)in_ZF) {
    return CONCAT44((int)*(undefined6 *)(unaff_EBP + 0xf),
                    CONCAT31((int3)((ulonglong)uVar7 >> 8),uVar3));
  }
  piVar1 = (int *)segment(in_DS,(short)unaff_EBX + 0x2444);
  *piVar1 = *piVar1 + -1;
  uVar5 = (undefined2)((ulonglong)uVar7 >> 0x20);
  out(uVar5,0xd4);
  uRam31c2a738 = in(uVar5);
  if (extraout_ECX + unaff_EBP[-0x53f76e7] != 1) {
    uRam054418d4 = 0xa8;
    puStack_24 = &stack0xfffffffc;
    puVar6 = (undefined4 *)&stack0xfffffffc;
    cVar2 = '\a';
    do {
      unaff_EBP = unaff_EBP + -1;
      puVar6 = puVar6 + -1;
      *puVar6 = *unaff_EBP;
      cVar2 = cVar2 + -1;
    } while ('\0' < cVar2);
    uVar4 = CONCAT31(0x54418,in_AF * -6 + -0x2c) & 0xffffff0f;
    uRam31c2a739 = CONCAT22((short)(uVar4 >> 0x10),CONCAT11('\x18' - in_AF,(char)uVar4));
    *(int *)((int)auStack_3982 + in_GS_OFFSET) = (int)((ulonglong)uVar7 >> 0x20);
    uVar7 = FUN_696b0d06();
    return uVar7;
  }
  bRam46b34021 = bRam46b34021 ^ (byte)((ulonglong)uVar7 >> 0x28);
  uRam31c2a739 = *unaff_ESI;
  *(undefined1 *)(0x31c2a73d - *(int *)(unaff_EBX + 0x37c32dde)) = *(undefined1 *)(unaff_ESI + 1);
  uStack00000007 = 0xb3;
  uVar7 = FUN_696b0d1f();
  return uVar7;
}



//── FUN_696b0d58  @0x00000000696b0d58  (10B) ──

/* WARNING: Instruction at (ram,0x696b0c79) overlaps instruction at (ram,0x696b0c78)
    */
/* WARNING: Unable to track spacebase fully for stack */
/* WARNING: Removing unreachable block (ram,0x696b0ca7) */
/* WARNING: Removing unreachable block (ram,0x696b0c81) */
/* WARNING: Removing unreachable block (ram,0x696b0c28) */
/* WARNING: Removing unreachable block (ram,0x696b0c8b) */

undefined8 FUN_696b0d58(void)

{
  int *piVar1;
  char cVar2;
  undefined1 uVar3;
  uint uVar4;
  int extraout_ECX;
  undefined2 uVar5;
  int unaff_EBX;
  undefined4 *puVar6;
  undefined4 *unaff_EBP;
  undefined4 *unaff_ESI;
  undefined2 in_DS;
  int in_GS_OFFSET;
  undefined1 in_CF;
  char in_AF;
  undefined1 in_ZF;
  undefined8 uVar7;
  undefined1 uStack00000009;
  undefined4 auStack_3980 [3671];
  undefined1 *puStack_22;
  undefined4 uStack_6;
  
  uVar7 = FUN_696b0dec();
  uVar3 = in(0x6e);
  if (!(bool)in_CF && !(bool)in_ZF) {
    return CONCAT44((int)*(undefined6 *)(unaff_EBP + 0xf),
                    CONCAT31((int3)((ulonglong)uVar7 >> 8),uVar3));
  }
  piVar1 = (int *)segment(in_DS,(short)unaff_EBX + 0x2444);
  *piVar1 = *piVar1 + -1;
  uVar5 = (undefined2)((ulonglong)uVar7 >> 0x20);
  out(uVar5,0xd4);
  uRam31c2a738 = in(uVar5);
  if (extraout_ECX + unaff_EBP[-0x53f76e7] != 1) {
    uRam054418d4 = 0xa8;
    puStack_22 = &stack0xfffffffe;
    puVar6 = (undefined4 *)&stack0xfffffffe;
    cVar2 = '\a';
    do {
      unaff_EBP = unaff_EBP + -1;
      puVar6 = puVar6 + -1;
      *puVar6 = *unaff_EBP;
      cVar2 = cVar2 + -1;
    } while ('\0' < cVar2);
    uVar4 = CONCAT31(0x54418,in_AF * -6 + -0x2c) & 0xffffff0f;
    uRam31c2a739 = CONCAT22((short)(uVar4 >> 0x10),CONCAT11('\x18' - in_AF,(char)uVar4));
    *(int *)((int)auStack_3980 + in_GS_OFFSET) = (int)((ulonglong)uVar7 >> 0x20);
    uVar7 = FUN_696b0d06();
    return uVar7;
  }
  bRam46b34021 = bRam46b34021 ^ (byte)((ulonglong)uVar7 >> 0x28);
  uRam31c2a739 = *unaff_ESI;
  *(undefined1 *)(0x31c2a73d - *(int *)(unaff_EBX + 0x37c32dde)) = *(undefined1 *)(unaff_ESI + 1);
  uStack00000009 = 0xb3;
  uVar7 = FUN_696b0d1f();
  return uVar7;
}



//── FUN_696b0d63  @0x00000000696b0d63  (12B) ──

void FUN_696b0d63(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_696b0f29();
    return;
  }
  FUN_696b0f03();
  in(0x66);
  FUN_696b0fca();
  return;
}



//── FUN_696b0d85  @0x00000000696b0d85  (78B) ──

void FUN_696b0d85(void)

{
  bool in_SF;
  
  if (in_SF) {
    FUN_696b0c94();
    return;
  }
  FUN_696b0d1f();
  return;
}



//── FUN_696b0dcc  @0x00000000696b0dcc  (11B) ──

void FUN_696b0dcc(void)

{
  FUN_696b0ea3();
  return;
}



//── FUN_696b0dec  @0x00000000696b0dec  (16B) ──

void FUN_696b0dec(void)

{
  FUN_696b0dcc();
  return;
}



//── FUN_696b0e15  @0x00000000696b0e15  (24B) ──

void FUN_696b0e15(void)

{
  FUN_696b0d85();
  return;
}



//── FUN_696b0e41  @0x00000000696b0e41  (10B) ──

void FUN_696b0e41(void)

{
  code *pcVar1;
  byte extraout_CL;
  int unaff_EBP;
  
  FUN_696b0ad5();
  *(char *)(unaff_EBP + -0x162e089a) = *(char *)(unaff_EBP + -0x162e089a) >> (extraout_CL & 0x1f);
  pcVar1 = (code *)swi(1);
  (*pcVar1)();
  return;
}



//── FUN_696b0e4b  @0x00000000696b0e4b  (69B) ──

void FUN_696b0e4b(undefined8 param_1)

{
  undefined2 uStack00000018;
  undefined2 uStack0000001a;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined1 uStack00000020;
  undefined1 uStack00000021;
  
  uStack0000001e = (undefined1)((ulonglong)param_1 >> 0x10);
  uStack0000001f = (undefined1)((ulonglong)param_1 >> 0x18);
  uStack00000020 = (undefined1)((ulonglong)param_1 >> 0x20);
  uStack00000021 = (undefined1)((ulonglong)param_1 >> 0x28);
  uStack00000018 = (undefined2)((ulonglong)param_1 >> 0x20);
  uStack0000001a = uStack00000018;
  FUN_696b0d63();
  return;
}



//── FUN_696b0ea3  @0x00000000696b0ea3  (27B) ──

void FUN_696b0ea3(void)

{
  FUN_696b0e4b();
  return;
}



//── FUN_696b0ec1  @0x00000000696b0ec1  (65B) ──

/* WARNING: Unable to track spacebase fully for stack */

void FUN_696b0ec1(void)

{
  code *pcVar1;
  byte extraout_CL;
  int unaff_EBP;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_696b0e41();
    return;
  }
  FUN_696b0ad5();
  *(char *)(unaff_EBP + -0x162e089a) = *(char *)(unaff_EBP + -0x162e089a) >> (extraout_CL & 0x1f);
  pcVar1 = (code *)swi(1);
  (*pcVar1)();
  return;
}



//── FUN_696b0eef  @0x00000000696b0eef  (10B) ──

void FUN_696b0eef(void)

{
  FUN_696b0f42();
  return;
}



//── FUN_696b0f03  @0x00000000696b0f03  (16B) ──

void __fastcall FUN_696b0f03(undefined4 param_1,undefined4 param_2)

{
  undefined4 in_EAX;
  undefined4 unaff_EBX;
  undefined4 unaff_EBP;
  undefined4 unaff_ESI;
  
  FUN_696b1143(unaff_ESI,unaff_EBP,&stack0x00000000,unaff_EBX,param_2,param_1,in_EAX);
  return;
}



//── FUN_696b0f29  @0x00000000696b0f29  (10B) ──

void FUN_696b0f29(void)

{
  FUN_696b0eef();
  return;
}



//── FUN_696b0f42  @0x00000000696b0f42  (20B) ──

void FUN_696b0f42(void)

{
  FUN_696b0f03();
  in(0x66);
  FUN_696b0fca();
  return;
}



//── FUN_696b0f99  @0x00000000696b0f99  (13B) ──

void FUN_696b0f99(void)

{
  FUN_696b08ff();
  return;
}



//── FUN_696b0fa7  @0x00000000696b0fa7  (11B) ──

void FUN_696b0fa7(void)

{
  FUN_696b101e();
  return;
}



//── FUN_696b0fca  @0x00000000696b0fca  (14B) ──

void FUN_696b0fca(void)

{
  FUN_696b0fa7();
  return;
}



//── FUN_696b0ff6  @0x00000000696b0ff6  (15B) ──

void FUN_696b0ff6(void)

{
  FUN_696b0fa7();
  return;
}



//── FUN_696b101e  @0x00000000696b101e  (106B) ──

void FUN_696b101e(void)

{
  uint *puVar1;
  uint uVar2;
  undefined4 extraout_ECX;
  int in_stack_00000010;
  undefined2 uStack0000001a;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  undefined1 uStack0000001e;
  undefined1 uStack0000001f;
  undefined1 uStack00000021;
  undefined2 uStack00000022;
  undefined1 uStack00000025;
  
  uStack0000001a = (undefined2)in_stack_00000010;
  uStack0000001c = 0x68;
  uStack0000001d = 0x10;
  uStack0000001e = 0x6b;
  uStack0000001f = 0x69;
  uVar2 = func_0x696b0fd8();
  puVar1 = (uint *)(in_stack_00000010 + -100);
  *puVar1 = *puVar1 & uVar2;
  uStack00000021 = (undefined1)in_stack_00000010;
  uStack00000025 = (undefined1)((uint)extraout_ECX >> 0x18);
  uStack00000022 = (undefined2)extraout_ECX;
  if (*puVar1 == 0) {
    uStack0000001e = (undefined1)extraout_ECX;
    uStack0000001f = (undefined1)((uint)extraout_ECX >> 8);
    FUN_696b1276();
    return;
  }
  FUN_696b170f();
  return;
}



//── FUN_696b1095  @0x00000000696b1095  (71B) ──

void FUN_696b1095(undefined4 param_1,undefined4 param_2)

{
  bool in_ZF;
  undefined4 uStack00000011;
  undefined1 in_stack_00000018;
  undefined1 uStack0000001c;
  undefined1 uStack0000001d;
  undefined2 uStack0000001e;
  undefined2 in_stack_00000020;
  undefined4 uStack0000002e;
  
  uStack0000002e = param_2;
  uStack0000001d = in_stack_00000018;
  uStack0000001e = (undefined2)((uint)param_1 >> 0x10);
  uStack0000001c = (undefined1)((uint)param_1 >> 8);
  uStack00000011 = CONCAT22(in_stack_00000020,uStack0000001e);
  if (in_ZF) {
    FUN_696b0ff6();
    return;
  }
  FUN_696b0fca();
  return;
}



//── FUN_696b1143  @0x00000000696b1143  (9B) ──

void FUN_696b1143(void)

{
  FUN_696b1095();
  return;
}



//── FUN_696b1161  @0x00000000696b1161  (15B) ──

void FUN_696b1161(void)

{
  FUN_696b0204(0x12db153c);
  return;
}



//── FUN_696b11c1  @0x00000000696b11c1  (19B) ──

void FUN_696b11c1(void)

{
  FUN_696b129d();
  return;
}



//── FUN_696b11e8  @0x00000000696b11e8  (16B) ──

void FUN_696b11e8(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_696b11c1();
    return;
  }
  FUN_696b1369();
  return;
}



//── FUN_696b1210  @0x00000000696b1210  (108B) ──

void FUN_696b1210(void)

{
  FUN_696b11e8();
  return;
}



//── FUN_696b1276  @0x00000000696b1276  (10B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_696b1276(void)

{
  code *pcVar1;
  undefined1 in_AL;
  int unaff_EBP;
  undefined2 unaff_DI;
  
  FUN_696b1210(CONCAT12(in_AL,unaff_DI));
  pcVar1 = (code *)swi(4);
  if (SCARRY4(unaff_EBP,1)) {
    (*pcVar1)();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



//── FUN_696b129d  @0x00000000696b129d  (11B) ──

void FUN_696b129d(void)

{
  FUN_696b1280();
  return;
}



//── FUN_696b12d1  @0x00000000696b12d1  (15184B) ──

void FUN_696b12d1(void)

{
  bool in_CF;
  
  if (in_CF) {
    FUN_696b1334();
    return;
  }
  FUN_696b15d7();
  return;
}



//── FUN_696b12ee  @0x00000000696b12ee  (10B) ──

void FUN_696b12ee(void)

{
  char in_SF;
  char in_OF;
  
  if (in_OF == in_SF) {
    FUN_696b12c0();
    return;
  }
  thunk_FUN_696b12d1();
  return;
}



//── FUN_696b1334  @0x00000000696b1334  (14B) ──

void FUN_696b1334(void)

{
  FUN_696b15d7();
  return;
}



//── FUN_696b1369  @0x00000000696b1369  (13B) ──

void FUN_696b1369(void)

{
  FUN_696b1280();
  return;
}



//── FUN_696b1402  @0x00000000696b1402  (11B) ──

void FUN_696b1402(void)

{
  FUN_696b15d7();
  return;
}



//── FUN_696b15d7  @0x00000000696b15d7  (27B) ──

/* WARNING: Removing unreachable block (ram,0x696b15e3) */

void FUN_696b15d7(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_696b15d7();
    return;
  }
  FUN_696b1684();
  return;
}



//── FUN_696b1684  @0x00000000696b1684  (20B) ──

/* WARNING: Removing unreachable block (ram,0x696ac051) */
/* WARNING: Removing unreachable block (ram,0x696ac064) */
/* WARNING: Removing unreachable block (ram,0x696ac076) */
/* WARNING: Removing unreachable block (ram,0x696ac862) */
/* WARNING: Removing unreachable block (ram,0x696ac58c) */
/* WARNING: Removing unreachable block (ram,0x696ac0fe) */
/* WARNING: Removing unreachable block (ram,0x696ac69b) */
/* WARNING: Removing unreachable block (ram,0x696ac867) */
/* WARNING: Removing unreachable block (ram,0x696ac6bb) */
/* WARNING: Removing unreachable block (ram,0x696ac31f) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __fastcall FUN_696b1684(undefined4 param_1,undefined4 param_2)

{
  bool bVar1;
  undefined2 uVar2;
  byte bVar3;
  undefined1 uVar4;
  undefined1 uVar5;
  undefined1 uVar6;
  byte bVar7;
  short sVar8;
  int iVar9;
  int in_EAX;
  ushort uVar10;
  uint uVar11;
  uint uVar12;
  int iVar13;
  ushort uVar14;
  ushort uVar15;
  int iVar16;
  ushort uVar17;
  int unaff_EBX;
  short *psVar18;
  uint unaff_EBP;
  ushort uVar19;
  uint unaff_ESI;
  uint unaff_EDI;
  byte in_AF;
  bool bVar20;
  byte in_TF;
  byte in_IF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  int in_stack_0000002c;
  undefined1 uStack_6a;
  undefined1 uStack_69;
  byte bStack_65;
  undefined1 uStack_64;
  undefined1 uStack_63;
  undefined1 uStack_62;
  byte bStack_61;
  byte bStack_60;
  byte bStack_5f;
  undefined1 uStack_5e;
  undefined1 uStack_5d;
  char cStack_5c;
  byte bStack_5b;
  byte bStack_5a;
  undefined1 uStack_59;
  char cStack_58;
  undefined1 uStack_57;
  undefined1 uStack_56;
  byte bStack_55;
  byte bStack_54;
  byte bStack_53;
  byte bStack_52;
  undefined1 uStack_51;
  undefined1 uStack_50;
  undefined1 uStack_4f;
  undefined1 uStack_4e;
  undefined1 uStack_4d;
  undefined1 uStack_4c;
  undefined1 uStack_4b;
  undefined1 uStack_4a;
  undefined1 uStack_49;
  undefined1 uStack_48;
  char cStack_47;
  undefined1 uStack_46;
  undefined1 uStack_45;
  undefined1 uStack_44;
  undefined1 uStack_43;
  undefined1 uStack_42;
  undefined1 uStack_41;
  byte bStack_40;
  byte bStack_3f;
  undefined1 uStack_3e;
  byte bStack_3d;
  char cStack_3c;
  undefined1 uStack_3b;
  undefined1 uStack_3a;
  char cStack_39;
  char cStack_38;
  byte bStack_37;
  byte bStack_36;
  byte bStack_35;
  byte bStack_34;
  byte bStack_33;
  undefined1 uStack_32;
  undefined1 uStack_31;
  char cStack_30;
  undefined1 uStack_2f;
  byte bStack_2e;
  undefined1 uStack_2d;
  byte bStack_2c;
  byte bStack_2b;
  undefined1 uStack_2a;
  byte bStack_29;
  byte bStack_28;
  byte bStack_27;
  undefined1 uStack_26;
  undefined1 uStack_25;
  char cStack_24;
  ushort uStack_23;
  undefined1 uStack_21;
  char cStack_20;
  byte bStack_1f;
  byte bStack_1e;
  byte bStack_1d;
  undefined1 uStack_1c;
  undefined1 uStack_1b;
  undefined1 uStack_1a;
  undefined1 uStack_19;
  byte bStack_18;
  undefined1 uStack_17;
  undefined1 uStack_16;
  undefined1 uStack_15;
  undefined1 uStack_14;
  undefined1 uStack_13;
  undefined1 uStack_12;
  byte bStack_11;
  undefined1 uStack_10;
  undefined1 uStack_f;
  undefined1 uStack_e;
  undefined4 uStack_d;
  undefined1 uStack_9;
  undefined4 uStack_8;
  
  psVar18 = (short *)(unaff_EBX + in_EAX);
  if (SCARRY4(unaff_EBX,in_EAX) != (int)psVar18 < 0) {
    FUN_696b1394();
    return;
  }
  if (*psVar18 != 0x4550) {
    FUN_696b1402();
    return;
  }
  uStack_8 = 0x696ac1b2;
  if (_DAT_6949be5c == 0) {
    _DAT_6949be5c = 1;
    uStack_d._0_1_ = (undefined1)((uint)param_1 >> 0x18);
    uVar6 = (undefined1)uStack_d;
    bStack_11 = (byte)((uint)param_2 >> 0x18);
    bVar3 = bStack_11;
    cStack_20 = (char)unaff_EBP;
    cStack_58 = cStack_20;
    bStack_1f = (byte)(unaff_EBP >> 8);
    bStack_37 = bStack_1f;
    bStack_1e = (byte)(unaff_EBP >> 0x10);
    bStack_36 = bStack_1e;
    bStack_1d = (byte)(unaff_EBP >> 0x18);
    cStack_24 = (char)unaff_ESI;
    uStack_21 = (undefined1)(unaff_ESI >> 0x18);
    bStack_28 = (byte)unaff_EDI;
    bStack_27 = (byte)(unaff_EDI >> 8);
    uStack_26 = (undefined1)(unaff_EDI >> 0x10);
    uStack_3e = uStack_26;
    uStack_25 = (undefined1)(unaff_EDI >> 0x18);
    uVar4 = uStack_25;
    iVar9 = 0x1f;
    if (unaff_EDI != 0) {
      for (; unaff_EDI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    cStack_39 = bStack_28 + 0x7e;
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (&stack0x00000000 != (undefined1 *)0x4d) {
      for (; (uint)&uStack_4d >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    uVar17 = (ushort)unaff_EBP;
    LOCK();
    UNLOCK();
    uVar19 = (ushort)unaff_ESI;
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    uVar14 = (ushort)(unaff_ESI - 0xb98);
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_23 = (ushort)unaff_EDI;
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    uVar14 = (ushort)&uStack_2a;
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    bStack_29 = (byte)((uint)&uStack_2a >> 8);
    uVar11 = ~((uint)CONCAT12(bStack_27,CONCAT11(bStack_28,bStack_29)) << 8);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    bStack_2e = (byte)(uVar11 >> 8);
    UNLOCK();
    uVar12 = CONCAT22((short)(uVar11 >> 0x10),CONCAT11(bStack_2e,0x68));
    iVar9 = 0;
    if (uVar12 != 0) {
      for (; (uVar12 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = ~(CONCAT12(bStack_1d,CONCAT11(cStack_39,(char)(uVar11 >> 0x18))) | 0x97000000) - 1;
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    uVar14 = (ushort)(unaff_EDI >> 8);
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22(uVar14,(short)iVar9);
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    sVar8 = 0xf;
    if (uVar19 != 0) {
      for (; uVar19 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar19 != 0) {
      for (; uVar19 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EDI != 0) {
      for (; (unaff_EDI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    uStack_3b = (undefined1)(unaff_ESI >> 8);
    sVar8 = 0xf;
    if (uVar17 != 0) {
      for (; uVar17 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    uVar10 = CONCAT11(uStack_3b,0xfd) + 1;
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uVar10 = CONCAT11(uStack_21,(int)&uStack_46 < 9);
    uVar11 = ((uint)((ushort)(uStack_23 + 0x63a3) >> 8 & 0x25) << 0x10) >> 8 |
             (uVar10 & 0xff00) << 8 | (uint)uVar10 << 0x18;
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if ((ushort)&bStack_29 != 0) {
      for (; ((ushort)&bStack_29 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (CONCAT11(1,bStack_27) != 0) {
      for (; (ushort)(CONCAT11(1,bStack_27) >> sVar8) == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    bStack_2b = (byte)((uint)(in_ID & 1) * 0x200000 >> 0x10) |
                (byte)((uint)(in_VIP & 1) * 0x100000 >> 0x10) |
                (byte)((uint)(in_VIF & 1) * 0x80000 >> 0x10) |
                (byte)((uint)(in_AC & 1) * 0x40000 >> 0x10);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_EBP != 0) {
      for (; unaff_EBP >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    sVar8 = 0;
    uVar10 = (ushort)CONCAT31((int3)(((uint)CONCAT11(bStack_28,bStack_28) << 1) >> 8),bStack_2b);
    if (uVar10 != 0) {
      for (; (uVar10 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar10 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> uVar10 == 0; uVar10 = uVar10 - 1) {
      }
    }
    sVar8 = 0xf;
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    sVar8 = 0;
    if (CONCAT11(cStack_20,bStack_1e) != 0) {
      for (; (CONCAT11(cStack_20,bStack_1e) >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = ~(1 << (unaff_ESI & 0x1f) ^ 0x4cab2a95U);
    LOCK();
    UNLOCK();
    bVar7 = (byte)uVar11;
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar15 = uVar19 | 1 << ((ushort)&bStack_29 & 0xf);
    uVar10 = -(short)CONCAT21((short)((CONCAT22((short)(uVar11 >> 0x10),
                                                CONCAT11(bStack_1d &
                                                         ~(byte)((ushort)(1 << (uVar19 & 0xf)) >> 8)
                                                         ,bVar7)) >> (bVar7 & 0x1f)) >> 0x10),
                              ~bStack_1f);
    uVar11 = CONCAT22(uVar15 >> 8 | (ushort)(((uint)uVar15 << 0x18) >> 0x10),0x6262);
    sVar8 = 0;
    if (uVar10 != 0) {
      for (; (uVar10 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_EBP != 0) {
      for (; unaff_EBP >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    uVar11 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> uVar11 & 1) == 0; uVar11 = uVar11 + 1) {
      }
    }
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_EDI != 0) {
      for (; unaff_EDI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar10 = CONCAT11(99,cStack_24 + '\n');
    sVar8 = 0;
    if (uVar10 != 0) {
      for (; (uVar10 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    bStack_5b = (byte)(((0x3a84U >> (bStack_28 & 0xf) & 1) != 0) + 0x19f51802 >> 0x18);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (&stack0x00000000 != (undefined1 *)0x40) {
      for (; (uint)&bStack_40 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    iVar9 = 0x1f;
    if (&stack0x00000000 != (undefined1 *)0x36) {
      for (; (uint)&bStack_36 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    sVar8 = 0xf;
    if (uVar19 != 0) {
      for (; uVar19 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uStack_2d = (undefined1)((uint)&bStack_36 >> 8);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar10 = 0xf;
    if ((ushort)((ushort)bStack_28 * -0x100) != 0) {
      for (; (ushort)((ushort)bStack_28 * -0x100) >> uVar10 == 0; uVar10 = uVar10 - 1) {
      }
    }
    sVar8 = 0xf;
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (CONCAT11(~bStack_5b,uStack_2d) != 0) {
      for (; (((uint)CONCAT11(~bStack_5b,uStack_2d) << 0x10) >> iVar9 & 1) == 0; iVar9 = iVar9 + 1)
      {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_EDI != 0) {
      for (; unaff_EDI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    for (sVar8 = 0; (0x4f44U >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
    }
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar17 != 0) {
      for (; uVar17 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_ESI != 0) {
      for (; (unaff_ESI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if ((ushort)&bStack_29 != 0) {
      for (; ((ushort)&bStack_29 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar10 = CONCAT11(0x4e,cStack_20 + -0x25) ^ 1 << (uVar19 & 0xf);
    sVar8 = 0xf;
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    sVar8 = 0;
    if (uStack_23 != 0) {
      for (; (uStack_23 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    sVar8 = 0;
    if ((ushort)&uStack_41 != 0) {
      for (; ((ushort)&uStack_41 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if (uStack_23 != 0) {
      for (; (uStack_23 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    bVar7 = (((byte)(unaff_EDI - 0x58c >> 0x10) ^ bStack_1f) & 0x1f) % 0x11;
    uVar11 = (uint)(&uStack_50 < (undefined1 *)0x18) << 0x10 |
             -(uint)CONCAT11(bStack_1f,0xfc) & 0xffff;
    uVar10 = -((ushort)(uVar11 >> bVar7) | (ushort)(uVar11 << 0x11 - bVar7));
    sVar8 = 0xf;
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uVar10 = (ushort)(unaff_EBP >> 8) >> 8;
    bStack_29 = (byte)((uint)&bStack_28 >> 8);
    LOCK();
    UNLOCK();
    uVar11 = CONCAT31((int3)(CONCAT22(uVar14,CONCAT11((char)(unaff_EDI + 0x9a >> 8),bStack_29)) >> 8
                            ),~bStack_29);
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    sVar8 = 0xf;
    if ((ushort)&cStack_38 != 0) {
      for (; (ushort)((ushort)&cStack_38 >> sVar8) == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = CONCAT13(bStack_27,CONCAT12(bStack_28,CONCAT11(0x12,bStack_27))) +
            CONCAT22((short)(CONCAT13((char)(unaff_EBP + 0x40aa4082 >> 0x18),
                                      CONCAT12(cStack_24,uVar10)) >> 0x10),
                     CONCAT11(bStack_1f,bStack_1e));
    bVar20 = iVar9 < 0;
    sVar8 = CONCAT11(-bVar20,(char)iVar9);
    bVar7 = bStack_1e & 0x1f;
    bVar1 = (uVar10 & 0x1f) != 0;
    bStack_2b = (byte)((uint)(in_NT & 1) * 0x4000 >> 8) |
                (byte)((uint)(bVar7 != 1 && SBORROW1('\0',bVar20) ||
                             bVar7 == 1 &&
                             (!bVar1 && bVar20 || bVar1 && (short)(sVar8 << bVar7 - 1) < 0) !=
                             (short)(sVar8 << bVar7) < 0) * 0x800 >> 8) |
                (byte)((uint)(in_IF & 1) * 0x200 >> 8) | (byte)((uint)(in_TF & 1) * 0x100 >> 8);
    sVar8 = 0;
    if (uVar19 != 0) {
      for (; (uVar19 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar17 != 0) {
      for (; uVar17 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22(CONCAT11(bStack_2b,bStack_1e),CONCAT11(uStack_26,0x59));
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    iVar9 = CONCAT13(bStack_2b,CONCAT12(bStack_27,CONCAT11(bStack_28,0xad)));
    iVar16 = -iVar9;
    uVar11 = CONCAT31((uint3)((ushort)((uint)iVar16 >> 0x10) & 0xff) | (uint3)iVar16 & 0xff00 |
                      (uint3)((uint)(iVar9 * -0x1000000) >> 8),
                      (char)((uint)iVar16 >> 0x18) << (~bStack_1d & 0x1f));
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    sVar8 = 0xf;
    uVar10 = (ushort)CONCAT31((int3)(unaff_EDI + 1 >> 8),200);
    if (uVar10 != 0) {
      for (; uVar10 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    sVar8 = 0;
    if ((ushort)&bStack_28 != 0) {
      for (; ((ushort)&bStack_28 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if ((ushort)&bStack_40 != 0) {
      for (; ((ushort)&bStack_40 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = CONCAT21(uVar19,bStack_28) + 0x4c945f34;
    uVar11 = CONCAT22((short)((uint)iVar9 >> 0x10),CONCAT11(bStack_1f,(char)iVar9));
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    for (iVar9 = 0x1f; 0x29fb34f8U >> iVar9 == 0; iVar9 = iVar9 + -1) {
    }
    LOCK();
    uVar11 = CONCAT13(uStack_3b,CONCAT12(cStack_24,CONCAT11(bStack_1d,bStack_1f)));
    UNLOCK();
    bStack_60 = (byte)&uStack_4c;
    iVar16 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar16 & 1) == 0; iVar16 = iVar16 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    uStack_6a = (undefined1)((uint)(-0x7e6c - iVar9) >> 0x10);
    uStack_69 = (undefined1)((uint)(-0x7e6c - iVar9) >> 0x18);
    uVar11 = CONCAT13(uStack_69,CONCAT12(uStack_6a,0x62b0));
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    for (sVar8 = 0xf; 0x9d4fU >> sVar8 == 0; sVar8 = sVar8 + -1) {
    }
    for (sVar8 = 0xf; 0x25feU >> sVar8 == 0; sVar8 = sVar8 + -1) {
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if ((ushort)~uVar14 != 0) {
      for (; (ushort)~uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_ESI != 0) {
      for (; (unaff_ESI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    bVar7 = (byte)&bStack_65 & 7;
    bVar7 = 0x36U >> bVar7 | '6' << 8 - bVar7;
    bStack_2e = (byte)((uint)(in_NT & 1) * 0x4000 >> 8) |
                (byte)((uint)(((byte)&bStack_65 & 0x1f) == 1 &&
                             (char)bVar7 < '\0' != (char)(bVar7 << 1) < '\0') * 0x800 >> 8) |
                (byte)((uint)(in_IF & 1) * 0x200 >> 8) | (byte)((uint)(in_TF & 1) * 0x100 >> 8);
    LOCK();
    uVar11 = CONCAT22(CONCAT11(bStack_60,0xc),
                      (ushort)(in_ID & 1) * 0x20 | (ushort)(in_VIP & 1) * 0x10 |
                      (ushort)(in_VIF & 1) * 8 | (ushort)(in_AC & 1) * 4);
    UNLOCK();
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22((short)((uint)iVar9 >> 0x10),
                      (short)CONCAT31((int3)((uint)iVar9 >> 8),bStack_2e) + 1);
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    for (iVar9 = 0x1f; 0xe52fb8b8U >> iVar9 == 0; iVar9 = iVar9 + -1) {
    }
    iVar9 = 0x1f;
    if (unaff_EDI != 0) {
      for (; unaff_EDI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22((short)((uint)&bStack_29 >> 0x10),0x6528);
    for (sVar8 = 0xf; 0x6528U >> sVar8 == 0; sVar8 = sVar8 + -1) {
    }
    LOCK();
    UNLOCK();
    cStack_30 = (char)((uint)&bStack_33 >> 8);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    for (iVar9 = 0; (0x3176030aU >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
    }
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    for (uVar14 = 0xf; 0x1f27U >> uVar14 == 0; uVar14 = uVar14 - 1) {
    }
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22(CONCAT11((char)(((uint)CONCAT11(bStack_28,cStack_30) << 0x13) >> 0x18),
                               uStack_21),uVar14);
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (&stack0x00000000 != (undefined1 *)0x48) {
      for (; (uint)&uStack_48 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    uVar11 = CONCAT22((ushort)(unaff_EDI - 0x7583 >> 0x10) & (ushort)(unaff_ESI >> 0x10),
                      CONCAT11(~(~(byte)((uint)iVar9 >> 0x18) + 1),
                               ((int)&uStack_44 < 0) * -0x80 |
                               (&stack0x00000000 == (undefined1 *)0x48) * '@' | (in_AF & 1) * '\x10'
                               | ((POPCOUNT((uint)&uStack_44 & 0xff) & 1U) == 0) * '\x04' |
                               (byte *)0x1a < &bStack_29));
    UNLOCK();
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    uVar11 = (uint)(CONCAT11(~(byte)((uint)(1 << (uVar14 & 0x1f)) >> 8),(char)((uint)iVar9 >> 8)) &
                   0xe1ff) << 0x10;
    UNLOCK();
    uVar11 = uVar11 >> 0x18 | (uVar11 & 0xff0000) >> 8 | 0xc46d0000;
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar2 = (undefined2)(unaff_EDI >> 0x10);
    uVar11 = CONCAT22(uStack_23,uVar2);
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if (uStack_23 != 0) {
      for (; (uStack_23 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    iVar9 = 0x1f;
    if (unaff_ESI != 0) {
      for (; unaff_ESI >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if (uStack_23 != 0) {
      for (; (uStack_23 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    uVar14 = uStack_23 - 1;
    bVar7 = (byte)uVar14 & 0xf;
    uVar14 = uVar14 >> bVar7 | uVar14 << 0x10 - bVar7;
    bVar7 = (char)(uVar14 >> 8) + 1;
    uVar14 = CONCAT11(bVar7,(char)uVar14);
    sVar8 = 0;
    if (uVar14 != 0) {
      for (; (uVar14 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    uVar11 = CONCAT22((ushort)bVar7 | (ushort)(((uint)uVar14 << 0x18) >> 0x10),
                      (CONCAT22(uVar2,CONCAT11((char)sVar8,bStack_28)) != 0) + 0x7f30);
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    sVar8 = 0;
    if (uVar19 != 0) {
      for (; (uVar19 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    iVar9 = 0;
    if (unaff_ESI != 0) {
      for (; (unaff_ESI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    uVar14 = (ushort)((uint)iVar9 >> 0x10);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar14 = uVar14 >> 8 | (ushort)(((uVar14 & 0xff) << 0x10) >> 8);
    sVar8 = 0xf;
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_59 = (undefined1)((ushort)~(uVar17 + 1) >> 8);
    iVar9 = 0;
    if (unaff_ESI != 0) {
      for (; (unaff_ESI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EDI != 0) {
      for (; (unaff_EDI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if ((ushort)&cStack_3c != 0) {
      for (; ((ushort)&cStack_3c >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EDI != 0) {
      for (; (unaff_EDI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_49 = SUB41(&uStack_45,0);
    sVar8 = 0xf;
    if (CONCAT11(uStack_49,cStack_24) != 0) {
      for (; (ushort)(CONCAT11(uStack_49,cStack_24) >> sVar8) == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0;
    if ((ushort)&uStack_48 != 0) {
      for (; ((ushort)&uStack_48 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    uVar12 = CONCAT13(bStack_1e,
                      CONCAT12(uStack_59,
                               CONCAT11((char)~(uVar17 + 1) + -1,
                                        (char)((ushort)-(short)&bStack_28 >> 8))));
    uVar11 = 0;
    if (uVar12 != 0) {
      for (; (uVar12 >> uVar11 & 1) == 0; uVar11 = uVar11 + 1) {
      }
    }
    sVar8 = 0;
    if ((ushort)&bStack_29 != 0) {
      for (; ((ushort)&bStack_29 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    iVar9 = 0;
    if (uVar11 != 0) {
      for (; (uVar11 >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    bStack_2b = (byte)&cStack_30;
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar19 != 0) {
      for (; uVar19 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    uStack_2a = (undefined1)((ushort)(CONCAT11(bStack_1f,(char)&uStack_45) + 0x3d0d) >> 8);
    UNLOCK();
    LOCK();
    UNLOCK();
    bStack_2c = (byte)((uint)(CONCAT31(CONCAT21((short)((uint)(CONCAT22((short)(CONCAT13(0xfc,(uint3
                                                  )bStack_2b << 0x10) >> 0x10),
                                                  CONCAT11((char)iVar9 + -0x2e,
                                                           bStack_27 >> 6 | bStack_27 << 3)) + -1)
                                                  >> 0x10),uStack_2a),bStack_28 + 6) + 1) >> 0x18);
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_8 = 0x694192ed;
    uStack_12 = (undefined1)((uint)param_1 >> 0x10);
    uStack_26 = uStack_12;
    LOCK();
    UNLOCK();
    for (sVar8 = 0xf; 0x62a7U >> sVar8 == 0; sVar8 = sVar8 + -1) {
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = bStack_2c | 0x8e00 | 1 << (CONCAT12(uStack_2a,(ushort)bStack_2c) & 0x1f);
    sVar8 = 0;
    uVar14 = (ushort)CONCAT31((int3)(uVar11 >> 8),-(char)uVar11);
    if (uVar14 != 0) {
      for (; (uVar14 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_2a = (undefined1)(unaff_ESI >> 0x10);
    uStack_3a = uStack_2a;
    uStack_1a = (undefined1)((uint)param_2 >> 0x10);
    uStack_2a = uStack_1a;
    uStack_17 = (undefined1)((uint)param_1 >> 8);
    uVar5 = uStack_17;
    uStack_9 = 0;
    bStack_18 = (byte)param_1;
    bVar7 = bStack_18;
    uStack_1b = (undefined1)((uint)param_2 >> 8);
    bStack_2b = uStack_1b;
    uVar14 = CONCAT11((char)psVar18,0xb5);
    sVar8 = 0xf;
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uStack_49 = (undefined1)((uint)&cStack_38 >> 0x18);
    uStack_10 = 0x22;
    uStack_f = 0xcd;
    uStack_e = 0x49;
    uStack_d = 0x69;
    cStack_30 = cStack_24;
    bStack_33 = bStack_27;
    LOCK();
    UNLOCK();
    uVar14 = (ushort)CONCAT31((uint3)((uint)psVar18 >> 8) |
                              (uint3)((uint)(1 << ((uint)&bStack_34 & 0x1f)) >> 8),cStack_20);
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    iVar9 = 0x1f;
    if (unaff_EBP != 0) {
      for (; unaff_EBP >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    LOCK();
    UNLOCK();
    LOCK();
    UNLOCK();
    uVar11 = CONCAT31(CONCAT21(CONCAT11(bStack_28,bStack_1f),uStack_49),cStack_24);
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    uStack_14 = 0xd7;
    uStack_13 = 0xb7;
    uStack_12 = 0x6a;
    bStack_11 = 0x69;
    uVar14 = (ushort)((uint)(psVar18 + 0x21e2) >> 8) & 0xff00;
    bStack_65 = (byte)((uint)(psVar18 + 0x21e2) >> 0x18);
    uVar17 = bStack_65 | uVar14;
    sVar8 = 0xf;
    if (uVar17 != 0) {
      for (; uVar17 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uStack_62 = (undefined1)(uStack_23 >> 6);
    LOCK();
    UNLOCK();
    uVar11 = CONCAT22(0xe4c,CONCAT11(uStack_62,(char)(-((unaff_EDI & 0xffff) - 1) >> 8)) + 1);
    uStack_63 = (undefined1)((uint)&bStack_52 >> 0x18);
    iVar9 = 0;
    if (unaff_ESI != 0) {
      for (; (unaff_ESI >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    uStack_64 = (undefined1)(uVar14 >> 8);
    LOCK();
    UNLOCK();
    bStack_61 = ((int)&uStack_5d < 0) * -0x80 | (&stack0x00000000 == (undefined1 *)0x5d) * '@' |
                ((in_AF & 1) != 0) * '\x10' |
                ((POPCOUNT((uint)&uStack_5d & 0xff) & 1U) == 0) * '\x04' |
                (undefined1 *)0xfffffff7 < &bStack_65;
    LOCK();
    UNLOCK();
    sVar8 = 0xf;
    if (uStack_23 != 0) {
      for (; uStack_23 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uVar11 = (CONCAT22(0x4c00,sVar8) | 0xe0000) - 5;
    iVar9 = 0x1f;
    if (uVar11 != 0) {
      for (; uVar11 >> iVar9 == 0; iVar9 = iVar9 + -1) {
      }
    }
    bStack_18 = 0x62;
    uStack_17 = 0xe2;
    uStack_16 = 0x49;
    uStack_15 = 0x69;
    bStack_3d = (byte)((uint)&cStack_3c >> 8);
    LOCK();
    UNLOCK();
    uVar14 = CONCAT11(bStack_28,bStack_3d) << 0xb;
    LOCK();
    UNLOCK();
    bStack_40 = ~bStack_3d;
    sVar8 = 0;
    if (uVar19 != 0) {
      for (; (uVar19 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    uStack_59 = uStack_21;
    uStack_5d = uStack_25;
    sVar8 = 0;
    if (uVar14 != 0) {
      for (; (uVar14 >> sVar8 & 1) == 0; sVar8 = sVar8 + 1) {
      }
    }
    LOCK();
    UNLOCK();
    uStack_5e = 0x6b;
    cStack_47 = (char)(uVar14 >> 8);
    LOCK();
    UNLOCK();
    uStack_42 = (undefined1)((uint)&uStack_48 >> 8);
    uStack_41 = (undefined1)((uint)&uStack_48 >> 0x10);
    uStack_1c = 0xa5;
    uStack_1b = 0xb7;
    uStack_1a = 0x6a;
    uStack_19 = 0x69;
    uStack_25 = uVar6;
    bStack_29 = bVar3;
    uStack_32 = (undefined1)((uint)&cStack_20 >> 0x10);
    uStack_31 = (undefined1)((uint)&cStack_20 >> 0x18);
    bStack_35 = bStack_1d;
    cStack_3c = cStack_24;
    cStack_39 = uStack_21;
    bStack_3d = uVar4;
    uStack_4a = 0;
    uVar11 = CONCAT22((short)(CONCAT13(cStack_20,CONCAT12(cStack_47,(ushort)bStack_40)) >> 0x10),
                      -(ushort)bStack_40) & 0xffff00ff;
    LOCK();
    UNLOCK();
    uStack_57 = SUB41(&uStack_45,0);
    iVar9 = CONCAT31((int3)((uint)&uStack_45 >> 8),0x27) + -0x164d;
    iVar16 = (uint)CONCAT21((short)(uVar11 >> 0x10),uStack_42) * 0x100 + 1;
    sVar8 = 0xf;
    uVar14 = (ushort)CONCAT31((int3)((uint)iVar9 >> 8),
                              (POPCOUNT((short)uVar11 - 0x7c4U & 0xff) & 1U) != 0);
    if (uVar14 != 0) {
      for (; uVar14 >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    bStack_60 = bStack_28;
    bStack_5f = bStack_27;
    iVar13 = CONCAT22((short)((uint)&uStack_45 >> 0x10),
                      CONCAT11(&cStack_47 < (undefined1 *)0x17 ||
                               &stack0x00000000 == (undefined1 *)0x5e,0x27)) + 1;
    bStack_5b = bStack_28;
    bStack_5a = bStack_27;
    bStack_53 = (byte)((uint)iVar13 >> 8) | 0xbe;
    bVar3 = bStack_53;
    LOCK();
    UNLOCK();
    uStack_56 = uStack_41;
    bStack_55 = bStack_28;
    bStack_54 = bStack_27;
    uStack_49 = (undefined1)sVar8;
    uStack_48 = (undefined1)((ushort)sVar8 >> 8);
    cStack_47 = (char)((uint)iVar16 >> 0x10);
    uStack_46 = (undefined1)((uint)iVar16 >> 0x18);
    uStack_4f = uStack_41;
    bStack_53 = (byte)iVar13;
    uStack_51 = (undefined1)((uint)iVar13 >> 0x18);
    iVar16 = (uint)CONCAT21((short)((uint)iVar9 >> 0x10),bStack_40) * -0x100;
    iVar9 = 0;
    if (unaff_EBP != 0) {
      for (; (unaff_EBP >> iVar9 & 1) == 0; iVar9 = iVar9 + 1) {
      }
    }
    LOCK();
    uStack_4e = 0;
    uStack_4d = (undefined1)((uint)iVar16 >> 8);
    uStack_4c = (undefined1)((uint)iVar16 >> 0x10);
    uStack_4b = (undefined1)((uint)iVar16 >> 0x18);
    UNLOCK();
    uStack_50 = (undefined1)((uint)iVar13 >> 0x10);
    sVar8 = 0xf;
    if ((ushort)((ushort)bStack_53 * -0x100) != 0) {
      for (; (ushort)((ushort)bStack_53 * -0x100) >> sVar8 == 0; sVar8 = sVar8 + -1) {
      }
    }
    uStack_44 = (undefined1)iVar9;
    uStack_43 = (undefined1)((uint)iVar9 >> 8);
    uStack_42 = (undefined1)((uint)iVar9 >> 0x10);
    uStack_41 = (undefined1)((uint)iVar9 >> 0x18);
    uStack_21 = 0;
    bStack_2c = 0;
    uStack_2d = uStack_44;
    cStack_20 = '\a';
    bStack_1f = 0xcb;
    bStack_1e = 0x6a;
    bStack_1d = 0x69;
    cStack_5c = cStack_30;
    bStack_52 = bStack_53;
    bStack_53 = bVar3;
    uStack_45 = uStack_51;
    bStack_40 = bStack_28;
    bStack_3f = bStack_33;
    cStack_38 = cStack_58;
    bStack_34 = bStack_37;
    bStack_33 = bStack_36;
    cStack_30 = cStack_47;
    uStack_2f = uStack_46;
    bStack_2e = uStack_51;
    bStack_28 = bVar7;
    bStack_27 = uVar5;
    cStack_24 = uVar5;
    FUN_694200b8();
    cStack_20 = '<';
    bStack_1f = 0x15;
    bStack_1e = 0xdb;
    bStack_1d = 0x12;
    cStack_24 = 0xa6;
    uStack_23 = 0xb32e;
    uStack_21 = 0xb;
    bStack_28 = 0xfc;
    bStack_27 = 0x9f;
    uStack_26 = 3;
    uStack_25 = 0;
    bStack_2c = 0;
    bStack_2b = 0x90;
    uStack_2a = 4;
    bStack_29 = 0;
    thunk_FUN_696b0144();
    return;
  }
  if (in_stack_0000002c == 0) {
    FUN_6941cdb0();
    FUN_696ab700();
    return;
  }
  FUN_6901c8e7();
  return;
}



//── FUN_696b170f  @0x00000000696b170f  (25B) ──

/* WARNING: Control flow encountered bad instruction data */

void FUN_696b170f(void)

{
  code *pcVar1;
  undefined1 in_AL;
  int unaff_EBP;
  undefined2 unaff_DI;
  
  FUN_696b1210(CONCAT12(in_AL,unaff_DI));
  pcVar1 = (code *)swi(4);
  if (SCARRY4(unaff_EBP,1)) {
    (*pcVar1)();
  }
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}




// Total: 785 functions, 521 decompiled, 13 failed, 251 skipped (<=8B)
