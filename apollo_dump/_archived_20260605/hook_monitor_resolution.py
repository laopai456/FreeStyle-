"""
hook_monitor_resolution.py — 分辨率切换崩溃诊断 v3
v3: 主动扫描已存在的D3D设备，不等CreateDevice
    去掉NativeFunction/setInterval（QuickJS不兼容）

用法: 先启动游戏，再运行此脚本，然后改分辨率触发崩溃
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'res_crash_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int(time.time()*1000)%1000:03d}'
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
'use strict';

function hex(p) { return '0x' + p.toString(16); }

// 解析 D3DPRESENT_PARAMETERS
function dumpPresentParams(pp) {
    if (pp.isNull()) return 'null';
    try {
        var w = pp.add(0x00).readU32();
        var h = pp.add(0x04).readU32();
        var fmt = pp.add(0x08).readU32();
        var bbCount = pp.add(0x0C).readU32();
        var swapEffect = pp.add(0x18).readU32();
        var hwnd = pp.add(0x1C).readU32();
        var windowed = pp.add(0x20).readU32();
        var flags = pp.add(0x2C).readU32();
        return JSON.stringify({
            BackBuffer: w + 'x' + h, Fmt: hex(fmt),
            BBufCount: bbCount, SwapEffect: swapEffect,
            hwnd: hex(hwnd), Windowed: !!windowed, Flags: hex(flags)
        });
    } catch(e) { return 'parse_error: ' + e; }
}

send({t: 'step', msg: 'JS v3 开始 — 主动扫描D3D设备'});

// ==========================================
// 模块信息
// ==========================================
var d3d8Base = 0, d3d8End = 0, d3d8Size = 0;
var d3d9Base = 0, d3d9End = 0, d3d9Size = 0;
var fsBase = ptr('0x400000'), fsSize = 0;

Process.enumerateModules().forEach(function(m) {
    if (m.name.toLowerCase() === 'd3d8.dll') {
        d3d8Base = m.base.toInt32();
        d3d8Size = m.size;
        d3d8End = d3d8Base + d3d8Size;
    }
    if (m.name.toLowerCase() === 'd3d9.dll') {
        d3d9Base = m.base.toInt32();
        d3d9Size = m.size;
        d3d9End = d3d9Base + d3d9Size;
    }
    if (m.name.toLowerCase() === 'freestyle.exe') {
        fsBase = m.base;
        fsSize = m.size;
    }
    // 输出关键模块
    var nl = m.name.toLowerCase();
    if (nl.indexOf('apollo') >= 0 || nl.indexOf('free') >= 0 ||
        nl.indexOf('d3d') >= 0 || nl.indexOf('ddraw') >= 0 ||
        nl.indexOf('errorreport') >= 0 || nl.indexOf('msvcr71') >= 0 ||
        nl.indexOf('dxgi') >= 0) {
        send({t: 'module', name: m.name, base: m.base.toString(), size: m.size});
    }
});

send({t: 'step', msg: 'd3d8: ' + (d3d8Base ? hex(ptr(d3d8Base)) + '-' + hex(ptr(d3d8End)) : '未加载')});
send({t: 'step', msg: 'd3d9: ' + (d3d9Base ? hex(ptr(d3d9Base)) + '-' + hex(ptr(d3d9End)) : '未加载')});

// ==========================================
// 全局状态
// ==========================================
var g_presentCount = 0;
var g_resetCount = 0;
var g_d3dDevice = 0;
var g_d3dApi = '';

// ==========================================
// 异常处理器
// ==========================================
var crashCount = 0;

Process.setExceptionHandler(function(details) {
    crashCount++;
    var crashAddr = details.address;
    var crashModule = 'unknown';
    var crashOffset = 0;
    Process.enumerateModules().forEach(function(m) {
        var mEnd = m.base.add(m.size);
        if (crashAddr.compare(m.base) >= 0 && crashAddr.compare(mEnd) < 0) {
            crashModule = m.name;
            crashOffset = crashAddr.sub(m.base).toInt32();
        }
    });

    send({t: 'CRASH', n: crashCount,
          type: details.type, addr: hex(crashAddr),
          module: crashModule, offset: hex(crashOffset),
          eip: hex(details.context.pc),
          eax: hex(details.context.eax), ebx: hex(details.context.ebx),
          ecx: hex(details.context.ecx), edx: hex(details.context.edx),
          esi: hex(details.context.esi), edi: hex(details.context.edi),
          esp: hex(details.context.esp), ebp: hex(details.context.ebp)});

    // 栈回溯
    try {
        var esp = details.context.esp;
        var stack = [];
        for (var i = 0; i < 32; i++) {
            var val = esp.add(i * 4).readU32();
            var inModule = '';
            Process.enumerateModules().forEach(function(m) {
                if (val >= m.base.toInt32() && val < m.base.add(m.size).toInt32()) {
                    inModule = m.name + '+0x' + (val - m.base.toInt32()).toString(16);
                }
            });
            stack.push(hex(ptr(val)) + (inModule ? ' <' + inModule + '>' : ''));
        }
        send({t: 'STACK', vals: stack});
    } catch(e) {}

    try {
        var pc = details.context.pc;
        var codeBytes = new Uint8Array(pc.sub(16).readByteArray(64));
        var hexStr = '';
        for (var i = 0; i < 64; i++) hexStr += ('0' + codeBytes[i].toString(16)).slice(-2) + ' ';
        send({t: 'CODE', hex: hexStr});
    } catch(e) {}

    if (details.memory) {
        send({t: 'MEM', addr: hex(details.memory.address),
              op: details.memory.operation || '?'});
    }

    send({t: 'CRASH_STATE', device: g_d3dDevice ? hex(ptr(g_d3dDevice)) : 'none',
          api: g_d3dApi, presents: g_presentCount, resets: g_resetCount});
    return false;
});
send({t: 'step', msg: '异常处理器就绪'});

// ==========================================
// 主动扫描D3D设备
// ==========================================
// 策略: 扫描FreeStyle.exe的.data段，找指针p使得
//   *p (vtable指针) 落在d3d8.dll或d3d9.dll的地址范围内
//   **p (QueryInterface) 也落在同一DLL范围内
//   这样p就是一个D3D COM对象的指针

function scanForD3DDevice(dllBase, dllEnd, dllName, resetOff, presentOff) {
    if (!dllBase) return null;

    send({t: 'step', msg: '扫描 ' + dllName + ' 设备...'});

    // 扫描范围: FreeStyle.exe 整个镜像
    // 但只扫 .data/.bss 段（通常是后半部分）
    // 先扫描最后8MB（.data段通常在末尾）
    var scanStart = fsBase.add(fsSize - 0x800000); // 最后8MB
    var scanSize = 0x800000;

    var candidates = [];

    try {
        Memory.scan(scanStart, scanSize, '00 00 00 00', {
            onMatch: function(address, size) {
                // 检查这个地址开始的4字节是否指向d3d8/d3d9
                try {
                    var vtblPtr = address.readU32();
                    if (vtblPtr >= dllBase && vtblPtr < dllEnd) {
                        // vtable指向DLL内，检查vtable[0](QueryInterface)是否也在DLL内
                        var qi = ptr(vtblPtr).readU32();
                        if (qi >= dllBase && qi < dllEnd) {
                            // 再检查vtable[2](Release)也在DLL内
                            var rel = ptr(vtblPtr).add(8).readU32();
                            if (rel >= dllBase && rel < dllEnd) {
                                candidates.push({
                                    ptr: address,
                                    vtbl: vtblPtr,
                                    reset: ptr(vtblPtr).add(resetOff).readU32(),
                                    present: ptr(vtblPtr).add(presentOff).readU32()
                                });
                            }
                        }
                    }
                } catch(e) {}
            },
            onComplete: function() {
                send({t: 'step', msg: dllName + ' 扫描完成, 候选=' + candidates.length});
                candidates.forEach(function(c, idx) {
                    send({t: 'scan', dll: dllName, idx: idx,
                          ptr: hex(c.ptr), vtbl: hex(ptr(c.vtbl)),
                          reset_fn: hex(ptr(c.reset)),
                          present_fn: hex(ptr(c.present))});

                    // 验证: 尝试读Reset/Present的前几条指令
                    try {
                        var instr = new Uint8Array(ptr(c.reset).readByteArray(8));
                        // Reset应该是 push ebp; mov ebp, esp 或 sub esp
                        var valid = (instr[0] === 0x55) || (instr[0] === 0x83) ||
                                    (instr[0] === 0x8B) || (instr[0] === 0x89);
                        if (valid) {
                            send({t: 'scan_valid', dll: dllName, idx: idx,
                                  ptr: hex(c.ptr), vtbl: hex(ptr(c.vtbl))});
                            // 如果还没hook过，hook这个
                            if (!g_d3dDevice) {
                                hookDevice(dllName, c.ptr, ptr(c.vtbl), resetOff, presentOff);
                            }
                        }
                    } catch(e) {}
                });
            }
        });
    } catch(e) {
        send({t: 'step', msg: dllName + ' 扫描失败: ' + e});
        // fallback: 直接扫FreeStyle.exe全局变量区域
        // 常见位置: 0x400000 + 很大的offset
        tryFallbackScan(dllBase, dllEnd, dllName, resetOff, presentOff);
    }
}

function tryFallbackScan(dllBase, dllEnd, dllName, resetOff, presentOff) {
    send({t: 'step', msg: dllName + ' fallback扫描: 逐页扫描FreeStyle.exe'});

    // 扫描FreeStyle.exe .data段（0x2800000 附近的典型位置）
    var ranges = [
        [fsBase.add(0x2000000), 0x1000000],  // 0x2400000 - 0x3400000
        [fsBase.add(0x1000000), 0x1000000],  // 0x1400000 - 0x2400000
    ];

    ranges.forEach(function(range) {
        var base = range[0];
        var size = range[1];
        try {
            var found = false;
            for (var offset = 0; offset < size; offset += 4) {
                try {
                    var vtblPtr = base.add(offset).readU32();
                    if (vtblPtr >= dllBase && vtblPtr < dllEnd) {
                        var qi = ptr(vtblPtr).readU32();
                        if (qi >= dllBase && qi < dllEnd) {
                            var rel = ptr(vtblPtr).add(8).readU32();
                            if (rel >= dllBase && rel < dllEnd) {
                                send({t: 'fallback_hit', dll: dllName,
                                      addr: hex(base.add(offset)),
                                      vtbl: hex(ptr(vtblPtr))});
                                if (!g_d3dDevice) {
                                    hookDevice(dllName, base.add(offset), ptr(vtblPtr), resetOff, presentOff);
                                    found = true;
                                    break;
                                }
                            }
                        }
                    }
                } catch(e) { continue; }
            }
            if (found) return;
        } catch(e) {}
    });
}

function hookDevice(dllName, devicePtr, vtbl, resetOff, presentOff) {
    g_d3dDevice = devicePtr.toInt32();
    g_d3dApi = dllName;

    send({t: 'step', msg: '★ 找到' + dllName + '设备! ptr=' + devicePtr + ' vtbl=' + vtbl});

    // Hook Reset
    try {
        var pReset = vtbl.add(resetOff).readPointer();
        send({t: 'step', msg: dllName + '::Reset = ' + pReset});
        Interceptor.attach(pReset, {
            onEnter: function(args) {
                g_resetCount++;
                send({t: 'RESET', n: g_resetCount, api: dllName,
                      device: hex(args[0]), params: dumpPresentParams(args[1])});
            },
            onLeave: function(retval) {
                send({t: 'RESET_RET', api: dllName, hr: hex(retval),
                      resets: g_resetCount});
            }
        });
    } catch(e) {
        send({t: 'step', msg: dllName + ' Reset hook失败: ' + e});
    }

    // Hook Present
    try {
        var pPresent = vtbl.add(presentOff).readPointer();
        send({t: 'step', msg: dllName + '::Present = ' + pPresent});
        Interceptor.attach(pPresent, {
            onEnter: function(args) {
                g_presentCount++;
                if (g_presentCount <= 30 || g_presentCount % 60 === 0) {
                    send({t: 'PRESENT', n: g_presentCount, api: dllName});
                }
            },
            onLeave: function(retval) {
                if (retval.toInt32() < 0) {
                    send({t: 'PRESENT_ERR', api: dllName, hr: hex(retval)});
                }
            }
        });
    } catch(e) {}

    // D3D9: TestCooperativeLevel (offset 0x78)
    if (dllName === 'd3d9.dll') {
        try {
            var pTCL = vtbl.add(0x78).readPointer();
            Interceptor.attach(pTCL, {
                onLeave: function(retval) {
                    if (retval.toInt32() !== 0) {
                        send({t: 'COOP_LEVEL', hr: hex(retval), presents: g_presentCount});
                    }
                }
            });
            send({t: 'step', msg: 'D3D9 TestCooperativeLevel hook OK'});
        } catch(e) {}
    }

    // CreateRenderTarget
    var crtOff = dllName === 'd3d8.dll' ? 0x64 : 0x70;
    try {
        var pCRT = vtbl.add(crtOff).readPointer();
        var crtN = 0;
        Interceptor.attach(pCRT, {
            onEnter: function(args) {
                crtN++;
                send({t: 'CREATE_RT', api: dllName, n: crtN,
                      w: args[1].toInt32(), h: args[2].toInt32()});
            }
        });
    } catch(e) {}

    // CreateDepthStencilSurface
    var dssOff = dllName === 'd3d8.dll' ? 0x68 : 0x74;
    try {
        var pDSS = vtbl.add(dssOff).readPointer();
        var dssN = 0;
        Interceptor.attach(pDSS, {
            onEnter: function(args) {
                dssN++;
                send({t: 'CREATE_DS', api: dllName, n: dssN,
                      w: args[1].toInt32(), h: args[2].toInt32()});
            }
        });
    } catch(e) {}

    // Release
    try {
        var pRelease = vtbl.add(0x08).readPointer();
        Interceptor.attach(pRelease, {
            onEnter: function(args) {
                send({t: 'RELEASE', api: dllName, device: hex(args[0]),
                      presents: g_presentCount, resets: g_resetCount});
            }
        });
    } catch(e) {}

    send({t: 'step', msg: '★ ' + dllName + ' 设备hook全部就绪'});
}

// ==========================================
// 执行扫描
// ==========================================
// D3D8: Reset=14*4=0x38, Present=15*4=0x3C
scanForD3DDevice(d3d8Base, d3d8End, 'd3d8.dll', 0x38, 0x3C);
// D3D9: Reset=16*4=0x40, Present=17*4=0x44
scanForD3DDevice(d3d9Base, d3d9End, 'd3d9.dll', 0x40, 0x44);

// ==========================================
// ChangeDisplaySettingsA
// ==========================================
try {
    var user32 = Process.getModuleByName('user32.dll');
    Interceptor.attach(user32.getExportByName('ChangeDisplaySettingsA'), {
        onEnter: function(args) {
            try {
                var dm = args[0];
                if (!dm.isNull()) {
                    send({t: 'resolution', api: 'CDSA',
                          w: dm.add(0x6C).readU32(), h: dm.add(0x70).readU32(),
                          bpp: dm.add(0x7C).readU32(), flags: args[1].toInt32(),
                          presents: g_presentCount, resets: g_resetCount});
                }
            } catch(e) {}
        }
    });
    try {
        Interceptor.attach(user32.getExportByName('ChangeDisplaySettingsExA'), {
            onEnter: function(args) {
                try {
                    var dm = args[1];
                    if (!dm.isNull()) {
                        send({t: 'resolution', api: 'CDSEXA',
                              w: dm.add(0x6C).readU32(), h: dm.add(0x70).readU32(),
                              flags: args[3].toInt32(),
                              presents: g_presentCount, resets: g_resetCount});
                    }
                } catch(e) {}
            }
        });
    } catch(e) {}
    send({t: 'step', msg: 'DisplaySettings hook OK'});
} catch(e) {}

// ==========================================
// SetWindowPos
// ==========================================
try {
    var user32 = Process.getModuleByName('user32.dll');
    var swpN = 0;
    Interceptor.attach(user32.getExportByName('SetWindowPos'), {
        onEnter: function(args) {
            swpN++;
            if (swpN <= 30) {
                send({t: 'winpos', n: swpN,
                      w: args[3].toInt32(), h: args[4].toInt32(),
                      flags: args[6].toInt32(),
                      presents: g_presentCount, resets: g_resetCount});
            }
        }
    });
    send({t: 'step', msg: 'SetWindowPos hook OK'});
} catch(e) {}

// ==========================================
// VirtualFree
// ==========================================
try {
    var kernel32 = Process.getModuleByName('KERNEL32.DLL');
    var vfN = 0;
    Interceptor.attach(kernel32.getExportByName('VirtualFree'), {
        onEnter: function(args) {
            vfN++;
            if (vfN <= 50) {
                send({t: 'virtualfree', n: vfN,
                      addr: hex(args[0]), size: args[1].toInt32(),
                      type: hex(args[2])});
            }
        }
    });
    send({t: 'step', msg: 'VirtualFree hook OK'});
} catch(e) {}

send({t: 'ready', msg: 'v3 就绪 — D3D设备扫描+全监控'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            crashes: crashCount,
            resets: g_resetCount,
            presents: g_presentCount,
            device: g_d3dDevice ? hex(ptr(g_d3dDevice)) + ' (' + g_d3dApi + ')' : 'none'
        });
    }
};
"""


