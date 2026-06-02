#include <windows.h>
#include <stdio.h>
#include <tlhelp32.h>

DWORD FindProcessId(const wchar_t* name) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W pe = { sizeof(pe) };
    DWORD pid = 0;
    if (Process32FirstW(snap, &pe)) {
        do {
            if (wcsicmp(pe.szExeFile, name) == 0) { pid = pe.th32ProcessID; break; }
        } while (Process32NextW(snap, &pe));
    }
    CloseHandle(snap);
    return pid;
}

int wmain(int argc, wchar_t* argv[]) {
    if (argc < 3) {
        wprintf(L"Usage: inject_dll.exe <pid> <dll_path>\n");
        wprintf(L"   or: inject_dll.exe /name <process_name> <dll_path>\n");
        return 1;
    }

    DWORD pid;
    wchar_t* dllPath;

    if (wcscmp(argv[1], L"/name") == 0) {
        pid = FindProcessId(argv[2]);
        dllPath = argv[3];
        if (!pid) { wprintf(L"Process not found: %s\n", argv[2]); return 1; }
        wprintf(L"Found PID: %d\n", pid);
    } else {
        pid = _wtoi(argv[1]);
        dllPath = argv[2];
    }

    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!hProcess) { wprintf(L"OpenProcess failed: %d\n", GetLastError()); return 1; }

    SIZE_T pathSize = (wcslen(dllPath) + 1) * sizeof(wchar_t);
    PVOID remoteMem = VirtualAllocEx(hProcess, NULL, pathSize, MEM_COMMIT, PAGE_READWRITE);
    if (!remoteMem) { wprintf(L"VirtualAllocEx failed: %d\n", GetLastError()); CloseHandle(hProcess); return 1; }

    WriteProcessMemory(hProcess, remoteMem, dllPath, pathSize, NULL);

    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    LPTHREAD_START_ROUTINE loadLib = (LPTHREAD_START_ROUTINE)GetProcAddress(kernel32, "LoadLibraryW");

    HANDLE hThread = CreateRemoteThread(hProcess, NULL, 0, loadLib, remoteMem, 0, NULL);
    if (!hThread) {
        wprintf(L"CreateRemoteThread failed: %d\n", GetLastError());
        VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return 1;
    }

    wprintf(L"Injecting... ");
    WaitForSingleObject(hThread, INFINITE);

    DWORD exitCode;
    GetExitCodeThread(hThread, &exitCode);
    if (exitCode != 0) {
        wprintf(L"OK (LoadLibrary returned 0x%x)\n", exitCode);
    } else {
        wprintf(L"FAILED (LoadLibrary returned NULL)\n");
    }

    VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
    CloseHandle(hThread);
    CloseHandle(hProcess);
    return 0;
}