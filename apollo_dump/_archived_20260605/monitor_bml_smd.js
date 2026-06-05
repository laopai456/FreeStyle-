// monitor_bml_smd.js — 监控BML读取和SMD加载
// 用法: py monitor_bml_smd.py 50125461  # 美丽梦想发型(pak767)
var TARGET_IC = '__TARGET_IC__';

try { send({type:'info', msg:'JS start'}); } catch(e) {}

// === Part1: Hook ReadFile ===
try {
    // 不同Frida版本API不同，都试一下
    var pReadFile = null;
    try { pReadFile = Module.findExportByName('kernel32.dll', 'ReadFile'); } catch(e) {}
    if (!pReadFile) {
        try { pReadFile = Process.getModuleByName('kernel32.dll').findExportByName('ReadFile'); } catch(e) {}
    }
    if (!pReadFile) {
        try { pReadFile = Module.getExportByName('kernel32.dll', 'ReadFile'); } catch(e) {}
    }
    send({type:'info', msg:'ReadFile addr: ' + pReadFile});

    if (!pReadFile) throw new Error('Cannot resolve ReadFile');

    Interceptor.attach(pReadFile, {
        onEnter: function(args) {
            this.lpBuffer = args[1];
            this.lpBytesRead = args[3];
        },
        onLeave: function(retval) {
            if (retval.toInt32() === 0) return;
            try {
                var n = this.lpBytesRead.readU32();
                if (n < 50 || n > 10000) return;

                var buf = new Uint8Array(this.lpBuffer.readByteArray(n));

                // XOR 0xFF, 检查 <root>
                var ok = true;
                var tag = [0x3C,0x72,0x6F,0x6F,0x74,0x3E];
                for (var i = 0; i < 6; i++) {
                    if ((buf[i] ^ 0xFF) !== tag[i]) { ok = false; break; }
                }
                if (!ok) return;

                var text = '';
                for (var i = 0; i < n; i++) {
                    var c = buf[i] ^ 0xFF;
                    if (c >= 0x20 && c < 0x7F) text += String.fromCharCode(c);
                    else if (c === 0x0A || c === 0x0D) text += '\n';
                }

                var meshPaths = [];
                var re = /<mesh>([^<]+)<\/mesh>/g, m;
                while ((m = re.exec(text)) !== null) meshPaths.push(m[1]);

                var icMatch = text.match(/i(\d{6,8})/);
                var ic = icMatch ? icMatch[1] : '';
                if (TARGET_IC && ic !== TARGET_IC) return;

                send({
                    type: 'bml_read',
                    size: n,
                    itemcode: ic,
                    mesh_paths: meshPaths,
                    preview: text.substring(0, 300)
                });
            } catch(e) {
                send({type:'error', msg:'ReadFile leave: ' + e});
            }
        }
    });
    send({type:'info', msg:'ReadFile hook OK'});
} catch(e) {
    send({type:'error', msg:'ReadFile hook FAIL: ' + e.message + ' | stack: ' + e.stack});
}

// AcquireSMD hook 已禁用 — 栈扫描会导致崩溃

send({type:'info', msg:'Monitor ready'});
