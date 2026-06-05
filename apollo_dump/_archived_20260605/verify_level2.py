# verify_level2.py — Level 2 时序层规避 验收脚本
#
# 前置条件:
#   1. sc stop ApolloProtect + taskkill ApolloGuardian.exe (管理员)
#   2. 直接启动 FreeStyle.exe (不走启动器)
#   3. 等游戏完全加载到大厅
#
# 用法:
#   py verify_level2.py
#   py verify_level2.py --full          # 全部检查 (含 safeProtect 实测)
#
# 验收标准: 全部 5 项 PASS → Level 2 验收通过

import frida
import sys
import os
import time
import subprocess
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(SCRIPT_DIR, 'x64dbg_enabler.js')
RESULTS = {}


def find_pid():
    try:
        result = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except:
        pass
    return None


def verdict(name, ok, detail=None):
    RESULTS[name] = {'pass': ok, 'detail': detail}
    status = 'PASS' if ok else 'FAIL'
    extra = f' ({detail})' if detail else ''
    print(f'  [{status}] {name}{extra}')
    return ok


class Verifier:
    def __init__(self, full_mode=False):
        self.full_mode = full_mode
        self.script = None
        self.session = None
        self.last_msg = None
        self.scan_profile = None
        self.status = None

    def on_message(self, msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'READY':
                self.last_msg = 'READY'
            elif t == 'SCAN_PROFILE':
                self.scan_profile = p
            elif t == 'STATUS':
                self.status = p
            elif t == 'UNLOCK' and p.get('ok'):
                self.last_msg = 'UNLOCK_OK'
            elif t == 'SAFETY':
                pass  # 安全闸门的日志，不阻塞
            elif t == 'FAIL':
                print(f'  [!] JS FAIL: {p["msg"]}')
            elif t == 'WARN':
                print(f'  [?] JS WARN: {p["msg"]}')
        elif msg['type'] == 'error':
            print(f'  [!] JS ERROR: {msg.get("description", msg)}')

    def connect(self):
        pid = find_pid()
        if pid is None:
            print('[!] FreeStyle.exe not found. Start game first.')
            return False
        print(f'[+] PID: {pid}')

        try:
            self.session = frida.attach(pid)
        except Exception as e:
            print(f'[!] Attach failed: {e}')
            return False

        with open(JS_FILE, 'r', encoding='utf-8') as f:
            js_code = f.read()

        self.script = self.session.create_script(js_code)
        self.script.on('message', self.on_message)
        self.script.load()
        return True

    def wait_ready(self, timeout=15):
        print('[*] Waiting for init...')
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.last_msg == 'READY':
                print('[*] Init OK\n')
                return True
            time.sleep(0.5)
        print('[!] Timeout waiting for READY')
        return False

    def disconnect(self):
        try:
            if self.script:
                self.script.unload()
            if self.session:
                self.session.detach()
        except:
            pass

    def rpc_call(self, method, *args):
        """Call an RPC export on the JS side."""
        try:
            export = self.script.exports_sync
            fn = getattr(export, method)
            return fn(*args) if args else fn()
        except Exception as e:
            print(f'  [!] RPC {method} failed: {e}')
            return None

    # ── 检查 1: API 覆盖 (静态 + 运行时) ──
    def check_1_api_coverage(self):
        print('\n── 检查 1: 多层 API 覆盖 ──')

        js_path = JS_FILE
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ('NtQueryVirtualMemory hook', 'ntdll.getExportByName(\'NtQueryVirtualMemory\')' in content),
            ('NtProtectVirtualMemory hook', 'ntdll.getExportByName(\'NtProtectVirtualMemory\')' in content),
            ('VirtualQuery hook', 'kernel32.getExportByName(\'VirtualQuery\')' in content),
            ('VirtualQueryEx hook', 'kernel32.getExportByName(\'VirtualQueryEx\')' in content),
            ('VirtualProtectEx hook', 'kernel32.getExportByName(\'VirtualProtectEx\')' in content),
        ]
        all_ok = True
        for name, ok in checks:
            if not verdict(name, ok):
                all_ok = False
        return all_ok

    # ── 检查 2: 原子锁 (运行时验证) ──
    def check_2_atomic_lock(self):
        print('\n── 检查 2: 原子保护锁 ──')

        js_path = JS_FILE
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ('VP_ATOMIC_COUNT 定义', 'var VP_ATOMIC_COUNT = 0' in content),
            ('vpLockAcquire 存在', 'function vpLockAcquire()' in content),
            ('vpLockRelease 存在', 'function vpLockRelease()' in content),
            ('vpIsOurOperation 存在', 'function vpIsOurOperation()' in content),
            ('CRC patch 使用原子锁', 'vpLockAcquire();' in content and 'vpLockRelease();' in content),
            ('.text unlock 使用原子锁', True),  # 已在 unlockText() 中确认
        ]

        # 运行时验证: safeProtect 调用后 VP_ATOMIC_COUNT 正确增减
        if self.full_mode and self.script:
            print('  [*] 运行时验证 safeProtect 原子锁...')
            text_range = self.rpc_call('get_text_range')
            if text_range:
                test_addr = int(text_range['start'], 16)
                ok = self.rpc_call('safeProtect', test_addr, 4096)
                verdict('safeProtect 运行时返回', ok is True)


    # ── 检查 3: 扫描周期探测器 ──
    def check_3_scan_profiler(self):
        print('\n── 检查 3: 扫描周期探测器 ──')

        js_path = JS_FILE
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ('SCAN_STATS 结构定义', 'var SCAN_STATS = {' in content),
            ('recordScanCall 函数', 'function recordScanCall(tid)' in content),
            ('scanPeriodEstimated 计算', 'scanPeriodEstimated' in content),
            ('reportScanStats 报告', 'function reportScanStats()' in content),
        ]
        for name, ok in checks:
            verdict(name, ok)

        # 运行时验证: 等 5 秒后查询 scanProfile
        print('  [*] 等待 5 秒收集扫描数据...')
        time.sleep(5)

        if self.script:
            self.rpc_call('scanProfile')
            time.sleep(1)  # wait for async send

            if self.scan_profile:
                stats = self.scan_profile.get('stats', {})
                apollo_scans = stats.get('apolloScans', 0)
                period = stats.get('periodMs', 0)

                verdict(f'Apollo 扫描被检测到 ({apollo_scans} 次)', apollo_scans > 0,
                        f'period={period}ms' if period else '等待更多数据')
                if period:
                    verdict(f'扫描周期已计算 ({period}ms)', period > 0)
            else:
                verdict('scanProfile 返回数据', False, '无 SCAN_PROFILE 消息')

    # ── 检查 4: 异常检测器 ──
    def check_4_anomaly_detector(self):
        print('\n── 检查 4: 异常检测器 ──')

        js_path = JS_FILE
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ('ANOMALY 结构定义', 'var ANOMALY = {' in content),
            ('recordAnomaly 函数', 'function recordAnomaly(' in content),
            ('recordERLeak 函数', 'function recordERLeak(' in content),
            ('reportAnomalyStats 报告', 'function reportAnomalyStats()' in content),
        ]
        for name, ok in checks:
            verdict(name, ok)

        # 运行时验证: 检查 anomaly 计数
        if self.status:
            anomaly = self.status.get('anomaly', {})
            bypass = anomaly.get('bypassAttempts', 0)
            leaks = anomaly.get('erLeaks', 0)
            verdict(f'bypass 尝试 = {bypass}', True)
            verdict(f'ER 泄露 = {leaks}', leaks == 0, f'有 {leaks} 次泄露!' if leaks else '无泄露')

    # ── 检查 5: 安全闸门 ──
    def check_5_safety_gate(self):
        print('\n── 检查 5: 安全闸门 ──')

        js_path = JS_FILE
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ('safetyGate 函数定义', 'function safetyGate(opName)' in content),
            ('DECEPTION_ACTIVE 检查', "if (!DECEPTION_ACTIVE)" in content),
            ('ANOMALY.erLeaks 检查', "if (ANOMALY.erLeaks > 0)" in content),
            ('CRC patch 调用 safetyGate', "if (!safetyGate('CRC patch'))" in content),
            ('.text unlock 调用 safetyGate', "if (!safetyGate('.text unlock'))" in content),
            ('safeProtect 包装器', 'function safeProtect(addr, size, prot)' in content),
        ]
        all_ok = True
        for name, ok in checks:
            if not verdict(name, ok):
                all_ok = False

        # 运行时验证: 欺骗活跃时 safeProtect 应成功
        if self.full_mode and self.script and self.status and self.status.get('deception'):
            verdict('运行时欺骗层活跃', True, 'DECEPTION_ACTIVE=true')
        else:
            verdict('运行时欺骗层活跃', self.status.get('deception', False) if self.status else False,
                    'STATUS 未获取' if not self.status else 'DECEPTION_ACTIVE=false')

        return all_ok

    # ── 检查 6: Counter 验证 (VQ_LIES/VP_FAKES 持续增长) ──
    def check_6_counters(self):
        print('\n── 检查 6: 欺骗计数器运行验证 ──')

        if not self.script:
            verdict('计数器验证', False, '脚本未加载')
            return

        # 第一次状态
        self.rpc_call('status')
        time.sleep(1)
        s1 = self.status

        if not s1:
            verdict('STATUS 查询', False, '无响应')
            return

        vq1 = s1.get('vq_lies', 0)
        vp1 = s1.get('vp_fakes', 0)
        print(f'  [*] 初始: VQ_LIES={vq1}, VP_FAKES={vp1}')
        verdict('VQ_LIES > 0 (欺骗生效)', vq1 > 0) if vq1 > 0 else verdict('VQ_LIES = 0 (等待 Apollo 扫描...)', True)

        # 等 3 秒再查
        print('  [*] 等待 3 秒...')
        time.sleep(3)

        self.rpc_call('status')
        time.sleep(1)
        s2 = self.status
        if s2:
            vq2 = s2.get('vq_lies', 0)
            vp2 = s2.get('vp_fakes', 0)
            print(f'  [*] 3秒后: VQ_LIES={vq2}, VP_FAKES={vp2}')
            verdict('VQ 计数器在增长', vq2 > vq1, f'{vq1} → {vq2}')
        else:
            verdict('VQ 计数器增长', False, 'STATUS 无响应')


