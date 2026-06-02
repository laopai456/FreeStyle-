"""
trace_resource_load.py — 追踪资源加载函数，对比商城内外调用差异

Hook 目标:
  0xe8aa00 — 解析 .ppi 路径 (0x2371b00 内部调用)
  0x21df240 — 实际资源加载
  0x2371b00 — .ppi 处理主函数

目标: 对比"商城试用"和"退出商城"时的调用参数差异，
      找到模型恢复的切入点。

用法:
  1. 运行脚本
  2. 进商城，试用一个物品
  3. 退出商城回大厅
  4. Ctrl+C 停止，查看结果
"""
import frida, json, sys, time, subprocess

JS = r"""
'use strict';

var log = [];
var MAX_LOG = 500;

function addLog(entry) {
    if (log.length >= MAX_LOG) log.shift();
    log.push(entry);
    send(JSON.stringify(entry));
}

// 读 CString (安全)
function readCStringSafe(addr, maxLen) {
    try {
        if (addr.isNull()) return '<null>';
        return addr.readUtf8String(maxLen || 256);
    } catch(e) {
        return '<unreadable>';
    }
}

// 读 WideString (安全)
function readWideStringSafe(addr, maxLen) {
    try {
        if (addr.isNull()) return '<null>';
        return addr.readUtf16String(maxLen || 256);
    } catch(e) {
        return '<unreadable>';
    }
}

// 短调用栈
function shortBt(ctx, depth) {
    try {
        return Thread.backtrace(ctx, Backtracer.FUZZY)
            .slice(0, depth || 6)
            .map(function(a) { return a.toString(); });
    } catch(e) {
        return ['<bt error>'];
    }
}

// ====== Hook 0xe8aa00 (.ppi 路径解析) ======
// 从 disasm: call 0xe8aa00 是 thiscall (ecx = 对象), 参数 = push ".ppi", push dest, lea ecx
// 签名: thiscall(ecx=this, [esp+4]=dest, [esp+8]=".ppi" 或者 push ".ppi" then push edx)
try {
    var addr_e8aa00 = ptr(0xe8aa00);
    Interceptor.attach(addr_e8aa00, {
        onEnter: function(args) {
            this.ecx = this.context.ecx;
            this.arg0 = args[0]; // 可能是 dest 或 ".ppi" 字符串
            this.arg1 = args[1]; // 第二个参数
        },
        onLeave: function(retval) {
            // 尝试读取 ecx 相关的字符串
            var s_ecx = readCStringSafe(this.ecx, 128);
            var s_arg0 = readCStringSafe(this.arg0, 128);
            var s_arg1 = readCStringSafe(this.arg1, 128);

            var entry = {
                t: time(),
                func: 'e8aa00_ppi_parse',
                ecx: this.ecx.toString(),
                ecx_str: s_ecx.substring(0, 100),
                arg0_str: s_arg0.substring(0, 100),
                arg1_str: s_arg1.substring(0, 100),
                retval: retval.toString(),
                bt: shortBt(this.context, 4)
            };
            addLog(entry);
        }
    });
    send(JSON.stringify({t: time(), type:'info', msg:'Hooked 0xe8aa00 (.ppi parse)'}));
} catch(e) {
    send(JSON.stringify({t: time(), type:'error', msg:'Failed to hook 0xe8aa00: ' + e}));
}

// ====== Hook 0x21df240 (资源加载) ======
try {
    var addr_21df240 = ptr(0x21df240);
    Interceptor.attach(addr_21df240, {
        onEnter: function(args) {
            this.arg0 = args[0];
            this.arg1 = args[1];
            this.arg2 = args[2];
            this.ecx = this.context.ecx;
        },
        onLeave: function(retval) {
            var entry = {
                t: time(),
                func: '21df240_resource_load',
                ecx: this.ecx.toString(),
                arg0: this.arg0.toString(),
                arg1: this.arg1.toString(),
                arg2: this.arg2.toString(),
                retval: retval.toString(),
                bt: shortBt(this.context, 6)
            };
            addLog(entry);
        }
    });
    send(JSON.stringify({t: time(), type:'info', msg:'Hooked 0x21df240 (resource load)'}));
} catch(e) {
    send(JSON.stringify({t: time(), type:'error', msg:'Failed to hook 0x21df240: ' + e}));
}

// ====== Hook 0x2371b00 (.ppi 处理主函数) ======
try {
    var addr_2371b00 = ptr(0x2371b00);
    // thiscall, ecx = this, [esp+4] = 参数
    Interceptor.attach(addr_2371b00, {
        onEnter: function(args) {
            this.ecx = this.context.ecx;
            // [ebp+8] 是第一个参数 (从 disasm: lea ecx, [ebp + 8])
            // 但通过 Interceptor, args[0] = [esp+4]
            this.arg0 = args[0];
            var s_arg0 = readCStringSafe(this.arg0, 128);
            var s_ecx = readCStringSafe(this.ecx, 128);

            addLog({
                t: time(),
                func: '2371b00_ppi_main',
                ecx: this.ecx.toString(),
                ecx_str: s_ecx.substring(0, 100),
                arg0: this.arg0.toString(),
                arg0_str: s_arg0.substring(0, 100),
                bt: shortBt(this.context, 8)
            });
        },
        onLeave: function(retval) {
            addLog({
                t: time(),
                func: '2371b00_ppi_main_RET',
                retval: retval.toString()
            });
        }
    });
    send(JSON.stringify({t: time(), type:'info', msg:'Hooked 0x2371b00 (.ppi main)'}));
} catch(e) {
    send(JSON.stringify({t: time(), type:'error', msg:'Failed to hook 0x2371b00: ' + e}));
}

// ====== 监控全局资源管理器 [0x2A95520] ======
rpc.exports = {
    dumpglobal: function() {
        try {
            var gobj = ptr(0x2A95520).readPointer();
            var default_res = gobj.add(0x160).readPointer();
            var arr_begin = gobj.add(0x16c).readPointer();
            var arr_end = gobj.add(0x170).readPointer();
            var count = arr_end.sub(arr_begin).toInt32() / 4;

            var items = [];
            for (var i = 0; i < Math.min(count, 20); i++) {
                try {
                    items.push(arr_begin.add(i * 4).readPointer().toString());
                } catch(e) {
                    items.push('<error>');
                }
            }

            return JSON.stringify({
                global_obj: gobj.toString(),
                default_resource: default_res.toString(),
                array_begin: arr_begin.toString(),
                array_end: arr_end.toString(),
                array_count: count,
                items: items
            });
        } catch(e) {
            return JSON.stringify({error: e.toString()});
        }
    },
    getlog: function() {
        return JSON.stringify(log);
    },
    clearlog: function() {
        log = [];
        return 'cleared';
    }
};

send(JSON.stringify({t: time(), type:'info', msg:'All hooks ready. Enter shop, try on item, then exit shop. Ctrl+C to stop.'}));
""";

