"""
dump_constructor.py — 反汇编描述符构造函数，找 ItemCode 写入位置
"""
import frida, json, sys

JS_CODE = r"""
'use strict';

rpc.exports = {
    disasm: function() {
        var results = [];
        var refs = [
            ptr('0x1c2a041'),  // mov [edx], vtable
            ptr('0x1f1bf4a'),  // mov [eax], vtable
            ptr('0x1f1bf7a')   // mov [eax], vtable
        ];
        
        for (var i = 0; i < refs.length; i++) {
            var start = refs[i].sub(0x40); // 从 vtable 写入前 0x40 开始
            var instructions = [];
            var addr = start;
            for (var j = 0; j < 120; j++) {
                try {
                    var insn = Instruction.parse(addr);
                    instructions.push({
                        addr: addr.toString(),
                        mnemonic: insn.mnemonic,
                        opStr: insn.opStr,
                        size: insn.size
                    });
                    addr = addr.add(insn.size);
                } catch(e) {
                    instructions.push({addr: addr.toString(), raw: 'parse error'});
                    addr = addr.add(1);
                }
            }
            results.push({ref: refs[i].toString(), instructions: instructions});
        }
        return JSON.stringify(results);
    }
};
""";

pid = int(sys.argv[1])
session = frida.attach(pid)
script = session.create_script(JS_CODE)
script.load()

data = json.loads(script.exports_sync.disasm())
for entry in data:
    print(f"\n{'='*60}")
    print(f"Constructor near {entry['ref']}")
    print(f"{'='*60}")
    for insn in entry['instructions']:
        marker = ""
        if '0x027fcea0' in insn.get('opStr','').lower() or '0x27fcea0' in insn.get('opStr',''):
            marker = "  <<< VT WRITE"
        if '60' in insn.get('opStr','') and ('mov' in insn.get('mnemonic','')):
            marker += "  <<< +0x060?"
        print(f"  {insn['addr']}:  {insn.get('mnemonic','?'):8s} {insn.get('opStr','')}  {marker}")

session.detach()
