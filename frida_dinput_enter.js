/*
 * frida_dinput_enter.js — Hook DirectInput8 COM vtable 注入 Enter 键
 * 
 * 原理: 游戏用 DINPUT8.dll → IDirectInputDevice8::GetDeviceData()
 *       读取键盘状态。Hook 此 COM 虚函数, 向返回的 DIDEVICEOBJECTDATA
 *       数组中注入 Enter 键的按下+释放事件。
 * 
 * IDirectInputDevice8 vtable (x86):
 *   [0]  QueryInterface
 *   [1]  AddRef
 *   [2]  Release
 *   ...
 *   [9]  GetDeviceState    (读取 256 字节键盘状态数组)
 *   [10] GetDeviceData     (读取缓冲的按键事件队列)
 *
 * 方案: hook GetDeviceData, 在 onLeave 中修改返回值
 */

'use strict';

var injectedEnter = false;  // 只注入一次 Enter

// === 32-bit DIDEVICEOBJECTDATA ===
// typedef struct {
//     DWORD dwOfs;       //  0: 设备对象标识符 (键盘: DIK_* scan code)
//     DWORD dwData;      //  4: 按键状态 (bit7=按下, 其他位=应用定义)
//     DWORD dwTimeStamp; //  8: 时间戳
//     DWORD dwSequence;  // 12: 序列号
// } DIDEVICEOBJECTDATA;  // sizeof = 16

// DIK_RETURN = 0x1C (DirectInput scan code for Enter)
var DIK_RETURN = 0x1C;
var DIK_LCONTROL = 0x1D;
var KEY_DOWN_MASK = 0x80;

// GUID_SysKeyboard = {6F1D2B61-D5A0-11CF-BFC7444553540000}
// Little-endian 表示:
var KEYBOARD_GUID_BYTES = [
    0x61, 0x2B, 0x1D, 0x6F, 0xA0, 0xD5, 0xCF, 0x11,
    0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00
];


function bytesToHex(arr, maxLen) {
    var end = maxLen || arr.length;
    var s = '';
    for (var i = 0; i < end && i < arr.length; i++) {
        s += ('0' + arr[i].toString(16)).slice(-2);
    }
    return s;
}

// ====== 扫描内存中的 COM 对象，找到 IDirectInputDevice8 实例 ======
function scanForDInputDevice() {
    var di8 = Process.findModuleByName('DINPUT8.dll');
    if (!di8) {
        send(JSON.stringify({type:'di_err', msg:'DINPUT8.dll not found'}));
        return;
    }
    send(JSON.stringify({type:'di_log', msg:'DINPUT8.dll @ ' + di8.base + ' size=' + di8.size}));

    // 枚举 DINPUT8 的导出
    // 枚举 DINPUT8 的导出
    var DirectInput8Create = null;
    try {
        DirectInput8Create = Module.findExportByName('DINPUT8.dll', 'DirectInput8Create');
    } catch(e) {}

    // Fallback: 遍历所有导出找匹配的
    if (!DirectInput8Create) {
        var exps = di8.enumerateExports();
        for (var i = 0; i < exps.length; i++) {
            var n = exps[i].name.toLowerCase();
            if (n.includes('directinput8create') || n.includes('directinputcreate')) {
                DirectInput8Create = exps[i].address;
                send(JSON.stringify({type:'di_log', msg:'Found via enumeration: ' + exps[i].name + ' @ ' + DirectInput8Create}));
                break;
            }
        }
    }

    if (!DirectInput8Create) {
        // 最后手段: 尝试通过 ordinal 1 (常见于 DINPUT8)
        try {
            DirectInput8Create = Module.findExportByName('DINPUT8.dll', '#1');
        } catch(e) {}
    }

    if (!DirectInput8Create) {
        // 列举所有导出名, 打日志帮助调试
        var exps = di8.enumerateExports();
        send(JSON.stringify({type:'di_err', msg:'DirectInput8Create not found. ' + exps.length + ' exports: ' +
            exps.slice(0, 10).map(function(e){return e.name;}).join(', ')}));
        return;
    }
    send(JSON.stringify({type:'di_log', msg:'DirectInput8Create @ ' + DirectInput8Create}));

    // Hook DirectInput8Create 来拦截设备创建
    Interceptor.attach(DirectInput8Create, {
        onEnter: function(args) {
            // HRESULT DirectInput8Create(HINSTANCE hinst, DWORD dwVersion,
            //     REFIID riidltf, LPVOID* ppvOut, LPUNKNOWN punkOuter);
            this.ppvOut = args[3];  // LPVOID* — 输出 IDirectInput8*
            this.riid = args[2];     // REFIID — 请求的接口 GUID
        },
        onLeave: function(retval) {
            if (retval.toInt32() !== 0) return;  // S_OK = 0
            try {
                var pOut = this.ppvOut.readPointer();
                if (pOut.isNull()) return;
                send(JSON.stringify({type:'di_log', msg:'DirectInput8 created @ ' + pOut}));

                // Hook IDirectInput8::CreateDevice (vtable[3])
                var vtbl = pOut.readPointer();
                var createDevice = vtbl.add(3 * 4).readPointer();
                send(JSON.stringify({type:'di_log', msg:'IDirectInput8::CreateDevice @ ' + createDevice}));

                Interceptor.attach(createDevice, {
                    onEnter: function(args2) {
                        // HRESULT CreateDevice(REFGUID rguid, LPDIRECTINPUTDEVICE* lplpDirectInputDevice, LPUNKNOWN pUnkOuter);
                        this.pGuid = args2[0];    // 设备类型 GUID
                        this.ppDevice = args2[1];  // 输出设备指针
                    },
                    onLeave: function(retval2) {
                        if (retval2.toInt32() !== 0) return;
                        try {
                            var guidBytes = new Uint8Array(this.pGuid.readByteArray(16));
                            var guidHex = bytesToHex(guidBytes, 16);

                            // 检查是否是键盘设备
                            var isKeyboard = true;
                            for (var i = 0; i < 16; i++) {
                                if (guidBytes[i] !== KEYBOARD_GUID_BYTES[i]) {
                                    isKeyboard = false;
                                    break;
                                }
                            }

                            if (isKeyboard) {
                                var pDevice = this.ppDevice.readPointer();
                                send(JSON.stringify({type:'di_log', msg:'KEYBOARD device created @ ' + pDevice}));
                                hookKeyboardDevice(pDevice);
                            }
                        } catch(e) {
                            send(JSON.stringify({type:'di_err', msg:'CreateDevice onLeave: ' + e}));
                        }
                    }
                });
            } catch(e) {
                send(JSON.stringify({type:'di_err', msg:'DirectInput8Create onLeave: ' + e}));
            }
        }
    });
}

