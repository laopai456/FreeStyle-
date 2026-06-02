# 1.py
# 房间阶段 sprintf ItemCode 替换 — 可切换发型版
#
# 用法：
#   python 1.py                    # 默认：美丽梦想 → 紫色超赛
#   python 1.py <itemcode>         # 指定目标发型
#   python 1.py list               # 列出可用发型
#   python 1.py <名称关键词>        # 按名称搜索

import sys
import os
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

# 发型数据文件
HAIR_JSON = r'C:\Users\w\Desktop\hair_styles.json'
SRC_IC = 50125461  # 默认源：美丽梦想发型

def load_hair_table():
    """从 JSON 文件加载发型表"""
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
    print('\n可用发型：')
    print('-' * 50)
    for name, (code, pak) in sorted(hair_table.items(), key=lambda x: x[1][0]):
        print(f'  {code}: {name} (pak{pak})')
    print('-' * 50)
    print(f'\n默认源发型: {SRC_IC} (美丽梦想发型)')
    print('\n用法: python 1.py <itemcode>')
    print('例如: python 1.py 50125711  # 切换到紫色超赛')

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
                callerEbp.sub(0xD8).writeU32(DST_IC);
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

    dst_code = 50125711  # 默认目标：紫色超赛

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'list':
            list_hairs(hair_table)
            return
        try:
            dst_code = int(arg)
        except ValueError:
            # 按名称搜索
            found = False
            for name, (code, pak) in hair_table.items():
                if arg in name:
                    dst_code = code
                    print(f'找到: {name} ({code})')
                    found = True
                    break
            if not found:
                print(f'未找到含 "{arg}" 的发型')
                list_hairs(hair_table)
                return

    src_name = code_to_name.get(SRC_IC, f'ItemCode {SRC_IC}')
    dst_name = code_to_name.get(dst_code, f'ItemCode {dst_code}')

    print('=== sprintf 替换（房间阶段）===')
    print(f'{SRC_IC} ({src_name}) → {dst_code} ({dst_name})')
    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    print(f'PID: {pid}')

    session = frida.attach(pid)
    script = session.create_script(create_js(SRC_IC, dst_code))

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'就绪: {p["src"]} → {p["dst"]}')
            elif t == 'patch':
                print(f'替换 #{p["n"]}')

    script.on('message', on_msg)
    script.load()

    print('')
    print('进房间观察发型。命令: quit | count | list')
    print('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'count':
                print(f'替换次数: {script.exports_sync.count()}')
            elif cmd == 'list':
                list_hairs(hair_table)
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    print('已断开。')

if __name__ == '__main__':
    main()