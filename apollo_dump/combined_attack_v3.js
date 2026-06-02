// combined_attack_v3.js — 组合攻击 v3: BML替换 + SSKF监控 + Actor创建监控
// 新增: hook Static创建(0x0231B930) 和 Dynamic创建(0x02299730) 看哪个被调用
'use strict';

var SRC_CODE = '50125461';
var DST_CODE = '50125711';

// RVAs (runtime address - 0x400000)
var RVA_STATIC_CREATE  = 0x01F1B930;  // 0x0231B930 DStaticActor创建
var RVA_STATIC_CREATE2 = 0x01F1BDB0;  // 0x0231BDB0 DStaticActor创建#2
var RVA_DYNAMIC_CREATE = 0x01E99730;  // 0x02299730 DDynamicActor创建
var RVA_DYNAMIC_CREATE2= 0x01EF27B0;  // 0x022F27B0 DDynamicActor创建#2
var RVA_STATIC_FACTORY = 0x01F6B340;  // 0x0236B340 DStaticActor工厂
var RVA_DYNAMIC_FACTORY= 0x01E9AF00;  // 0x0229AF00 DDynamicActor工厂

// === Module ===
var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;
fsMod.enumerateSections().forEach(function(s) { if (s.name === '.text') textSection = s; });
if (!textSection) throw new Error('.text not found');
var textStart = textSection.address;
var textEnd = textStart.add(textSection.size);

function inText(addr) { return addr.compare(textStart) >= 0 && addr.compare(textEnd) < 0; }

function log(obj) { send({t: 'log', line: new Date().toISOString().substr(11,12) + ' ' + JSON.stringify(obj)}); }

log({event:'module', base: base.toString(), text: textStart.toString(), size: textSection.size});

// === Apollo deception ===
var ntdll = Process.getModuleByName('ntdll.dll');
Interceptor.attach(ntdll.getExportByName('NtQueryVirtualMemory'), {
    onEnter: function(a) { this.mi=a[3]; this.ic=a[2]; },
    onLeave: function(r) {
        if(r.toInt32()||this.ic.toInt32()) return;
        try{var a=this.mi.readPointer();if(inText(a)){this.mi.add(8).writeU32(0x20);this.mi.add(20).writeU32(0x20);}}catch(e){}
    }
});
Interceptor.attach(ntdll.getExportByName('NtProtectVirtualMemory'), {
    onEnter: function(a) { this.bp=a[1]; this.op=a[4]; },
    onLeave: function(r) {
        try{var a=this.bp.readPointer();if(inText(a)&&!this.op.isNull()){this.op.writeU32(0x20);r.replace(0);}}catch(e){}
    }
});
log({event:'apollo', msg:'deception active'});

// === Actor creation hooks ===
var ACTOR_CALLS = [];

function hookActorCreate(rva, name) {
    var addr = base.add(rva);
    try {
        Interceptor.attach(addr, {
            onEnter: function(args) {
                // 读取前几个参数和栈上数据
                var stackDump = [];
                try {
                    var esp = this.context.esp;
                    for (var off = 0; off < 0x40; off += 4) {
                        var val = esp.add(off).readU32();
                        stackDump.push(val);
                    }
                } catch(e) {}

                // 读返回地址
                var retAddr = this.context.esp.readU32();

                var entry = {
                    event: 'actor_call', type: name, addr: addr.toString(),
                    retAddr: retAddr.toString(),
                    retAddrRVA: '0x' + (retAddr - base).toString(16),
                    eax: this.context.eax.toString(),
                    ecx: this.context.ecx.toString(),
                    edx: this.context.edx.toString(),
                    stackTop8: stackDump.slice(0, 8).map(function(v) { return '0x' + v.toString(16); })
                };
                ACTOR_CALLS.push(entry);
                log(entry);
            },
            onLeave: function(retval) {
                log({event:'actor_ret', type: name, retval: retval.toString()});
            }
        });
        log({event:'hook_ok', name: name, addr: addr.toString()});
    } catch(e) {
        log({event:'hook_fail', name: name, addr: addr.toString(), err: e.toString()});
    }
}

hookActorCreate(RVA_STATIC_CREATE,  'StaticCreate1');
hookActorCreate(RVA_STATIC_CREATE2, 'StaticCreate2');
hookActorCreate(RVA_DYNAMIC_CREATE, 'DynamicCreate1');
hookActorCreate(RVA_DYNAMIC_CREATE2,'DynamicCreate2');
hookActorCreate(RVA_STATIC_FACTORY, 'StaticFactory');
hookActorCreate(RVA_DYNAMIC_FACTORY,'DynamicFactory');

// === BML hook (same as v2) ===
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var BML_COUNT = 0, SSKF_COUNT = 0, PATCH_COUNT = 0;

