"""
dump_equip_list.py — Hook 0x23c6570, 遍历 this+4 链表, dump data 对象

0x23c6570 遍历 this+4 的链表:
  node+4 -> next node
  node+8 -> data object (检查 data+0x40, data+0x44)
  data->vtable[0xCC]() 判断类型

用法: py dump_equip_list.py
  装备粉色网红主播, 看输出
"""
import frida, json, sys, time

IC_MIN = 0x02F00000
IC_MAX = 0x03200000
TARGET_IC = 50122721

JS = r"""
'use strict';

var IC_MIN = 0x02F00000;
var IC_MAX = 0x03200000;
var TARGET_IC = """ + str(TARGET_IC) + r""";

function walkList(thisPtr) {
    // this+4 -> list head
    var listHead = thisPtr.add(4).readPointer();
    if (listHead.isNull()) return {error: 'this+4 is null'};

    // [this+4] -> first node value
    var firstVal = listHead.readPointer();
    var endMarker = firstVal;  // end of list marker

    var items = [];
    // Start from firstVal, follow linked list
    // Each node: node+4 -> next, node+8 -> data
    // Actually from disasm: starts at [this+4] value, then [node+4] is next
    // The iteration: current = [ebp-8] from call 0x23ca7f0, then current = [current+4]
    // node data = [[current+4]+8] ... let me just try both patterns

    // Pattern from disasm:
    // [ebp-0x10] starts as result of 0x23ca7f0 call
    // loop: node = [ebp-0x10], next = [node+4], data = [next+8]
    // Actually simpler: let's just walk this+4 as linked list

    var node = listHead;
    var count = 0;
    var maxIter = 50;  // safety

    // Read the "begin" from iterator construction
    // call 0x23ca7f0(listHead_value, listHead) -> returns iterator
    // But let's just walk manually

    // From disasm, the list head [this+4] points to a container
    // [container] = begin node
    // Each node: [node] = value, [node+4] = next
    // The "data" is extracted as [node+4]+8 in the loop body at 0x23c6638-0x23c663e

    var current = firstVal;
    while (count < maxIter) {
        try {
            if (current.isNull()) break;
            if (current.equals(endMarker)) break;

            // Read next
            var next = current.add(4).readPointer();

            // data = [next+8]
            var dataPtr = null;
            try {
                dataPtr = next.add(8).readPointer();
            } catch(e) {}

            var info = {
                nodeAddr: current.toString(),
                nextAddr: next.toString()
            };

            if (dataPtr && !dataPtr.isNull()) {
                info.dataAddr = dataPtr.toString();
                info.data_0x40 = '0x' + dataPtr.add(0x40).readU32().toString(16);
                info.data_0x44 = '0x' + dataPtr.add(0x44).readU32().toString(16);
                info.data_vtable = dataPtr.readPointer().toString();

                // Search data object for IC range values (first 0x200 bytes)
                var icHits = [];
                for (var off = 0; off < 0x200; off += 4) {
                    try {
                        var val = dataPtr.add(off).readU32();
                        if (val >= IC_MIN && val <= IC_MAX) {
                            icHits.push({off: off, val: '0x' + val.toString(16)});
                        }
                    } catch(e) {}
                }
                info.icHits = icHits;

                // Also check data+0x40 as pointer, search sub-object
                try {
                    var sub40 = dataPtr.add(0x40).readPointer();
                    if (!sub40.isNull() && sub40.compare(ptr(0x10000)) > 0) {
                        var sub40ics = [];
                        for (var off = 0; off < 0x100; off += 4) {
                            try {
                                var val = sub40.add(off).readU32();
                                if (val >= IC_MIN && val <= IC_MAX) {
                                    sub40ics.push({off: off, val: '0x' + val.toString(16)});
                                }
                            } catch(e) {}
                        }
                        if (sub40ics.length > 0) info.data_0x40_ptr_icHits = sub40ics;
                    }
                } catch(e) {}

                // Check data+0x44 as pointer
                try {
                    var sub44 = dataPtr.add(0x44).readPointer();
                    if (!sub44.isNull() && sub44.compare(ptr(0x10000)) > 0) {
                        var sub44ics = [];
                        for (var off = 0; off < 0x100; off += 4) {
                            try {
                                var val = sub44.add(off).readU32();
                                if (val >= IC_MIN && val <= IC_MAX) {
                                    sub44ics.push({off: off, val: '0x' + val.toString(16)});
                                }
                            } catch(e) {}
                        }
                        if (sub44ics.length > 0) info.data_0x44_ptr_icHits = sub44ics;
                    }
                } catch(e) {}
            }

            items.push(info);
            current = next;
            count++;
        } catch(e) {
            items.push({error: e.toString()});
            break;
        }
    }

    return {count: count, items: items};
}

var targetFn = ptr(0x23c6570);

Interceptor.attach(targetFn, {
    onEnter: function(args) {
        var thisPtr = this.context.ecx;
        if (thisPtr.isNull()) return;

        var result = walkList(thisPtr);
        send(JSON.stringify({type: 'EQUIP_LIST', thisPtr: thisPtr.toString(), result: result}));
    }
});

send(JSON.stringify({type:'info', msg:'Hooked 0x23c6570, walking linked list on equip'}));
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

    print(f"PID={pid}  Walking equip linked list")
    print("Equip item now. Ctrl+C to stop.\n")

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
        if t == 'EQUIP_LIST':
            r = p['result']
            print(f"  === EQUIP LIST this={p['thisPtr']} items={r['count']} ===")
            for i, item in enumerate(r.get('items', [])):
                if 'error' in item:
                    print(f"  [{i}] ERROR: {item['error']}")
                    continue
                print(f"  [{i}] node={item.get('nodeAddr','?')} next={item.get('nextAddr','?')}")
                if 'dataAddr' in item:
                    print(f"       data={item['dataAddr']}  vtbl={item['data_vtable']}")
                    print(f"       +0x40={item['data_0x40']}  +0x44={item['data_0x44']}")
                    for h in item.get('icHits', []):
                        print(f"       IC: data+0x{h['off']:X} = {h['val']}")
                    for h in item.get('data_0x40_ptr_icHits', []):
                        print(f"       IC: [data+0x40]+0x{h['off']:X} = {h['val']}")
                    for h in item.get('data_0x44_ptr_icHits', []):
                        print(f"       IC: [data+0x44]+0x{h['off']:X} = {h['val']}")
            print()
        elif t == 'info':
            print(f"  [*] {p['msg']}")
        else:
            print(f"  [{t}] {p}")

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
