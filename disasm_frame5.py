"""
disasm_frame5.py — 详细反汇编 frame #5 附近区域
"""
import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    dumprange: function(startStr, count) {
        var addr = ptr(startStr);
        var n = parseInt(count);
        var results = [];
        for (var i = 0; i < n; i++) {
            try {
                var insn = Instruction.parse(addr);
                var mark = '';
                if (insn.mnemonic === 'call') mark += ' [CALL]';
                if (insn.mnemonic === 'ret') mark += ' [RET]';
                if (insn.mnemonic === 'jmp' && insn.opStr.indexOf('0x1b9107f') !== -1) mark += ' [SWITCH_BREAK]';
                var op = insn.opStr;
                // ItemCode 相关偏移
                if (op.indexOf('+ 0x60') !== -1 || op.indexOf('+ 0x6c') !== -1 ||
                    op.indexOf('+ 0x64') !== -1 || op.indexOf('+ 0x68') !== -1) mark += ' [IC?]';

                results.push({
                    addr: addr.toString(),
                    mn: insn.mnemonic,
                    op: insn.opStr,
                    size: insn.size,
                    mark: mark
                });
                addr = addr.add(insn.size);
            } catch(e) {
                results.push({addr: addr.toString(), mn: '??', op: '', size: 1, mark: ''});
                addr = addr.add(1);
            }
        }
        return JSON.stringify(results);
    },

    // 读取 [ebp-0x45d8] 对象的字段
    readObject: function() {
        // 先找当前 ebp — 通过反汇编函数 prologue
        // 实际上我们 hook 这个函数时才能拿到 ebp
        // 这里改为读取 call 0x1922720 的参数设置区域
        // 先返回一些静态分析信息
        return JSON.stringify({note: 'need live hook for this'});
    }
};
""";

pid = int(sys.argv[1]) if len(sys.argv) > 1 else None
if not pid:
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            pid = int(parts[1])
            break

if not pid:
    print("FreeStyle.exe not found")
    sys.exit(1)

print(f"PID={pid}")
session = frida.attach(pid)
script = session.create_script(JS)
script.load()

# Dump 区域1: call 0x1922720 之前 0x100 字节 (参数设置)
print("\n=== Before call 0x1922720 (0x1b90dc0 - 0x1b90ed0) ===")
data = json.loads(script.exports_sync.dumprange('0x1b90dc0', '200'))
for ins in data:
    mark = ins.get('mark', '')
    print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{mark}")

# Dump 区域2: call 0x1922720 之后 (返回值处理)
print("\n=== After call 0x1922720 (0x1b90ed0 - 0x1b90f60) ===")
data2 = json.loads(script.exports_sync.dumprange('0x1b90ed0', '100'))
for ins in data2:
    mark = ins.get('mark', '')
    print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{mark}")

# Dump 区域3: switch case 入口 (找 case 分支如何跳到这里)
print("\n=== Switch dispatch area (0x1b9107f) ===")
data3 = json.loads(script.exports_sync.dumprange('0x1b9107f', '30'))
for ins in data3:
    mark = ins.get('mark', '')
    print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{mark}")

session.detach()
print("\nDone.")
