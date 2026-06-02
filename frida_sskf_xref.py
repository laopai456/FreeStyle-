"""
frida_sskf_xref.py — Frida + Python 同步扫描 SSKF 引用
用法: py frida_sskf_xref.py
"""
import frida, struct, sys

PID = 9248

def on_message(msg, data):
    if msg['type'] == 'send':
        print(msg['payload'])

# 1. 附到进程
session = frida.attach(PID)
print(f'[+] Attached to PID {PID}')

# 2. 用 Frida 的 Memory.scan (回调式)
scan_js = '''
'use strict';
rpc.exports = {
    scanSskf: function () {
        return new Promise(function(resolve, reject) {
            var results = [];
            var ranges = Process.enumerateRanges({protection: 'rwx'});
            var pending = ranges.length;
            if (pending === 0) { resolve([]); return; }
            
            for (var r of ranges) {
                Memory.scan(r.base, r.size, '53 53 4B 46', {
                    onMatch: function(addr, size) {
                        results.push({addr: addr.toString(), range: r.base.toString()});
                    },
                    onError: function(reason) {},
                    onComplete: function() {
                        pending--;
                        if (pending === 0) resolve(results);
                    }
                });
            }
        });
    },
    scanXref: function(addrStr) {
        return new Promise(function(resolve, reject) {
            var target = ptr(addrStr);
            var tv = target.toInt32();
            var hex = tv.toString(16).padStart(8, '0');
            var pattern = '';
            for (var i = 0; i < hex.length; i += 2)
                pattern += hex.substring(i, i+2) + ' ';
            pattern = pattern.trim();
            
            var results = [];
            var ranges = Process.enumerateRanges({protection: 'rwx'});
            var pending = ranges.length;
            if (pending === 0) { resolve([]); return; }
            
            for (var r of ranges) {
                Memory.scan(r.base, r.size, pattern, {
                    onMatch: function(addr, size) {
                        if (addr.equals(target)) return;
                        try {
                            var inst = Instruction.parse(addr);
                            results.push({addr: addr.toString(), inst: inst.toString()});
                        } catch(e) {
                            results.push({addr: addr.toString(), inst: '(data)'});
                        }
                    },
                    onError: function(reason) {},
                    onComplete: function() {
                        pending--;
                        if (pending === 0) resolve(results);
                    }
                });
            }
        });
    }
};
'''

script = session.create_script(scan_js)
script.load()

# 3. 扫描 SSKF
import time
print('[+] Scanning for SSKF in executable memory...')
results = script.exports.scan_sskf()
if not results:
    print('[-] SSKF not found in rwx ranges')
    # Also check r-- ranges (might be in .rdata)
else:
    print(f'[+] SSKF found at {len(results)} locations:')
    for r in results:
        print(f'    {r["addr"]} (range: {r["range"]})')

# 4. 用第一个 SSKF 地址搜交叉引用
if results:
    target_addr = results[0]['addr']
    print(f'\n[+] Scanning for xrefs to {target_addr}...')
    xrefs = script.exports.scan_xref(target_addr)
    print(f'[+] Found {len(xrefs)} xrefs:')
    for x in xrefs:
        print(f'    {x["addr"]}: {x["inst"]}')

script.unload()
session.detach()
