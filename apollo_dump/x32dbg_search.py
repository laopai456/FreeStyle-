import socket, struct, json, time

REQ_PORT = 59595
SUB_PORT = 61903

def send_cmd(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(('127.0.0.1', REQ_PORT))
    msg = json.dumps({"type": "request", "command": cmd})
    s.send(msg.encode() + b'\n')
    time.sleep(0.5)
    data = b''
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
        except: break
    s.close()
    return data.decode('utf-8', errors='replace')

# Search for push 0x028405CC (68 CC 05 84 02) in code section
print("Searching for 'push 0x028405CC' in 0x401000-0x2C00000...")
result = send_cmd("findall 401000, 68CC058402")
print(result[:2000])

# Also search for mov reg, 0x028405CC patterns
print("\nSearching for 'mov eax, 0x028405CC' (B8 CC058402)...")
result2 = send_cmd("findall 401000, B8CC058402")
print(result2[:2000])

# Search for the "couldn't open file" string reference
print("\nSearching for push 0x028406A8 (couldn't open file)...")
result3 = send_cmd("findall 401000, 68A8068402")
print(result3[:2000])

# Try broader: search for "SSKF" reference
print("\nSearching for 'SSKF' (53534B46) reference...")
result4 = send_cmd("findall 401000, 53534B46")
print(result4[:2000])
