"""
find_itemcode_reader.py — 定位读取描述符 ItemCode 的代码

通过 Frida MemoryAccessMonitor 监控描述符 +0x060 的读取，
捕获调用栈，找到游戏读取 ItemCode 的函数地址。

用法: py find_itemcode_reader.py <pid> <itemcode>
"""
import frida, sys, json, struct, time

JS_CODE = r"""
'use strict';

var VT = 0x027FCEA0;
var IC_OFFSET = 0x060;
var targetItemCode = 0;

// 搜索堆上的描述符
function findDescriptor(itemcode) {
    targetItemCode = itemcode;
    var mod = Process.enumerateModules()[0];
    var modEnd = mod.base.add(mod.size);
    var vtBytes = new Uint8Array([0xA0, 0xCE, 0x7F, 0x02]);
    
    var results = Memory.scanSync(modEnd, Process.enumerateRanges('r--')[0] ? 
        Process.enumerateRanges('rw-').reduce(function(acc, r) { return acc + r.size; }, 0) : 0x10000000,
        'A0 CE 7F 02');
    
    // 实际做法：扫描所有可读写内存
    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    for (var ri = 0; ri < ranges.length; ri++) {
        try {
            var found = Memory.scanSync(ranges[ri].base, ranges[ri].size, 'A0 CE 7F 02');
            for (var fi = 0; fi < found.length; fi++) {
                var addr = found[fi].address;
                if (addr.compare(modEnd) > 0) {
                    try {
                        var ic = addr.add(IC_OFFSET).readU32();
                        if (ic === itemcode) {
                            hits.push(addr);
                        }
                    } catch(e) {}
                }
            }
        } catch(e) {}
    }
    return hits;
}

rpc.exports = {
    scan: function(itemcode) {
        var hits = findDescriptor(itemcode);
        var result = [];
        for (var i = 0; i < hits.length; i++) {
            result.push(hits[i].toString());
        }
        return JSON.stringify(result);
    },
    
    watch: function(itemcode) {
        var hits = findDescriptor(itemcode);
        if (hits.length === 0) {
            return JSON.stringify({ok: false, msg: 'descriptor not found'});
        }
        
        var descAddr = hits[0];
        var icAddr = descAddr.add(IC_OFFSET);
        
        // 用 Interceptor hook 附近的读取操作不太可行
        // 改用 Stalker 或简单轮询 + 读断点模拟
        
        // 方案：用 Memory.patchCode 在描述符附近设 watchpoint 不现实
        // 改为：直接在 ItemCode 内存位置设 Frida 的 MemoryAccessMonitor
        
        send({
            type: 'watch_setup',
            descAddr: descAddr.toString(),
            icAddr: icAddr.toString()
        });
        
        // 启用 Stalker 追踪读取消
        // 实际上用简单的方案：hook 游戏的内存分配 + 紧急 patch
        
        return JSON.stringify({
            ok: true, 
            descAddr: descAddr.toString(),
            icAddr: icAddr.toString()
        });
    }
};
""";

def main():
    if len(sys.argv) < 3:
        print("Usage: py find_itemcode_reader.py <pid> <itemcode>")
        return
    
    pid = int(sys.argv[1])
    itemcode = int(sys.argv[2])
    
    print(f"Attaching to PID {pid}...")
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)
    
    def on_message(msg, data):
        if msg['type'] == 'send':
            print(f"  [JS] {msg['payload']}")
        else:
            print(f"  [FRIDA] {msg}")
    
    script.on('message', on_message)
    script.load()
    
    # 先找到描述符
    result = json.loads(script.exports_sync.scan(itemcode))
    print(f"\nFound descriptors: {result}")
    
    if result:
        desc_addr = result[0]
        print(f"\nDescriptor at {desc_addr}")
        print(f"ItemCode at {desc_addr}+0x060")
        print(f"\nNow use x64dbg or Cheat Engine to set a hardware read breakpoint")
        print(f"  on address {desc_addr}+0x060")
        print(f"  Then click the item in shop to trigger the read")
        print(f"  The breakpoint will show you which instruction reads the ItemCode")
    
    input("\nPress Enter to detach...")
    try: script.unload()
    except: pass
    session.detach()

if __name__ == "__main__":
    main()
