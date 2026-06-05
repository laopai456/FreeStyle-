"""
monitor_itemcode.py — 监控 ItemCode 内存变化
每秒读取两个已知地址, 报告变化
"""
import sys, time, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752
SRC_IC = 50125461  # 0x2FCDA95

JS = r"""
'use strict';

var SRC_IC = """ + str(SRC_IC) + """;

// 两个对象 (本session地址)
var objA = ptr('0x19DB25');
var objB = ptr('0x19B8B0');

// 读取 ItemCode 的位置 (从之前扫描结果)
// 对象A +0x70, 对象B +0x184
var addrs = [
    {name: 'ObjA+0x70',  ptr: objA.add(0x70)},
    {name: 'ObjA+0x74',  ptr: objA.add(0x74)},
    {name: 'ObjA+0x78',  ptr: objA.add(0x78)},
    {name: 'ObjA+0x7C',  ptr: objA.add(0x7C)},
    {name: 'ObjB+0x184', ptr: objB.add(0x184)},
    {name: 'ObjB+0x188', ptr: objB.add(0x188)},
    {name: 'ObjB+0x18C', ptr: objB.add(0x18C)},
    {name: 'ObjB+0x190', ptr: objB.add(0x190)},
];

// 也监控 sprintf 调用
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var sprintfN = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = args[1];
            var c0 = fmt.readU8();
            if (c0 !== 0x63) return;
            var fmtStr = '';
            for (var i = 0; i < 50; i++) {
                var c = fmt.add(i).readU8();
                if (c === 0) break;
                fmtStr += String.fromCharCode(c);
            }
            if (fmtStr.indexOf('customize') < 0) return;
            if (fmtStr.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfN++;
            send({t: 'sprintf', n: sprintfN, ic: ic});
        } catch(e) {}
    }
});

// 每秒读取并报告
var prevVals = {};
setInterval(function() {
    for (var i = 0; i < addrs.length; i++) {
        try {
            var val = addrs[i].ptr.readU32();
            var key = addrs[i].name;
            if (prevVals[key] === undefined) {
                prevVals[key] = val;
                send({t: 'init', addr: key, val: val, isIC: val === SRC_IC});
            } else if (prevVals[key] !== val) {
                send({t: 'change', addr: key, old: prevVals[key], new: val,
                      oldDec: prevVals[key], newDec: val,
                      wasIC: prevVals[key] === SRC_IC, isIC: val === SRC_IC});
                prevVals[key] = val;
            }
        } catch(e) {
            var key = addrs[i].name;
            if (prevVals[key] !== 'ERROR') {
                send({t: 'error', addr: key, msg: '' + e});
                prevVals[key] = 'ERROR';
            }
        }
    }
}, 500);

send({t: 'ready', msg: '监控就绪, 每500ms读取。现在去背包操作发型。'});
"""

session = frida.attach(PID)
script = session.create_script(JS)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        ts = time.strftime('%H:%M:%S')
        if t == 'ready':
            print(f'[{ts}] ★ {p["msg"]}')
        elif t == 'init':
            mark = ' ← ItemCode!' if p.get('isIC') else ''
            print(f'[{ts}] 初始 {p["addr"]} = {p["val"]} (0x{p["val"]:X}){mark}')
        elif t == 'change':
            mark = ' ★★★' if p.get('wasIC') or p.get('isIC') else ''
            print(f'[{ts}] 变化 {p["addr"]}: 0x{p["old"]:X} → 0x{p["new"]:X} ({p["oldDec"]}→{p["newDec"]}){mark}')
        elif t == 'sprintf':
            print(f'[{ts}] sprintf #{p["n"]} ItemCode={p["ic"]}')
        elif t == 'error':
            print(f'[{ts}] 错误 {p["addr"]}: {p["msg"]}')
    elif msg['type'] == 'error':
        print(f'JS error: {msg.get("description","")}')

script.on('message', on_msg)
script.load()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

script.unload()
session.detach()
print('已断开。')
