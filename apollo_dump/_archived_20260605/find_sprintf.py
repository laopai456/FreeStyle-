"""
find_sprintf.py — 快速查 sprintf 所在模块
"""
import sys, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752

JS = """
'use strict';

// 列出所有含 msvc/msvcr/msvcp 的模块
var mods = Process.enumerateModules();
var crt = [];
for (var i = 0; i < mods.length; i++) {
    var n = mods[i].name.toLowerCase();
    if (n.indexOf('msvc') !== -1 || n.indexOf('vcrun') !== -1 || n.indexOf('crt') !== -1) {
        crt.push(mods[i].name + ' base=' + mods[i].base);
    }
}
send({crt: crt});

// 直接搜 sprintf
var sp = Module.findExportByName(null, 'sprintf');
send({sprintf_null: sp ? sp.toString() : 'null'});

// 也试试各个 CRT 模块
var names = ['MSVCR100', 'MSVCR100.dll', 'msvcr100', 'msvcr100.dll', 'api-ms-win-crt-stdio-l1-1-0'];
for (var i = 0; i < names.length; i++) {
    var addr = Module.findExportByName(names[i], 'sprintf');
    send({name: names[i], sprintf: addr ? addr.toString() : 'null'});
}
""";

def on_message(msg, data):
    if msg['type'] == 'send':
        print(msg['payload'], flush=True)
    elif msg['type'] == 'error':
        print(f"[ERR] {msg.get('description','')}", flush=True)

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', on_message)
sc.load()

import time; time.sleep(2)
s.detach()
print("done", flush=True)
