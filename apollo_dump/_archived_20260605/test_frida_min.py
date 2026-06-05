"""Find which module owns 0x7c69abd5 and test Thread.backtrace"""
import frida, time

pid = 24180
s = frida.attach(pid)

js = """
// Step 1: Find module for 0x7c69abd5
var addr = ptr('0x7c69abd5');
var mod = Process.findModuleByAddress(addr);
send({t:'addr_module', addr: '0x7c69abd5', name: mod ? mod.name : 'NOT FOUND',
    base: mod ? mod.base : 'N/A'});

// Also list modules to find which DLLs are in that range
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    var m = mods[i];
    var rangeStart = m.base;
    var rangeEnd = m.base.add(m.size);
    if (addr.compare(rangeStart) >= 0 && addr.compare(rangeEnd) < 0) {
        send({t:'module_found', name: m.name, base: m.base.toString(),
            size: m.size, path: m.path});
    }
}

// Step 2: Test Thread.backtrace
try {
    send({t:'bt', type: typeof Thread.backtrace});
} catch(e) {
    send({t:'bt', err: e.message});
}
"""
sc = s.create_script(js)
sc.on('message', lambda msg, _: print(' ', msg))
sc.load()
time.sleep(2)
sc.unload()
s.detach()