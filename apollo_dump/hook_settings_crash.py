"""
hook_settings_crash.py — 设置崩溃诊断
停Apollo后运行: sc.exe stop ApolloProtect, 再跑此脚本
监控: 写配置 + D3D Reset + 窗口操作 → 找到崩溃点
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'settings_crash_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// === 全局状态 ===
var fsBase = ptr('0x400000'), fsSize = 0;
var d3d9Base = 0;
Process.enumerateModules().forEach(function(m) {
    if (m.name.toLowerCase() === 'freestyle.exe') { fsBase = m.base; fsSize = m.size; }
    if (m.name.toLowerCase() === 'd3d9.dll') { d3d9Base = m.base.toInt32(); }
});
send({t:'step', msg:'FreeStyle base=' + fsBase + ' size=' + fsSize});
send({t:'step', msg:'d3d9 base=' + hex(ptr(d3d9Base))});

var g_device = 0;
var g_resetCount = 0;
var g_presentCount = 0;
var g_createRT = 0;
var g_createDS = 0;

// === 异常处理器 ===
var crashN = 0;
Process.setExceptionHandler(function(details) {
    crashN++;
    var addr = details.address;
    var mod = 'unknown', off = 0;
    try {
        var m = Process.findModuleByAddress(addr);
        if (m) { mod = m.name; off = addr.sub(m.base).toInt32(); }
    } catch(e){}
    send({t:'CRASH', n:crashN, type:details.type, addr:hex(addr),
          mod:mod, off:hex(ptr(off)),
          eip:hex(details.context.pc),
          eax:hex(details.context.eax), ebx:hex(details.context.ebx),
          ecx:hex(details.context.ecx), edx:hex(details.context.edx),
          esp:hex(details.context.esp), ebp:hex(details.context.ebp)});
    try {
        var code = new Uint8Array(details.context.pc.sub(4).readByteArray(32));
        var h = ''; for(var i=0;i<32;i++) h += ('0'+code[i].toString(16)).slice(-2)+' ';
        send({t:'CODE', hex:h});
    } catch(e){}
    if (details.memory) {
        send({t:'MEM', addr:hex(details.memory.address), op:details.memory.operation||'?'});
    }
    send({t:'STATE', dev:g_device?hex(ptr(g_device)):'none', resets:g_resetCount,
          presents:g_presentCount, crt:g_createRT, cds:g_createDS, crashes:crashN});
    return false;
});
send({t:'step', msg:'异常处理器就绪'});

// === 1. WriteFile / WritePrivateProfileStringA — 配置文件写入 ===
try {
    var k32 = Process.getModuleByName('KERNEL32.DLL');
    var wfN = 0;
    Interceptor.attach(k32.getExportByName('WriteFile'), {
        onEnter: function(args) {
            wfN++;
            if (wfN <= 30) {
                try {
                    var buf = args[1];
                    var sz = args[2].toInt32();
                    var preview = '';
                    if (sz > 0 && sz < 200) {
                        preview = buf.readUtf8String(Math.min(sz, 100));
                    }
                    send({t:'writefile', n:wfN, sz:sz, preview:preview});
                } catch(e) {
                    send({t:'writefile', n:wfN, sz:args[2].toInt32(), preview:'(binary)'});
                }
            }
        }
    });
    send({t:'step', msg:'WriteFile hook OK'});
} catch(e) { send({t:'step', msg:'WriteFile hook skip: ' + e}); }

try {
    var wpsN = 0;
    Interceptor.attach(k32.getExportByName('WritePrivateProfileStringA'), {
        onEnter: function(args) {
            wpsN++;
            send({t:'iniput', n:wpsN, section:args[0].readUtf8String(),
                  key:args[1].readUtf8String(), val:args[2].isNull()?'(null)':args[2].readUtf8String(),
                  file:args[3].readUtf8String()});
        }
    });
    Interceptor.attach(k32.getExportByName('WritePrivateProfileSectionA'), {
        onEnter: function(args) {
            send({t:'inisection', section:args[0].readUtf8String(), file:args[2].readUtf8String()});
        }
    });
    send({t:'step', msg:'INI write hook OK'});
} catch(e) {}

try {
    var gpN = 0;
    Interceptor.attach(k32.getExportByName('GetPrivateProfileStringA'), {
        onEnter: function(args) {
            gpN++;
            if (gpN <= 20) {
                send({t:'iniget', n:gpN, section:args[0].readUtf8String(),
                      key:args[1].readUtf8String(), file:args[3].readUtf8String()});
            }
        }
    });
    send({t:'step', msg:'INI read hook OK'});
} catch(e) {}

// === 2. D3D9 CreateDevice + Reset + Present ===
try {
    var d3d9 = Process.getModuleByName('d3d9.dll');
    Interceptor.attach(d3d9.getExportByName('Direct3DCreate9'), {
        onLeave: function(retval) {
            send({t:'D3D9CREATE', ptr:hex(retval)});
            if (!retval.isNull()) {
                try {
                    var vtbl = retval.readPointer();
                    var pCreateDev = vtbl.add(0x10).readPointer(); // CreateDevice = vtable[4]
                    Interceptor.attach(pCreateDev, {
                        onEnter: function(args) {
                            this.ppDevice = args[2];
                            send({t:'CREATEDEV_ENTER', adapter:args[1].toInt32(),
                                  devType:args[2].toInt32(),
                                  hwnd:hex(args[3]),
                                  flags:hex(args[5])});
                            // dump D3DPRESENT_PARAMETERS (args[6])
                            try {
                                var pp = args[6];
                                send({t:'PRESENTPARAMS',
                                      bb_w:pp.add(0x00).readU32(), bb_h:pp.add(0x04).readU32(),
                                      bb_fmt:pp.add(0x08).readU32(), bb_count:pp.add(0x0C).readU32(),
                                      swap:pp.add(0x18).readU32(), hwnd:hex(pp.add(0x1C).readU32()),
                                      windowed:pp.add(0x20).readU32(),
                                      refresh:pp.add(0x24).readU32(),
                                      flags:pp.add(0x2C).readU32()});
                            } catch(e){}
                        },
                        onLeave: function(retval) {
                            send({t:'CREATEDEV_RET', hr:hex(retval)});
                            if (retval.toInt32() >= 0 && !this.ppDevice.isNull()) {
                                try {
                                    var devPtr = this.ppDevice.readPointer();
                                    var devVtbl = devPtr.readPointer();
                                    g_device = devPtr.toInt32();
                                    send({t:'DEVICE', ptr:hex(devPtr), vtbl:hex(devVtbl)});

                                    // hook Reset (vtable[16] = 0x40)
                                    var pReset = devVtbl.add(0x40).readPointer();
                                    Interceptor.attach(pReset, {
                                        onEnter: function(args) {
                                            g_resetCount++;
                                            try {
                                                var pp = args[1];
                                                send({t:'RESET', n:g_resetCount,
                                                      bb_w:pp.add(0x00).readU32(), bb_h:pp.add(0x04).readU32(),
                                                      bb_fmt:pp.add(0x08).readU32(),
                                                      swap:pp.add(0x18).readU32(),
                                                      windowed:pp.add(0x20).readU32(),
                                                      refresh:pp.add(0x24).readU32()});
                                            } catch(e) {
                                                send({t:'RESET', n:g_resetCount, params:'?'});
                                            }
                                        },
                                        onLeave: function(retval) {
                                            send({t:'RESET_RET', n:g_resetCount, hr:hex(retval)});
                                        }
                                    });

                                    // hook Present (vtable[17] = 0x44)
                                    var pPresent = devVtbl.add(0x44).readPointer();
                                    Interceptor.attach(pPresent, {
                                        onEnter: function(args) {
                                            g_presentCount++;
                                            if (g_presentCount <= 10 || g_presentCount % 100 === 0) {
                                                send({t:'PRESENT', n:g_presentCount});
                                            }
                                        }
                                    });

                                    // hook CreateRenderTarget
                                    var pCRT = devVtbl.add(0x70).readPointer();
                                    Interceptor.attach(pCRT, {
                                        onEnter: function(args) {
                                            g_createRT++;
                                            send({t:'CRT', n:g_createRT, w:args[1].toInt32(), h:args[2].toInt32()});
                                        }
                                    });

                                    // hook CreateDepthStencilSurface
                                    var pDSS = devVtbl.add(0x74).readPointer();
                                    Interceptor.attach(pDSS, {
                                        onEnter: function(args) {
                                            g_createDS++;
                                            send({t:'CDS', n:g_createDS, w:args[1].toInt32(), h:args[2].toInt32()});
                                        }
                                    });

                                    send({t:'step', msg:'★ D3D9 Device hook 全部就绪 (Reset/Present/CRT/CDS)'});
                                } catch(e) {
                                    send({t:'step', msg:'Device hook 失败: ' + e});
                                }
                            }
                        }
                    });
                } catch(e) {}
            }
        }
    });
    send({t:'step', msg:'D3D9 Direct3DCreate9 hook OK'});
} catch(e) { send({t:'step', msg:'D3D9 hook skip: ' + e}); }

// === 3. 窗口操作 ===
try {
    var u32 = Process.getModuleByName('user32.dll');
    var swpN = 0;
    Interceptor.attach(u32.getExportByName('SetWindowPos'), {
        onEnter: function(args) {
            swpN++;
            if (swpN <= 30) {
                send({t:'SWP', n:swpN, w:args[3].toInt32(), h:args[4].toInt32(), flags:hex(args[6])});
            }
        }
    });
    var smwN = 0;
    Interceptor.attach(u32.getExportByName('ShowWindow'), {
        onEnter: function(args) {
            smwN++;
            if (smwN <= 20) {
                send({t:'SHOWWIN', n:smwN, cmd:args[1].toInt32()});
            }
        }
    });
    Interceptor.attach(u32.getExportByName('ChangeDisplaySettingsA'), {
        onEnter: function(args) {
            var dm = args[0];
            if (!dm.isNull()) {
                send({t:'CHGDISP', w:dm.add(0x6C).readU32(), h:dm.add(0x70).readU32(),
                      bpp:dm.add(0x7C).readU32(), flags:args[1].toInt32()});
            }
        },
        onLeave: function(retval) {
            send({t:'CHGDISP_RET', hr:hex(retval)});
        }
    });
    Interceptor.attach(u32.getExportByName('ChangeDisplaySettingsExA'), {
        onEnter: function(args) {
            var dm = args[1];
            if (!dm.isNull()) {
                send({t:'CHGDISPE', w:dm.add(0x6C).readU32(), h:dm.add(0x70).readU32(),
                      bpp:dm.add(0x7C).readU32(), flags:args[3].toInt32()});
            }
        },
        onLeave: function(retval) {
            send({t:'CHGDISPE_RET', hr:hex(retval)});
        }
    });
    send({t:'step', msg:'Window hooks OK'});
} catch(e) {}

// === 4. HeapAlloc — 检测大块分配(Reset前常有) ===
try {
    var haN = 0;
    Interceptor.attach(Process.getModuleByName('ntdll.dll').getExportByName('RtlAllocateHeap'), {
        onEnter: function(args) {
            haN++;
            var sz = args[2].toInt32();
            if (sz > 0x100000) { // >1MB
                send({t:'BIGALLOC', n:haN, size:sz});
            }
        }
    });
} catch(e) {}

// === 5.TerminateProcess — 游戏自杀 ===
try {
    Interceptor.attach(Process.getModuleByName('KERNEL32.DLL').getExportByName('TerminateProcess'), {
        onEnter: function(args) {
            send({t:'TERMINATE', handle:hex(args[0]), exitCode:args[1].toInt32()});
            send({t:'STATE', dev:g_device?hex(ptr(g_device)):'none', resets:g_resetCount,
                  presents:g_presentCount, crt:g_createRT, cds:g_createDS, crashes:crashN});
        }
    });
    send({t:'step', msg:'TerminateProcess hook OK'});
} catch(e) {}

// === 6. FreeLibrary — DLL卸载(游戏退出前) ===
try {
    var flN = 0;
    Interceptor.attach(Process.getModuleByName('KERNEL32.DLL').getExportByName('FreeLibrary'), {
        onEnter: function(args) {
            flN++;
            if (flN <= 10) {
                try {
                    var m = Process.findModuleByAddress(args[0]);
                    send({t:'FREELIB', n:flN, name:m?m.name:hex(args[0])});
                } catch(e){}
            }
        }
    });
} catch(e) {}

send({t:'ready', msg:'设置崩溃诊断就绪 — 改设置触发崩溃'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            device: g_device ? hex(ptr(g_device)) : 'none',
            resets: g_resetCount, presents: g_presentCount,
            createRT: g_createRT, createDS: g_createDS,
            crashes: crashN
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
    log(f'=== 设置崩溃诊断 === PID:{pid} ===')
    log(f'日志: {LOG_FILE}')
    log('前提: sc.exe stop ApolloProtect 已执行')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'writefile':
                log(f'  [WriteFile] #{p["n"]} {p["sz"]}B "{p.get("preview","")[:80]}"')
            elif t == 'iniput':
                log(f'  [INI写] #{p["n"]} [{p["section"]}] {p["key"]}={p["val"]} → {p["file"]}')
            elif t == 'iniget':
                log(f'  [INI读] #{p["n"]} [{p["section"]}] {p["key"]} ← {p["file"]}')
            elif t == 'inisection':
                log(f'  [INI段] [{p["section"]}] → {p["file"]}')
            elif t == 'D3D9CREATE':
                log(f'  [D3D9] Direct3DCreate9 → {p["ptr"]}')
            elif t == 'CREATEDEV_ENTER':
                log(f'  [CreateDevice] adapter={p["adapter"]} type={p["devType"]} hwnd={p["hwnd"]} flags={p["flags"]}')
            elif t == 'PRESENTPARAMS':
                log(f'    [参数] {p["bb_w"]}x{p["bb_h"]} fmt={p["bb_fmt"]} count={p["bb_count"]} swap={p["swap"]} windowed={p["windowed"]} refresh={p["refresh"]} flags={p["flags"]}')
            elif t == 'CREATEDEV_RET':
                log(f'  [CreateDevice] hr={p["hr"]}')
            elif t == 'DEVICE':
                log(f'  ★ [Device] ptr={p["ptr"]} vtbl={p["vtbl"]}')
            elif t == 'RESET':
                log(f'  ★ [Reset] #{p["n"]} {p.get("bb_w","?")}x{p.get("bb_h","?")} fmt={p.get("bb_fmt","?")} swap={p.get("swap","?")} windowed={p.get("windowed","?")} refresh={p.get("refresh","?")}')
            elif t == 'RESET_RET':
                log(f'  [Reset返回] #{p["n"]} hr={p["hr"]}')
            elif t == 'PRESENT':
                log(f'  [Present] #{p["n"]}')
            elif t == 'CRT':
                log(f'  [CreateRenderTarget] #{p["n"]} {p["w"]}x{p["h"]}')
            elif t == 'CDS':
                log(f'  [CreateDepthStencil] #{p["n"]} {p["w"]}x{p["h"]}')
            elif t == 'SWP':
                log(f'  [SetWindowPos] #{p["n"]} {p["w"]}x{p["h"]} flags={p["flags"]}')
            elif t == 'SHOWWIN':
                log(f'  [ShowWindow] #{p["n"]} cmd={p["cmd"]}')
            elif t == 'CHGDISP':
                log(f'  [ChangeDisplaySettings] {p["w"]}x{p["h"]} bpp={p["bpp"]} flags={p["flags"]}')
            elif t == 'CHGDISP_RET':
                log(f'  [CDS返回] hr={p["hr"]}')
            elif t == 'CHGDISPE':
                log(f'  [ChangeDisplaySettingsEx] {p["w"]}x{p["h"]} bpp={p["bpp"]} flags={p["flags"]}')
            elif t == 'CHGDISPE_RET':
                log(f'  [CDSE返回] hr={p["hr"]}')
            elif t == 'BIGALLOC':
                log(f'  [大块分配] #{p["n"]} {p["size"]}B')
            elif t == 'TERMINATE':
                log(f'  ★★★ TerminateProcess handle={p["handle"]} exitCode={p["exitCode"]} ★★★')
            elif t == 'FREELIB':
                log(f'  [FreeLibrary] #{p["n"]} {p["name"]}')
            elif t == 'CRASH':
                log(f'  ★★★ 崩溃 #{p["n"]} ★★★')
                log(f'    type={p["type"]} addr={p["addr"]}')
                log(f'    模块={p["mod"]} offset={p["off"]}')
                log(f'    EIP={p["eip"]} EAX={p["eax"]} EBX={p["ebx"]}')
                log(f'    ECX={p["ecx"]} EDX={p["edx"]}')
                log(f'    ESP={p["esp"]} EBP={p["ebp"]}')
            elif t == 'CODE':
                log(f'    代码: {p["hex"]}')
            elif t == 'MEM':
                log(f'    内存访问: addr={p["addr"]} op={p["op"]}')
            elif t == 'STATE':
                log(f'    [状态] device={p["dev"]} resets={p["resets"]} presents={p["presents"]} CRT={p["crt"]} CDS={p["cds"]} crashes={p["crashes"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:300]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('诊断就绪。改任何设置触发崩溃。')
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
