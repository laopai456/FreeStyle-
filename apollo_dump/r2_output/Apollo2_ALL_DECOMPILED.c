// Apollo2 - ALL DECOMPILED
// Ghidra 12.0.1 headless
// ====================

//── FUN_1031899b                   @0x000000001031899b (16B) ──

uint FUN_1031899b(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_10620af3();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_10319c37                   @0x0000000010319c37 (29B) ──

void FUN_10319c37(void)

{
  FUN_1066ac5d();
  return;
}



//── FUN_105d4cc5                   @0x00000000105d4cc5 (16B) ──

uint FUN_105d4cc5(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_10665ae7();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_105d5221                   @0x00000000105d5221 (30B) ──

void FUN_105d5221(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    FUN_107b6066();
    return;
  }
  FUN_1074fa70();
  return;
}



//── FUN_105dc826                   @0x00000000105dc826 (38B) ──

void __fastcall FUN_105dc826(undefined4 param_1,int param_2)

{
  int iVar1;
  int unaff_EBP;
  bool in_ZF;
  
  if ((in_ZF) && (iVar1 = *(int *)(param_2 + 0x78), *(int *)(unaff_EBP + -4) = iVar1, iVar1 != 0)) {
    FUN_106ee4ad();
    return;
  }
  FUN_106b017e();
  return;
}



//── FUN_105dd8eb                   @0x00000000105dd8eb (10B) ──

void FUN_105dd8eb(void)

{
  return;
}



//── FUN_105dfc5c                   @0x00000000105dfc5c (16B) ──

void FUN_105dfc5c(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_106afdb5();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_105dff08                   @0x00000000105dff08 (31B) ──

void FUN_105dff08(void)

{
  FUN_1078729e();
  return;
}



//── FUN_105e1e30                   @0x00000000105e1e30 (16B) ──

void FUN_105e1e30(void)

{
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_106c36c1();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_105e739a                   @0x00000000105e739a (15B) ──

void FUN_105e739a(void)

{
  bool in_CF;
  
  if (in_CF) {
    FUN_10687e08();
    return;
  }
  FUN_10687dd7();
  return;
}



//── FUN_105e78a2                   @0x00000000105e78a2 (9B) ──

void FUN_105e78a2(void)

{
  code *in_EAX;
  
  (*in_EAX)();
  return;
}



//── FUN_105e7fdd                   @0x00000000105e7fdd (9B) ──

void FUN_105e7fdd(void)

{
  code *in_EAX;
  
  (*in_EAX)();
  FUN_1070ec48();
  return;
}



//── FUN_105f00f2                   @0x00000000105f00f2 (14B) ──

void __fastcall FUN_105f00f2(undefined1 param_1)

{
  int unaff_EBP;
  
  *(undefined1 *)(unaff_EBP + -1) = param_1;
  FUN_10650f17();
  return;
}



//── FUN_105f047a                   @0x00000000105f047a (49B) ──

void __fastcall FUN_105f047a(int param_1)

{
  int in_EAX;
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if ((in_ZF) && (*(char *)(in_EAX + 4 + param_1) == 'u')) {
    FUN_107ae35a();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_105f83cf                   @0x00000000105f83cf (14B) ──

void FUN_105f83cf(void)

{
  FUN_1031e642();
  return;
}



//── FUN_10600fcc                   @0x0000000010600fcc (20B) ──

void FUN_10600fcc(void)

{
  FUN_105dc826();
  return;
}



//── FUN_1060494d                   @0x000000001060494d (15B) ──

void FUN_1060494d(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_106546fc();
    return;
  }
  FUN_105e739a();
  return;
}



//── FUN_1060558d                   @0x000000001060558d (16B) ──

uint FUN_1060558d(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_10773794();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_1060e63c                   @0x000000001060e63c (45B) ──

void FUN_1060e63c(void)

{
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    FUN_106f30d2();
    return;
  }
  FUN_1060494d();
  return;
}



//── FUN_10612103                   @0x0000000010612103 (28B) ──

void FUN_10612103(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_10687dd7();
    return;
  }
  FUN_1064b318();
  return;
}



//── FUN_1061cf60                   @0x000000001061cf60 (16B) ──

uint FUN_1061cf60(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_105d4cc5();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_10620af3                   @0x0000000010620af3 (16B) ──

uint FUN_10620af3(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_10749a96();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_10622da5                   @0x0000000010622da5 (29B) ──

void FUN_10622da5(void)

{
  bool in_ZF;
  char in_SF;
  char in_OF;
  
  if (!in_ZF && in_OF == in_SF) {
    FUN_105e739a();
    return;
  }
  FUN_1064cf86();
  return;
}



//── FUN_10623aa9                   @0x0000000010623aa9 (25B) ──

void FUN_10623aa9(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_107acf79();
    return;
  }
  FUN_10688a49();
  return;
}



//── FUN_1062c413                   @0x000000001062c413 (18B) ──

void FUN_1062c413(void)

{
  FUN_106a483d();
  return;
}



//── FUN_1062f765                   @0x000000001062f765 (41B) ──

void FUN_1062f765(void)

{
  FUN_10738d47();
  return;
}



//── FUN_1064b2fd                   @0x000000001064b2fd (27B) ──

void __fastcall FUN_1064b2fd(uint param_1)

{
  uint in_EAX;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_10687dd7();
    return;
  }
  if (in_EAX <= param_1) {
    FUN_10687cac();
    return;
  }
  FUN_105f8a1a();
  return;
}



//── FUN_1064b318                   @0x000000001064b318 (14B) ──

void FUN_1064b318(void)

{
  int in_EAX;
  int unaff_EBP;
  int unaff_ESI;
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_106da7b2();
    return;
  }
  if ((uint)(unaff_ESI - in_EAX) < 0x104) {
    *(undefined4 *)(unaff_EBP + 8) = 0;
    FUN_105d5221();
    return;
  }
  FUN_10687dd7();
  return;
}



//── FUN_1064cf86                   @0x000000001064cf86 (22B) ──

void FUN_1064cf86(void)

{
  FUN_1068c3bb();
  return;
}



//── FUN_10650f17                   @0x0000000010650f17 (32B) ──

void FUN_10650f17(void)

{
  char in_AL;
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_1063a636();
    return;
  }
  if (in_AL != '\0') {
    FUN_106947e0();
    return;
  }
  FUN_1071cccf();
  return;
}



//── FUN_106546fc                   @0x00000000106546fc (65B) ──

void __fastcall FUN_106546fc(undefined4 param_1,int param_2)

{
  int unaff_EBX;
  int unaff_EBP;
  int unaff_EDI;
  
  *(undefined4 *)(unaff_EBP + 8) = 0;
  *(int *)(unaff_EBP + -0xc) = param_2 + unaff_EDI;
  if (-1 < unaff_EBX + -1) {
    FUN_1064cf86();
    return;
  }
  FUN_105e739a();
  return;
}



//── FUN_10654fa1                   @0x0000000010654fa1 (34B) ──

void FUN_10654fa1(void)

{
  int in_EAX;
  int unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_105e7fdd();
    return;
  }
  if (in_EAX == unaff_EDI) {
    FUN_10623aa9();
    return;
  }
  FUN_1078da4b();
  return;
}



