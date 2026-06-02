"""
run_find_crypto.py — 运行 find_crypto_funcs.js，扫描内存找加密函数
"""
import frida
import sys
import json

SCRIPT_PATH = r"d:\py\反编译\FreeStyle\find_crypto_funcs.js"
OUTPUT_PATH = r"d:\py\反编译\FreeStyle\apollo_dump\crypto_funcs_scan.txt"

def main():
    print("=" * 60)
    print("  find_crypto_funcs — 内存扫描加密函数地址")
    print("=" * 60)

    try:
        session = frida.attach("FreeStyle.exe")
    except frida.ProcessNotFoundError:
        print("[!] FreeStyle.exe 未运行，请先启动游戏！")
        sys.exit(1)

    output_lines = []
    
    def on_msg(msg, data):
        if msg["type"] == "send":
            payload = msg["payload"]
            if isinstance(payload, dict) and "type" in payload:
                t = payload["type"]
                if t == "result":
                    header = payload.get("header")
                    msg_text = payload.get("msg")
                    if header:
                        line = "\n" + header
                    else:
                        line = msg_text
                    print(line, flush=True)
                    output_lines.append(line)
                elif t == "info":
                    line = "[INFO] " + payload["msg"]
                    print(line, flush=True)
                    output_lines.append(line)
                elif t == "done":
                    line = "[DONE] " + payload["msg"]
                    print(line, flush=True)
                    output_lines.append(line)
                elif t == "error":
                    line = "[ERROR] " + payload["msg"]
                    print(line, flush=True)
                    output_lines.append(line)
            else:
                print(str(payload), flush=True)
        elif msg["type"] == "error":
            err = msg.get("stack", msg.get("description", str(msg)))
            print(f"[ERROR] {err}", flush=True)

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on("message", on_msg)
    script.load()

    print("[*] 等待扫描完成（约 10-30 秒）...", flush=True)
    try:
        import time
        time.sleep(60)  # 最多等 60 秒
    except KeyboardInterrupt:
        pass

    # 保存结果
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\n[+] 结果保存至: {OUTPUT_PATH}")

    session.detach()


if __name__ == "__main__":
    main()