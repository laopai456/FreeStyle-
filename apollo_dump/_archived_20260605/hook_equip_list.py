import sys, frida, time, os
sys.stdout.reconfigure(encoding='utf-8')

BASE = 0x400000
FUNC_ADDR = 0x1AE1F80
SPRINT_SITE = 0x1AE255E
OUT = os.path.join(os.path.dirname(__file__), '_equip_list_dump.txt')

JS = """
var base = ptr(0x400000);
var funcAddr = base.add(0x1AE1F80);
var sprintSite = base.add(0x1AE255E);
var callCount = 0;
var out = '';

function log(msg) {
    var ts = new Date().toISOString().slice(11,23);
    out += '[' + ts + '] ' + msg + '\\n';
    send({kind:'log', msg: msg});
}

function traverseList(listPtr) {
    if (listPtr.isNull()) return '  listPtr=null';
    var lines = [];
    var seen = {};
    var safety = 0;
    var node = listPtr;
    try { node = Memory.readPointer(node); } catch(e) { lines.push('  readPtr fail: ' + e); return lines.join('\\n'); }

    while (!node.isNull() && safety < 50) {
        safety++;
        try {
            var nodeAddr = node.toString();
            if (seen[nodeAddr]) { lines.push('  (cycle)'); break; }
            seen[nodeAddr] = true;

            var itemCode = Memory.readU32(node.add(0x10));
            var slotType = Memory.readU32(node.add(0x14));
            var slotName = '?';
            if (slotType == 1) slotName = 'HAIR';
            else if (slotType == 0xC) slotName = 'FACE';
            else if (slotType == 0x10) slotName = 'ACCESSORY';
            else if (slotType == 0x14) slotName = 'BODY';
            else if (slotType == 0x18) slotName = 'PANTS';
            else if (slotType == 0x1C) slotName = 'SHOES';
            else if (slotType == 0x20) slotName = 'HAND';
            else if (slotType == 0x24) slotName = 'HEAD';
            else if (slotType == 0x28) slotName = 'BACK';
            else if (slotType == 0x2C) slotName = 'NECK';
            else if (slotType == 0x30) slotName = 'RING';
            else if (slotType == 0x34) slotName = 'WRIST';
            else if (slotType == 0x38) slotName = 'GLASSES';
            else if (slotType == 0x3C) slotName = 'EAR';
            else if (slotType == 0x40) slotName = 'MASK';
            else if (slotType == 0x44) slotName = 'TATTOO';
            else if (slotType == 0x48) slotName = 'PET';
            else if (slotType == 0x4C) slotName = 'TAIL';

            var next = Memory.readPointer(node);
            lines.push('  node=' + nodeAddr + ' itemCode=' + itemCode + ' (0x' + itemCode.toString(16) + ') slotType=' + slotType + ' (' + slotName + ') next=' + next);
            node = next;
        } catch(e) {
            lines.push('  readFail: ' + e);
            break;
        }
    }
    return lines.join('\\n');
}

// Hook 1: 函数入口
try {
    Interceptor.attach(funcAddr, {
        onEnter: function(args) {
            callCount++;
            var ebp = this.context.ebp;
            var retAddr = ebp.add(4).readPointer();
            var listPtr = ebp.add(0x14).readPointer();
            var phaseLabel = callCount >= 2 ? 'PRACTICE_LOAD' : 'ROOM_LOAD';

            log('===== [FUNC_ENTRY] #' + callCount + ' phase=' + phaseLabel + ' =====');
            log('  ret=' + retAddr.sub(base) + ' listPtr=' + listPtr);
            log('  --- equip list ---');
            if (listPtr.isNull()) {
                log('  listPtr = NULL');
            } else {
                log(traverseList(listPtr));
            }
            log('  --- end ---');
        }
    });
    log('[HOOK] func entry 0x' + funcAddr.sub(base).toString(16) + ' OK');
} catch(e) {
    log('[HOOK] func entry FAIL: ' + e);
}

// Hook 2: sprint 调用点 (备用)
try {
    Interceptor.attach(sprintSite, {
        onEnter: function(args) {
            var ebp = this.context.ebp;
            // 在 sprint 调用点，ebp 是外层函数的 ebp
            var listPtr = ebp.add(0x14).readPointer();
            var itemCode = ebp.add(-0xD8).readU32();
            var slotType = ebp.add(-0xDC).readU32();
            var retAddr = ebp.add(4).readPointer();

            log('  [SPRINT_SITE] itemCode=' + itemCode + ' slotType=' + slotType + ' ret=' + retAddr.sub(base));
        }
    });
    log('[HOOK] sprint site 0x' + sprintSite.sub(base).toString(16) + ' OK');
} catch(e) {
    log('[HOOK] sprint site FAIL: ' + e);
}
"""

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

pid = find_pid()
if not pid:
    print('FreeStyle.exe 未运行')
    sys.exit(1)

session = frida.attach(pid)
script = session.create_script(JS)

def on_msg(msg, data):
    if msg['type'] == 'send':
        print(msg['payload']['msg'])
    elif msg['type'] == 'error':
        print(f'JS: {msg.get("description","")}')

script.on('message', on_msg)
script.load()
print(f'[脚本已注入] func=0x{FUNC_ADDR:X}  sprint_site=0x{SPRINT_SITE:X}')
print(f'[输出文件] {OUT}')
print('[操作] 退出练习场 → 回到房间 → 重新进练习场 → 回终端按 Ctrl+C')
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n[停止] 正在卸载...')
    try:
        script.unload()
    except:
        pass
    session.detach()
    print(f'[完毕] 数据已写入 {OUT}')