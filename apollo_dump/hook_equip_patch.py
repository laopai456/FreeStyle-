"""
hook_equip_patch.py — 物品替换 Phase 2: 内存补丁
在角色装备列表中把 50125461(美丽梦想) 替换为 50125711(紫色超赛)

原理:
  游戏内存中有一个"角色装备数组", 每个槽位记录穿着的物品ItemCode。
  记录结构 (每条52字节 = 0x34):
    +0x00: flags (4B)
    +0x04: 常量 08 (4B)
    +0x08: 常量 0F (4B)
    +0x0C: padding (4B)
    +0x10: ItemCode INT (4B)        ← 要改的
    +0x14: 详细记录指针 (4B)
    +0x18: 指针2 (4B)
    +0x1C: 指针3 (4B)
    +0x20: padding (4B)
    +0x24: ItemCode STRING (8B+"\\0") ← 也要改的
    +0x2C: padding (4B)
    +0x30: 下一组flags (4B)

  补丁策略:
  1. 扫描堆内存找到 "50125461" 字符串 + 旁边有 INT 0x02FCDA95 的位置
  2. 把 INT 改为 0x02FCDB8F (50125711)
  3. 把 STRING 改为 "50125711\0"
  4. 同时也改指针指向的详细记录中的字符串
  5. 触发角色重加载 (进房间/换频道)
  6. 游戏读到新的ItemCode → 从自己的item数据库查50125711 → 走完整动态管线

  不需要改pak的原因:
  游戏改了ItemCode后会去查item数据库里50125711的记录, 里面有PakNum=768,
  它会自动去res768.pak读数据, 那里面本来就有50125711的所有文件。

用法:
  1. 游戏运行, 角色穿着美丽梦想发型
  2. py hook_equip_patch.py          # 扫描+补丁
  3. 进房间触发角色重加载
  4. 观察效果
  5. py hook_equip_patch.py --restore # 恢复原始数据
"""
import sys, os, time, struct, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_INT = 50125461
DST_INT = 50125711
SRC_HEX = struct.pack('<I', SRC_INT)  # 95 DA FC 02
DST_HEX = struct.pack('<I', DST_INT)  # 8F DB FC 02
SRC_STR = str(SRC_INT).encode('ascii')  # b'50125461'
DST_STR = str(DST_INT).encode('ascii')  # b'50125711'

LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_patch_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# JS: 找装备记录 + 补丁
JS_CODE = r"""
'use strict';

var SRC_INT = 50125461;
var DST_INT = 50125711;
var SRC_STR = '50125461';
var DST_STR = '50125711';

// INT LE bytes
var srcIntHex = '95 da fc 02';
var dstIntBytes = [0x8f, 0xdb, 0xfc, 0x02];

// ASCII bytes
var srcAsciiBytes = [];
for (var i = 0; i < SRC_STR.length; i++) srcAsciiBytes.push(SRC_STR.charCodeAt(i));
var dstAsciiBytes = [];
for (var i = 0; i < DST_STR.length; i++) dstAsciiBytes.push(DST_STR.charCodeAt(i));

var patches = [];  // 记录所有补丁 {addr, desc, old, new}
var backups = [];  // 备份原始值用于恢复

send({t: 'info', msg: 'Phase 2: 扫描装备记录...'});

// Step 1: 找到所有ASCII "50125461" 的位置
var ranges = Process.enumerateRanges('rw-');  // 只搜索可读写区域
var asciiHits = [];

for (var ri = 0; ri < ranges.length; ri++) {
    var range = ranges[ri];
    if (range.size < 8 || range.size > 200 * 1024 * 1024) continue;
    // 跳过模块
    try { var mod = Process.findModuleByAddress(range.base); if (mod) continue; } catch(e) {}

    try {
        var hexPattern = srcAsciiBytes.map(function(b) { return ('0' + b.toString(16)).slice(-2); }).join(' ');
        var matches = Memory.scanSync(range.base, range.size, hexPattern);
        for (var mi = 0; mi < matches.length; mi++) {
            asciiHits.push(matches[mi].address);
        }
    } catch(e) {}
}

send({t: 'info', msg: 'ASCII "' + SRC_STR + '" 找到 ' + asciiHits.length + ' 处'});

// Step 2: 对每个ASCII位置, 检查-20偏移处是否有对应的INT值
// 装备数组结构: INT在STRING前面20字节 (0x10 offset)
var equipRecords = [];

for (var i = 0; i < asciiHits.length; i++) {
    var strAddr = asciiHits[i];

    // 检查-0x14处是否有INT 50125461
    // INT位置 = STRING位置 - 0x14 (= +0x10 - +0x24 = -0x14)
    var intAddr = strAddr.sub(0x14);

    try {
        var intVal = intAddr.readU32();
        if (intVal === SRC_INT) {
            // 验证结构: 检查+0x04是否有常量8, +0x08是否有常量15
            var v4 = intAddr.add(0x04).readU32();
            var v8 = intAddr.add(0x08).readU32();
            var record = {
                base: intAddr.toString(),
                intAddr: intAddr.toString(),
                strAddr: strAddr.toString(),
                const4: v4,
                const8: v8
            };

            // 也读取指针指向的详细记录
            var ptrVal = intAddr.add(0x14).readPointer();
            record.detailPtr = ptrVal.toString();

            // 检查详细记录中是否有"50125461"
            try {
                var detailStr = ptrVal.add(0x10).readAnsiString(16);
                if (detailStr && detailStr.indexOf(SRC_STR) >= 0) {
                    record.detailHasStr = true;
                    record.detailStrAddr = ptrVal.add(0x10).toString();
                }
            } catch(e) {}

            equipRecords.push(record);
            send({t: 'equip', record: record});
        }
    } catch(e) {}
}

send({t: 'info', msg: '装备记录找到 ' + equipRecords.length + ' 条'});

// Step 3: 执行补丁
var patched = 0;

for (var i = 0; i < equipRecords.length; i++) {
    var rec = equipRecords[i];
    var intAddr = ptr(rec.intAddr);
    var strAddr = ptr(rec.strAddr);

    // 备份
    backups.push({
        intAddr: rec.intAddr,
        oldInt: intAddr.readU32(),
        strAddr: rec.strAddr,
        oldStr: new Uint8Array(strAddr.readByteArray(8))
    });

    // Patch INT
    intAddr.writeU32(DST_INT);
    patches.push({addr: rec.intAddr, desc: 'ItemCode INT', old: SRC_INT, new: DST_INT});

    // Patch STRING
    for (var j = 0; j < dstAsciiBytes.length; j++) {
        strAddr.add(j).writeU8(dstAsciiBytes[j]);
    }
    patches.push({addr: rec.strAddr, desc: 'ItemCode STRING', old: SRC_STR, new: DST_STR});

    patched++;

    // 也Patch详细记录
    if (rec.detailStrAddr) {
        var dsAddr = ptr(rec.detailStrAddr);
        try {
            backups.push({
                strAddr: rec.detailStrAddr,
                oldStr: new Uint8Array(dsAddr.readByteArray(8))
            });
            for (var j = 0; j < dstAsciiBytes.length; j++) {
                dsAddr.add(j).writeU8(dstAsciiBytes[j]);
            }
            patches.push({addr: rec.detailStrAddr, desc: 'Detail STRING', old: SRC_STR, new: DST_STR});
        } catch(e) {}
    }
}

send({t: 'patched', count: patched, patches: patches});

// === 以下是Hook保持逻辑 ===
// 游戏可能从服务器刷新装备数据覆盖我们的补丁
// 用ReadFile hook监控BML加载, 如果检测到50125461的BML被加载说明补丁被覆盖了

var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3];
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 50 || n > 10000) return;
            var buf = new Uint8Array(this.buf.readByteArray(n));
            var tag = [0x3C,0x72,0x6F,0x6F,0x74,0x3E];
            var ok = true;
            for (var i=0;i<6;i++) if((buf[i]^0xFF)!==tag[i]){ok=false;break;}
            if (!ok) return;

            var text = '';
            for (var i=0;i<n;i++){var c=buf[i]^0xFF;if(c>=0x20&&c<0x7F)text+=String.fromCharCode(c);}
            var icM = text.match(/i(\d{6,8})/);
            var ic = icM ? icM[1] : '';
            if (ic === SRC_STR) {
                send({t: 'warn', msg: '补丁可能被覆盖! 检测到50125461的BML被加载'});
                // 自动重新补丁
                for (var i = 0; i < equipRecords.length; i++) {
                    try {
                        ptr(equipRecords[i].intAddr).writeU32(DST_INT);
                        var sa = ptr(equipRecords[i].strAddr);
                        for (var j = 0; j < dstAsciiBytes.length; j++) sa.add(j).writeU8(dstAsciiBytes[j]);
                    } catch(e) {}
                }
                send({t: 'repatch', msg: '已重新补丁'});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '补丁完成, BML监控已激活. 进房间触发重加载.'});

// RPC: 恢复
rpc.exports = {
    restore: function() {
        for (var i = 0; i < backups.length; i++) {
            var b = backups[i];
            try {
                if (b.oldInt !== undefined) {
                    ptr(b.intAddr).writeU32(b.oldInt);
                }
                if (b.oldStr !== undefined) {
                    var sa = ptr(b.strAddr);
                    for (var j = 0; j < b.oldStr.length; j++) {
                        sa.add(j).writeU8(b.oldStr[j]);
                    }
                }
            } catch(e) {}
        }
        send({t: 'restored', msg: '已恢复 ' + backups.length + ' 处补丁'});
    },
    status: function() {
        // 检查补丁是否还在
        var alive = 0;
        for (var i = 0; i < equipRecords.length; i++) {
            try {
                var v = ptr(equipRecords[i].intAddr).readU32();
                if (v === DST_INT) alive++;
            } catch(e) {}
        }
        send({t: 'status', alive: alive, total: equipRecords.length, patches: patches.length});
    }
};
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Phase 2: 装备记录补丁 === PID:{pid} ===')
    log(f'{SRC_INT} (美丽梦想) → {DST_INT} (紫色超赛)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t','')

            if t == 'info':
                log(f'  {p["msg"]}')
            elif t == 'equip':
                r = p['record']
                log(f'  [装备记录] base={r["base"]} int={r["intAddr"]} str={r["strAddr"]}')
                log(f'    常量: {r.get("const4","?")} {r.get("const8","?")} 详情指针={r.get("detailPtr","?")}')
                if r.get('detailHasStr'):
                    log(f'    详情记录也有ItemCode字符串 @ {r["detailStrAddr"]}')
            elif t == 'patched':
                count = p['count']
                patches = p['patches']
                log(f'  补丁完成: {count} 条记录, {len(patches)} 处修改')
                for pc in patches:
                    log(f'    {pc["addr"]} {pc["desc"]}: {pc["old"]} → {pc["new"]}')
            elif t == 'warn':
                log(f'  [警告] {p["msg"]}')
            elif t == 'repatch':
                log(f'  [重补丁] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'restored':
                log(f'  {p["msg"]}')
            elif t == 'status':
                log(f'  补丁存活: {p["alive"]}/{p["total"]} 条, 共{p["patches"]}处修改')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:150]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('补丁已应用。现在进房间触发角色重加载。')
    log('命令: status | restore | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                script.post({'type':'cmd','cmd':'status'})
            elif cmd == 'restore':
                script.exports_sync.restore()
    except (KeyboardInterrupt, EOFError):
        pass

    log('会话结束')
    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()
