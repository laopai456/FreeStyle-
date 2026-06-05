# call_dynamic_init.py - 用Frida NativeFunction直接调用DynamicInit
# 不hook，不修改.text，安全
import sys, os, struct, frida
sys.stdout.reconfigure(encoding='utf-8')
import psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
// 0x0229AF00 是工厂(分配新内存), 0x229B0B0 是构造函数, 0x229B4D0 是DynamicInit
var DYNAMIC_CTOR = new NativeFunction(ptr('0x0229B0B0'), 'pointer', ['pointer'], 'thiscall');
var DYNAMIC_INIT = new NativeFunction(ptr('0x0229B4D0'), 'pointer', ['pointer'], 'thiscall');
var DYNAMIC_PHYSICS_INIT = new NativeFunction(ptr('0x0229C2D0'), 'pointer', ['pointer'], 'thiscall');
var VTABLE_STATIC = ptr('0x0284E00C');
var VTABLE_DYNAMIC = ptr('0x0284A9EC');

// 验证函数可调用（读前几个字节确认）
send({type:'info', msg:'DynamicInit bytes: ' + hexdump(ptr('0x0229B4D0'), {length: 16})});
send({type:'info', msg:'DDynamicCtor bytes: ' + hexdump(ptr('0x0229B0B0'), {length: 16})});

