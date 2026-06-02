'use strict';
// frida_hook_acquiresmd.js — Hook 真正的 AcquireSMD 入口 (RVA 0x01EED020)
// 
// 用法: 先 apollo_launcher.py 启动游戏，再
//   frida -p <PID> -l frida_hook_acquiresmd.js
//
// 或: py -c "import frida; s=frida.attach(PID); 
//      s.create_script(open('frida_hook_acquiresmd.js').read()).load(); input()"

var mod = Process.getModuleByName('FreeStyle.exe');
var base = mod.base;
var ACQUIRE_SMD = base.add(0x01EED020);

console.log('[+] FreeStyle.exe base: ' + base);
console.log('[+] AcquireSMD @ 0x' + (base.add(0x01EED020)).toString().substring(2));

// Hook
Interceptor.attach(ACQUIRE_SMD, {
    onEnter: function(args) {
        console.log('\n[AcquireSMD] ENTER');
        console.log('  this/ecx: ' + this.context.ecx);
        console.log('  arg0 (SString*): ' + args[0]);
        console.log('  arg1 (Preset): ' + args[1]);
        
        // Read SString: SString has a pointer to the string data
        // Usually at SString+0 or SString+4 depending on implementation
        try {
            var sstrPtr = args[0];
            // SString first field is usually the data pointer
            var dataPtr = sstrPtr.readPointer();
            var filename = dataPtr.readUtf8String();
            if (filename) {
                console.log('  Filename: ' + filename);
            } else {
                // Maybe it's inline (short string optimization)
                var inline = sstrPtr.readCString();
                if (inline && inline.length > 0 && inline.length < 260) {
                    console.log('  Filename (inline): ' + inline);
                }
            }
        } catch(e) {
            console.log('  (Cannot read filename: ' + e.message + ')');
        }
    },
    onLeave: function(retVal) {
        console.log('  retval: ' + retVal);
    }
});

console.log('[+] Hook installed. Trigger AcquireSMD by entering shop or equipping item.');
