"""
hook_equip_ic.py — Hook 包构造函数, 修改装备 ItemCode
v2: 不恢复原值 + 异常捕获

用法: py hook_equip_ic.py <src_itemcode> <dst_itemcode> [pid]
"""
import frida, json, sys, time

JS_TEMPLATE = r"""
'use strict';

var g_srcIC = {src_ic};
var g_dstIC = {dst_ic};
var g_hook = null;
var g_count = 0;

function hookEquipPkt() {{
    if (g_hook) return;
    var pktBuilder = ptr(0x1922720);

    g_hook = Interceptor.attach(pktBuilder, {{
        onEnter: function(args) {{
            var thisPtr = this.context.ecx;
            if (thisPtr.isNull()) return;

            try {{
                var ic = thisPtr.add(0xE34).readU32();
                if (ic !== g_srcIC) return;

                g_count++;
                // 保存原始值用于 Ctrl+C 后手动恢复
                this._savedThis = thisPtr;
                this._oldIC = ic;

                // 修改为目标 IC (不恢复)
                thisPtr.add(0xE34).writeU32(g_dstIC);

                send(JSON.stringify({{
                    type: 'PATCH',
                    n: g_count,
                    thisPtr: thisPtr.toString(),
                    oldIC: ic,
                    newIC: g_dstIC
                }}));
            }} catch(e) {{
                send(JSON.stringify({{type:'err', msg:'onEnter: ' + e}}));
            }}
        }}
    }});
    send(JSON.stringify({{type:'info', msg:'Hooked 0x1922720: ' + g_srcIC + ' -> ' + g_dstIC}}));
}}

// RPC: 手动恢复
rpc.exports = {{
    restore: function() {{
        // 无法精确恢复, 因为可能多次调用
        return JSON.stringify({{ok: false, msg: 'no auto restore in v2'}});
    }}
}};

hookEquipPkt();
""";

def main():
    if len(sys.argv) < 3:
        print("Usage: py hook_equip_ic.py <src_itemcode> <dst_itemcode> [pid]")
        print("  Example: py hook_equip_ic.py 50122721 50125721")
        return

    src_ic = int(sys.argv[1])
    dst_ic = int(sys.argv[2])

    pid = None
    if len(sys.argv) >= 4:
        pid = int(sys.argv[3])
    else:
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

    print(f"PID={pid}")
    print(f"ItemCode: {src_ic} -> {dst_ic}")
    print("v2: modify only, no restore. Ctrl+C to stop.\n")

    js = JS_TEMPLATE.format(src_ic=src_ic, dst_ic=dst_ic)
    session = frida.attach(pid)
    script = session.create_script(js)

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}")
            return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except:
                print(f"  {p}")
                return
        t = p.get('type', '')
        if t == 'PATCH':
            print(f"  [{p['n']}] PATCHED this={p['thisPtr']}  "
                  f"0x{p['oldIC']:08X} -> 0x{dst_ic:08X}")
        elif t == 'EXCEPTION':
            print(f"  !!! EXCEPTION addr={p['addr']} type={p['type2']} pc={p['context']}")
        elif t == 'info':
            print(f"  [*] {p['msg']}")
        elif t == 'err':
            print(f"  [ERR] {p['msg']}")
        else:
            print(f"  [{t}] {p}")

    script.on('message', on_message)
    script.load()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print("\nDone.")

if __name__ == '__main__':
    main()
