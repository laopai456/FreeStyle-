"""run_frida_recon.py — 运行 frida_crypto_recon.js 并保存输出"""
import frida
import sys

SCRIPT_PATH = r"d:\py\反编译\FreeStyle\frida_crypto_recon.js"
OUTPUT_PATH = r"d:\py\反编译\FreeStyle\recon_output.txt"

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    def on_msg(msg, data):
        if msg["type"] == "send":
            payload = msg["payload"]
            print(payload, flush=True)
            f.write(payload + "\n")
            f.flush()
        elif msg["type"] == "error":
            err = msg.get("stack", msg.get("description", str(msg)))
            print(f"ERROR: {err}", flush=True)
            f.write(f"ERROR: {err}\n")
            f.flush()

    try:
        session = frida.attach("FreeStyle.exe")
    except frida.ProcessNotFoundError:
        print("FreeStyle.exe not found. Please start the game first.")
        sys.exit(1)

    with open(SCRIPT_PATH, "r", encoding="utf-8") as sf:
        script_code = sf.read()

    script = session.create_script(script_code)
    script.on("message", on_msg)
    script.load()

    print("Hooks loaded. Operate in game for 1-2 minutes, then press Ctrl+C...")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone. Output saved to recon_output.txt")
        session.detach()