def main():
    global LOG_F
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 分辨率崩溃诊断 v3 === PID:{pid} ===')
    log(f'主动扫描D3D设备')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'module':
                log(f'  [模块] {p["name"]} base={p["base"]} size={p["size"]}')
            elif t == 'scan':
                log(f'  [扫描] {p["dll"]} #{p["idx"]} ptr={p["ptr"]} vtbl={p["vtbl"]} reset={p["reset_fn"]} present={p["present_fn"]}')
            elif t == 'scan_valid':
                log(f'  [扫描有效] {p["dll"]} #{p["idx"]} ptr={p["ptr"]} vtbl={p["vtbl"]}')
            elif t == 'fallback_hit':
                log(f'  [fallback] {p["dll"]} addr={p["addr"]} vtbl={p["vtbl"]}')
            elif t == 'resolution':
                log(f'  [分辨率] {p["api"]} {p.get("w","?")}x{p.get("h","?")} bpp={p.get("bpp","?")} flags={p.get("flags","?")} presents={p.get("presents",0)} resets={p.get("resets",0)}')
            elif t == 'winpos':
                log(f'  [窗口] #{p["n"]} {p["w"]}x{p["h"]} flags={p["flags"]} presents={p.get("presents",0)} resets={p.get("resets",0)}')
            elif t == 'RESET':
                log(f'  ★ [RESET] #{p["n"]} {p["api"]} device={p["device"]}')
                log(f'    params={p.get("params","")}')
            elif t == 'RESET_RET':
                log(f'  ★ [RESET返回] {p["api"]} hr={p["hr"]} resets={p["resets"]}')
            elif t == 'PRESENT':
                log(f'  [Present] #{p["n"]} {p["api"]}')
            elif t == 'PRESENT_ERR':
                log(f'  ★ [Present失败] {p["api"]} hr={p["hr"]}')
            elif t == 'COOP_LEVEL':
                log(f'  ★ [设备丢失] hr={p["hr"]} presents={p["presents"]}')
            elif t == 'CREATE_RT':
                log(f'  [创建RT] {p["api"]} #{p["n"]} {p["w"]}x{p["h"]}')
            elif t == 'CREATE_DS':
                log(f'  [创建DS] {p["api"]} #{p["n"]} {p["w"]}x{p["h"]}')
            elif t == 'RELEASE':
                log(f'  [Release] {p["api"]} device={p["device"]} presents={p["presents"]} resets={p["resets"]}')
            elif t == 'CRASH':
                log(f'  ★★★ 崩溃 #{p["n"]} ★★★')
                log(f'    type={p["type"]} addr={p["addr"]}')
                log(f'    模块={p["module"]} offset={p["offset"]}')
                log(f'    EIP={p["eip"]} EAX={p["eax"]} EBX={p["ebx"]}')
                log(f'    ECX={p["ecx"]} EDX={p["edx"]} ESI={p["esi"]} EDI={p["edi"]}')
                log(f'    ESP={p["esp"]} EBP={p["ebp"]}')
            elif t == 'CRASH_STATE':
                log(f'    [状态] device={p["device"]} api={p["api"]} presents={p["presents"]} resets={p["resets"]}')
            elif t == 'STACK':
                log(f'    栈回溯:')
                for i, v in enumerate(p['vals']):
                    log(f'      [{i*4:02x}] {v}')
            elif t == 'CODE':
                log(f'    代码: {p["hex"]}')
            elif t == 'MEM':
                log(f'    内存访问: addr={p["addr"]} op={p["op"]}')
            elif t == 'virtualfree':
                log(f'  [VirtualFree] #{p["n"]} addr={p["addr"]} size={p["size"]} type={p["type"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:300]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('监控就绪。改分辨率触发崩溃。')
    log('命令: status | quit')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()
