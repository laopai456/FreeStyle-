import frida, json, sys

JS = r"""
'use strict';
var g_patchSrcIC = 0;
var g_patchDstIC = 0;

function hex(buf) {
    var arr = new Uint8Array(buf);
    var s = '';
    for (var i = 0; i < arr.length; i++) s += ('0' + arr[i].toString(16)).slice(-2) + ' ';
    return s.trim();
}

rpc.exports = {
    findstart: function() {
        var addr = ptr('0x1c2a001');
        var results = [];
        for (var i = 0; i < 80; i++) {
            var check = addr.sub(i);
            try {
                var b0 = check.readU8();
                if (b0 === 0x55) {
                    var b1 = check.add(1).readU8();
                    var b2 = check.add(2).readU8();
                    if (b1 === 0x8B && b2 === 0xEC) {
                        results.push({
                            addr: check.toString(),
                            offset: i,
                            bytes: hex(check.readByteArray(Math.min(12, 80-i)))
                        });
                    }
                }
            } catch(e) {}
        }
        return JSON.stringify(results);
    }
};
""";

pid = int(sys.argv[1])
session = frida.attach(pid)
script = session.create_script(JS)

def on_msg(msg, data):
    print(f"  [FRIDA] {msg}")
script.on('message', on_msg)
script.load()

results = json.loads(script.exports_sync.findstart())
print("Function prologue candidates:")
for r in results:
    print(f"  {r['addr']}  (0x1c2a001 - {r['offset']})  bytes: {r['bytes']}")

session.detach()
