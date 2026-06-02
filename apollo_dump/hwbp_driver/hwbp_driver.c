#include <ntifs.h>
#include <intrin.h>

#pragma warning(disable: 4100 4189 4201 4133 4013)

#define POOL_TAG 'PBWH'
#define MAX_HIT_RECORDS 200
#define MAX_TARGET_THREADS 64

#define SystemProcessInformation 5

// IOCTL codes
#define IOCTL_SET_BP    CTL_CODE(FILE_DEVICE_UNKNOWN, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_GET_HIT   CTL_CODE(FILE_DEVICE_UNKNOWN, 0x801, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_CLEAR_BP  CTL_CODE(FILE_DEVICE_UNKNOWN, 0x802, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_GET_STATE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x803, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_LIST_THREADS CTL_CODE(FILE_DEVICE_UNKNOWN, 0x804, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_DETACH    CTL_CODE(FILE_DEVICE_UNKNOWN, 0x805, METHOD_BUFFERED, FILE_ANY_ACCESS)

NTSYSAPI NTSTATUS NTAPI PsGetContextThread(PETHREAD Thread, PCONTEXT Context, KPROCESSOR_MODE Mode);
NTSYSAPI NTSTATUS NTAPI PsSetContextThread(PETHREAD Thread, PCONTEXT Context, KPROCESSOR_MODE Mode);

typedef struct _SYSTEM_THREAD_INFORMATION {
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER CreateTime;
    ULONG WaitTime;
    PVOID StartAddress;
    CLIENT_ID ClientId;
    KPRIORITY Priority;
    LONG BasePriority;
    ULONG ContextSwitches;
    ULONG ThreadState;
    ULONG WaitReason;
} SYSTEM_THREAD_INFORMATION, *PSYSTEM_THREAD_INFORMATION;

typedef struct _SYSTEM_PROCESS_INFORMATION {
    ULONG NextEntryOffset;
    ULONG NumberOfThreads;
    LARGE_INTEGER WorkingSetPrivateSize;
    ULONG HardFaultCount;
    ULONG NumberOfThreadsHighWatermark;
    ULONGLONG CycleTime;
    LARGE_INTEGER CreateTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER KernelTime;
    UNICODE_STRING ImageName;
    KPRIORITY BasePriority;
    HANDLE UniqueProcessId;
    HANDLE InheritedFromUniqueProcessId;
    ULONG HandleCount;
    ULONG SessionId;
    ULONG_PTR UniqueProcessKey;
    SIZE_T PeakVirtualSize;
    SIZE_T VirtualSize;
    ULONG PageFaultCount;
    SIZE_T PeakWorkingSetSize;
    SIZE_T WorkingSetSize;
    SIZE_T QuotaPeakPagedPoolUsage;
    SIZE_T QuotaPagedPoolUsage;
    SIZE_T QuotaPeakNonPagedPoolUsage;
    SIZE_T QuotaNonPagedPoolUsage;
    SIZE_T PagefileUsage;
    SIZE_T PeakPagefileUsage;
    SIZE_T PrivatePageCount;
    LARGE_INTEGER ReadOperationCount;
    LARGE_INTEGER WriteOperationCount;
    LARGE_INTEGER OtherOperationCount;
    LARGE_INTEGER ReadTransferCount;
    LARGE_INTEGER WriteTransferCount;
    LARGE_INTEGER OtherTransferCount;
    SYSTEM_THREAD_INFORMATION Threads[1];
} SYSTEM_PROCESS_INFORMATION, *PSYSTEM_PROCESS_INFORMATION;

typedef struct _SET_BP_REQUEST {
    ULONG ProcessId;
    ULONG ThreadId;
    ULONG64 Address;
    ULONG Type;
    ULONG Length;
    ULONG DrIndex;
} SET_BP_REQUEST, *PSET_BP_REQUEST;