// ====== Hook 键盘设备的 GetDeviceData ======
function hookKeyboardDevice(pDevice) {
    try {
        var vtbl = pDevice.readPointer();

        // vtable[10] = GetDeviceData
        var getDeviceData = vtbl.add(10 * 4).readPointer();
        send(JSON.stringify({type:'di_log', msg:'IDirectInputDevice8::GetDeviceData(vtbl[10]) @ ' + getDeviceData}));

        Interceptor.attach(getDeviceData, {
            onEnter: function(args) {
                // HRESULT GetDeviceData(
                //   DWORD cbObjectData,       // sizeof(DIDEVICEOBJECTDATA) = 16
                //   LPDIDEVICEOBJECTDATA rgdod,  // 输出数组
                //   LPDWORD pdwInOut,          // 输入:数组容量, 输出:实际填充数
                //   DWORD dwFlags              // DIGDD_PEEK (不消费事件)
                // );
                this.cbObjectData = args[0].toInt32();
                this.rgdod = args[1];
                this.pdwInOut = args[2];
                this.capacity = args[2].readU32();  // 读入时的容量
                this.dwFlags = args[3].toInt32();
            },
            onLeave: function(retval) {
                if (!injectedEnter) return;

                // HRESULT: DI_OK = 0, DI_BUFFEROVERFLOW = 1
                var hr = retval.toInt32();
                if (hr === 0 || hr === 1) {
                    try {
                        var count = this.pdwInOut.readU32();  // 函数写入后的事件数
                        var lastSeq = 0;
                        if (count > 0) {
                            lastSeq = this.rgdod.add((count - 1) * 16 + 12).readU32();
                        }

                        // 在缓冲区末尾追加 ENTER DOWN + ENTER UP
                        var newCount = Math.min(count + 2, this.capacity);
                        this.pdwInOut.writeU32(newCount);

                        // ENTER DOWN
                        var off = count * 16;
                        this.rgdod.add(off).writeU32(DIK_RETURN);         // dwOfs
                        this.rgdod.add(off + 4).writeU32(KEY_DOWN_MASK);  // dwData (pressed)
                        this.rgdod.add(off + 8).writeU32(0);              // dwTimeStamp
                        this.rgdod.add(off + 12).writeU32(lastSeq + 1);   // dwSequence

                        // ENTER UP
                        if (count + 1 < this.capacity) {
                            off = (count + 1) * 16;
                            this.rgdod.add(off).writeU32(DIK_RETURN);     // dwOfs
                            this.rgdod.add(off + 4).writeU32(0);          // dwData (released)
                            this.rgdod.add(off + 8).writeU32(0);          // dwTimeStamp
                            this.rgdod.add(off + 12).writeU32(lastSeq + 2); // dwSequence
                        }

                        injectedEnter = false;  // 注入完成
                        send(JSON.stringify({type:'di_log', msg:'[DI] ENTER key injected! (buf ' + count + '→' + newCount + ' events)'}));
                    } catch(e) {
                        send(JSON.stringify({type:'di_err', msg:'Inject ENTER: ' + e}));
                    }
                }
            }
        });

        send(JSON.stringify({type:'di_log', msg:'Keyboard GetDeviceData hooked successfully'}));
    } catch(e) {
        send(JSON.stringify({type:'di_err', msg:'hookKeyboardDevice: ' + e}));
    }
}

// ====== 主流程: 延迟扫描 (等 DINPUT8 加载) ======
function tryInit() {
    try {
        var di8 = Process.findModuleByName('DINPUT8.dll');
        if (di8) {
            scanForDInputDevice();
            return true;
        }
    } catch(e) {}
    return false;
}

// 轮询等待 DINPUT8.dll 加载
var attempts = 0;
var intervalId = setInterval(function() {
    attempts++;
    if (tryInit()) {
        clearInterval(intervalId);
        send(JSON.stringify({type:'di_log', msg:'DirectInput hook ready! Send "enter" to inject ENTER key.'}));
    } else if (attempts > 30) {
        clearInterval(intervalId);
        send(JSON.stringify({type:'di_err', msg:'DINPUT8.dll not loaded after 30 attempts'}));
    }
}, 1000);

// ====== RPC: Python 触发 ENTER 注入 ======
rpc.exports = {
    injectEnter: function() {
        injectedEnter = true;
        send(JSON.stringify({type:'di_log', msg:'ENTER injection queued — will fire on next GetDeviceData call'}));
        return 'queued';
    },

    injectKeys: function(keys) {
        // keys: array of DIK_* scan codes, e.g. [0x1C] for Enter
        // Not yet implemented for multi-key, just Enter for now
        injectedEnter = true;
        return 'queued';
    }
};