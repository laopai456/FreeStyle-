"""
hook_header_only.py — Header-only 替换测试
只替换512B SSKF header, 不动mesh数据
目的: 验证游戏是否从header读取骨骼数/flag等元数据
数据: 直接嵌入JS, 无需外部文件

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'header_only_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// ==========================================
// 1. 目标Header数据 (直接嵌入, 无需外部文件)
//    i50125711_FN.smd (紫色超赛发型, 动态)
// ==========================================
var targetHeaderHex = "53534b46010000006935303132353731315f464e2e736d64000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004e6f6e65000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004f00000042697030310000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004e6f6e6500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0200000000000000000000009cc4603089076d3f75e50e3d00000080eb04353f00000080fc04353f010000005043e30000322106426970303120466f6f74737465707300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004e6f6e6500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000088856cbf0000000000000080eb0435bf00000080fc04353f010000005043e3000032";

// hex string → NativePointer buffer
var targetHeader = Memory.alloc(512);
for (var i = 0; i < targetHeaderHex.length; i += 2) {
    var byte = parseInt(targetHeaderHex.substr(i, 2), 16);
    targetHeader.add(i / 2).writeU8(byte);
}

send({t: 'ready', msg: 'Header-only 替换就绪 (数据已嵌入). 进房间.'});

// ==========================================
// 2. 状态机
// ==========================================
var STATE_IDLE = 0;
var STATE_HEADER_REPLACED = 1;

var sskfState = STATE_IDLE;
var patchedHandle = 0;
var patchCount = 0;
var totalSSKF = 0;
var origHeaderSaved = null;  // 保存原始header用于对比

// ==========================================
// 3. Hook ReadFile
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.bytesToRead = args[2].toInt32();
        this.brPtr = args[3];
        this.handle = args[0].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;

        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 8) return;

            // === 状态: header已替换, 等待第二次读取 ===
            if (sskfState === STATE_HEADER_REPLACED && this.handle === patchedHandle) {
                // 第二次读取(100KB+), 不修改mesh
                // 但记录一下原始header和第二次读取的开头
                var secondName = '';
                for (var i = 8; i < 72; i++) {
                    var c = this.buf.add(i).readU8();
                    if (c === 0) break;
                    secondName += String.fromCharCode(c);
                }
                send({t: 'second_read', size: bytesRead, name: secondName,
                      firstByte: this.buf.readU8()});

                // 注意: 这次不替换, 只观察
                sskfState = STATE_IDLE;
                patchedHandle = 0;
                return;
            }

            // === 检查SSKF magic ===
            var b0 = this.buf.readU8();
            var b1 = this.buf.add(1).readU8();
            var b2 = this.buf.add(2).readU8();
            var b3 = this.buf.add(3).readU8();
            if (b0 !== 0x53 || b1 !== 0x53 || b2 !== 0x4B || b3 !== 0x46) return;

            totalSSKF++;

            // 读文件名
            var name = '';
            for (var i = 8; i < 72; i++) {
                var c = this.buf.add(i).readU8();
                if (c === 0) break;
                name += String.fromCharCode(c);
            }

            if (totalSSKF <= 30) {
                send({t: 'sskf', n: totalSSKF, name: name, size: bytesRead});
            }

            // 检查目标
            if (name.indexOf('50125461_FN') < 0) return;

            send({t: 'target_sskf', name: name, size: bytesRead});

            // === 保存原始header对比 ===
            origHeaderSaved = Memory.alloc(512);
            Memory.copy(origHeaderSaved, this.buf, 512);

            // === 替换Header ===
            Memory.copy(this.buf, targetHeader, 512);

            // 读回确认
            var newName = '';
            for (var i = 8; i < 72; i++) {
                var c = this.buf.add(i).readU8();
                if (c === 0) break;
                newName += String.fromCharCode(c);
            }

            // 关键字段对比
            var origBoneCount = origHeaderSaved.add(0x114).readU32();
            var newBoneCount = this.buf.add(0x114).readU32();
            var origFlag = origHeaderSaved.add(0x48).readU8();
            var newFlag = this.buf.add(0x48).readU8();

            sskfState = STATE_HEADER_REPLACED;
            patchedHandle = this.handle;
            patchCount++;

            send({
                t: 'header_replaced',
                newName: newName,
                origBoneCount: origBoneCount,
                newBoneCount: newBoneCount,
                origFlag: origFlag,
                newFlag: newFlag
            });

        } catch(e) {
            send({t: 'error', msg: 'ReadFile hook: ' + e});
        }
    }
});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            totalSSKF: totalSSKF,
            patches: patchCount,
            state: sskfState === STATE_IDLE ? 'idle' : 'header_replaced'
        });
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
    log(f'=== Header-only 替换测试 === PID:{pid} ===')
    log(f'策略: 只替换512B SSKF header, 不动mesh')
    log(f'目标: i50125461_FN.smd header → i50125711_FN.smd header')
    log(f'目的: 验证游戏是否从header读取骨骼数/flag等元数据')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'sskf':
                if p['n'] <= 20:
                    log(f'  [SSKF #{p["n"]}] "{p["name"]}" ({p["size"]}B)')
            elif t == 'target_sskf':
                log(f'  [目标SSKF] "{p["name"]}" ({p["size"]}B)')
            elif t == 'header_replaced':
                log(f'  [Header替换] "{p["newName"]}"')
                log(f'    骨骼数: {p["origBoneCount"]} → {p["newBoneCount"]}')
                log(f'    flag:   {p["origFlag"]} → {p["newFlag"]}')
            elif t == 'second_read':
                log(f'  [第二次读取] {p["size"]}B name="{p["name"]}" first=0x{p["firstByte"]:02x}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()