typedef struct _BP_HIT_INFO {
    ULONG HitCount;
    ULONG64 TriggerAddress;
    ULONG64 HitAddress;
    ULONG DrIndex;
    LARGE_INTEGER Timestamp;
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

typedef struct _DRIVER_GLOBAL {
    PDEVICE_OBJECT DeviceObject;
    PEPROCESS TargetProcess;
    KAPC_STATE ApcState;
    BOOLEAN Attached;
    BP_HIT_INFO HitInfo[MAX_HIT_RECORDS];
    volatile LONG HitCount;
    KSPIN_LOCK Lock;

    ULONG64 DrAddrs[4];
    ULONG DrTypes[4];
    ULONG DrLengths[4];
    ULONG ActiveBps;

    ULONG TargetThreads[MAX_TARGET_THREADS];
    ULONG ThreadCount;
} DRIVER_GLOBAL, *PDRIVER_GLOBAL;

DRIVER_GLOBAL g_Global = { 0 };

DRIVER_UNLOAD HwBpUnload;
DRIVER_DISPATCH HwBpCreate, HwBpClose, HwBpDeviceControl;

NTSTATUS SetThreadHardwareBp(PETHREAD Thread, ULONG DrIndex, ULONG64 Address, ULONG Type, ULONG Length);
VOID ClearAllHardwareBp(VOID);
NTSTATUS AttachToProcess(ULONG ProcessId);
VOID DetachFromProcess(VOID);
NTSTATUS EnumerateThreads(ULONG ProcessId, PULONG ThreadIds, ULONG MaxCount, PULONG OutCount);

VOID HwBpUnload(PDRIVER_OBJECT DriverObject) {
    UNREFERENCED_PARAMETER(DriverObject);
    DetachFromProcess();

    KIRQL oldIrql;
    KeAcquireSpinLock(&g_Global.Lock, &oldIrql);
    g_Global.HitCount = 0;
    RtlZeroMemory(g_Global.HitInfo, sizeof(g_Global.HitInfo));
    KeReleaseSpinLock(&g_Global.Lock, oldIrql);

    UNICODE_STRING symLink = RTL_CONSTANT_STRING(L"\\??\\HwBpDriver");
    IoDeleteSymbolicLink(&symLink);

    if (DriverObject->DeviceObject) {
        IoDeleteDevice(DriverObject->DeviceObject);
    }

    DbgPrint("[HwBp] Driver unloaded\n");
}

NTSTATUS HwBpCreate(PDEVICE_OBJECT DeviceObject, PIRP Irp) {
    UNREFERENCED_PARAMETER(DeviceObject);
    Irp->IoStatus.Status = STATUS_SUCCESS;
    Irp->IoStatus.Information = 0;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return STATUS_SUCCESS;
}

NTSTATUS HwBpClose(PDEVICE_OBJECT DeviceObject, PIRP Irp) {
    UNREFERENCED_PARAMETER(DeviceObject);
    Irp->IoStatus.Status = STATUS_SUCCESS;
    Irp->IoStatus.Information = 0;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return STATUS_SUCCESS;
}

NTSTATUS EnumerateThreads(ULONG ProcessId, PULONG ThreadIds, ULONG MaxCount, PULONG OutCount) {
    NTSTATUS status;
    ULONG bufferSize = 0x400000;
    PVOID buffer = NULL;
    PSYSTEM_PROCESS_INFORMATION current;
    ULONG count = 0;

    *OutCount = 0;
    if (MaxCount == 0) return STATUS_INVALID_PARAMETER;

    buffer = ExAllocatePool2(POOL_FLAG_NON_PAGED, bufferSize, POOL_TAG);
    if (!buffer) return STATUS_INSUFFICIENT_RESOURCES;

    status = ZwQuerySystemInformation(SystemProcessInformation, buffer, bufferSize, &bufferSize);
    if (status == STATUS_INFO_LENGTH_MISMATCH) {
        ExFreePool(buffer);
        buffer = ExAllocatePool2(POOL_FLAG_NON_PAGED, bufferSize * 2, POOL_TAG);
        if (!buffer) return STATUS_INSUFFICIENT_RESOURCES;
        status = ZwQuerySystemInformation(SystemProcessInformation, buffer, bufferSize * 2, &bufferSize);
    }

    if (!NT_SUCCESS(status)) {
        ExFreePool(buffer);
        return status;
    }

    current = (PSYSTEM_PROCESS_INFORMATION)buffer;

    while (TRUE) {
        if ((ULONG)(ULONG_PTR)current->UniqueProcessId == ProcessId) {
            for (ULONG i = 0; i < current->NumberOfThreads && count < MaxCount; i++) {
                ULONG tid = (ULONG)(ULONG_PTR)current->Threads[i].ClientId.UniqueThread;
                if (tid != 0) {
                    ThreadIds[count++] = tid;
                }
            }
            break;
        }
        if (current->NextEntryOffset == 0) break;
        current = (PSYSTEM_PROCESS_INFORMATION)((PUCHAR)current + current->NextEntryOffset);
    }

    ExFreePool(buffer);
    *OutCount = count;
    return count > 0 ? STATUS_SUCCESS : STATUS_NOT_FOUND;
}

NTSTATUS AttachToProcess(ULONG ProcessId) {
    NTSTATUS status;
    PEPROCESS process = NULL;

    DetachFromProcess();

    status = PsLookupProcessByProcessId((HANDLE)(ULONG_PTR)ProcessId, &process);
    if (!NT_SUCCESS(status)) return status;

    KeStackAttachProcess((PRKPROCESS)process, &g_Global.ApcState);
    g_Global.TargetProcess = process;
    g_Global.Attached = TRUE;

    return STATUS_SUCCESS;
}

VOID DetachFromProcess(VOID) {
    if (g_Global.Attached && g_Global.TargetProcess) {
        ClearAllHardwareBp();
        KeUnstackDetachProcess(&g_Global.ApcState);
        ObDereferenceObject(g_Global.TargetProcess);
        g_Global.TargetProcess = NULL;
        g_Global.Attached = FALSE;
    }
}

NTSTATUS SetThreadHardwareBp(PETHREAD Thread, ULONG DrIndex, ULONG64 Address, ULONG Type, ULONG Length) {
    CONTEXT ctx = { 0 };
    CONTEXT verifyCtx = { 0 };
    NTSTATUS status;

    if (DrIndex >= 4) return STATUS_INVALID_PARAMETER;

    KeSetSystemAffinityThread(1);

    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS | CONTEXT_INTEGER;
    status = PsGetContextThread(Thread, &ctx, KernelMode);
    if (!NT_SUCCESS(status)) {
        KeRevertToUserAffinityThread();
        return status;
    }

    (&ctx.Dr0)[DrIndex] = Address;

    ULONG64 dr7 = ctx.Dr7;

    dr7 |= (1ULL << (DrIndex * 2));

    ULONG rw = (Type == 0) ? 0 : (Type == 1) ? 1 : 3;
    dr7 &= ~(3ULL << (16 + DrIndex * 4));
    dr7 |= ((ULONG64)rw << (16 + DrIndex * 4));

    ULONG lenBits = 0;
    switch (Length) {
        case 1: lenBits = 0; break;
        case 2: lenBits = 1; break;
        case 4: lenBits = 3; break;
        case 8: lenBits = 2; break;
        default: lenBits = 3; break;
    }
    dr7 &= ~(3ULL << (18 + DrIndex * 4));
    dr7 |= ((ULONG64)lenBits << (18 + DrIndex * 4));

    dr7 |= (1ULL << 13);

    ctx.Dr7 = dr7;
    ctx.Dr6 = 0;

    status = PsSetContextThread(Thread, &ctx, KernelMode);

    if (NT_SUCCESS(status)) {
        verifyCtx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
        NTSTATUS vStatus = PsGetContextThread(Thread, &verifyCtx, KernelMode);
        if (NT_SUCCESS(vStatus)) {
            if (verifyCtx.Dr7 != dr7 || (&verifyCtx.Dr0)[DrIndex] != Address) {
                DbgPrint("[HwBp] WARNING: DR write verification failed! Written DR%d=0x%llx, Read DR%d=0x%llx\n",
                    DrIndex, Address, DrIndex, (&verifyCtx.Dr0)[DrIndex]);
                status = STATUS_UNSUCCESSFUL;
            }
        }
    }

    KeRevertToUserAffinityThread();
    return status;
}

VOID ClearAllHardwareBp(VOID) {
    if (!g_Global.Attached || !g_Global.TargetProcess) return;

    KAPC_STATE apcState;
    KeStackAttachProcess((PRKPROCESS)g_Global.TargetProcess, &apcState);

    for (ULONG i = 0; i < g_Global.ThreadCount && i < MAX_TARGET_THREADS; i++) {
        PETHREAD thread = NULL;
        NTSTATUS s = PsLookupThreadByThreadId((HANDLE)(ULONG_PTR)g_Global.TargetThreads[i], &thread);
        if (NT_SUCCESS(s)) {
            CONTEXT ctx = { 0 };
            ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
            PsGetContextThread(thread, &ctx, KernelMode);
            ctx.Dr0 = 0; ctx.Dr1 = 0; ctx.Dr2 = 0; ctx.Dr3 = 0;
            ctx.Dr6 = 0; ctx.Dr7 = 0;
            PsSetContextThread(thread, &ctx, KernelMode);
            ObDereferenceObject(thread);
        }
    }

    KeUnstackDetachProcess(&apcState);

    g_Global.ThreadCount = 0;
    g_Global.ActiveBps = 0;
    RtlZeroMemory(g_Global.DrAddrs, sizeof(g_Global.DrAddrs));
    RtlZeroMemory(g_Global.DrTypes, sizeof(g_Global.DrTypes));
    RtlZeroMemory(g_Global.DrLengths, sizeof(g_Global.DrLengths));
}

NTSTATUS HandleSetBp(SET_BP_REQUEST* Request) {
    NTSTATUS status;

    if (Request->DrIndex >= 4) return STATUS_INVALID_PARAMETER;

    if (!g_Global.Attached || !g_Global.TargetProcess ||
        PsGetProcessId(g_Global.TargetProcess) != (HANDLE)(ULONG_PTR)Request->ProcessId) {
        status = AttachToProcess(Request->ProcessId);
        if (!NT_SUCCESS(status)) return status;
    }

    if (Request->ThreadId != 0) {
        PETHREAD thread = NULL;
        status = PsLookupThreadByThreadId((HANDLE)(ULONG_PTR)Request->ThreadId, &thread);
        if (!NT_SUCCESS(status)) return status;

        status = SetThreadHardwareBp(thread, Request->DrIndex, Request->Address, Request->Type, Request->Length);
        ObDereferenceObject(thread);

        if (NT_SUCCESS(status)) {
            if (g_Global.ThreadCount < MAX_TARGET_THREADS) {
                BOOLEAN found = FALSE;
                for (ULONG i = 0; i < g_Global.ThreadCount; i++) {
                    if (g_Global.TargetThreads[i] == Request->ThreadId) { found = TRUE; break; }
                }
                if (!found) g_Global.TargetThreads[g_Global.ThreadCount++] = Request->ThreadId;
            }
        }
    } else {
        ULONG threadIds[MAX_TARGET_THREADS];
        ULONG count = 0;

        status = EnumerateThreads(Request->ProcessId, threadIds, MAX_TARGET_THREADS, &count);
        if (!NT_SUCCESS(status)) return status;

        ULONG successCount = 0;
        for (ULONG i = 0; i < count; i++) {
            PETHREAD thread = NULL;
            NTSTATUS ts = PsLookupThreadByThreadId((HANDLE)(ULONG_PTR)threadIds[i], &thread);
            if (NT_SUCCESS(ts)) {
                ts = SetThreadHardwareBp(thread, Request->DrIndex, Request->Address, Request->Type, Request->Length);
                ObDereferenceObject(thread);
                if (NT_SUCCESS(ts)) {
                    successCount++;
                    if (g_Global.ThreadCount < MAX_TARGET_THREADS) {
                        g_Global.TargetThreads[g_Global.ThreadCount++] = threadIds[i];
                    }
                }
            }
        }
        if (successCount == 0) return STATUS_UNSUCCESSFUL;
    }

    g_Global.DrAddrs[Request->DrIndex] = Request->Address;
    g_Global.DrTypes[Request->DrIndex] = Request->Type;
    g_Global.DrLengths[Request->DrIndex] = Request->Length;
    g_Global.ActiveBps |= (1 << Request->DrIndex);

    return STATUS_SUCCESS;
}

NTSTATUS HandleGetHit(PBP_HIT_INFO OutInfo, ULONG Index) {
    KIRQL oldIrql;
    KeAcquireSpinLock(&g_Global.Lock, &oldIrql);

    if (Index >= (ULONG)g_Global.HitCount) {
        KeReleaseSpinLock(&g_Global.Lock, oldIrql);
        return STATUS_NO_MORE_ENTRIES;
    }

    RtlCopyMemory(OutInfo, &g_Global.HitInfo[Index], sizeof(BP_HIT_INFO));
    KeReleaseSpinLock(&g_Global.Lock, oldIrql);
    return STATUS_SUCCESS;
}

NTSTATUS HandleClearBp(VOID) {
    ClearAllHardwareBp();
    DetachFromProcess();
    return STATUS_SUCCESS;
}

NTSTATUS HwBpDeviceControl(PDEVICE_OBJECT DeviceObject, PIRP Irp) {
    UNREFERENCED_PARAMETER(DeviceObject);
    NTSTATUS status = STATUS_INVALID_DEVICE_REQUEST;
    PIO_STACK_LOCATION stack = IoGetCurrentIrpStackLocation(Irp);
    ULONG inLen = stack->Parameters.DeviceIoControl.InputBufferLength;
    ULONG outLen = stack->Parameters.DeviceIoControl.OutputBufferLength;

    switch (stack->Parameters.DeviceIoControl.IoControlCode) {
        case IOCTL_SET_BP:
            if (inLen >= sizeof(SET_BP_REQUEST)) {
                PSET_BP_REQUEST req = (PSET_BP_REQUEST)Irp->AssociatedIrp.SystemBuffer;
                status = HandleSetBp(req);
                Irp->IoStatus.Information = 0;
            }
            break;

        case IOCTL_GET_HIT:
            if (outLen >= sizeof(BP_HIT_INFO)) {
                ULONG index = 0;
                if (inLen >= sizeof(ULONG)) {
                    index = *(PULONG)Irp->AssociatedIrp.SystemBuffer;
                }
                PBP_HIT_INFO outInfo = (PBP_HIT_INFO)Irp->AssociatedIrp.SystemBuffer;
                status = HandleGetHit(outInfo, index);
                if (NT_SUCCESS(status)) Irp->IoStatus.Information = sizeof(BP_HIT_INFO);
            }
            break;

        case IOCTL_CLEAR_BP:
            status = HandleClearBp();
            Irp->IoStatus.Information = 0;
            break;

        case IOCTL_GET_STATE:
            if (outLen >= 3 * sizeof(ULONG)) {
                PULONG out = (PULONG)Irp->AssociatedIrp.SystemBuffer;
                out[0] = g_Global.ActiveBps;
                out[1] = (ULONG)g_Global.HitCount;
                out[2] = g_Global.ThreadCount;
                status = STATUS_SUCCESS;
                Irp->IoStatus.Information = 3 * sizeof(ULONG);
            }
            break;

        case IOCTL_LIST_THREADS:
            if (outLen >= sizeof(ULONG) * MAX_TARGET_THREADS) {
                PULONG pid = (PULONG)Irp->AssociatedIrp.SystemBuffer;
                PULONG threadIds = (PULONG)Irp->AssociatedIrp.SystemBuffer;
                ULONG count = 0;
                status = EnumerateThreads(*pid, threadIds, MAX_TARGET_THREADS, &count);
                Irp->IoStatus.Information = count * sizeof(ULONG);
            }
            break;

        case IOCTL_DETACH:
            DetachFromProcess();
            status = STATUS_SUCCESS;
            Irp->IoStatus.Information = 0;
            break;
    }

    Irp->IoStatus.Status = status;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return status;
}

NTSTATUS DriverEntry(PDRIVER_OBJECT DriverObject, PUNICODE_STRING RegistryPath) {
    UNREFERENCED_PARAMETER(RegistryPath);
    NTSTATUS status;
    PDEVICE_OBJECT deviceObject = NULL;

    DbgPrint("[HwBp] DriverEntry starting...\n");

    UNICODE_STRING deviceName = RTL_CONSTANT_STRING(L"\\Device\\HwBpDriver");
    UNICODE_STRING symLink = RTL_CONSTANT_STRING(L"\\??\\HwBpDriver");

    status = IoCreateDevice(DriverObject, 0, &deviceName, FILE_DEVICE_UNKNOWN, 0, FALSE, &deviceObject);
    if (!NT_SUCCESS(status)) {
        DbgPrint("[HwBp] IoCreateDevice failed: 0x%x\n", status);
        return status;
    }

    status = IoCreateSymbolicLink(&symLink, &deviceName);
    if (!NT_SUCCESS(status)) {
        DbgPrint("[HwBp] IoCreateSymbolicLink failed: 0x%x\n", status);
        IoDeleteDevice(deviceObject);
        return status;
    }

    deviceObject->Flags |= DO_BUFFERED_IO;
    deviceObject->Flags &= ~DO_DEVICE_INITIALIZING;

    DriverObject->MajorFunction[IRP_MJ_CREATE] = HwBpCreate;
    DriverObject->MajorFunction[IRP_MJ_CLOSE] = HwBpClose;
    DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = HwBpDeviceControl;
    DriverObject->DriverUnload = HwBpUnload;

    KeInitializeSpinLock(&g_Global.Lock);
    g_Global.DeviceObject = deviceObject;
    g_Global.HitCount = 0;
    g_Global.ActiveBps = 0;
    g_Global.ThreadCount = 0;

    DbgPrint("[HwBp] DriverEntry complete\n");
    return STATUS_SUCCESS;
}