"""
hook_diag.py — 诊断: 验证hook地址 + 最小hook测试
打印base地址、计算hook地址、读取目标处指令字节、验证函数存在
然后用最小hook (只记数) 看是否崩溃
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

JS_CODE = r"""
'use strict';

var mod = Process.getModuleByName('FreeStyle.exe');
var base = mod.base;
var size = mod.size;

send({t: 'info', msg: 'Module: base=' + base + ' size=0x' + size.toString(16)});

// 验证几个关键RVA
var targets = [
    {rva: 0x01E99730, name: 'DynamicCreate1'},
    {rva: 0x01EF27B0, name: 'DynamicCreate2'},
    {rva: 0x01EFA370, name: 'DynamicWrapper'},
];

for (var i = 0; i < targets.length; i++) {
    var t = targets[i];
    var addr = base.add(t.rva);
    var abs = '0x' + addr.toString(16);
    // 读取前16字节看指令
    var hex = '';
    try {
        var bytes = new Uint8Array(addr.readByteArray(16));
        for (var j = 0; j < bytes.length; j++) {
            hex += ('0' + bytes[j].toString(16)).slice(-2) + ' ';
        }
    } catch(e) { hex = 'READ FAILED: ' + e; }

    // 检查是否在模块范围内
    var inRange = addr.compare(base) >= 0 && addr.compare(base.add(size)) < 0;
    send({t: 'check', name: t.name, rva: '0x' + t.rva.toString(16), abs: abs,
          hex: hex, inRange: inRange});
}

// 最小hook: 只记数, 不做任何内存操作
var dc1Addr = base.add(0x01E99730);
var callCount = 0;

Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callCount++;
        if (callCount <= 10) {
            send({t: 'call', idx: callCount, ecx: this.context.ecx.toString()});
        }
    }
});

send({t: 'ready', msg: '诊断hook ready (最小hook, 只记数). 进房间测试.'});

rpc.exports = {
    count: function() { return callCount; }
};
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 诊断 === PID:{pid} ===')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'info':
                log(f'  {p["msg"]}')
            elif t == 'check':
                status = 'OK' if p['inRange'] else 'OUT OF RANGE!'
                log(f'  {p["name"]}: RVA={p["rva"]} abs={p["abs"]} [{status}]')
                log(f'    bytes: {p["hex"]}')
            elif t == 'call':
                log(f'  [#{p["idx"]}] DynamicCreate1 ecx={p["ecx"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            else:
                log(f'  {json.dumps(p)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间测试。命令: count | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'count':
                c = script.exports_sync.count()
                log(f'  调用次数: {c}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()
