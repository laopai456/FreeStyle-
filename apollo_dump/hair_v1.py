# hair_v1.py
# v1: Room-only sprintf replacement (hardcoded ebp-0xDC)
#
# Status: DEPRECATED - room works, practice range does NOT
# Lesson: ebp offset hardcoded, breaks on game update
#         strcpy path-only replacement causes bald (PAK lookup uses old ItemCode DWORD)

import sys
import os
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

HAIR_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hair_styles.json')
SRC_IC = 50125461

def load_hair_table():
    if os.path.exists(HAIR_JSON):
        with open(HAIR_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['name']: (item['itemCode'], item['pak']) for item in data}
    return {}

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def list_hairs(hair_table):
    print('\nAvailable:')
    for name, (code, pak) in sorted(hair_table.items(), key=lambda x: x[1][0]):
        print(f'  {code}: {name} (pak{pak})')

def create_js(src_code, dst_code):
    return r"""
'use strict';

var SRC_IC = """ + str(src_code) + """;
var DST_IC = """ + str(dst_code) + """;

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var patchCount = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xDC).writeU32(DST_IC);
                patchCount++;
                send({t: 'patch', n: patchCount});
            }
        } catch(e) {}
    }
});

send({t: 'ready', src: SRC_IC, dst: DST_IC});

rpc.exports = {
    count: function() { return patchCount; }
};
"""

def main():
    hair_table = load_hair_table()
    code_to_name = {v[0]: k for k, v in hair_table.items()}

    dst_code = 50125711

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'list':
            list_hairs(hair_table)
            return
        try:
            dst_code = int(arg)
        except ValueError:
            for name, (code, pak) in hair_table.items():
                if arg in name:
                    dst_code = code
                    print(f'found: {name} ({code})')
                    break

    src_name = code_to_name.get(SRC_IC, f'ItemCode {SRC_IC}')
    dst_name = code_to_name.get(dst_code, f'ItemCode {dst_code}')

    print('=== v1: Room only (sprintf, hardcoded ebp-0xDC) ===')
    print(f'{SRC_IC} ({src_name}) -> {dst_code} ({dst_name})')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe not running')
        return

    print(f'PID: {pid}')
    session = frida.attach(pid)
    script = session.create_script(create_js(SRC_IC, dst_code))

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'ready: {p["src"]} -> {p["dst"]}')
            elif t == 'patch':
                print(f'patch #{p["n"]}')

    script.on('message', on_msg)
    script.load()
    print('Commands: quit | count | list\n')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'count':
                print(f'patches: {script.exports_sync.count()}')
            elif cmd == 'list':
                list_hairs(hair_table)
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    print('detached.')

if __name__ == '__main__':
    main()
