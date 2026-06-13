"""角色替换工具 - Hook sprintf 替换 c%d.xml 的 IC 值"""
import frida, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

# ============ 配置区 ============
# 要替换成的目标角色 c-code (头模)
# 修改这里来切换角色
TARGET_HEAD_CODE = 647   # XIAOLU 小陆
TARGET_BODY_CODE = 648   # XIAOLU_T 小陆变身

# 是否启用替换
ENABLE_REPLACE = True

# 只替换指定来源的c-code（留空则替换所有）
REPLACE_ONLY_FROM = []  # 例: [800, 801] 只替换鲁美的头模/体模
# ============ 配置区结束 ============

def find_pid():
    out = subprocess.check_output(
        ['wmic', 'process', 'where', 'name=\'FreeStyle.exe\'', 'get', 'ProcessId', '/value'],
        text=True
    )
    for line in out.strip().split('\n'):
        line = line.strip()
        if line.startswith('ProcessId='):
            return int(line.split('=', 1)[1])
    return None

# 角色名映射（从specialcharacter_info.pak提取）
CHAR_MAP = {
    9: 'ALICE', 10: 'HOWL', 11: 'FRANCIS', 12: 'SACHI', 13: 'MIKA',
    14: 'YOSHINO', 15: 'SIEG', 16: 'OPHELIA', 17: 'RAYMOND',
    43: 'SARU', 523: 'HORAN', 524: 'HORAN_T', 525: 'HORAN_M', 526: 'HORAN_M_T',
    527: 'RAIDEN', 528: 'RAIDEN_T', 529: 'RAIDEN_M', 530: 'RAIDEN_M_T',
    531: 'LIA', 532: 'LIA_T', 533: 'LIA_M', 534: 'LIA_M_T',
    535: 'UL_MIKA', 536: 'UL_HOWL',
    800: 'RUMI', 801: 'CREATOR_RUMI_T',
    537: 'AIDA', 538: 'AIDA_T', 539: 'AIDA_M', 540: 'AIDA_M_T',
    541: 'ZERO', 542: 'ZERO_T', 543: 'ZERO_M', 544: 'ZERO_M_T',
    547: 'RUBI', 548: 'MARIN', 549: 'RUBI_M', 550: 'MARIN_M',
    551: 'IRIS', 552: 'LIME', 553: 'NW_ANGELA', 554: 'NW_ANGELA_T',
    555: 'NW_BEELZE', 556: 'NW_BEELZE_T',
    557: 'STAN', 558: 'VIPER', 559: 'IRIS_M', 560: 'LIME_M',
    561: 'STAN_M', 562: 'VIPER_M', 563: 'LIEL', 564: 'PIE',
    565: 'LIEL_M', 566: 'PIE_M', 567: 'NW_ELSIS', 568: 'NW_ELSIS_T',
    569: 'SHALOMET', 570: 'SHALOMET_T',
    573: 'SEOLHA', 574: 'SEOLHA_T', 575: 'SEOLHA_M', 576: 'SEOLHA_M_T',
    577: 'BIHYUN', 578: 'BIHYUN_T', 579: 'BIHYUN_M', 580: 'BIHYUN_M_T',
    581: 'WOLAH', 582: 'WOLAH_T', 583: 'WOLAH_M', 584: 'WOLAH_M_T',
    587: 'HATHOR', 588: 'HATHOR_T', 589: 'HATHOR_M', 590: 'HATHOR_M_T',
    593: 'HOYEON', 594: 'HOYEON_T', 595: 'YUHA', 596: 'YUHA_T',
    597: 'ODIN', 598: 'ODIN_T', 599: 'ODIN_M', 600: 'ODIN_M_T',
    605: 'NW_MAY', 606: 'NW_SHARON',
    601: 'ARTEMIS', 602: 'ARTEMIS_T', 603: 'ARTEMIS_M', 604: 'ARTEMIS_M_T',
    607: 'ROX', 608: 'ROX_T',
    609: 'RUKA', 610: 'RUKA_T', 611: 'RUKA_M', 612: 'RUKA_M_T',
    613: 'NW_ROY', 614: 'NW_JOKER',
    615: 'ARK', 616: 'ARK_T', 617: 'ARK_M', 618: 'ARK_M_T',
    619: 'FOXY', 620: 'FOXY_T',
    621: 'AKI', 622: 'AKI_T', 623: 'AKI_M', 624: 'AKI_M_T',
    625: 'THOMSON', 626: 'THOMSON_T',
    627: 'EDDIE', 628: 'EDDIE_T', 629: 'EDDIE_M', 630: 'EDDIE_M_T',
    631: 'IVY', 632: 'IVY_T', 633: 'IVY_M', 634: 'IVY_M_T',
    635: 'VOLKAN', 636: 'VOLKAN_T', 637: 'VOLKAN_M', 638: 'VOLKAN_M_T',
    639: 'HYLIN', 640: 'HYLIN_T', 806: 'HYLIN_M', 807: 'HYLIN_M_T',
    643: 'DRAKOV', 644: 'DRAKOV_T', 645: 'DRAKOV_M', 646: 'DRAKOV_M_T',
    647: 'XIAOLU', 648: 'XIAOLU_T', 649: 'XIAOLU_M', 650: 'XIAOLU_M_T',
    3000: 'TMAC', 3001: 'EX_TMAC', 3002: 'L_TMAC', 3003: 'L_TMAC_T',
    808: 'XIAOLU', 900: 'UL_SIEG', 901: 'UL_OPHELIA', 902: 'UL_ALICE',
    903: 'UL_YOSHINO', 904: 'UL_SARU',
}