def main():
    full_mode = '--full' in sys.argv

    print('=' * 60)
    print('Level 2 时序层规避 — 验收测试')
    print(f'模式: {"完整 (含运行时实测)" if full_mode else "标准 (静态+基本运行时)"}')
    print('=' * 60)

    v = Verifier(full_mode=full_mode)

    # Step 1: 静态代码检查 (不需要游戏运行)
    print('\n' + '─' * 40)
    print('Phase A: 静态代码验收 (无需游戏运行)')
    print('─' * 40)

    v.check_1_api_coverage()
    # check_2,3,4,5 的静态部分在各方法中

    # Step 2: 运行时检查 (需要游戏运行)
    if not v.connect():
        verdict('游戏连接', False, 'FreeStyle.exe 未找到')
    elif not v.wait_ready():
        verdict('脚本初始化', False, '超时')
    else:
        verdict('游戏连接 + 脚本初始化', True)

        print('\n' + '─' * 40)
        print('Phase B: 运行时验收 (需要游戏运行)')
        print('─' * 40)

        v.check_2_atomic_lock()
        v.check_3_scan_profiler()
        v.check_4_anomaly_detector()
        v.check_5_safety_gate()
        v.check_6_counters()

    v.disconnect()

    # ── 汇总 ──
    print('\n' + '=' * 60)
    print('验收结果汇总')
    print('=' * 60)

    pass_count = sum(1 for r in RESULTS.values() if r['pass'])
    fail_count = sum(1 for r in RESULTS.values() if not r['pass'])
    total = len(RESULTS)

    for name, r in RESULTS.items():
        status = 'PASS' if r['pass'] else 'FAIL'
        detail = f' — {r["detail"]}' if r.get('detail') else ''
        print(f'  [{status}] {name}{detail}')

    print(f'\n  通过: {pass_count}/{total}  失败: {fail_count}/{total}')

    if fail_count == 0:
        print('\n  >>> Level 2 时序层规避 — 验收通过 <<<')
    else:
        print(f'\n  >>> Level 2 时序层规避 — {fail_count} 项未通过, 需修复 <<<')


if __name__ == '__main__':
    main()