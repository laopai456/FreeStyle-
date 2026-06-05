/* KdDisableDebugger_loop @ 0x1402399e8 */

void FUN_1402399e8(void)

{
  char cVar1;
  
  while( true ) {
    cVar1 = FUN_140239970();
    if (cVar1 == '\0') break;
    KdDisableDebugger();
  }
  return;
}