pid = find_pid()
if not pid:
    print('FreeStyle.exe not found')
    sys.exit(1)

print(f'PID={pid}')

session = frida.attach(pid)

head_name = CHAR_MAP.get(TARGET_HEAD_CODE, '???')
body_name = CHAR_MAP.get(TARGET_BODY_CODE, '???')
print(f'目标: 头模 c{TARGET_HEAD_CODE}({head_name}) + 体模 c{TARGET_BODY_CODE}({body_name})')
print(f'替换模式: {"仅替换" + str(REPLACE_ONLY_FROM) if REPLACE_ONLY_FROM else "替换所有c-code"}')

JS_CODE = r'''
'use strict';

var msvcr = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr.getExportByName('sprintf');

var CUSTOMIZE_PREFIX = 0x74737563;
var ENABLE_REPLACE = ''' + ('true' if ENABLE_REPLACE else 'false') + r''';
var TARGET_HEAD = ''' + str(TARGET_HEAD_CODE) + r''';
var TARGET_BODY = ''' + str(TARGET_BODY_CODE) + r''';
var REPLACE_ONLY_FROM = ''' + str(REPLACE_ONLY_FROM) + r''';

var callIndex = 0;
var cCodeCount = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            try { if (args[1].readU32() !== CUSTOMIZE_PREFIX) return; } catch(e) { return; }
            var fmt = args[1].readUtf8String(80);
            if (!fmt || fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            callIndex++;
            var originalIC = args[2].toInt32();
            var isCcode = fmt.indexOf('c%d.xml') >= 0;

            if (isCcode && ENABLE_REPLACE) {
                cCodeCount++;
                var shouldReplace = REPLACE_ONLY_FROM.length === 0 || REPLACE_ONLY_FROM.indexOf(originalIC) >= 0;

                if (shouldReplace) {
                    // 第1个c-code调用用头模，第2个用体模
                    var targetIC = (cCodeCount % 2 === 1) ? TARGET_HEAD : TARGET_BODY;
                    args[2] = ptr(targetIC);
                    send({
                        t: 'replace',
                        idx: callIndex,
                        orig: originalIC,
                        new: targetIC,
                        ret: this.returnAddress.toString()
                    });
                } else {
                    send({
                        t: 'pass',
                        idx: callIndex,
                        ic: originalIC,
                        ret: this.returnAddress.toString()
                    });
                }
            }
        } catch(e) {
            send({t:'err', msg: e.message});
        }
    }
});

send({t:'ready', addr: sprintfAddr.toString()});
'''

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'ready':
            print(f'[READY] sprintf @ {p["addr"]}')
        elif t == 'replace':
            orig_name = CHAR_MAP.get(p['orig'], '???')
            new_name = CHAR_MAP.get(p['new'], '???')
            print(f'  #{p["idx"]:3d}  c{p["orig"]}({orig_name}) → c{p["new"]}({new_name})  ret={p["ret"]}', flush=True)
        elif t == 'pass':
            orig_name = CHAR_MAP.get(p['ic'], '???')
            print(f'  #{p["idx"]:3d}  c{p["ic"]}({orig_name}) [跳过]  ret={p["ret"]}', flush=True)
        elif t == 'err':
            print(f'[ERR] {p.get("msg","")}', flush=True)
    elif msg['type'] == 'error':
        print(f'[FRIDA ERROR] {msg.get("description","")}', flush=True)

script = session.create_script(JS_CODE)
script.on('message', on_message)
script.load()
print('Hook已注入！进房间触发角色加载即可替换。Ctrl+C退出\n', flush=True)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n退出')
    session.detach()
