/*
 * apollo_hook.c v8d — 诊断版：测试IAT patch的哪一步被Apollo检测
 * 只做VirtualProtect + 回写原值，不做实际替换
 */

__attribute__((dllimport)) void* __stdcall CreateFileA(const char*, unsigned long, unsigned long, void*, unsigned long, unsigned long, void*);
__attribute__((dllimport)) int __stdcall WriteFile(void*, const void*, unsigned long, unsigned long*, void*);
__attribute__((dllimport)) int __stdcall CloseHandle(void*);
__attribute__((dllimport)) void* __stdcall GetModuleHandleA(const char*);
__attribute__((dllimport)) void* __stdcall GetProcAddress(void*, const char*);
__attribute__((dllimport)) int __stdcall VirtualProtect(void*, unsigned long, unsigned long, unsigned long*);
__attribute__((dllimport)) int __stdcall VirtualQuery(const void*, void*, unsigned long);
__attribute__((dllimport)) void __stdcall Sleep(unsigned long);
__attribute__((dllimport)) void* __stdcall CreateThread(void*, unsigned long, unsigned long __stdcall (*)(void*), void*, unsigned long, unsigned long*);
__attribute__((dllimport)) int __stdcall IsBadReadPtr(const void*, unsigned long);

static void* g_log = 0;

static void raw_write(const char* s) {
    if (!g_log) return;
    unsigned long n = 0;
    while (s[n]) n++;
    unsigned long w;
    WriteFile(g_log, s, n, &w, 0);
}

static void raw_hex(unsigned long val, char* out) {
    const char* hex = "0123456789ABCDEF";
    out[0] = '0'; out[1] = 'x';
    int i;
    for (i = 7; i >= 0; i--) {
        out[2 + (7 - i)] = hex[(val >> (i * 4)) & 0xF];
    }
    out[10] = 0;
}

static void log_addr(const char* prefix, unsigned long addr) {
    char h[12];
    raw_write(prefix);
    raw_hex(addr, h);
    raw_write(h);
    raw_write("\r\n");
}

static unsigned long __stdcall worker_thread(void* param) {
    (void)param;
    unsigned long base = (unsigned long)GetModuleHandleA(0);
    log_addr("[w] base=", base);

    raw_write("[w] sleep 3000ms\r\n");
    Sleep(3000);

    void* hMsvc = GetModuleHandleA("MSVCR100.dll");
    if (!hMsvc) { raw_write("[w] MSVCR100 not loaded\r\n"); return 1; }
    log_addr("[w] MSVCR100=", (unsigned long)hMsvc);

    unsigned long pSprintf = (unsigned long)GetProcAddress(hMsvc, "sprintf");
    if (!pSprintf) { raw_write("[w] sprintf not found\r\n"); return 1; }
    log_addr("[w] sprintf=", pSprintf);

    /* 获取模块大小 */
    unsigned long pe_off = *(unsigned long*)(base + 0x3C);
    unsigned long mod_size = *(unsigned long*)(base + pe_off + 4 + 20 + 56);
    unsigned long mod_end = base + mod_size;

    /* 找sprintf IAT条目 */
    unsigned char mbi[28];
    unsigned long addr = base;
    unsigned long* iat_entry = 0;
    while (addr < mod_end) {
        unsigned long* mp = (unsigned long*)mbi;
        if (!VirtualQuery((const void*)addr, mbi, 28)) break;
        if (mp[0] >= mod_end) break;
        unsigned long rbase = mp[0], rsize = mp[3], prot = mp[5], st = mp[4];
        if (st == 0x1000 && (prot & 0x06 || prot & 0x40 || prot & 0x20 || prot & 0x80) && !(prot & 0x100)) {
            unsigned long* p = (unsigned long*)rbase;
            unsigned long* rend = (unsigned long*)(rbase + rsize - 4);
            if ((unsigned long)rend > mod_end) rend = (unsigned long*)mod_end;
            while (p <= rend) {
                if (!IsBadReadPtr(p, 4) && *p == pSprintf) {
                    iat_entry = p;
                    break;
                }
                p++;
            }
        }
        if (iat_entry) break;
        addr = rbase + rsize;
    }

    if (!iat_entry) { raw_write("[w] sprintf IAT not found\r\n"); return 1; }
    log_addr("[w] IAT entry at ", (unsigned long)iat_entry);
    log_addr("[w] IAT value=", *iat_entry);

    /* 测试1: 只做VirtualProtect改属性再改回来，不改IAT值 */
    raw_write("[w] test1: VirtualProtect RW→RWX→back\r\n");
    {
        unsigned long old_prot;
        int ok = VirtualProtect(iat_entry, 4, 0x04, &old_prot);
        raw_write(ok ? "[w] VP→RW OK\r\n" : "[w] VP→RW FAIL\r\n");
        if (ok) {
            /* 立即恢复原属性 */
            unsigned long tmp;
            VirtualProtect(iat_entry, 4, old_prot, &tmp);
            raw_write("[w] VP restored\r\n");
        }
    }

    raw_write("[w] test1 done, sleeping 10s...\r\n");
    Sleep(10000);
    raw_write("[w] alive after 10s\r\n");

    /* 测试2: 改IAT值为一个合法地址（sprintf自身），模拟写入 */
    raw_write("[w] test2: write original value back (no-op write)\r\n");
    {
        unsigned long old_prot;
        int ok = VirtualProtect(iat_entry, 4, 0x04, &old_prot);
        if (ok) {
            *iat_entry = pSprintf; /* 写回原值 */
            unsigned long tmp;
            VirtualProtect(iat_entry, 4, old_prot, &tmp);
            raw_write("[w] no-op write done\r\n");
        }
    }

    raw_write("[w] test2 done, sleeping 10s...\r\n");
    Sleep(10000);
    raw_write("[w] alive after test2\r\n");

    /* 存活 */
    raw_write("[w] all tests done, keeping alive\r\n");
    while (1) {
        Sleep(60000);
        raw_write("[w] alive tick\r\n");
    }
    return 0;
}

int __stdcall DllMain(void* h, unsigned long r, void* p) {
    if (r != 1) return 1;
    (void)h; (void)p;

    void* f = CreateFileA("C:\\tmp\\hook_alive.txt", 0x40000000, 1, 0, 2, 0x80, 0);
    if (f) { unsigned long w; WriteFile(f, "ALIVE v8d\r\n", 11, &w, 0); CloseHandle(f); }

    g_log = CreateFileA("C:\\tmp\\apollo_hook_v8d.log", 0x40000000, 1, 0, 2, 0x80, 0);

    void* hThread = CreateThread(0, 0, worker_thread, h, 0, 0);
    if (hThread) CloseHandle(hThread);

    return 1;
}
