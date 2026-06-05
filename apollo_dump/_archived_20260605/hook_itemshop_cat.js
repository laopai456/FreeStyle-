// hook_itemshop_cat.js — Hook ReadFile修改itemshop中50125461的category
// 给美丽梦想加上category=2147(同紫色超赛)，看是否变成动态
var SRC_CODE = '50125461';
var SRC_LINE = '50125461\t767\t\t';  // 原始行: itemcode\tpak\tcat\t(空category)
var DST_LINE = '50125461\t767\t2147\t'; // 改category为2147

function resolveExport(dll, name) {
    var addr = null;
    try { addr = Module.findExportByName(dll, name); } catch(e) {}
    if (!addr) try { addr = Process.getModuleByName(dll).findExportByName(name); } catch(e) {}
    if (!addr) try { addr = Module.getExportByName(dll, name); } catch(e) {}
    return addr;
}

(function() {
    var addr = resolveExport('kernel32.dll', 'ReadFile');
    if (!addr) { send({type:'error', msg:'ReadFile not found'}); return; }
    send({type:'info', msg:'ReadFile @ ' + addr});

    Interceptor.attach(addr, {
        onEnter: function(args) {
            this.lpBuffer = args[1];
            this.lpBytesRead = args[3];
        },
        onLeave: function(retval) {
            if (retval.toInt32() === 0) return;
            try {
                var n = this.lpBytesRead.readU32();
                if (n < 100 || n > 200000) return;

                var buf = new Uint8Array(this.lpBuffer.readByteArray(n));

                // GBK编码搜索 "50125461\t767\t\t"
                // GBK中 \t = 0x09, 数字是ASCII
                var srcBytes = [];
                for (var i = 0; i < SRC_LINE.length; i++) {
                    srcBytes.push(SRC_LINE.charCodeAt(i));
                }

                // 在buffer中搜索
                for (var pos = 0; pos <= n - srcBytes.length; pos++) {
                    var match = true;
                    for (var j = 0; j < srcBytes.length; j++) {
                        if (buf[pos + j] !== srcBytes[j]) { match = false; break; }
                    }
                    if (match) {
                        // 找到！替换为新的category
                        var dstBytes = [];
                        for (var i = 0; i < DST_LINE.length; i++) {
                            dstBytes.push(DST_LINE.charCodeAt(i));
                        }
                        // 长度差异: 原始 "50125461\t767\t\t" (14 bytes)
                        //        目标 "50125461\t767\t2147\t" (18 bytes)
                        // 多了4字节 "2147"，需要把后面的数据往后移
                        // 但ReadFile buffer大小固定，不能扩展
                        // 方案：不改长度，把category填入原本为空的字段
                        // 原始: 50125461\t767\t\tname...
                        //       0123456789012345
                        // 目标: 50125461\t767\t2147name...
                        // 不行，会覆盖name的第一个字符

                        // 改思路：只在原地改 \t\t 为 2147\t 不好扩展
                        // 用空格填充：把空的category改成2147，把后面的内容左移
                        // 但这太复杂了

                        // 最简单：如果category后面是\t，那原始是\t\t(两个tab)
                        // 改成\t2147（一个tab+2147），长度从2变5，多3字节
                        // 后面数据要移3字节，但buffer可能不够大

                        // 看看实际buffer够不够
                        send({type:'info', msg:'Found itemshop line for ' + SRC_CODE + ' at buf+' + pos + ', total=' + n + ', remaining=' + (n - pos)});

                        // 暴力方案：直接在原地写入2147，覆盖后面的tab和name的第一个字符
                        // 不可行，会破坏数据

                        // 正确方案：找到行尾\n，整行替换
                        // 先找行尾
                        var lineEnd = -1;
                        for (var k = pos; k < n; k++) {
                            if (buf[k] === 0x0A) { lineEnd = k; break; }
                        }
                        if (lineEnd === -1) lineEnd = pos + 100;

                        var origLine = '';
                        for (var k = pos; k < lineEnd; k++) {
                            origLine += String.fromCharCode(buf[k]);
                        }
                        send({type:'info', msg:'Original line: ' + origLine});

                        // 不修改了，先只观察
                        break;
                    }
                }
            } catch(e) {
                send({type:'error', msg:'ReadFile: ' + e});
            }
        }
    });
})();

send({type:'info', msg:'Ready — monitoring itemshop loading'});