rpc.exports = {
    // 调用DynamicInit初始化
    convertToDynamic: function(addrStr) {
        var addr = ptr(addrStr);
        var oldVtable = addr.readU32();
        if (oldVtable !== 0x0284E00C) {
            return {error: 'not a DStaticActor (vtable=0x' + oldVtable.toString(16) + ')'};
        }
        try {
            var result = DYNAMIC_INIT(addr);
            return {
                ok: true,
                obj: addrStr,
                newVtable: '0x' + addr.readU32().toString(16),
                newType: addr.add(8).readU32(),
                result: '0x' + result.toString(16)
            };
        } catch(e) {
            return {error: 'DynamicInit failed: ' + e};
        }
    },
    // 调用DynamicPhysicsInit
    initPhysics: function(addrStr) {
        var addr = ptr(addrStr);
        try {
            var result = DYNAMIC_PHYSICS_INIT(addr);
            return {
                ok: true,
                obj: addrStr,
                result: '0x' + result.toString(16)
            };
        } catch(e) {
            return {error: 'PhysicsInit failed: ' + e};
        }
    },
    // 调用构造函数（危险）
    callCtor: function(addrStr) {
        var addr = ptr(addrStr);
        try {
            var result = DYNAMIC_CTOR(addr);
            return {
                ok: true,
                obj: addrStr,
                newVtable: '0x' + addr.readU32().toString(16),
                newType: addr.add(8).readU32(),
            };
        } catch(e) {
            return {error: 'Ctor failed: ' + e};
        }
    },
    // 只改vtable+type，不调用ctor
    patchFields: function(addrStr) {
        var addr = ptr(addrStr);
        var oldVtable = addr.readU32();
        var oldType = addr.add(8).readU32();

        if (oldVtable !== 0x0284E00C) {
            return {error: 'not a DStaticActor (vtable=0x' + oldVtable.toString(16) + ')'};
        }

        addr.writeU32(0x0284A9EC);  // vtable -> Dynamic
        addr.add(8).writeU32(1);    // type -> 1

        return {
            ok: true,
            obj: addrStr,
            newVtable: '0x' + addr.readU32().toString(16),
            newType: addr.add(8).readU32()
        };
    },
    // 恢复为Static
    restoreStatic: function(addrStr) {
        var addr = ptr(addrStr);
        addr.writeU32(0x0284E00C);
        addr.add(8).writeU32(3);
        return {ok: true, obj: addrStr};
    },
    // dump对象内存
    dumpObj: function(addrStr) {
        var addr = ptr(addrStr);
        var fields = [];
        for (var i = 0; i < 64; i += 4) {
            var val = addr.add(i).readU32();
            var fval = addr.add(i).readFloat();
            fields.push({
                offset: '0x' + i.toString(16),
                hex: '0x' + val.toString(16),
                float: fval.toFixed(2)
            });
        }
        return fields;
    },
    // 读+460h区域
    readPhysics: function(addrStr) {
        var addr = ptr(addrStr);
        var phys = addr.add(0x460);
        var result = [];
        for (var i = 0; i < 32; i += 4) {
            try {
                var val = phys.add(i).readU32();
                result.push('0x' + val.toString(16));
            } catch(e) {
                result.push('???');
            }
        }
        return result.join(' ');
    }
};
"""

def find_statics(pm):
    import pymem
    vt_bytes = struct.pack('<I', 0x0284E00C)
    results = []
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if not data: continue
            off = 0
            while True:
                idx = data.find(vt_bytes, off)
                if idx == -1: break
                obj_addr = addr + idx
                raw = pm.read_bytes(obj_addr, 64)
                f = struct.unpack('<16I', raw)
                if f[2] == 3:
                    results.append(obj_addr)
                off = idx + 4
        except:
            continue
    return results

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')

    # Pymem扫描对象
    import pymem
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    statics = find_statics(pm)
    print(f'DStaticActor: {len(statics)} 个')
    for i, addr in enumerate(statics):
        raw = pm.read_bytes(addr, 64)
        f = struct.unpack('<16I', raw)
        c_val = struct.unpack_from('<f', raw, 12)[0]
        print(f'  [{i}] 0x{addr:08X}: +8={f[2]} +C={c_val:.1f} scale=({struct.unpack_from("<f",raw,36)[0]:.1f},{struct.unpack_from("<f",raw,40)[0]:.1f},{struct.unpack_from("<f",raw,44)[0]:.1f})')

    pm.close_process()

    # Frida连接
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            print(f"  [INFO] {msg['payload'].get('msg','')}")
        elif msg['type'] == 'error':
            print(f"  [JS错误] {msg.get('description','')}")

    script.on('message', on_msg)
    script.load()

    api = script.exports

    print('\n命令:')
    print('  d <编号>    - dump对象内存')
    print('  p <编号>    - 只改vtable+type字段')
    print('  c <编号>    - 调用DynamicInit')
    print('  x <编号>    - 调用DynamicPhysicsInit')
    print('  phys <编号> - 读+460h物理块')
    print('  r <编号>    - 恢复为Static')
    print('  scan        - 重新Pymem扫描')
    print('  q           - 退出')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('q','quit','exit'):
                break
            parts = cmd.split()
            if not parts:
                continue
            action = parts[0]
            if action == 'scan':
                import pymem
                pm2 = pymem.Pymem()
                pm2.open_process_from_id(pid)
                statics = find_statics(pm2)
                print(f'  {len(statics)} 个 DStaticActor')
                for i, addr in enumerate(statics):
                    raw = pm2.read_bytes(addr, 64)
                    f = struct.unpack('<16I', raw)
                    c_val = struct.unpack_from('<f', raw, 12)[0]
                    print(f'    [{i}] 0x{addr:08X}: +C={c_val:.1f}')
                pm2.close_process()
                continue
            if len(parts) < 2:
                print('  用法: d/p/c/phys/r <编号>  或 scan')
                continue
            idx_str = parts[1]
            try:
                idx = int(idx_str)
            except:
                continue
            if idx < 0 or idx >= len(statics):
                print('  索引越界')
                continue
            addr_hex = f'0x{statics[idx]:08X}'
            if action == 'd':
                fields = api.dump_obj(addr_hex)
                for f in fields:
                    tag = ''
                    if f['offset'] == '0x0': tag = ' <- vtable'
                    elif f['offset'] == '0x8': tag = ' <- type'
                    print(f"  +{f['offset']}: {f['hex']} ({f['float']}){tag}")
            elif action == 'p':
                result = api.patch_fields(addr_hex)
                print(f'  {result}')
            elif action == 'c':
                print(f'  调用 DynamicInit(0x{statics[idx]:08X})...')
                result = api.convert_to_dynamic(addr_hex)
                print(f'  {result}')
            elif action == 'x':
                print(f'  调用 DynamicPhysicsInit(0x{statics[idx]:08X})...')
                result = api.init_physics(addr_hex)
                print(f'  {result}')
            elif action == 'phys':
                data = api.read_physics(addr_hex)
                print(f'  +460h: {data}')
            elif action == 'r':
                result = api.restore_static(addr_hex)
                print(f'  {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()

if __name__ == '__main__':
    main()
