"""
monitor_backpack.py — 监控背包操作时的内存变化
每秒扫描 50125461 (美丽梦想发型) 的所有出现位置
当用户在背包中装备/卸载发型时，观察哪些地址的值发生变化
"""
import sys, time, struct, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752
TARGET_IC = 50125461  # 0x2FCDA95 美丽梦想发型

JS_CODE = r"""
'use strict';

var TARGET = %d;  // 50125461
var TARGET_BYTES = [];
var tmp = TARGET;
for (var i = 0; i < 4; i++) {
    TARGET_BYTES.push(tmp & 0xFF);
    tmp = tmp >>> 8;
}

// 上一次扫描结果
var lastHits = {};

function scanHeap() {
    var now = [];
    var ranges = Process.enumerateRanges('rw-');

    for (var ri = 0; ri < ranges.length; ri++) {
        var range = ranges[ri];
        if (range.size > 50 * 1024 * 1024) continue;  // skip >50MB

        try {
            var matches = Memory.scanSync(range.base, range.size,
                TARGET_BYTES.map(function(b) {
                    return (b < 16 ? '0' : '') + b.toString(16);
                }).join(' '));

            for (var mi = 0; mi < matches.length; mi++) {
                var addr = matches[mi].address;
                now.push(addr.toString());
            }
        } catch(e) {}
    }

    // 对比变化
    var added = [];
    var removed = [];
    var unchanged = [];

    var nowSet = {};
    for (var i = 0; i < now.length; i++) {
        nowSet[now[i]] = true;
        if (!lastHits[now[i]]) {
            added.push(now[i]);
        } else {
            unchanged.push(now[i]);
        }
    }

    for (var k in lastHits) {
        if (!nowSet[k]) {
            removed.push(k);
        }
    }

    lastHits = {};
    for (var i = 0; i < now.length; i++) {
        lastHits[now[i]] = true;
    }

    var msg = {
        total: now.length,
        added: added.length,
        removed: removed.length
    };

    if (added.length > 0 || removed.length > 0) {
        msg.added_addrs = added.slice(0, 20);
        msg.removed_addrs = removed.slice(0, 20);

        // 对新增地址，读前后上下文
        if (added.length > 0) {
            msg.contexts = [];
            for (var i = 0; i < Math.min(added.length, 5); i++) {
                try {
                    var a = ptr(added[i]);
                    var before = hexdump(a.sub(16), {length: 48, header: false});
                    msg.contexts.push({addr: added[i], dump: before});
                } catch(e) {}
            }
        }
    }

    send(msg);
}

// 每秒扫描一次
setInterval(scanHeap, 1000);

// 初始扫描
scanHeap();
""" % TARGET_IC

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        total = p.get('total', 0)
        added = p.get('added', 0)
        removed = p.get('removed', 0)

        ts = time.strftime('%H:%M:%S')
        if added > 0 or removed > 0:
            print(f"\n{'='*60}")
            print(f"[{ts}] *** 变化检测! total={total} +{added} -{removed}")
            for a in p.get('added_addrs', []):
                print(f"  +出现: {a}")
            for a in p.get('removed_addrs', []):
                print(f"  -消失: {a}")
            for ctx in p.get('contexts', []):
                print(f"\n  上下文 @ {ctx['addr']}:")
                for line in ctx['dump'].split('\n'):
                    print(f"    {line}")
            print(f"{'='*60}")
        else:
            # 静默输出, 只显示计数
            print(f"[{ts}] 扫描中... 发现 {total} 处含有 {TARGET_IC}", flush=True)
    elif msg['type'] == 'error':
        print(f"[ERROR] {msg.get('description','')}")


def main():
    print(f"[*] Attaching to PID {PID} ...")
    session = frida.attach(PID)
    script = session.create_script(JS_CODE)
    script.on('message', on_message)
    script.load()
    print(f"[*] 监控中: 每秒扫描 {TARGET_IC} (0x{TARGET_IC:X})")
    print(f"[*] 现在去背包里操作发型吧!")
    print(f"[*] Ctrl+C 退出\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 停止监控")
        session.detach()

if __name__ == '__main__':
    main()