//── FUN_106569d8                   @0x00000000106569d8 (14B) ──

uint FUN_106569d8(void)

{
  uint uVar1;
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    uVar1 = FUN_105dd8eb();
    return uVar1;
  }
  return (uint)in_CF;
}



//── FUN_10665ae7                   @0x0000000010665ae7 (22B) ──

uint FUN_10665ae7(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_1060558d();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_1066892e                   @0x000000001066892e (16B) ──

uint FUN_1066892e(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_1061cf60();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_1066ac5d                   @0x000000001066ac5d (74B) ──

void __fastcall FUN_1066ac5d(char param_1)

{
  char in_AL;
  int unaff_EBP;
  undefined1 *unaff_EDI;
  bool in_CF;
  bool in_ZF;
  
  if (in_CF || in_ZF) {
    param_1 = param_1 + ' ';
  }
  if ((in_AL != '\0') && (in_AL == param_1)) {
    *(undefined1 *)(unaff_EBP + -1) = *unaff_EDI;
    FUN_10319c37();
    return;
  }
  FUN_106569d8();
  return;
}



//── FUN_106781c0                   @0x00000000106781c0 (26B) ──

void __fastcall FUN_106781c0(int param_1)

{
  if (param_1 != 0) {
    FUN_10715aa9();
    return;
  }
  FUN_106b017e();
  return;
}



//── FUN_10687cac                   @0x0000000010687cac (20B) ──

void FUN_10687cac(void)

{
  bool in_CF;
  
  if (in_CF) {
    FUN_1073a308();
    return;
  }
  FUN_105f8a1a();
  return;
}



//── FUN_10687dd7                   @0x0000000010687dd7 (14B) ──

void FUN_10687dd7(void)

{
  return;
}



//── FUN_10687e08                   @0x0000000010687e08 (59B) ──

void FUN_10687e08(void)

{
  FUN_1064b2fd();
  return;
}



//── FUN_10688a49                   @0x0000000010688a49 (17B) ──

void FUN_10688a49(void)

{
  FUN_105e78a2();
  return;
}



//── FUN_106947e0                   @0x00000000106947e0 (26B) ──

void FUN_106947e0(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_1071cccf();
    return;
  }
  FUN_1074cd2f();
  return;
}



//── FUN_10694e2d                   @0x0000000010694e2d (13B) ──

void FUN_10694e2d(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_10757740();
    return;
  }
  FUN_10622da5();
  return;
}



