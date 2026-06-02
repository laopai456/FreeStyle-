"""
hook_equip_trace.py — Phase 3: 追溯装备函数调用链
在DynamicCreate被调用时dump完整callstack, 找到"装备物品"的入口函数

逻辑:
  从v3日志我们知道 DynamicCreate1(0x2299730) 被调用创建Actor。
  返回地址 0x22FA3A0 在 Dynamic包装函数 0x22FA370 内部。
  但我们不知道是谁调用了 0x22FA370。

  这个脚本 hook DynamicCreate1, 在调用时:
  1. 用 Thread.backtrace() 捕获完整调用栈
  2. 解析每个栈帧属于哪个函数
  3. 这样就能追溯到顶层 "装备物品" 函数

  然后我们可以 hook 那个顶层函数, 在那里替换ItemCode。
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_trace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var base = Process.getModuleByName('FreeStyle.exe').base;

// 要hook的地址 (RVA形式, 运行时 +base)
var HOOKS = [
    {rva: 0x01E99730, name: 'DynamicCreate1'},  // 0x2299730
    {rva: 0x01EF27B0, name: 'DynamicCreate2'},  // 0x22F27B0
];

var callLog = [];

function hookCreate(hookInfo) {
    var addr = base.add(hookInfo.rva);
    Interceptor.attach(addr, {
        onEnter: function(args) {
            // 捕获调用栈 (Frida的backtrace)
            var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);

            // 解析栈帧
            var frames = [];
            for (var i = 0; i < bt.length && i < 15; i++) {
                var frameAddr = bt[i];
                var rva = frameAddr.sub(base);
                var modInfo = '';
                try {
                    var mod = Process.findModuleByAddress(frameAddr);
                    if (mod) modInfo = mod.name;
                } catch(e) {}

                // 尝试读前几条指令来理解上下文
                var ctxBytes = '';
                try {
                    var before = frameAddr.sub(8).readByteArray(8);
                    var bytes = new Uint8Array(before);
                    for (var j = 0; j < bytes.length; j++) {
                        ctxBytes += ('0' + bytes[j].toString(16)).slice(-2) + ' ';
                    }
                } catch(e) {}

                frames.push({
                    addr: frameAddr.toString(),
                    rva: '0x' + rva.toString(16),
                    mod: modInfo,
                    before: ctxBytes
                });
            }

            // 也读栈上的参数/数据
            var esp = this.context.esp;
            var stackData = [];
            try {
                for (var off = 0; off < 0x60; off += 4) {
                    var val = esp.add(off).readU32();
                    stackData.push('0x' + val.toString(16));
                }
            } catch(e) {}

            var entry = {
                event: 'call',
                func: hookInfo.name,
                addr: addr.toString(),
                retAddr: '0x' + (esp.readU32() - base).toString(16),
                frames: frames,
                stack: stackData.slice(0, 16),
                eax: this.context.eax.toString(),
                ecx: this.context.ecx.toString(),
                edx: this.context.edx.toString()
            };

            callLog.push(entry);
            send({t: 'log', line: JSON.stringify(entry)});
        }
    });
    send({t: 'info', msg: 'Hooked ' + hookInfo.name + ' @ ' + addr.toString()});
}

for (var i = 0; i < HOOKS.length; i++) {
    hookCreate(HOOKS[i]);
}

send({t: 'ready', msg: 'Callstack tracer ready. Load character to capture call chain.'});

rpc.exports = {
    getLog: function() {
        return JSON.stringify(callLog, null, 2);
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
    log(f'=== Phase 3: 调用链追溯 === PID:{pid} ===')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'info' or t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'log':
                try:
                    raw = p.get('line', '')
                    brace = raw.find('{')
                    if brace > 0: raw = raw[brace:]
                    obj = json.loads(raw)

                    func = obj.get('func', '?')
                    ret = obj.get('retAddr', '?')
                    frames = obj.get('frames', [])
                    stack = obj.get('stack', [])
                    eax = obj.get('eax', '?')

                    log(f'  [CALL] {func} ret=RVA:{ret}')
                    log(f'    eax={eax} stack[:8]={stack[:8]}')
                    log(f'    调用栈:')
                    for i, f in enumerate(frames):
                        log(f'      #{i} RVA:{f["rva"]} {f.get("before","")}')
                except Exception as e:
                    log(f'  [parse err] {e}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:150]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Hook已激活。触发角色加载（进房间/换频道）来捕获调用链。')
    log('命令: save | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'save':
                calls_json = script.exports_sync.get_log()
                json_path = LOG_FILE.replace('.txt', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    f.write(calls_json)
                log(f'调用链已保存: {json_path}')
    except (KeyboardInterrupt, EOFError):
        pass

    # 结束时保存
    try:
        calls_json = script.exports_sync.get_log()
        json_path = LOG_FILE.replace('.txt', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(calls_json)
        log(f'调用链已保存: {json_path} ({len(json.loads(calls_json))} 条)')
    except: pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()
