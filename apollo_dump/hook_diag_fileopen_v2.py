"""
hook_diag_fileopen_v2.py — 诊断文件打开函数(0x1ACDF33)的Group逻辑
只hook函数入口点，不hook函数中间地址
关键: 读取 this->0x7E4 / this->0x7E8 看Group值，找出BML查找路径

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_fileopen2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767)
DST_IC = 50125711  # 紫色超赛发型 (pak768)

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

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function readHex(buf, len) {
    var s = '';
    for (var i = 0; i < len; i++) {
        s += ('0' + buf.add(i).readU8().toString(16)).slice(-2) + ' ';
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});
var base = ptr('0x400000');
var patchCount = 0;

// ==========================================
// 1. Hook LoadItemFile入口 (RVA 0x1ACE1C0)
// ==========================================
var loadItemFileAddr = base.add(0x1ACE1C0);
var lifCount = 0;

Interceptor.attach(loadItemFileAddr, {
    onEnter: function(args) {
        var iItemCode = args[0].toInt32();
        var szFilename = readAscii(args[1], 80);
        lifCount++;
        send({t: 'lif', n: lifCount, ic: iItemCode, fname: szFilename,
              ecx: this.context.ecx.toString()});
    }
});
send({t: 'step', msg: 'LoadItemFile hook已设置'});

// ==========================================
// 2. Hook 文件打开函数入口 (RVA 0x1ACDF33)
//    thiscall: ecx=this, [esp+4]=&iItemCode, [esp+8]=flag
//    内部: flag==0 → group=this->0x7E4, flag!=0 → group=this->0x7E8
// ==========================================
var fileOpenFunc = base.add(0x1ACDF33);
var fofCount = 0;

Interceptor.attach(fileOpenFunc, {
    onEnter: function(args) {
        var retAddr = this.returnAddress;
        var retOffset = retAddr.sub(base).toInt32();

        // 读取参数
        var pItemCodePtr = args[0];
        var flag = args[1].toInt32();
        var thisPtr = this.context.ecx;

        // 读this->0x7E4和this->0x7E8 (可能是Group字符串指针或ID)
        var group7E4 = 0, group7E8 = 0;
        var group7E4_str = '', group7E8_str = '';
        try { group7E4 = thisPtr.add(0x7E4).readU32(); } catch(e) {}
        try { group7E8 = thisPtr.add(0x7E8).readU32(); } catch(e) {}
        try { group7E4_str = readAscii(thisPtr.add(0x7E4).readPointer(), 32); } catch(e) {}
        try { group7E8_str = readAscii(thisPtr.add(0x7E8).readPointer(), 32); } catch(e) {}

        // *(&iItemCode)
        var itemCode = 0;
        try { itemCode = pItemCodePtr.readU32(); } catch(e) {}

        this._itemCode = itemCode;
        this._retAddr = retOffset;
        this._flag = flag;

        fofCount++;
        // 只输出来自LoadItemFile的调用(RA在0x1ACE30D附近)或前几次
        var fromLIF = (retOffset >= 0x1ACE1C0 && retOffset <= 0x1ACE400);
        if (fromLIF || fofCount <= 5) {
            send({t: 'fof_enter', n: fofCount, ic: itemCode, flag: flag,
                  ra: '0x' + retOffset.toString(16),
                  thisPtr: thisPtr.toString(),
                  g7E4: group7E4, g7E8: group7E8,
                  g7E4s: group7E4_str, g7E8s: group7E8_str,
                  fromLIF: fromLIF});
        }
    },
    onLeave: function(retval) {
        var ret = retval.toInt32();
        var fromLIF = (this._retAddr >= 0x1ACE1C0 && this._retAddr <= 0x1ACE400);
        if (fromLIF || fofCount <= 5) {
            send({t: 'fof_leave', ic: this._itemCode || 0,
                  ret: ret, ok: ret !== 0});
        }
    }
});
send({t: 'step', msg: '文件打开函数(0x1ACDF33) hook已设置'});

// ==========================================
// 3. Dump 0x1ACDF33前96字节 — 确认反汇编
// ==========================================
try {
    var fofBytes = new Uint8Array(fileOpenFunc.readByteArray(96));
    var lines = [];
    for (var i = 0; i < 96; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < 96; j++) {
            hex += ('0' + fofBytes[i + j].toString(16)).slice(-2) + ' ';
        }
        lines.push('0x' + (0x1ACDF33 + i).toString(16) + ': ' + hex);
    }
    send({t: 'code', label: 'FileOpenFunc', lines: lines});
} catch(e) {
    send({t: 'error', msg: 'dump failed: ' + e});
}

// ==========================================
// 4. sprintf + [ebp-0xD8] 双重替换
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;
            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);
                patchCount++;
                send({t: 'patched', n: patchCount});
            }
        } catch(e) {}
    }
});

// ==========================================
// 5. AcquireSMD监控
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;
Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            if (path.indexOf('50125') >= 0 || path.indexOf('768') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '文件打开诊断v2就绪 — 只hook函数入口'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, lifs: lifCount,
                               fofs: fofCount, acquires: acquireCount});
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
    log(f'=== 文件打开诊断v2 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'lif':
                log(f'  [LoadItemFile] #{p["n"]} ic={p["ic"]} '
                    f'fname="{p["fname"]}" ecx={p["ecx"]}')
            elif t == 'fof_enter':
                lif_tag = ' ←LIF' if p.get('fromLIF') else ''
                log(f'  [FileOpen] #{p["n"]} ic={p["ic"]} flag={p["flag"]} '
                    f'ra={p["ra"]} this={p["thisPtr"]}{lif_tag}')
                log(f'    group7E4=0x{p["g7E4"]:X}("{p["g7E4s"]}") '
                    f'group7E8=0x{p["g7E8"]:X}("{p["g7E8s"]}")')
            elif t == 'fof_leave':
                ok = '成功' if p['ok'] else '失败!'
                log(f'  [FileOpen返回] ic={p["ic"]} ret={p["ret"]} {ok}')
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}"')
            elif t == 'code':
                log(f'  [代码] {p["label"]}:')
                for line in p['lines']:
                    log(f'    {line}')
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
            if cmd in ('quit', 'q', 'exit'):
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