//── entry                          @0x00000000106a22d5 (12B) ──

void entry(void)

{
  FUN_107bb4ec(0xd4be4b34);
  return;
}



//── FUN_106a38c3                   @0x00000000106a38c3 (9B) ──

void FUN_106a38c3(void)

{
  return;
}



//── FUN_106a483d                   @0x00000000106a483d (14B) ──

void FUN_106a483d(void)

{
  code *in_EAX;
  
  (*in_EAX)();
  FUN_106a38c3();
  return;
}



//── FUN_106a8eb8                   @0x00000000106a8eb8 (14B) ──

uint FUN_106a8eb8(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_CF;
  
  if (in_CF) {
    uVar1 = FUN_1031899b();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_106ae71a                   @0x00000000106ae71a (10B) ──

void FUN_106ae71a(void)

{
  FUN_10731a01();
  return;
}



//── FUN_106afdb5                   @0x00000000106afdb5 (17B) ──

void FUN_106afdb5(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_107a35b7();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_106c36c1                   @0x00000000106c36c1 (16B) ──

void __fastcall FUN_106c36c1(int param_1)

{
  int in_EAX;
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if ((in_ZF) && (*(char *)(in_EAX + 9 + param_1) == 'x')) {
    FUN_106f37a9();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_106cdd22                   @0x00000000106cdd22 (178B) ──

void FUN_106cdd22(undefined4 param_1,undefined4 param_2,uint param_3)

{
  short sVar1;
  short unaff_BP;
  ushort uVar2;
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
  undefined4 uStack_1c;
  uint uStack_18;
  
  uStack_18 = (uint)(in_NT & 1) * 0x4000 | (uint)(in_OF & 1) * 0x800 | (uint)(in_IF & 1) * 0x200 |
              (uint)(in_TF & 1) * 0x100 | (uint)(in_SF & 1) * 0x80 | (uint)(in_ZF & 1) * 0x40 |
              (uint)(in_AF & 1) * 0x10 | (uint)(in_PF & 1) * 4 | (uint)(in_CF & 1) |
              (uint)(in_ID & 1) * 0x200000 | (uint)(in_VIP & 1) * 0x100000 |
              (uint)(in_VIF & 1) * 0x80000 | (uint)(in_AC & 1) * 0x40000;
  uStack_1c = 0;
  sVar1 = 0xf;
  if ((ushort)(unaff_BP - 1U) != 0) {
    for (; (ushort)(unaff_BP - 1U) >> sVar1 == 0; sVar1 = sVar1 + -1) {
    }
  }
  uVar2 = (short)((param_3 ^ 0x472e2093) + 0x456b5d7f >> 2) + 0x38cb;
  sVar1 = 0;
  if (uVar2 != 0) {
    for (; (uVar2 >> sVar1 & 1) == 0; sVar1 = sVar1 + 1) {
    }
  }
  sVar1 = 0xf;
  if ((ushort)&uStack_1c != 0) {
    for (; (ushort)((ushort)&uStack_1c >> sVar1) == 0; sVar1 = sVar1 + -1) {
    }
  }
  FUN_10754535();
  return;
}



//── FUN_106cdfdb                   @0x00000000106cdfdb (21B) ──

void FUN_106cdfdb(void)

{
  undefined1 in_AL;
  undefined1 *unaff_ESI;
  bool in_ZF;
  
  *unaff_ESI = in_AL;
  if (!in_ZF) {
    FUN_1076a633();
    return;
  }
  FUN_1062c413();
  return;
}



//── FUN_106d93c6                   @0x00000000106d93c6 (16B) ──

void FUN_106d93c6(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_10791e76();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_106da7b2                   @0x00000000106da7b2 (11B) ──

void FUN_106da7b2(void)

{
  FUN_10612103();
  return;
}



//── FUN_106dc367                   @0x00000000106dc367 (17B) ──

void FUN_106dc367(void)

{
  FUN_1062f765();
  FUN_10694e2d();
  return;
}



//── FUN_106ee4ad                   @0x00000000106ee4ad (23B) ──

void __fastcall FUN_106ee4ad(undefined4 param_1,undefined4 param_2)

{
  int unaff_EBP;
  
  *(undefined4 *)(unaff_EBP + -0x10) = param_2;
  *(undefined4 *)(unaff_EBP + -8) = 0xffffffff;
  FUN_1060e63c();
  return;
}



//── FUN_106f275b                   @0x00000000106f275b (27B) ──

void __fastcall FUN_106f275b(uint param_1,uint param_2)

{
  int unaff_EBP;
  
  *(uint *)(unaff_EBP + 8) = param_2;
  if (param_1 <= param_2) {
    FUN_1074fa70();
    return;
  }
  FUN_107b6066();
  return;
}



//── FUN_106f30d2                   @0x00000000106f30d2 (16B) ──

void FUN_106f30d2(void)

{
  bool in_CF;
  
  if (in_CF) {
    FUN_1079a65d();
    return;
  }
  FUN_10687dd7();
  return;
}



//── FUN_106f365c                   @0x00000000106f365c (44B) ──

void __fastcall FUN_106f365c(uint param_1)

{
  uint in_EAX;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_1072d884();
    return;
  }
  if (in_EAX <= param_1) {
    FUN_10687cac();
    return;
  }
  FUN_105f8a1a();
  return;
}



//── FUN_106f37a9                   @0x00000000106f37a9 (22B) ──

undefined1 FUN_106f37a9(void)

{
  return 1;
}



//── FUN_106fd1f4                   @0x00000000106fd1f4 (9B) ──

void FUN_106fd1f4(void)

{
  code *in_EAX;
  
  (*in_EAX)();
  FUN_10654fa1();
  return;
}



//── FUN_1070092f                   @0x000000001070092f (13B) ──

void FUN_1070092f(void)

{
  FUN_107b69e8();
  return;
}



//── FUN_1070ec48                   @0x000000001070ec48 (23B) ──

void FUN_1070ec48(void)

{
  int in_EAX;
  int unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_10687dd7();
    return;
  }
  if (in_EAX == unaff_EDI) {
    FUN_10623aa9();
    return;
  }
  FUN_1078da4b();
  return;
}



//── FUN_10715aa9                   @0x0000000010715aa9 (20B) ──

void FUN_10715aa9(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_106b017e();
    return;
  }
  FUN_10600fcc();
  return;
}



//── FUN_1071c7eb                   @0x000000001071c7eb (111B) ──

void FUN_1071c7eb(void)

{
  short sVar1;
  
  for (sVar1 = 0; (0x7ac9U >> sVar1 & 1) == 0; sVar1 = sVar1 + 1) {
  }
  FUN_10319c37();
  return;
}



//── FUN_1071cccf                   @0x000000001071cccf (17B) ──

uint FUN_1071cccf(void)

{
  uint uVar1;
  bool in_CF;
  bool in_ZF;
  
  if (!in_CF && !in_ZF) {
    uVar1 = FUN_1079a3bc();
    return uVar1;
  }
  return (uint)in_CF;
}



//── FUN_10723f41                   @0x0000000010723f41 (16B) ──

void FUN_10723f41(void)

{
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_105e1e30();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_1072d884                   @0x000000001072d884 (13B) ──

void FUN_1072d884(void)

{
  return;
}



//── FUN_10731a01                   @0x0000000010731a01 (44B) ──

void FUN_10731a01(void)

{
  char *unaff_ESI;
  bool in_CF;
  bool in_ZF;
  
  if ((in_CF || in_ZF) && (*unaff_ESI != '\0')) {
    FUN_1076c7ff();
    return;
  }
  FUN_106ce234();
  return;
}



//── FUN_10733057                   @0x0000000010733057 (18B) ──

void __fastcall FUN_10733057(char param_1)

{
  if (param_1 != '\0') {
    FUN_1076c7ff();
    return;
  }
  FUN_106ce234();
  return;
}



//── FUN_10738d47                   @0x0000000010738d47 (12B) ──

void FUN_10738d47(void)

{
  FUN_1074cd2f();
  return;
}



//── FUN_1073a073                   @0x000000001073a073 (14B) ──

void FUN_1073a073(void)

{
  int unaff_EBP;
  uint unaff_ESI;
  bool in_CF;
  
  if (in_CF) {
    FUN_1079a6fd();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_1073a308                   @0x000000001073a308 (25B) ──

void FUN_1073a308(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_1064b318();
    return;
  }
  FUN_10687dd7();
  return;
}



//── FUN_1073e8c1                   @0x000000001073e8c1 (18B) ──

void FUN_1073e8c1(void)

{
  FUN_1078729e();
  FUN_1075a3c6();
  return;
}



//── FUN_10749a96                   @0x0000000010749a96 (17B) ──

uint FUN_10749a96(void)

{
  int in_EAX;
  uint uVar1;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_1066892e();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_1074fa70                   @0x000000001074fa70 (27B) ──

void FUN_1074fa70(void)

{
  int in_EAX;
  int unaff_EBP;
  
  *(undefined1 *)(unaff_EBP + -0x114 + in_EAX) = 0;
  FUN_106fd1f4();
  return;
}



//── FUN_10754535                   @0x0000000010754535 (32B) ──

void FUN_10754535(void)

{
  FUN_107a3c41();
  return;
}



//── FUN_10757740                   @0x0000000010757740 (63B) ──

void FUN_10757740(void)

{
  int in_EAX;
  int unaff_EBX;
  int unaff_EBP;
  int unaff_ESI;
  int unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    *(uint *)(unaff_EBP + -8) =
         (uint)*(ushort *)
                (*(int *)(*(int *)(unaff_EBP + -4) + 0x24 + unaff_EDI) + unaff_ESI * 2 + unaff_EDI);
    *(int *)(unaff_EBP + 8) = unaff_EBX + 1;
    thunk_FUN_1061b9f7();
    return;
  }
  if (in_EAX == 1) {
    *(int *)(unaff_EBP + 8) = unaff_ESI + 1;
    FUN_1061b9f7();
    return;
  }
  FUN_10622da5();
  return;
}



//── FUN_1075a3c6                   @0x000000001075a3c6 (20B) ──

void FUN_1075a3c6(void)

{
  return;
}



//── FUN_1076054e                   @0x000000001076054e (11B) ──

void FUN_1076054e(void)

{
  FUN_105f83cf();
  return;
}



//── FUN_1076a633                   @0x000000001076a633 (17B) ──

void FUN_1076a633(void)

{
  bool in_CF;
  
  if (!in_CF) {
    FUN_1062c413();
    return;
  }
  FUN_106cdfdb();
  return;
}



//── FUN_10773794                   @0x0000000010773794 (40B) ──

uint FUN_10773794(void)

{
  uint uVar1;
  int in_EAX;
  uint unaff_EDI;
  bool in_ZF;
  
  if (in_ZF) {
    uVar1 = FUN_106f37a9();
    return uVar1;
  }
  if (unaff_EDI <= in_EAX + 1U) {
    return in_EAX + 1U & 0xffffff00;
  }
  uVar1 = FUN_105f83cf();
  return uVar1;
}



//── FUN_1078729e                   @0x000000001078729e (41B) ──

void FUN_1078729e(int param_1)

{
  if (param_1 != 0) {
    FUN_106781c0();
    return;
  }
  FUN_106b017e();
  return;
}



//── FUN_1078da4b                   @0x000000001078da4b (13B) ──

void FUN_1078da4b(void)

{
  bool in_ZF;
  
  if (!in_ZF) {
    FUN_106e8756();
    return;
  }
  FUN_10733057();
  return;
}



//── FUN_10791e76                   @0x0000000010791e76 (27B) ──

void __fastcall FUN_10791e76(int param_1)

{
  int in_EAX;
  bool in_ZF;
  
  if ((in_ZF) && (*(char *)(in_EAX + 5 + param_1) == 'e')) {
    FUN_106f37a9();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_1079a65d                   @0x000000001079a65d (13B) ──

void FUN_1079a65d(void)

{
  FUN_106f365c();
  return;
}



//── FUN_1079a6fd                   @0x000000001079a6fd (38B) ──

void __fastcall FUN_1079a6fd(int param_1)

{
  int in_EAX;
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if (((in_ZF) && (*(char *)(in_EAX + 1 + param_1) == 'i')) &&
     (*(char *)(in_EAX + 2 + param_1) == 'r')) {
    FUN_105f047a();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_1079c329                   @0x000000001079c329 (15B) ──

void FUN_1079c329(void)

{
  char in_AL;
  
  if (in_AL != '\0') {
    FUN_106947e0();
    return;
  }
  FUN_1071cccf();
  return;
}



//── FUN_107a35b7                   @0x00000000107a35b7 (16B) ──

void FUN_107a35b7(void)

{
  bool in_ZF;
  
  if (in_ZF) {
    FUN_106d93c6();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_107a3c41                   @0x00000000107a3c41 (9B) ──

void FUN_107a3c41(void)

{
  FUN_106c5dda();
  return;
}



//── FUN_107acf79                   @0x00000000107acf79 (47B) ──

void FUN_107acf79(void)

{
  FUN_106cdfdb();
  return;
}



//── FUN_107ae35a                   @0x00000000107ae35a (16B) ──

void FUN_107ae35a(void)

{
  int unaff_EBP;
  uint unaff_ESI;
  bool in_ZF;
  
  if (in_ZF) {
    FUN_10723f41();
    return;
  }
  if (unaff_ESI < *(uint *)(unaff_EBP + 8)) {
    FUN_105dfc5c();
    return;
  }
  FUN_106a8eb8();
  return;
}



//── FUN_107b6066                   @0x00000000107b6066 (40B) ──

void __fastcall FUN_107b6066(undefined4 param_1,undefined1 param_2)

{
  int in_EAX;
  int unaff_EBX;
  bool in_ZF;
  
  if (!in_ZF) {
    *(undefined1 *)(unaff_EBX + in_EAX) = param_2;
    FUN_1063a3b0();
    return;
  }
  FUN_1074fa70();
  return;
}



//── FUN_107b69e8                   @0x00000000107b69e8 (28B) ──

undefined4 FUN_107b69e8(void)

{
  undefined4 uVar1;
  int unaff_EBP;
  
  if (*(int *)(unaff_EBP + 8) != 0) {
    uVar1 = FUN_1076054e();
    return uVar1;
  }
  return 0;
}




// Apollo2: 112 total, 94 ok, 0 fail, 18 skipped(<=8B)
