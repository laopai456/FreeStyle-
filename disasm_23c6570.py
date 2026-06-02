"""
disasm_23c6570.py — 反汇编 0x23c6570 (装包装包函数), 找 ItemCode 来源
结果写入 disasm_23c6570.txt
"""
import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    disasm: function() {
        var target = ptr(0x23c6570);
        var results = [];
        var addr = target;
        var retCount = 0;
        for (var i = 0; i < 500; i++) {
            try {
                var insn = Instruction.parse(addr);
                var mark = '';
                if (insn.mnemonic === 'call') mark += ' [CALL]';
                if (insn.mnemonic === 'ret') { mark += ' [RET]'; retCount++; }
                if (retCount >= 2) { results.push({addr: addr.toString(), mn: insn.mnemonic, op: insn.opStr, size: insn.size, mark: mark}); break; }
                if (insn.mnemonic === 'jmp' && insn.opStr.indexOf('0x') === 0) mark += ' [JMP]';
                results.push({addr: addr.toString(), mn: insn.mnemonic, op: insn.opStr, size: insn.size, mark: mark});
                addr = addr.add(insn.size);
            } catch(e) {
                results.push({addr: addr.toString(), mn: '??', op: '', size: 1, mark: ''});
                addr = addr.add(1);
            }
        }
        return JSON.stringify({count: results.length, insns: results});
    }
};
""";

pid = None
import subprocess
r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                   capture_output=True, text=True)
for line in r.stdout.strip().split('\n'):
    parts = line.strip().split()
    if len(parts) >= 2 and parts[1].isdigit():
        pid = int(parts[1])
        break

if not pid:
    print("FreeStyle.exe not found"); sys.exit(1)

print(f"PID={pid}")
session = frida.attach(pid)
script = session.create_script(JS)
script.load()

data = json.loads(script.exports_sync.disasm())
outpath = r"D:\py\反编译\FreeStyle\disasm_23c6570.txt"
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(f"Disasm 0x23c6570 — {data['count']} instructions\n\n")
    for ins in data['insns']:
        f.write(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{ins['mark']}\n")

print(f"Written to {outpath} ({data['count']} insns)")
session.detach()
