"""
monitor_backpack2.py — 轻量监控: 只轮询已发现的地址
初始全扫描一次找到所有位置, 之后只读这些地址的值
"""
import sys, time, struct, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752
TARGET_IC = 50125461  # 0x2FCDA95

JS_CODE = r"""
'use strict';

var TARGET = %d;
var TARGET_BYTES = [];
var tmp = TARGET;
for (var i = 0; i < 4; i++) {
    TARGET_BYTES.push(tmp & 0xFF);
    tmp = tmp >>> 8;
}
var PATTERN = TARGET_BYTES.map(function(b) {
    return (b < 16 ? '0' : '') + b.toString(16);
}).join(' ');

var knownAddrs = [];   // [{addr: ptr, val: int}]
var initialized = false;

// 一次性全扫描
function initScan() {
    var hits = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var ri = 0; ri < ranges.length; ri++) {
        var range = ranges[ri];
        if (range.size > 50 * 1024 * 1024) continue;
        try {
            var matches = Memory.scanSync(range.base, range.size, PATTERN);
            for (var mi = 0; mi < matches.length; mi++) {
                hits.push(matches[mi].address);
            }
        } catch(e) {}
    }

    knownAddrs = [];
    for (var i = 0; i < hits.length; i++) {
        try {
            var val = hits[i].readU32();
            knownAddrs.push({addr: hits[i], str: hits[i].toString(), val: val});
        } catch(e) {}
    }

    send({type: 'init', count: knownAddrs.length, addrs: knownAddrs.map(function(a) { return a.str; })});
    initialized = true;
}

// 轮询已知地址
function poll() {
    if (!initialized) return;

    var changes = [];
    var alive = 0;

    for (var i = 0; i < knownAddrs.length; i++) {
        try {
            var val = knownAddrs[i].addr.readU32();
            alive++;
            if (val !== knownAddrs[i].val) {
                changes.push({
                    addr: knownAddrs[i].str,
                    old: knownAddrs[i].val,
                    new: val
                });
                knownAddrs[i].val = val;
            }
        } catch(e) {
            // 地址失效(被释放)
            changes.push({
                addr: knownAddrs[i].str,
                old: knownAddrs[i].val,
                new: 'FREED'
            });
            knownAddrs[i].val = -1;
        }
    }

    send({type: 'poll', alive: alive, total: knownAddrs.length, changes: changes});
}

// 初始扫描
rpc.exports = {
    init: function() {
        initScan();
    }
};

// 每秒轮询
setInterval(poll, 1000);
""" % TARGET_IC

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        ts = time.strftime('%H:%M:%S')

        if p.get('type') == 'init':
            print(f"[{ts}] 初始扫描完成: 发现 {p['count']} 处")
            # 按 region 分组显示
            addrs = p.get('addrs', [])
            regions = {}
            for a in addrs:
                prefix = a[:6]
                regions.setdefault(prefix, []).append(a)
            for prefix, items in sorted(regions.items()):
                print(f"  {prefix}xxxxxx: {len(items)} 处")
            print(f"[*] 开始轮询, 去背包操作吧!\n")

        elif p.get('type') == 'poll':
            alive = p.get('alive', 0)
            changes = p.get('changes', [])
            if changes:
                print(f"\n[{ts}] *** {len(changes)} 处变化! (alive={alive})")
                for c in changes:
                    old_str = f"0x{c['old']:X}" if isinstance(c['old'], int) else str(c['old'])
                    new_str = f"0x{c['new']:X}" if isinstance(c['new'], int) else str(c['new'])
                    match = "✓ 仍是目标" if c['new'] == TARGET_IC else "✗ 已改变!"
                    print(f"  {c['addr']}: {old_str} → {new_str}  {match}")
                print()
            else:
                print(f"[{ts}] 稳定 alive={alive}", flush=True)
    elif msg['type'] == 'error':
        print(f"[ERROR] {msg.get('description','')}")


def main():
    print(f"[*] Attaching to PID {PID} ...")
    session = frida.attach(PID)
    script = session.create_script(JS_CODE)
    script.on('message', on_message)
    script.load()

    # 触发初始扫描
    print(f"[*] 初始全堆扫描中...")
    script.exports_sync.init()

    print(f"[*] Ctrl+C 退出\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 停止")
        session.detach()

if __name__ == '__main__':
    main()
