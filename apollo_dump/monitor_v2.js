'use strict';
// monitor_v2.js — 监控 PAK 文件加载 + BML 读取
// 双重 hook: CreateFileW + CreateFileMappingW + ReadFile

try { send({type:'info', msg:'v2 start'}); } catch(e) {}

function hookCreateFileW() {
    var p = Module.findExportByName('kernel32.dll', 'CreateFileW');
    if (!p) return send({type:'err', msg:'CreateFileW not found'});
    Interceptor.attach(p, {
        onEnter: function(args) {
            this.path = args[0].readUtf16String();
        },
        onLeave: function(ret) {
            if (!this.path) return;
            if (this.path.indexOf('item767') >= 0 || this.path.indexOf('.pak') >= 0) {
                send({type:'file_open', path: this.path, handle: ret.toInt32()});
            }
        }
    });
    send({type:'info', msg:'CreateFileW hook OK'});
}

function hookCreateFileMappingW() {
    var p = Module.findExportByName('kernel32.dll', 'CreateFileMappingW');
    if (!p) return;
    Interceptor.attach(p, {
        onEnter: function(args) {
            var hFile = args[0].toInt32();
            if (hFile !== 0xFFFFFFFF && hFile !== 0) {
                this.hFile = hFile;
            }
        },
        onLeave: function(ret) {
            if (!this.hFile) return;
            send({type:'info', msg:'CreateFileMappingW called, handle=' + this.hFile});
        }
    });
    send({type:'info', msg:'CreateFileMappingW hook OK'});
}

function hookMapViewOfFile() {
    var p = Module.findExportByName('kernel32.dll', 'MapViewOfFile');
    if (!p) return;
    Interceptor.attach(p, {
        onEnter: function(args) {
            this.hMap = args[0].toInt32();
        },
        onLeave: function(ret) {
            if (ret.isNull()) return;
            send({type:'info', msg:'MapViewOfFile -> ' + ret});
        }
    });
    send({type:'info', msg:'MapViewOfFile hook OK'});
}

function hookReadFile() {
    var p = Module.findExportByName('kernel32.dll', 'ReadFile');
    if (!p) return send({type:'err', msg:'ReadFile not found'});
    
    Interceptor.attach(p, {
        onEnter: function(args) {
            this.buf = args[1];
            this.bytes = args[3];
            this.handle = args[0].toInt32();
        },
        onLeave: function(ret) {
            if (ret.toInt32() === 0) return;
            try {
                var n = this.bytes.readU32();
                if (n < 50 || n > 20000) return;
                var buf = new Uint8Array(this.buf.readByteArray(n));
                // Check for BML (XOR 0xFF, starts with <root>)
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
                var icMatch = text.match(/i(\d{6,8})/);
                var ic = icMatch ? icMatch[1] : '';
                var meshPaths = [];
                var re = /<mesh>([^<]+)<\/mesh>/g, m;
                while ((m = re.exec(text)) !== null) meshPaths.push(m[1]);
                
                send({
                    type: 'bml', handle: this.handle,
                    size: n, itemcode: ic, mesh_paths: meshPaths
                });
            } catch(e) {}
        }
    });
    send({type:'info', msg:'ReadFile hook OK'});
}

hookCreateFileW();
hookCreateFileMappingW();
hookMapViewOfFile();
hookReadFile();

send({type:'info', msg:'Monitor v2 ready. Trigger character/equip load.'});
