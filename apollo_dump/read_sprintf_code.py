"""
read_sprintf_code.py — 读取sprintf调用点周围的原始字节
不hook任何东西，只读取内存，分析指令布局

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, frida
sys.stdout.reconfigure(encoding='utf-8')

SRC_IC = 50125461  # 美丽梦想发型 (pak767)
DST_IC = 50125711  # 紫色超赛发型 (pak768)

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
'use strict';

var base = ptr('0x400000');
var results = [];

// 1. 读取sprintf返回地址0x1AE2563附近的代码
// sprintf返回地址是0x1AE2563，CALL指令在前面
// 读取0x1AE2500到0x1AE2580的范围
var codeStart = base.add(0x1AE2500);
var codeBytes = new Uint8Array(codeStart.readByteArray(0x80));

// 格式化hex dump
var dump = '';
for (var i = 0; i < 0x80; i++) {
    if (i % 16 === 0) dump += '\n  ' + (0x1AE2500 + i).toString(16) + ': ';
    dump += ('0' + codeBytes[i].toString(16)).slice(-2) + ' ';
}
results.push('sprintf call site (0x1AE2500-0x1AE2580):' + dump);

// 2. 读取LoadItemFile入口0x1ACE1C0附近的代码
var lifStart = base.add(0x1ACE1B0);
var lifBytes = new Uint8Array(lifStart.readByteArray(0x40));
var lifDump = '';
for (var i = 0; i < 0x40; i++) {
    if (i % 16 === 0) lifDump += '\n  ' + (0x1ACE1B0 + i).toString(16) + ': ';
    lifDump += ('0' + lifBytes[i].toString(16)).slice(-2) + ' ';
}
results.push('LoadItemFile (0x1ACE1B0-0x1ACE1F0):' + lifDump);

// 3. 搜索ItemCode 50125461在代码段中的位置
// 50125461 = 0x02FD6A55 (little-endian: 55 6A FD 02)
var searchBytes = [0x55, 0x6A, 0xFD, 0x02]; // little-endian of 50125461
var dstBytes = [0x5F, 0x6E, 0xFD, 0x02]; // 50125711 = 0x02FD6E5F

// 在0x1AE2400-0x1AE2600范围搜索
var searchStart = base.add(0x1AE2400);
var searchBuf = new Uint8Array(searchStart.readByteArray(0x200));
var found = [];
for (var i = 0; i < 0x200 - 4; i++) {
    if (searchBuf[i] === searchBytes[0] && searchBuf[i+1] === searchBytes[1] &&
        searchBuf[i+2] === searchBytes[2] && searchBuf[i+3] === searchBytes[3]) {
        found.push('0x' + (0x1AE2400 + i).toString(16));
    }
}
results.push('ItemCode 50125461 found at: ' + (found.length > 0 ? found.join(', ') : 'NOT FOUND in range'));

// 4. 也搜索50125711
var found2 = [];
for (var i = 0; i < 0x200 - 4; i++) {
    if (searchBuf[i] === dstBytes[0] && searchBuf[i+1] === dstBytes[1] &&
        searchBuf[i+2] === dstBytes[2] && searchBuf[i+3] === dstBytes[3]) {
        found2.push('0x' + (0x1AE2400 + i).toString(16));
    }
}
results.push('ItemCode 50125711 found at: ' + (found2.length > 0 ? found2.join(', ') : 'NOT FOUND'));

send({t: 'results', data: results});
"""

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    print(f'PID: {pid}')
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            if p.get('t') == 'results':
                for line in p['data']:
                    print(line)
        elif msg['type'] == 'error':
            print(f'JS错误: {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    import time
    time.sleep(1)
    script.unload()
    session.detach()
    print('完成。')

if __name__ == '__main__':
    main()
