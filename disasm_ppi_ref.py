"""
disasm_ppi_ref.py — 反汇编 0x02371B55 附近 (唯一引用 .ppi 的代码)
"""
import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    disasm: function() {
        var target = ptr(0x02371B55);
        var funcStart = null;
        for (var back = 0; back < 0x200; back++) {
            try {
                var addr = target.sub(back);
                var b0 = addr.readU8();
                var b1 = addr.add(1).readU8();
                if (b0 === 0x55 && b1 === 0x8B) {
                    funcStart = addr;
                    break;
                }
            } catch(e) {}
        }
        var results = [];
        var addr = funcStart || target.sub(0x40);
        for (var i = 0; i < 200; i++) {
            try {
                var insn = Instruction.parse(addr);
                var mark = '';
                if (insn.mnemonic === 'call') mark += ' [CALL]';
                if (insn.mnemonic === 'ret') mark += ' [RET]';
                if (insn.mnemonic === 'push' && insn.opStr.indexOf('0x0284') === 0) mark += ' [PUSH .ppi]';
                results.push({addr: addr.toString(), mn: insn.mnemonic, op: insn.opStr, mark: mark});
                addr = addr.add(insn.size);
                if (insn.mnemonic === 'ret' && i > 20) break;
            } catch(e) {
                results.push({addr: addr.toString(), mn: '??', op: '', mark: ''});
                addr = addr.add(1);
            }
        }
        return JSON.stringify({funcStart: funcStart ? funcStart.toString() : 'not found', insns: results});
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

session = frida.attach(pid)
script = session.create_script(JS)
script.load()
data = json.loads(script.exports_sync.disasm())

outpath = r"D:\py\反编译\FreeStyle\disasm_ppi_ref.txt"
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(f"Function start: {data['funcStart']}\n\n")
    for ins in data['insns']:
        f.write(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{ins['mark']}\n")

print(f"Written to {outpath} ({len(data['insns'])} insns)")
session.detach()