def get_pid():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    return None

def main():
    pid = get_pid()
    if not pid:
        print("FreeStyle.exe not found"); return

    print(f"PID={pid}")
    print("Hooking resource loading functions...")
    print("Flow: enter shop → try on item → exit shop → Ctrl+C\n")

    outpath = r"D:\py\反编译\FreeStyle\trace_resource_result.txt"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('')

    session = frida.attach(pid)
    script = session.create_script(JS)

    count = [0]

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}"); return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except: print(f"  {p}"); return

        t = p.get('type', '')
        if t == 'info':
            print(f"  [*] {p['msg']}")
            return
        if t == 'error':
            print(f"  [!] {p['msg']}")
            return

        count[0] += 1
        func = p.get('func', '?')
        ts = p.get('t', 0)

        if 'ppi_main' in func:
            ecx_s = p.get('ecx_str', '')[:60]
            arg_s = p.get('arg0_str', '')[:60]
            bt = p.get('bt', [])
            print(f"  [{count[0]:3d}] {func}")
            print(f"       ecx_str: {ecx_s}")
            print(f"       arg0_str: {arg_s}")
            for b in bt[:4]:
                print(f"       ← {b}")
        elif 'ppi_parse' in func:
            ecx_s = p.get('ecx_str', '')[:60]
            arg_s = p.get('arg0_str', '')[:60]
            print(f"  [{count[0]:3d}] {func}  ecx={ecx_s}  arg0={arg_s}")
        elif 'resource_load' in func:
            bt = p.get('bt', [])
            print(f"  [{count[0]:3d}] {func}  ret={p.get('retval','')}")
            for b in bt[:4]:
                print(f"       ← {b}")
        else:
            print(f"  [{count[0]:3d}] {func}  {json.dumps(p)[:120]}")

        with open(outpath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(p, indent=2, ensure_ascii=False) + '\n\n')

    script.on('message', on_message)
    script.load()

    # Dump global resource state
    print("\n  Global resource manager state:")
    try:
        g = json.loads(script.exports_sync.dumpglobal())
        print(f"  {json.dumps(g, indent=2)}")
        with open(outpath, 'a', encoding='utf-8') as f:
            f.write("=== INITIAL GLOBAL STATE ===\n")
            f.write(json.dumps(g, indent=2) + '\n\n')
    except Exception as e:
        print(f"  Error dumping global: {e}")

    print("\n  Waiting for activity... (enter shop, try on, exit shop)\n")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

    # Final dump
    print("\n  Final global resource state:")
    try:
        g = json.loads(script.exports_sync.dumpglobal())
        print(f"  {json.dumps(g, indent=2)}")
        with open(outpath, 'a', encoding='utf-8') as f:
            f.write("=== FINAL GLOBAL STATE ===\n")
            f.write(json.dumps(g, indent=2) + '\n\n')
    except: pass

    total = count[0]
    print(f"\n  Total calls captured: {total}")
    print(f"  Results in {outpath}")

    try: script.unload()
    except: pass
    try: session.detach()
    except: pass

if __name__ == '__main__':
    main()
