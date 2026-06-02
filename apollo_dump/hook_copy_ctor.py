"""
hook_copy_ctor.py — hook 描述符拷贝构造函数，实时替换 ItemCode

用法:
  1. py inject_test.py 15676  (已有 Frida 连接)
  2. 在 inject_test 里输入: hcopy 50125691 50125721
  3. 进入商城点击黑金 → 显示粉色超赛3

或独立运行: py hook_copy_ctor.py 15676 50125691 50125721
"""
import frida, json, sys, time

JS = r"""
'use strict';

var g_hook = null;
var g_patchSrcIC = 0;
var g_patchDstIC = 0;

rpc.exports = {
    hook: function(srcIC, dstIC) {
        if (g_hook !== null) {
            g_hook.detach();
        }
        
        g_patchSrcIC = srcIC;
        g_patchDstIC = dstIC;
        
        // 拷贝构造函数: 0x1C29FE0
        // thiscall: ecx = dest outer object
        // vtable at this+0x0C, ItemCode at vtable+0x060 = this+0x06C
        var ctorAddr = ptr('0x1C29FE0');
        
        g_hook = Interceptor.attach(ctorAddr, {
            onEnter: function(args) {
                // ecx = this (dest outer object)
                this.destOuter = this.context.ecx;
            },
            onLeave: function(retval) {
                if (g_patchSrcIC === 0) return;
                try {
                    var descAddr = this.destOuter.add(0x0C);
                    var icAddr = descAddr.add(0x060);  // = outer + 0x06C
                    var ic = icAddr.readU32();
                    if (ic === g_patchSrcIC) {
                        icAddr.writeU32(g_patchDstIC);
                        send({type:'patch', desc: descAddr.toString(), ic: ic, newic: g_patchDstIC});
                    }
                } catch(e) {
                    // 地址无效，忽略
                }
            }
        });
        
        return JSON.stringify({ok: true, msg: 'hooked', addr: '0x1C29FE0', srcIC: srcIC, dstIC: dstIC});
    },
    
    unhook: function() {
        if (g_hook !== null) {
            g_hook.detach();
            g_hook = null;
        }
        var old = g_patchSrcIC;
        g_patchSrcIC = 0;
        g_patchDstIC = 0;
        return JSON.stringify({ok: true, msg: 'unhooked', srcIC: old});
    }
};
""";

def main():
    pid = int(sys.argv[1])
    src = int(sys.argv[2])
    dst = int(sys.argv[3])
    
    print(f"Attaching to PID {pid}...")
    session = frida.attach(pid)
    script = session.create_script(JS)
    
    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            if isinstance(p, dict) and p.get('type') == 'patch':
                print(f"  [{time.strftime('%H:%M:%S')}] PATCHED desc={p['desc']} {p['ic']}->{p['newic']}")
            else:
                print(f"  [JS] {p}")
        else:
            print(f"  [FRIDA] {msg}")
    
    script.on('message', on_message)
    script.load()
    
    result = json.loads(script.exports_sync.hook(src, dst))
    print(f"  {result}")
    
    print(f"\nHook active: {src} -> {dst}")
    print(f"Now enter shop and click the source item.")
    print(f"Ctrl+C to stop.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    script.exports_sync.unhook()
    session.detach()
    print("Unhooked.")

if __name__ == "__main__":
    main()
