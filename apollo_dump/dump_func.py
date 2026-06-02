"""
dump_func.py — Dump ReadFile调用方函数 + 搜索关键常量
RVA 0x1DE2605: 调用fread的子函数
"""
import sys, os, time, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import psutil
pid = None
for p in psutil.process_iter(['pid','name']):
    if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
        pid = p.info['pid']; break
if not pid:
    print('FreeStyle.exe 未运行'); sys.exit(1)

print(f'PID={pid}')

JS_CODE = r"""
'use strict';

var base = Process.getModuleByName('FreeStyle.exe').base;
send({msg: 'base=' + base});

// 目标函数 RVA 0x1DE2605
var funcAddr = base.add(0x1DE2605);
var dumpSize = 4096;

var buf = funcAddr.readByteArray(dumpSize);
if (buf === null) {
    send({msg: 'ERROR: 读取失败'});
} else {
    var bytes = new Uint8Array(buf);
    send({msg: '读取 ' + dumpSize + ' 字节从 ' + funcAddr});

    // hex dump前256字节
    for (var row = 0; row < Math.min(256, bytes.length); row += 16) {
        var hex = [];
        for (var col = 0; col < 16; col++) {
            hex.push(('0' + bytes[row + col].toString(16)).slice(-2));
        }
        var addr = ('00000000' + row.toString(16)).slice(-8);
        send({msg: addr + '  ' + hex.join(' ')});
    }

    // 搜索关键常量
    var patterns = [
        {name: '100864 (0x189A0)', hex: 'a0890100'},
        {name: '512 (0x200)', hex: '00020000'},
        {name: 'ReadFile IAT ff15', hex: 'ff15'},
        {name: 'fread call (e8)', hex: 'e8'},
    ];
    for (var pi = 0; pi < patterns.length; pi++) {
        var pat = patterns[pi];
        var patHex = pat.hex;
        var found = [];
        for (var i = 0; i < bytes.length - patHex.length / 2; i++) {
            var match = true;
            for (var j = 0; j < patHex.length; j += 2) {
                var expected = parseInt(patHex.substring(j, j + 2), 16);
                if (bytes[i + j / 2] !== expected) { match = false; break; }
            }
            if (match) {
                var ctx = [];
                for (var ci = Math.max(0, i - 4); ci < Math.min(bytes.length, i + 12); ci++) {
                    ctx.push(('0' + bytes[ci].toString(16)).slice(-2));
                }
                found.push('off=0x' + i.toString(16) + ': ' + ctx.join(' '));
            }
        }
        send({msg: pat.name + ': ' + found.length + '处' + (found.length > 0 ? ' ' + found.slice(0, 8).join(' | ') : '')});
    }
}

// 也dump AcquireSMD调用点附近 (0x1EECBA7 - 32)
var callSite = base.add(0x1EECBA0);
var csBuf = callSite.readByteArray(64);
if (csBuf) {
    var csBytes = new Uint8Array(csBuf);
    var csHex = [];
    for (var k = 0; k < csBytes.length; k++) {
        csHex.push(('0' + csBytes[k].toString(16)).slice(-2));
    }
    send({msg: 'AcquireSMD调用点(0x1EECBA0): ' + csHex.join(' ')});
}

// 读IAT: fread地址
var msvcr = Process.getModuleByName('MSVCR100.dll');
var freadAddr = msvcr.getExportByName('fread');
send({msg: 'MSVCR100 fread=' + freadAddr});

// 读buffer分配: 0x189A0附近
// 检查调用方传入的buffer地址来源
send({msg: '上次buf地址范围: 0x5b70a008 (heap)'});
"""

session = frida.attach(pid)
script = session.create_script(JS_CODE)

def on_msg(msg, data):
    if msg['type'] == 'send':
        print(f'  {msg["payload"]["msg"]}')
    elif msg['type'] == 'error':
        print(f'  ERROR: {msg.get("description","")} line {msg.get("lineNumber","")}')

script.on('message', on_msg)
script.load()

import time; time.sleep(2)
script.unload()
session.detach()
print('完成。')
