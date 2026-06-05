#include <windows.h>
#include <intrin.h>

#pragma warning(disable: 4100 4201)

#define MAX_HIT_RECORDS 200

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
} BP_HIT_INFO, *PBP_HIT_INFO;

typedef struct _SHARED_HIT_DATA {
    volatile LONG HitCount;
    BP_HIT_INFO Records[MAX_HIT_RECORDS];
    volatile LONG Initialized;
} SHARED_HIT_DATA, *PSHARED_HIT_DATA;
#pragma pack(pop)

#define SHARED_MEM_NAME L"HwBpVEHSharedMem"
#define SHARED_DATA_SIZE sizeof(SHARED_HIT_DATA)

PSHARED_HIT_DATA g_SharedData = NULL;
HANDLE g_SharedFile = NULL;
PVOID g_VeHandle = NULL;
CRITICAL_SECTION g_Cs;

LONG WINAPI VexHandler(PEXCEPTION_POINTERS ExceptionInfo) {
    PEXCEPTION_RECORD er = ExceptionInfo->ExceptionRecord;
    PCONTEXT ctx = ExceptionInfo->ContextRecord;

    if (er->ExceptionCode != STATUS_SINGLE_STEP &&
        er->ExceptionCode != STATUS_BREAKPOINT) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (!g_SharedData) return EXCEPTION_CONTINUE_SEARCH;

    EnterCriticalSection(&g_Cs);

    LONG idx = g_SharedData->HitCount;
    if (idx < MAX_HIT_RECORDS) {
        PBP_HIT_INFO info = &g_SharedData->Records[idx];
        info->HitCount = idx + 1;
        info->TriggerAddress = (ULONG64)er->ExceptionAddress;
        info->HitAddress = er->ExceptionInformation[1];
        info->DrIndex = ctx->Dr6 & 0xF;
        info->Timestamp = GetTickCount64();
        info->ThreadId = GetCurrentThreadId();
        info->Rax = ctx->Rax;
        info->Rbx = ctx->Rbx;
        info->Rcx = ctx->Rcx;
        info->Rdx = ctx->Rdx;
        info->Rbp = ctx->Rbp;
        info->Rsp = ctx->Rsp;
        info->Rsi = ctx->Rsi;
        info->Rdi = ctx->Rdi;
        info->R8 = ctx->R8;
        info->R9 = ctx->R9;

        g_SharedData->HitCount = idx + 1;
    }

    LeaveCriticalSection(&g_Cs);

    ctx->Dr6 = 0;

    return EXCEPTION_CONTINUE_EXECUTION;
}

BOOL InitSharedMemory() {
    g_SharedFile = CreateFileMappingW(
        INVALID_HANDLE_VALUE, NULL,
        PAGE_READWRITE, 0, SHARED_DATA_SIZE,
        SHARED_MEM_NAME
    );
    if (!g_SharedFile) return FALSE;

    g_SharedData = (PSHARED_HIT_DATA)MapViewOfFile(
        g_SharedFile, FILE_MAP_ALL_ACCESS, 0, 0, SHARED_DATA_SIZE
    );
    if (!g_SharedData) {
        CloseHandle(g_SharedFile);
        g_SharedFile = NULL;
        return FALSE;
    }

    g_SharedData->HitCount = 0;
    g_SharedData->Initialized = 1;

    return TRUE;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        InitializeCriticalSection(&g_Cs);

        if (!InitSharedMemory()) return TRUE;

        g_VeHandle = AddVectoredExceptionHandler(1, VexHandler);
        if (g_VeHandle) {
            OutputDebugStringW(L"[VEH_Hook] VEH registered OK");
        } else {
            OutputDebugStringW(L"[VEH_Hook] VEH register FAILED");
        }
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_VeHandle) RemoveVectoredExceptionHandler(g_VeHandle);
        if (g_SharedData) UnmapViewOfFile(g_SharedData);
        if (g_SharedFile) CloseHandle(g_SharedFile);
        DeleteCriticalSection(&g_Cs);
    }
    return TRUE;
}