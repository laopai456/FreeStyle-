# trace_actors.py — Frida hook DDynamicActor/DStaticActor 构造函数，trace 调用栈
#
# 目的: 找到谁通过 operator new + placement new 创建 Dynamic/Static Actor
#
# 用法: py trace_actors.py

import frida
import sys
import os
import subprocess
import time

JS_CODE = r"""
'use strict';

var BASE = Process.getModuleByName('FreeStyle.exe').base;

// DDynamicActor 构造函数 0x0229AE80
// DStaticActor  构造函数 0x024C5520
var DD_CTOR = BASE.add(0x0229AE80);
var DS_CTOR = BASE.add(0x024C5520);

// 也 hook operator new 来看分配大小
var op_new_sizes = {};

// Hook operator new (常见地址模式)
// MSVC operator new 通常在 msvcrt.dll 或内联
var newAddrs = [];
try {
    var msvcrt = Process.getModuleByName('msvcrt.dll');
    var newAddr = msvcrt.getExportByName('??2@YAPAXI@Z'); // operator new(unsigned int)
    if (newAddr) newAddrs.push({addr: newAddr, name: 'msvcrt.??2@YAPAXI@Z'});
} catch(e) {}
try {
    var msvcrt = Process.getModuleByName('msvcrt.dll');
    var newAddr = msvcrt.getExportByName('_malloc');
    if (newAddr) newAddrs.push({addr: newAddr, name: 'msvcrt._malloc'});
} catch(e) {}

// Hook operator new
newAddrs.forEach(function(item) {
    try {
        Interceptor.attach(item.addr, {
            onEnter: function(args) {
                this.size = args[0].toInt32();
            },
            onLeave: function(retval) {
                if (this.size > 0x400 && this.size < 0x2000) {
                    // Actor 大小范围 ~1KB-8KB
                    op_new_sizes[retval.toString()] = this.size;
                }
            }
        });
        send({t: 'INFO', msg: 'Hooked ' + item.name});
    } catch(e) {
        send({t: 'WARN', msg: 'Failed to hook ' + item.name + ': ' + e});
    }
});

// Hook DDynamicActor 构造函数
Interceptor.attach(DD_CTOR, {
    onEnter: function(args) {
        this.thisPtr = this.context.ecx;
        var bt = Thread.backtrace(this.context, Backtracer.ACCURATE)
            .map(function(addr) {
                var mod = Process.findModuleByAddress(addr);
                var offset = mod ? addr.sub(mod.base).toInt32() : 0;
                return {
                    addr: addr.toString(),
                    module: mod ? mod.name : '?',
                    offset: offset
                };
            });

        var allocSize = op_new_sizes[this.thisPtr.toString()];

        send({
            t: 'DDYNAMIC',
            thisPtr: this.thisPtr.toString(),
            allocSize: allocSize || 'unknown',
            backtrace: bt
        });
    }
});

send({t: 'INFO', msg: 'Hooked DDynamicActor ctor @ 0x' + DD_CTOR.toString()});

// Hook DStaticActor 构造函数
Interceptor.attach(DS_CTOR, {
    onEnter: function(args) {
        this.thisPtr = this.context.ecx;
        var bt = Thread.backtrace(this.context, Backtracer.ACCURATE)
            .map(function(addr) {
                var mod = Process.findModuleByAddress(addr);
                var offset = mod ? addr.sub(mod.base).toInt32() : 0;
                return {
                    addr: addr.toString(),
                    module: mod ? mod.name : '?',
                    offset: offset
                };
            });

        var allocSize = op_new_sizes[this.thisPtr.toString()];

        send({
            t: 'DSTATIC',
            thisPtr: this.thisPtr.toString(),
            allocSize: allocSize || 'unknown',
            backtrace: bt
        });
    }
});

send({t: 'INFO', msg: 'Hooked DStaticActor ctor @ 0x' + DS_CTOR.toString()});

send({t: 'READY', msg: 'Both actor ctors hooked. Enter game to trigger actor creation.'});
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
    except Exception as e:
        print(f'[!] tasklist failed: {e}')
    return None


count = {'dd': 0, 'ds': 0}


def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')

        if t == 'INFO' or t == 'READY':
            print(f'[*] {p["msg"]}')
        elif t == 'DDYNAMIC':
            count['dd'] += 1
            print(f'\n[DDynamicActor #{count["dd"]}] this={p["thisPtr"]} size={p["allocSize"]}')
            print(f'  Backtrace:')
            for frame in p['backtrace'][:8]:
                if frame['module'] == 'FreeStyle.exe':
                    print(f'    0x{frame["offset"]:08X} ({frame["module"]})')
                else:
                    print(f'    {frame["addr"]} ({frame["module"]})')
        elif t == 'DSTATIC':
            count['ds'] += 1
            print(f'\n[DStaticActor #{count["ds"]}] this={p["thisPtr"]} size={p["allocSize"]}')
            print(f'  Backtrace:')
            for frame in p['backtrace'][:8]:
                if frame['module'] == 'FreeStyle.exe':
                    print(f'    0x{frame["offset"]:08X} ({frame["module"]})')
                else:
                    print(f'    {frame["addr"]} ({frame["module"]})')
        elif t == 'WARN':
            print(f'[WARN] {p["msg"]}')
    elif msg['type'] == 'error':
        print(f'[JS ERROR] {msg.get("description", msg)}')


def main():
    pid = find_pid()
    if pid is None:
        print('[!] FreeStyle.exe not found.')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    print('[*] Attaching...')
    try:
        session = frida.attach(pid)
    except Exception as e:
        print(f'[!] Attach failed: {e}')
        sys.exit(1)

    script = session.create_script(JS_CODE)
    script.on('message', on_message)
    script.load()

    print('[*] Waiting for actor creation... (enter game / equip items)')
    print('[*] Press Ctrl+C to stop\n')

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f'\n[*] Stopped. DDynamic={count["dd"]} DStatic={count["ds"]}')
    try:
        session.detach()
    except:
        pass


if __name__ == '__main__':
    main()