var encSrc = [];
for (var i = 0; i < SRC_CODE.length; i++) encSrc.push(SRC_CODE.charCodeAt(i) ^ 0xFF);
var encDst = [];
for (var i = 0; i < DST_CODE.length; i++) encDst.push(DST_CODE.charCodeAt(i) ^ 0xFF);

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3];
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 4) return;

            // SSKF check
            var m4 = new Uint8Array(this.buf.readByteArray(4));
            if (m4[0]===0x53 && m4[1]===0x53 && m4[2]===0x4B && m4[3]===0x46) {
                SSKF_COUNT++;
                var fname = scanStack(this.context.esp);
                var flag = '';
                if (fname && DST_CODE in {v:1} && fname.indexOf(DST_CODE) !== -1) flag = ' ★TARGET';
                if (fname && fname.indexOf(SRC_CODE) !== -1) flag = ' ★SOURCE';
                log({event:'sskf', n:SSKF_COUNT, size:n, fname: fname||'(?)', flag: flag});
                return;
            }

            // BML check
            if (n < 50 || n > 10000) return;
            var buf = new Uint8Array(this.buf.readByteArray(n));
            var tag = [0x3C,0x72,0x6F,0x6F,0x74,0x3E];
            var ok = true;
            for (var i=0;i<6;i++) if((buf[i]^0xFF)!==tag[i]){ok=false;break;}
            if (!ok) return;

            BML_COUNT++;
            var text = '';
            for (var i=0;i<n;i++){var c=buf[i]^0xFF;if(c>=0x20&&c<0x7F)text+=String.fromCharCode(c);}
            var icM = text.match(/i(\d{6,8})/);
            var ic = icM ? icM[1] : '';
            var meshes = [];
            var re=/<mesh>([^<]+)<\/mesh>/g, m;
            while((m=re.exec(text))!==null) meshes.push(m[1]);
            log({event:'bml', n:BML_COUNT, ic:ic, meshes:meshes});

            if (ic === SRC_CODE) {
                var pc = 0;
                var rawBuf = this.buf;
                // Replace in <mesh> tags
                pc += replaceInTag(buf, rawBuf, n,
                    [0x3C,0x6D,0x65,0x73,0x68,0x3E],
                    [0x3C,0x2F,0x6D,0x65,0x73,0x68,0x3E], encSrc, encDst);
                // Replace in <texture> tags
                pc += replaceInTag(buf, rawBuf, n,
                    [0x3C,0x74,0x65,0x78,0x74,0x75,0x72,0x65,0x3E],
                    [0x3C,0x2F,0x74,0x65,0x78,0x74,0x75,0x72,0x65,0x3E], encSrc, encDst);
                PATCH_COUNT += pc;

                var afterBuf = new Uint8Array(rawBuf.readByteArray(n));
                var afterText = '';
                for(var i=0;i<n;i++){var c=afterBuf[i]^0xFF;if(c>=0x20&&c<0x7F)afterText+=String.fromCharCode(c);}
                var am=[];
                var re2=/<mesh>([^<]+)<\/mesh>/g;
                while((m=re2.exec(afterText))!==null) am.push(m[1]);
                log({event:'patch', patches:pc, total:PATCH_COUNT, after:am});
            }
        } catch(e) {
            log({event:'error', where:'ReadFile', msg:e.toString()});
        }
    }
});

function replaceInTag(buf, rawBuf, n, openTag, closeTag, encSrc, encDst) {
    var count = 0;
    for (var pos=0; pos<=n-openTag.length; pos++) {
        var isS=true;
        for(var j=0;j<openTag.length;j++) if((buf[pos+j]^0xFF)!==openTag[j]){isS=false;break;}
        if(!isS) continue;
        var cs=pos+openTag.length, ce=-1;
        for(var p=cs;p<=n-closeTag.length;p++){
            var isE=true;
            for(var j=0;j<closeTag.length;j++) if((buf[p+j]^0xFF)!==closeTag[j]){isE=false;break;}
            if(isE){ce=p;break;}
        }
        if(ce===-1) continue;
        for(var pp=cs;pp<=ce-encSrc.length;pp++){
            var match=true;
            for(var j=0;j<encSrc.length;j++) if(buf[pp+j]!==encSrc[j]){match=false;break;}
            if(match){for(var j=0;j<encDst.length;j++) rawBuf.add(pp+j).writeU8(encDst[j]);count++;pp+=encSrc.length-1;}
        }
        pos=ce+closeTag.length-1;
    }
    return count;
}

function scanStack(esp) {
    for(var off=0;off<0x800;off+=4){
        try{
            var pv=esp.add(off).readPointer();
            var tries=[function(){return pv.readAnsiString(128);},function(){return pv.add(4).readAnsiString(128);}];
            for(var ti=0;ti<tries.length;ti++){try{var s=tries[ti]();if(s&&(s.indexOf('.smd')>=0||s.indexOf('.bml')>=0))return s;}catch(e){}}
            try{var p2=pv.readPointer();var s4=p2.readAnsiString(128);if(s4&&(s4.indexOf('.smd')>=0||s.indexOf('.bml')>=0))return s4;}catch(e){}
        }catch(e){}
    }
    return null;
}

log({event:'ready', msg:'v3: BML+SSKF+Actor monitoring', src:SRC_CODE, dst:DST_CODE});

rpc.exports = {
    status: function() {
        log({event:'status', bml:BML_COUNT, sskf:SSKF_COUNT, patch:PATCH_COUNT,
             actors: ACTOR_CALLS.length, actorTypes: ACTOR_CALLS.map(function(a){return a.type;})});
    },
    getLog: function() {
        // Return only actor calls for easy parsing
        return JSON.stringify(ACTOR_CALLS, null, 2);
    }
};
