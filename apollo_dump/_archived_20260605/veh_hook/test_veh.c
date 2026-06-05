#include <windows.h>
#include <stdio.h>

#pragma pack(push, 1)
typedef struct _BP_HIT_INFO {
    ULONG HitCount;
    ULONG64 TriggerAddress;
    ULONG64 HitAddress;
    ULONG DrIndex;
    ULONGLONG Timestamp;
    ULONG ThreadId;
    ULONG64 Rax;
    ULONG64 Rbx;
    ULONG64 Rcx;
    ULONG64 Rdx;
    ULONG64 Rbp;
    ULONG64 Rsp;
    ULONG64 Rsi;
    ULONG64 Rdi;
    ULONG64 R8;
    ULONG64 R9;
} BP_HIT_INFO;

typedef struct _SHARED_HIT_DATA {
    volatile LONG HitCount;
    BP_HIT_INFO Records[200];
    volatile LONG Initialized;
} SHARED_HIT_DATA;
#pragma pack(pop)

#define SHARED_MEM_NAME L"HwBpVEHSharedMem"

int main() {
    printf("=== VEH Shared Memory Checker ===\n\n");

    printf("[1] Checking shared memory '%ws'...\n", SHARED_MEM_NAME);
    HANDLE hMap = OpenFileMappingW(FILE_MAP_READ, FALSE, SHARED_MEM_NAME);
    if (!hMap) {
        printf("    NOT FOUND (error %d)\n", GetLastError());
        printf("    => VEH DLL is not injected in any process.\n");
        printf("    => Run: inject_dll.exe <pid> veh_hook.dll\n");
        return 1;
    }

    SHARED_HIT_DATA* data = (SHARED_HIT_DATA*)MapViewOfFile(hMap, FILE_MAP_READ, 0, 0, sizeof(SHARED_HIT_DATA));
    if (!data) {
        printf("    MapViewOfFile failed: %d\n", GetLastError());
        CloseHandle(hMap);
        return 1;
    }

    printf("    Found! Initialized=%d\n\n", data->Initialized);

    printf("[2] Hit records:\n");
    LONG count = data->HitCount;
    printf("    Total hits: %d\n\n", count);

    if (count > 0) {
        printf("=== Recent Hit Records ===\n");
        LONG show = count < 10 ? count : 10;
        for (LONG i = 0; i < show; i++) {
            BP_HIT_INFO* info = &data->Records[i];
            printf("  [%d]\n", i);
            printf("    TriggerAddress: 0x%llX\n", info->TriggerAddress);
            printf("    ThreadId:       %u\n", info->ThreadId);
            printf("    DrIndex:        %u\n", info->DrIndex);
            printf("    Timestamp:      %llu ms\n", info->Timestamp);
            printf("    RAX:            0x%llX\n", info->Rax);
            printf("    RBX:            0x%llX\n", info->Rbx);
            printf("    RCX:            0x%llX\n", info->Rcx);
            printf("    RDX:            0x%llX\n", info->Rdx);
            printf("    RSP:            0x%llX\n", info->Rsp);
            printf("    RBP:            0x%llX\n", info->Rbp);
            printf("\n");
        }
    } else {
        printf("    No hits yet. Set a hardware breakpoint and trigger it.\n");
    }

    printf("=== Done ===\n");

    UnmapViewOfFile(data);
    CloseHandle(hMap);
    return count > 0 ? 0 : 1;
}