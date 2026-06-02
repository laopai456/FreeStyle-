"""
hook_readfile_replace.py — ReadFile buffer 替换 v2
策略:
  1. Python端读取目标SSKF数据, 通过script.load()后send传给JS
  2. Hook ReadFile, 检测原始发型的SSKF数据
  3. 替换header (512B, 等长安全)
  4. 替换mesh (尽量填入, 目标270KB vs 原始100KB)
  5. 状态机跟踪 header→mesh 读取序列

前置: sc.exe stop ApolloProtect
数据文件: C:\tmp\sskf\sskf_50125711_header.bin + sskf_50125711_mesh.bin
"""
import sys, os, time, json
import frida
import base64

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'readfile_replace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

# 数据文件路径 (ASCII路径, 避免Frida File API中文问题)
DATA_DIR = r'C:\tmp\sskf'
HEADER_FILE = os.path.join(DATA_DIR, 'sskf_50125711_header.bin')
MESH_FILE = os.path.join(DATA_DIR, 'sskf_50125711_mesh.bin')

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

def load_and_send_data(script):
    """Python端读取数据文件, base64编码后send给JS"""
    header_b64 = ''
    mesh_b64 = ''

    if os.path.exists(HEADER_FILE):
        with open(HEADER_FILE, 'rb') as f:
            header_b64 = base64.b64encode(f.read()).decode('ascii')
        log(f'  Header: {HEADER_FILE} ({len(header_b64)} chars b64)')
    else:
        log(f'  [错误] {HEADER_FILE} 不存在')

    if os.path.exists(MESH_FILE):
        with open(MESH_FILE, 'rb') as f:
            mesh_b64 = base64.b64encode(f.read()).decode('ascii')
        log(f'  Mesh: {MESH_FILE} ({len(mesh_b64)} chars b64)')
    else:
        log(f'  [错误] {MESH_FILE} 不存在')

    # 分块发送mesh (base64太大, 分段)
    CHUNK = 60000  # 每段60KB base64
    script.post({'type': 'load_header', 'data': header_b64})

    total_chunks = (len(mesh_b64) + CHUNK - 1) // CHUNK
    for i in range(total_chunks):
        chunk = mesh_b64[i*CHUNK:(i+1)*CHUNK]
        script.post({'type': 'load_mesh_chunk', 'idx': i, 'total': total_chunks, 'data': chunk})

    log(f'  数据已发送: header({len(header_b64)}) + mesh({total_chunks} chunks)')


