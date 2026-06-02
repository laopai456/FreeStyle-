"""
check_iat.py — 读取IAT条目确认哪个是ReadFile
"""
import sys, time, frida
sys.stdout.reconfigure(encoding='utf-8')

import psutil
pid = None
for p in psutil.process_iter(['pid','name']):
    if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
        pid = p.info['pid']; break

if not pid:
    print('FreeStyle.exe 未运行'); sys.exit(1)

print(f'PID={pid}')

JS = r"""
'use strict';

// 已知的IAT地址
var iat_addrs = [0x0268F1AC, 0x0268F1B0, 0x0268F1A8, 0x0268F1B4, 0x0268F1B8, 0x0268F1BC];
var names = ['0x0268F1AC', '0x0268F1B0', '0x0268F1A8', '0x0268F1B4', '0x0268F1B8', '0x0268F1BC'];

for (var i = 0; i < iat_addrs.length; i++) {
    var addr = ptr(iat_addrs[i]);
    var target = addr.readPointer();
    send({msg: names[i] + ' -> ' + target});
}

// 也检查ReadFile实际地址
var readFileAddr = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');
send({msg: 'ReadFile actual = ' + readFileAddr});

// 搜索更大的IAT范围找ReadFile
var iatBase = ptr(0x0268F100);
var results = [];
for (var j = 0; j < 256; j += 4) {
    try {
        var entry = iatBase.add(j).readPointer();
        if (entry.equals(readFileAddr)) {
            results.push('0x' + iatBase.add(j).toString(16));
        }
    } catch(e) {}
}
send({msg: 'ReadFile IAT entries: ' + JSON.stringify(results)});
"""

session = frida.attach(pid)
script = session.create_script(JS)

def on_msg(msg, data):
    if msg['type'] == 'send':
        print(f'  {msg["payload"]["msg"]}')
    elif msg['type'] == 'error':
        print(f'  ERROR: {msg.get("description","")} at line {msg.get("lineNumber","")}')

script.on('message', on_msg)
script.load()

import time; time.sleep(1)
script.unload()
session.detach()
