"""
dump_equip_raw.py — Hook 0x23c6570, dump this 对象原始数据

不猜测结构, 直接 dump hex, 看数据长什么样。
结果写文件。
"""
import frida, json, sys, time

JS = r"""
'use strict';

function hdmp(addr, size) {
    var lines = [];
    for (var off = 0; off < size; off += 16) {
        var hex = '';
        var ascii = '';
        for (var i = 0; i < 16 && off+i < size; i++) {
            try {
                var b = addr.add(off+i).readU8();
                hex += ('0' + b.toString(16)).slice(-2) + ' ';
                ascii += (b >= 32 && b < 127) ? String.fromCharCode(b) : '.';
            } catch(e) {
                hex += '?? ';
                ascii += '?';
            }
        }
        lines.push('0x' + addr.add(off).toString(16) + ': ' + hex.padEnd(48) + ascii);
    }
    return lines.join('\n');
}

Interceptor.attach(ptr(0x23c6570), {
    onEnter: function(args) {
        var thisPtr = this.context.ecx;
        if (thisPtr.isNull()) return;

        var out = '=== 0x23c6570 this=' + thisPtr + ' ===\n';

        // dump this object (0x60 bytes)
        out += '\n--- this object ---\n';
        out += hdmp( thisPtr, 0x60);

        // this+4 and this+8
        try {
            var p4 = thisPtr.add(4).readPointer();
            var p8 = thisPtr.add(8).readPointer();
            out += '\n\n--- this+4 = ' + p4 + ' ---\n';
            if (!p4.isNull() && p4.compare(ptr(0x10000)) > 0) {
                out += hdmp( p4, 0x40);
            }
            out += '\n\n--- this+8 = ' + p8 + ' ---\n';
            if (!p8.isNull() && p8.compare(ptr(0x10000)) > 0) {
                out += hdmp( p8, 0x40);
            }

            // [[this+4]] - double deref
            try {
                var pp4 = p4.readPointer();
                out += '\n\n--- [this+4] = ' + pp4 + ' ---\n';
                if (!pp4.isNull() && pp4.compare(ptr(0x10000)) > 0) {
                    out += hdmp( pp4, 0x40);
                    // triple deref
                    try {
                        var ppp4 = pp4.readPointer();
                        out += '\n\n--- [[this+4]] = ' + ppp4 + ' ---\n';
                        if (!ppp4.isNull() && ppp4.compare(ptr(0x10000)) > 0) {
                            out += hdmp( ppp4, 0x40);
                        }
                    } catch(e) {}
                }
            } catch(e) {}

            // follow this+4 chain: try walking as linked list
            out += '\n\n--- Walking this+4 as linked list ---\n';
            var node = p4;
            for (var i = 0; i < 20; i++) {
                if (node.isNull() || node.compare(ptr(0x10000)) < 0) {
                    out += '  [' + i + '] null/invalid, stop\n';
                    break;
                }
                out += '\n  [' + i + '] node=' + node + '\n';
                out += hdmp( node, 0x30);

                // Try next = [node+4] or [node] depending on structure
                try {
                    var next = node.add(4).readPointer();
                    if (next.equals(node)) {
                        out += '\n  -> self-referencing, stop\n';
                        break;
                    }
                    node = next;
                } catch(e) {
                    out += '\n  -> read error, stop\n';
                    break;
                }
            }
        } catch(e) {
            out += '\nError: ' + e + '\n';
        }

        send(JSON.stringify({type:'DUMP', data: out}));
    }
});

send(JSON.stringify({type:'info', msg:'Hooked 0x23c6570 raw dump'}));
""";

def main():
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
        print("FreeStyle.exe not found"); return

    print(f"PID={pid}  Raw dump mode")
    print("Equip item now. Ctrl+C to stop.\n")

    outpath = r"D:\py\反编译\FreeStyle\dump_equip_raw.txt"
    count = [0]

    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}"); return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except: print(f"  {p}"); return
        t = p.get('type', '')
        if t == 'DUMP':
            count[0] += 1
            text = p['data']
            print(f"  --- Call #{count[0]} ---")
            # Print first 40 lines, full to file
            lines = text.split('\n')
            for line in lines[:40]:
                print(f"  {line}")
            if len(lines) > 40:
                print(f"  ... ({len(lines)} total lines, see dump_equip_raw.txt)")

            with open(outpath, 'a', encoding='utf-8') as f:
                f.write(text + '\n\n')
        elif t == 'info':
            print(f"  [*] {p['msg']}")

    # Clear output file
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('')

    script.on('message', on_message)
    script.load()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print("Done.")

if __name__ == '__main__':
    main()
