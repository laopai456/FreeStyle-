// hook_factory.js — hook对象工厂和SetMotionType，捕获发型Actor地址
var VTABLE_STATIC  = ptr('0x0284E00C');
var VTABLE_DYNAMIC = ptr('0x0284A9EC');
var SET_MOTION     = ptr('0x02297810');
var STATIC_INIT    = ptr('0x0236B36B');
var DYNAMIC_INIT   = ptr('0x0229AF00');

// 先验证地址，不hook
send({type:'info', msg:'验证函数地址...'});
var addrs = [
    {name:'SetMotionType', addr: SET_MOTION},
    {name:'DStaticActor::ctor', addr: STATIC_INIT},
    {name:'DDynamicActor::ctor', addr: DYNAMIC_INIT},
];
for (var i = 0; i < addrs.length; i++) {
    try {
        var bytes = addrs[i].addr.readByteArray(8);
        var hex = '';
        var arr = new Uint8Array(bytes);
        for (var j = 0; j < arr.length; j++) hex += ('0' + arr[j].toString(16)).slice(-2) + ' ';
        send({type:'info', msg: addrs[i].name + ' @ ' + addrs[i].addr + ': ' + hex});
    } catch(e) {
        send({type:'error', msg: addrs[i].name + ' @ ' + addrs[i].addr + ': ' + e});
    }
}

// 只hook SetMotionType，用try catch包裹
(function() {
    try {
        Interceptor.attach(SET_MOTION, {
            onEnter: function(args) {
                var thisPtr = args[0];
                var motionType = args[1].toInt32();
                // 读对象vtable确认
                var vtable = thisPtr.readU32();
                var isStatic = vtable === VTABLE_STATIC;
                var isDynamic = vtable === VTABLE_DYNAMIC;
                if (isStatic || isDynamic) {
                    var typeName = isStatic ? 'Static' : 'Dynamic';
                    send({
                        type: 'set_motion',
                        obj: '0x' + thisPtr.toString(16),
                        motion: motionType,
                        actor_type: typeName,
                        field_8: thisPtr.add(8).readU32()
                    });
                }
            }
        });
        send({type:'info', msg:'SetMotionType hook OK @ 0x' + SET_MOTION.toString(16)});
    } catch(e) {
        send({type:'error', msg:'SetMotionType hook FAIL: ' + e});
    }
})();

send({type:'info', msg:'SetMotionType hook ready — 只hook这一个函数'});
