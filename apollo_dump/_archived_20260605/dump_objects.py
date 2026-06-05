"""
dump_objects.py — dump 两个包含 ItemCode 的对象结构
已知地址 (本 session):
  对象A: 0x19DB25, ItemCode 在 +0x70
  对象B: 0x19B8B0, ItemCode 在 +0x184
"""
import sys, time, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752

JS = r"""
'use strict';

// 两个已知的对象基地址 (本session)
var objA = ptr('0x19DB25');
var objB = ptr('0x19B8B0');

function dumpObject(base, name, range) {
    send({t: 'header', name: name, base: base.toString(), range: '0x' + range.toString(16)});

    for (var off = 0; off < range; off += 4) {
        try {
            var val = base.add(off).readU32();
            var valHex = '0x' + val.toString(16);
            var asInt = val;
            // 尝试读 ASCII
            var asAscii = '';
            try {
                for (var i = 0; i < 4; i++) {
                    var c = base.add(off + i).readU8();
                    if (c >= 0x20 && c < 0x7F) asAscii += String.fromCharCode(c);
                    else asAscii += '.';
                }
            } catch(e) { asAscii = '????'; }

            send({t: 'field', off: '0x' + off.toString(16).padStart(4, '0'),
                  hex: valHex, int: asInt, ascii: asAscii});
        } catch(e) {
            send({t: 'field', off: '0x' + off.toString(16).padStart(4, '0'),
                  hex: '????????', int: '?', ascii: '????'});
        }
    }
}

// Dump 对象A: ItemCode在+0x70, 读 0x00~0x200
dumpObject(objA, 'ObjectA_equip_slot', 0x200);

send({t: 'sep'});

// Dump 对象B: ItemCode在+0x184, 读 0x00~0x300
dumpObject(objB, 'ObjectB_character', 0x300);
"""

session = frida.attach(PID)
script = session.create_script(JS)

current_name = ''

def on_msg(msg, data):
    global current_name
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'header':
            current_name = p['name']
            print(f"\n{'='*60}")
            print(f"  {p['name']} base={p['base']} dump range=0~{p['range']}")
            print(f"{'='*60}")
            print(f"  {'偏移':<10} {'hex':<14} {'int':<14} {'ascii'}")
            print(f"  {'-'*10} {'-'*14} {'-'*14} {'-'*8}")
        elif t == 'field':
            print(f"  {p['off']:<10} {p['hex']:<14} {str(p['int']):<14} {p['ascii']}")
        elif t == 'sep':
            print()
    elif msg['type'] == 'error':
        print(f"JS error: {msg.get('description','')}")

script.on('message', on_msg)
script.load()

import time
time.sleep(2)
script.unload()
session.detach()
