from scapy.all import conf

print("Available interfaces:\n")
for i, face in enumerate(conf.ifaces):
    data = conf.ifaces[face]
    print(f'  [{i}] {face}')
    print(f'      desc: {data.description if hasattr(data, "description") else "?"}')
    if hasattr(data, 'ips') and data.ips:
        print(f'      IPs:  {data.ips}')
    print()