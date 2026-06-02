# trace_actors_veh.py — Frida VEH 异常处理器 + 硬件断点
# 不修改 .text 段，不触发 CRC
#
# 原理:
#   1. Frida Process.setExceptionHandler() 注册 VEH (不写代码段)
#   2. 对目标线程设置 DR0/DR1 硬件断点 (x86 调试寄存器)
#   3. CPU 执行到断点地址时触发 SINGLE_STEP 异常
#   4. VEH 捕获异常，记录 EIP + 调用栈，恢复执行
#
# 用法: py trace_actors_veh.py

import frida
import sys
import os
import subprocess
import time

JS_CODE = r"""
'use strict';

var BASE = Process.getModuleByName('FreeStyle.exe').base;
var DD_CTOR_RVA = 0x0229AE80 - 0x400000;  // DDynamicActor 构造
var DS_CTOR_RVA = 0x024C5520 - 0x400000;  // DStaticActor 构造
var DD_VTABLE = 0x0284A9EC;
var DS_VTABLE = 0x0284E0B4;

var ntdll = Process.getModuleByName('ntdll.dll');

// NtGetContextThread / NtSetContextThread
var NtGetContextThread = new NativeFunction(
    ntdll.getExportByName('NtGetContextThread'),
    'uint32', ['pointer', 'pointer']
);
var NtSetContextThread = new NativeFunction(
    ntdll.getExportByName('NtSetContextThread'),
    'uint32', ['pointer', 'pointer']
);

var NtSuspendThread = new NativeFunction(
    ntdll.getExportByName('NtSuspendThread'),
    'uint32', ['pointer', 'pointer']
);
var NtResumeThread = new NativeFunction(
    ntdll.getExportByName('NtResumeThread'),
    'uint32', ['pointer', 'pointer']
);

var GetCurrentThread = new NativeFunction(
    Module.getExportByName('kernel32.dll', 'GetCurrentThread'),
    'pointer', []
);
var OpenThread = new NativeFunction(
    Module.getExportByName('kernel32.dll', 'OpenThread'),
    'pointer', ['uint32', 'int', 'uint32']
);
var CloseHandle = new NativeFunction(
    Module.getExportByName('kernel32.dll', 'CloseHandle'),
    'int', ['pointer']
);

var THREAD_SUSPEND_RESUME = 0x0002;
var THREAD_GET_CONTEXT = 0x0008;
var THREAD_SET_CONTEXT = 0x0010;
var THREAD_ALL_ACCESS = 0x1F03FF;

// 设置单线程的 DR0/DR1
function setDRForThread(tid) {
    var access = THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT;
    var hThread = OpenThread(access, 0, tid);
    if (hThread.isNull()) return false;

    var prevSuspendCount = new NativePointer(4);
    NtSuspendThread(hThread, prevSuspendCount);

    // CONTEXT structure for x86 - 我们只需要调试寄存器
    var ctx = Memory.alloc(716);  // sizeof(CONTEXT) on x86
    ctx.writeU32(0x00100007);  // CONTEXT_DEBUG_REGISTERS | CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_FULL
    var status = NtGetContextThread(hThread, ctx);
    if (status !== 0) {
        NtResumeThread(hThread, ptr(0));
        CloseHandle(hThread);
        return false;
    }

    // 设置 DR0 = DD_CTOR, DR1 = DS_CTOR, DR7 = enable both
    ctx.add(0x04).writeU32(BASE.add(DD_CTOR_RVA).toInt32());  // Dr0
    ctx.add(0x08).writeU32(BASE.add(DS_CTOR_RVA).toInt32());  // Dr1
    ctx.add(0x14).writeU32(0x00000005);  // Dr7: L0+L1 enable, execute, 1 byte
    ctx.add(0x10).writeU32(0);           // Dr6 = 0

    ctx.writeU32(0x00100007);
    status = NtSetContextThread(hThread, ctx);

    NtResumeThread(hThread, ptr(0));
    CloseHandle(hThread);
    return status === 0;
}

// VEH 异常处理器
var hitCount = {dd: 0, ds: 0};

Process.setExceptionHandler(function(details) {
    if (details.type !== 'single-step' && details.type !== 'breakpoint') {
        return false;  // 不处理其他异常
    }

    var addr = details.address;
    var ddAddr = BASE.add(DD_CTOR_RVA);
    var dsAddr = BASE.add(DS_CTOR_RVA);

    var actorType = null;
    if (addr.equals(ddAddr)) {
        actorType = 'DDynamicActor';
        hitCount.dd++;
    } else if (addr.equals(dsAddr)) {
        actorType = 'DStaticActor';
        hitCount.ds++;
    } else {
        return false;  // 不是我们的断点
    }

    // 读 this 指针 (ecx)
    var thisPtr = details.context.ecx;

    // 读栈回溯 (esp 指向的返回地址)
    var esp = details.context.esp;
    var retAddr = Memory.readU32(ptr(esp));
    var callers = [];
    try {
        for (var i = 0; i < 6; i++) {
            var ra = Memory.readU32(ptr(esp).add(i * 4 + 4));
            var mod = Process.findModuleByAddress(ptr(ra));
            if (mod && mod.name === 'FreeStyle.exe') {
                callers.push('0x' + ra.sub(BASE).add(0x400000).toString(16));
            } else if (mod) {
                callers.push(mod.name + '+0x' + ra.sub(mod.base).toString(16));
            }
        }
    } catch(e) {}

    send({
        t: 'HIT',
        actor: actorType,
        num: actorType === 'DDynamicActor' ? hitCount.dd : hitCount.ds,
        thisPtr: thisPtr.toString(),
        retAddr: '0x' + retAddr.sub(BASE).add(0x400000).toString(16),
        callers: callers
    });

    // 清除 DR6 标志，继续执行
    details.context.dr6 = 0;
    return true;  // 已处理，继续执行
});

// 设置所有线程的 DR
var threads = Process.enumerateThreads();
var okCount = 0;
threads.forEach(function(t) {
    if (setDRForThread(t.id)) okCount++;
});

send({t: 'INFO', msg: 'DR breakpoints set on ' + okCount + '/' + threads.length + ' threads'});
send({t: 'INFO', msg: 'DR0=DDynamicActor(0x' + BASE.add(DD_CTOR_RVA).toString(16) + ') DR1=DStaticActor(0x' + BASE.add(DS_CTOR_RVA).toString(16) + ')'});
send({t: 'READY', msg: 'VEH + DR active. Equip items to trigger.'});
"""


def find_pid():
    try:
        result = subprocess.run(
            ['tasklist.exe', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except:
        pass
    return None


def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t in ('INFO', 'READY'):
            print(f'[*] {p["msg"]}')
        elif t == 'HIT':
            actor = p['actor']
            num = p['num']
            this_ptr = p['thisPtr']
            ret = p['retAddr']
            callers = p.get('callers', [])
            print(f'\n[{actor} #{num}] this={this_ptr} ret={ret}')
            if callers:
                print(f'  Stack:')
                for c in callers:
                    print(f'    {c}')
        elif t == 'WARN':
            print(f'[WARN] {p["msg"]}')
    elif msg['type'] == 'error':
        print(f'[JS ERROR] {msg.get("description", msg)}')


def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    print('[*] Attaching (VEH mode, no .text modification)...')
    try:
        session = frida.attach(pid)
    except Exception as e:
        print(f'[!] Attach failed: {e}')
        sys.exit(1)

    script = session.create_script(JS_CODE)
    script.on('message', on_message)
    script.load()

    print('[*] 装备发型/进入游戏触发 Actor 创建')
    print('[*] Ctrl+C 停止\n')

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\n[exit]')
    try:
        session.detach()
    except:
        pass


if __name__ == '__main__':
    main()
