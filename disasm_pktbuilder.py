"""
disasm_pktbuilder.py — 反汇编包构造函数 0x1922720
找出它从 this 对象读取哪些字段来构造装备包

用法: py disasm_pktbuilder.py [pid]
"""
import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    dumppktbuilder: function() {
        var funcStart = ptr(0x1922700); // 已知入口
        var results = [];
        var addr = funcStart;
        for (var i = 0; i < 300; i++) {
            try {
                var insn = Instruction.parse(addr);
                var mark = '';
                if (insn.mnemonic === 'call') mark += ' [CALL]';
                if (insn.mnemonic === 'ret') mark += ' [RET]';
                if (insn.mnemonic === 'push' && insn.opStr.indexOf('0x17be') !== -1) mark += ' [MSGID=0x17BE]';
                if (insn.mnemonic === 'push' && insn.opStr.indexOf('0x17be') !== -1) mark += ' [MSGID=0x17BE]';

                results.push({
                    addr: addr.toString(),
                    mn: insn.mnemonic,
                    op: insn.opStr,
                    size: insn.size,
                    mark: mark
                });
                addr = addr.add(insn.size);
                // 在 ret 后停止 (函数结束)
                if (insn.mnemonic === 'ret' && i > 10) break;
            } catch(e) {
                results.push({addr: addr.toString(), mn: '??', op: '', size: 1, mark: ''});
                addr = addr.add(1);
            }
        }
        return JSON.stringify(results);
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

data = json.loads(script.exports_sync.dumppktbuilder())
print(f"\n=== Packet Builder 0x1922720 (func start 0x1922700) ===")
print(f"Instructions: {len(data)}\n")
for ins in data:
    print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{ins['mark']}")

session.detach()
print("\nDone.")
