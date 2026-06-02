"""
inline_patch_equip.py — Inline patch 装备发包调用点 (v2: call后恢复)

原理:
  0x1b90ec5: mov ecx, [ebp-0x45d8]   ; ecx = this
  0x1b90ecb: call 0x1922720          ; <- patch 为 jmp cave
  0x1b90ed0: ...                      ; 原流程继续

  cave:
    push ebx
    mov ebx, ecx              ; ebx = this (callee-saved, survives call)
    cmp [ecx+0xE34], srcIC
    jne skip
    mov [ecx+0xE34], dstIC    ; 改
  skip:
    call 0x1922720             ; 发包 (用改过的值)
    cmp [ebx+0xE34], dstIC    ; 检查是否被我们改过
    jne done
    mov [ebx+0xE34], srcIC    ; 恢复原值
  done:
    pop ebx
    jmp 0x1b90ed0

用法: py inline_patch_equip.py <src_itemcode> <dst_itemcode>
"""
import frida, json, sys, time

JS_TEMPLATE = r"""
'use strict';

var g_srcIC = {src_ic};
var g_dstIC = {dst_ic};

var callSite = ptr(0x1b90ecb);
var continueAddr = ptr(0x1b90ed0);
var origFn = ptr(0x1922720);
var g_origBytes = callSite.readByteArray(5);

var cave = Memory.alloc(Process.pageSize);
Memory.protect(cave, Process.pageSize, 'rwx');

function buildShellcode() {{
    var s = g_srcIC;
    var d = g_dstIC;
    var b = [];

    // push ebx
    b.push(0x53);
    // mov ebx, ecx
    b.push(0x8B, 0xD9);

    // cmp dword [ecx+0xE34], srcIC
    b.push(0x81, 0xB9, 0x34, 0x0E, 0x00, 0x00);
    b.push(s & 0xFF, (s >>> 8) & 0xFF, (s >>> 16) & 0xFF, (s >>> 24) & 0xFF);
    // jne skip (+10 = size of mov dword)
    b.push(0x75, 0x0A);
    // mov dword [ecx+0xE34], dstIC
    b.push(0xC7, 0x81, 0x34, 0x0E, 0x00, 0x00);
    b.push(d & 0xFF, (d >>> 8) & 0xFF, (d >>> 16) & 0xFF, (d >>> 24) & 0xFF);

    // skip: call origFn
    var callPos = cave.add(b.length);
    var callRel = origFn.sub(callPos.add(5)).toInt32();
    b.push(0xE8);
    b.push(callRel & 0xFF, (callRel >> 8) & 0xFF, (callRel >> 16) & 0xFF, (callRel >> 24) & 0xFF);

    // done: pop ebx
    b.push(0x5B);
    // jmp continueAddr
    var jmpPos = cave.add(b.length);
    var jmpRel = continueAddr.sub(jmpPos.add(5)).toInt32();
    b.push(0xE9);
    b.push(jmpRel & 0xFF, (jmpRel >> 8) & 0xFF, (jmpRel >> 16) & 0xFF, (jmpRel >> 24) & 0xFF);

    return b;
}}

function applyPatch() {{
    cave.writeByteArray(buildShellcode());
    Memory.patchCode(callSite, 5, function(buf) {{
        var r = cave.sub(callSite.add(5)).toInt32();
        buf.writeByteArray([0xE9, r & 0xFF, (r >> 8) & 0xFF, (r >> 16) & 0xFF, (r >> 24) & 0xFF]);
    }});
    send(JSON.stringify({{type:'info', msg:'Patch applied (v2: restore after call): ' + g_srcIC + ' -> ' + g_dstIC}}));
}}

function removePatch() {{
    Memory.patchCode(callSite, 5, function(buf) {{
        buf.writeByteArray(g_origBytes);
    }});
    send(JSON.stringify({{type:'info', msg:'Removed'}}));
}}

rpc.exports = {{ unpatch: function() {{ removePatch(); return 'ok'; }} }};

applyPatch();
""";

def main():
    if len(sys.argv) < 3:
        print("Usage: py inline_patch_equip.py <src_itemcode> <dst_itemcode>")
        return

    src_ic = int(sys.argv[1])
    dst_ic = int(sys.argv[2])

    pid = None
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            pid = int(parts[1])
            break

    if not pid:
        print("FreeStyle.exe not found")
        return

    print(f"PID={pid}  {src_ic} -> {dst_ic}  (v2: restore after call)")
    print("Patch at 0x1b90ecb, inline code cave.\n")

    js = JS_TEMPLATE.format(src_ic=src_ic, dst_ic=dst_ic)
    session = frida.attach(pid)
    script = session.create_script(js)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            if isinstance(p, str):
                try: p = json.loads(p)
                except: pass
            print(f"  [*] {p.get('msg', p) if isinstance(p, dict) else p}")
        else:
            print(f"  [FRIDA] {msg}")

    script.on('message', on_message)
    script.load()

    print("!! 只装备一次粉色网红主播, 看外观是否变了")
    print("!! 不要切换其他物品 (会崩)")
    print("Press Enter to unpatch...\n")
    try: input()
    except: pass

    try: script.exports_sync.unpatch()
    except: pass
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print("Done.")

if __name__ == '__main__':
    main()
