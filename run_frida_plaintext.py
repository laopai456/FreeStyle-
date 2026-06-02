"""run_frida_plaintext.py — 运行 frida_capture_plaintext.js 并保存输出"""
import frida
import sys
import json

SCRIPT_PATH = r"d:\py\反编译\FreeStyle\frida_capture_v2.js"
OUTPUT_PATH = r"d:\py\反编译\FreeStyle\plaintext_v2.txt"

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    def on_msg(msg, data):
        if msg["type"] == "send":
            payload = msg["payload"]
            # JSON 消息用 indent 输出便于阅读
            try:
                obj = json.loads(payload)
                line = json.dumps(obj, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                line = str(payload)
            print(line, flush=True)
            f.write(line + "\n")
            f.flush()
        elif msg["type"] == "error":
            err = msg.get("stack", msg.get("description", str(msg)))
            print(f"ERROR: {err}", flush=True)
            f.write(f"ERROR: {err}\n")
            f.flush()

    try:
        session = frida.attach("FreeStyle.exe")
    except frida.ProcessNotFoundError:
        print("FreeStyle.exe not found. Start the game first.")
        sys.exit(1)

    with open(SCRIPT_PATH, "r", encoding="utf-8") as sf:
        script_code = sf.read()

    script = session.create_script(script_code)
    script.on("message", on_msg)
    script.load()

    print("Hooks loaded. Login, enter game, operate for 1-2 min, then Ctrl+C...")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone. Output saved to plaintext_output.txt")
        session.detach()