JS_CODE = r"""
'use strict';

var base = Process.getModuleByName('FreeStyle.exe').base;

// ==========================================
// 1. 数据缓冲区
// ==========================================
var targetHeader = null;   // NativePointer
var targetHeaderSize = 0;
var targetMesh = null;     // NativePointer
var targetMeshSize = 0;
var meshChunksReceived = 0;
var meshChunksTotal = 0;
var meshChunks = [];       // 收集base64 chunks

// 接收Python发送的数据
recv('load_header', function(msg) {
    var bytes = base64Decode(msg.data);
    targetHeader = Memory.alloc(bytes.length);
    Memory.writeByteArray(targetHeader, bytes);
    targetHeaderSize = bytes.length;
    send({t: 'loaded', part: 'header', size: targetHeaderSize});
});

recv('load_mesh_chunk', function(msg) {
    var bytes = base64Decode(msg.data);
    meshChunks.push(bytes);
    meshChunksReceived++;

    if (meshChunksReceived >= msg.total) {
        // 合并所有chunks
        var totalSize = 0;
        for (var i = 0; i < meshChunks.length; i++) {
            totalSize += meshChunks[i].length;
        }
        targetMesh = Memory.alloc(totalSize);
        var offset = 0;
        for (var i = 0; i < meshChunks.length; i++) {
            Memory.writeByteArray(targetMesh.add(offset), meshChunks[i]);
            offset += meshChunks[i].length;
        }
        targetMeshSize = totalSize;
        meshChunks = [];  // 释放
        send({t: 'loaded', part: 'mesh', size: targetMeshSize});
    }
});

function base64Decode(str) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var result = [];
    var i = 0;
    str = str.replace(/=/g, '');
    while (i < str.length) {
        var a = chars.indexOf(str.charAt(i++));
        var b = chars.indexOf(str.charAt(i++));
        var c = (i <= str.length) ? chars.indexOf(str.charAt(i++)) : -1;
        var d = (i <= str.length) ? chars.indexOf(str.charAt(i++)) : -1;
        var triple = (a << 18) | (b << 12) | ((c >= 0 ? c : 0) << 6) | (d >= 0 ? d : 0);
        result.push((triple >> 16) & 0xFF);
        if (c >= 0) result.push((triple >> 8) & 0xFF);
        if (d >= 0) result.push(triple & 0xFF);
    }
    return result;
}

// ==========================================
// 2. 状态机
// ==========================================
var STATE_IDLE = 0;
var STATE_HEADER_REPLACED = 1;

var sskfState = STATE_IDLE;
var patchedHandle = 0;
var patchCount = 0;
var totalSSKF = 0;

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

            // === 状态机: HEADER_REPLACED → 等待第二次读取 ===
            if (sskfState === STATE_HEADER_REPLACED) {
                if (this.handle === patchedHandle) {
                    // 第二次读取: 游戏从头读整个文件(100KB+), 包含header+mesh
                    // 我们需要写入: targetHeader(512B) + targetMesh(尽可能多)
                    var totalTargetSize = targetHeaderSize + targetMeshSize;
                    var writeSize = Math.min(totalTargetSize, bytesRead);

                    send({t: 'full_read', size: bytesRead, bufSize: this.bytesToRead,
                          targetTotal: totalTargetSize});

                    if (targetHeader && targetMesh) {
                        // 写入header部分 (前512B)
                        var headerCopy = Math.min(targetHeaderSize, writeSize);
                        Memory.copy(this.buf, targetHeader, headerCopy);

                        // 写入mesh部分 (512B之后)
                        var meshWrite = Math.min(targetMeshSize, writeSize - headerCopy);
                        if (meshWrite > 0) {
                            Memory.copy(this.buf.add(headerCopy), targetMesh, meshWrite);
                        }

                        patchCount++;
                        if (writeSize >= totalTargetSize) {
                            send({t: 'mesh_replaced', method: 'full', written: writeSize});
                        } else {
                            send({t: 'mesh_replaced', method: 'partial', written: writeSize,
                                  targetTotal: totalTargetSize, truncated: totalTargetSize - writeSize});
                        }
                    }

                    sskfState = STATE_IDLE;
                    patchedHandle = 0;
                    return;
                }
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

            // 检查是否是目标发型
            if (name.indexOf('50125461_FN') < 0) return;

            send({t: 'target_sskf', name: name, size: bytesRead});

            // === 替换Header ===
            if (targetHeader && targetHeaderSize === 512 && bytesRead >= 512) {
                Memory.copy(this.buf, targetHeader, 512);

                // 读回确认
                var newName = '';
                for (var i = 8; i < 72; i++) {
                    var c = this.buf.add(i).readU8();
                    if (c === 0) break;
                    newName += String.fromCharCode(c);
                }

                sskfState = STATE_HEADER_REPLACED;
                patchedHandle = this.handle;
                patchCount++;
                send({t: 'header_replaced', newName: newName});
            }

        } catch(e) {
            send({t: 'error', msg: 'ReadFile hook错误: ' + e});
        }
    }
});

// ==========================================
// 4. SSKF诊断 (所有文件前20个)
// ==========================================

send({t: 'ready', msg: 'ReadFile buffer替换v2就绪 (Python送数据). 等待数据加载后进房间.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            totalSSKF: totalSSKF,
            patches: patchCount,
            state: sskfState === STATE_IDLE ? 'idle' : 'header_replaced',
            dataLoaded: targetHeaderSize > 0 && targetMeshSize > 0
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
    log(f'=== ReadFile Buffer 替换v2 === PID:{pid} ===')
    log(f'策略: Python读数据→base64→send给JS→Memory.copy替换')
    log(f'目标: i50125461_FN.smd → i50125711_FN.smd')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'loaded':
                log(f'  数据加载: {p["part"]}={p["size"]}B')
            elif t == 'sskf':
                if p['n'] <= 20:
                    log(f'  [SSKF #{p["n"]}] "{p["name"]}" ({p["size"]}B)')
            elif t == 'target_sskf':
                log(f'  [目标SSKF] "{p["name"]}" ({p["size"]}B)')
            elif t == 'header_replaced':
                log(f'  [Header替换 ✓] → "{p["newName"]}"')
            elif t == 'mesh_read':
                log(f'  [Mesh读取] buf={p["bufSize"]}B read={p["size"]}B target={p["targetMeshSize"]}B')
            elif t == 'mesh_replaced':
                if p['method'] == 'full':
                    log(f'  [Mesh替换 ✓] 完整 {p["written"]}B')
                else:
                    log(f'  [Mesh替换 ⚠] 部分 {p["written"]}B/{p["targetTotal"]}B (缺{p["truncated"]}B)')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    # 等待脚本就绪后发送数据
    time.sleep(0.5)
    log('  发送目标数据到JS...')
    load_and_send_data(script)
    time.sleep(0.5)

    # 确认数据加载
    status = json.loads(script.exports_sync.status())
    log(f'  状态: dataLoaded={status.get("dataLoaded", False)}')

    log('')
    log('数据已加载, 进房间触发角色加载。')
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
