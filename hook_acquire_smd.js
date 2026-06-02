try {
    var base = Process.getModuleByName('FreeStyle.exe').base;
    var modSize = Process.getModuleByName('FreeStyle.exe').size;
    var tid = 2888; // main thread from previous run

    // Phase 1: baseline
    var baseline = {};
    send({t:'info', msg: 'Phase 1: 3s baseline — DO NOT click'});

    Stalker.follow(tid, {
        events: { call: true },
        onReceive: function(raw) {
            try {
                var calls = Stalker.parse(raw);
                for (var c = 0; c < calls.length; c++) {
                    try {
                        var t = calls[c][2];
                        if (t) {
                            var rva = t.sub(base).toInt32();
                            if (rva > 0 && rva < modSize) baseline[rva] = (baseline[rva] || 0) + 1;
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }
    });

    setTimeout(function() {
        Stalker.unfollow(tid);
        var baseCount = Object.keys(baseline).length;
        send({t:'info', msg: 'Baseline: ' + baseCount + ' unique targets'});

        // Phase 2: click
        var clicked = {};
        send({t:'info', msg: '=== CLICK A HAIRSTYLE NOW (3s) ==='});

        Stalker.follow(tid, {
            events: { call: true },
            onReceive: function(raw) {
                try {
                    var calls = Stalker.parse(raw);
                    for (var c = 0; c < calls.length; c++) {
                        try {
                            var t = calls[c][2];
                            if (t) {
                                var rva = t.sub(base).toInt32();
                                if (rva > 0 && rva < modSize) clicked[rva] = (clicked[rva] || 0) + 1;
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
            }
        });

        setTimeout(function() {
            Stalker.unfollow(tid);

            // Diff
            var newFuncs = [];
            var clickKeys = Object.keys(clicked);
            for (var i = 0; i < clickKeys.length; i++) {
                var rva = clickKeys[i];
                var cc = clicked[rva];
                var bc = baseline[rva] || 0;
                if (bc === 0) {
                    newFuncs.push({rva: parseInt(rva), calls: cc, type: 'NEW'});
                } else if (cc > bc * 3 && cc >= 5) {
                    newFuncs.push({rva: parseInt(rva), calls: cc, base: bc, type: 'HOT'});
                }
            }
            newFuncs.sort(function(a, b) { return b.calls - a.calls; });

            send({t:'info', msg: '--- Diff: ' + newFuncs.length + ' new/hot functions ---'});
            for (var n = 0; n < Math.min(newFuncs.length, 50); n++) {
                var f = newFuncs[n];
                if (f.type === 'NEW') {
                    send({t:'new', abs: '0x' + (f.rva + 0x400000).toString(16), calls: f.calls});
                } else {
                    send({t:'hot', abs: '0x' + (f.rva + 0x400000).toString(16), calls: f.calls, base: f.base});
                }
            }
            send({t:'loaded', msg: 'Done.'});
        }, 3000);
    }, 3000);

} catch(e) {
    send({t:'error', msg: 'FATAL: ' + e.message});
}
