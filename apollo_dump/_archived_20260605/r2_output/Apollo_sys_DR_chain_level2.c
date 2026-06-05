/* DR_chain_level2 @ 0x1400aa799 */

/* WARNING: Removing unreachable block (ram,0x000140111de0) */
/* WARNING: Removing unreachable block (ram,0x00014020a695) */
/* WARNING: Removing unreachable block (ram,0x0001401b3253) */
/* WARNING: Removing unreachable block (ram,0x000140111e18) */
/* WARNING: Removing unreachable block (ram,0x000140111e31) */
/* WARNING: Removing unreachable block (ram,0x000140221113) */
/* WARNING: Removing unreachable block (ram,0x0001400aa808) */
/* WARNING: Removing unreachable block (ram,0x0001400aa82c) */
/* WARNING: Removing unreachable block (ram,0x0001401908d0) */
/* WARNING: Removing unreachable block (ram,0x0001400a25bf) */
/* WARNING: Removing unreachable block (ram,0x000140151ee8) */
/* WARNING: Removing unreachable block (ram,0x000140151f19) */
/* WARNING: Removing unreachable block (ram,0x000140152045) */
/* WARNING: Removing unreachable block (ram,0x0001400aac3c) */
/* WARNING: Removing unreachable block (ram,0x00014020e7ce) */
/* WARNING: Removing unreachable block (ram,0x0001401f5718) */

void FUN_1400aa799(void)

{
  uint uVar1;
  uint *puVar2;
  int iStackX_10;
  
  uVar1 = iStackX_10 - 1;
  uVar1 = ~(uVar1 >> 0x18 | (uVar1 & 0xff0000) >> 8 | (uVar1 & 0xff00) << 8 | uVar1 * 0x1000000) - 1
  ;
  puVar2 = (uint *)((ulonglong)
                    (uVar1 >> 0x18 | (uVar1 & 0xff0000) >> 8 | (uVar1 & 0xff00) << 8 |
                    uVar1 * 0x1000000) + 0x100000000);
  uVar1 = (*puVar2 ^ (uint)puVar2 ^ 0xc3af7507) - 1;
                    /* WARNING: Could not recover jumptable at 0x00014005ec13. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)(&LAB_140151e7e +
            (int)((0x472c4c9b -
                   ((uVar1 >> 0x18 | (uVar1 & 0xff0000) >> 8 | (uVar1 & 0xff00) << 8 |
                    uVar1 * 0x1000000) << 2 | uVar1 * 0x1000000 >> 0x1e) ^ 0xffffffff) + 0x75579a7a)
            ))(0x9f390124,0xffffe000,0x399e226);
  return;
}


