import sys
sys.stdout.reconfigure(encoding='utf-8')

pak = open(r'C:\Program Files (x86)\T2CN\街头篮球\item768.pak', 'rb').read()

# XOR decode entire pak and search for 50125711
dec = bytes(b ^ 0xFF for b in pak)
idx = dec.find(b'50125711')
if idx >= 0:
    print(f'50125711 found at offset 0x{idx:X} in XOR-decoded item768.pak')
    ctx = dec[max(0,idx-200):idx+300]
    print('Context:')
    print(ctx.decode('utf-8', errors='replace'))
else:
    print('50125711 NOT FOUND in item768.pak (XOR decoded)')

# Also search in item767.pak
print()
pak767 = open(r'C:\Program Files (x86)\T2CN\街头篮球\item767.pak', 'rb').read()
dec767 = bytes(b ^ 0xFF for b in pak767)
idx767 = dec767.find(b'50125711')
if idx767 >= 0:
    print(f'50125711 found at offset 0x{idx767:X} in item767.pak')
else:
    print('50125711 NOT FOUND in item767.pak (XOR decoded)')

# ALSO check: does the 5293-byte file at Resource\item\ actually contain 50125711?
print()
res_item = open(r'C:\Program Files (x86)\T2CN\街头篮球\Resource\item\i50125711.bml', 'rb').read()
res_dec = bytes(b ^ 0xFF for b in res_item)
ridx = res_dec.find(b'50125711')
if ridx >= 0:
    print(f'Resource\item\i50125711.bml: 50125711 found at offset 0x{ridx:X}')
    ctx = res_dec[max(0,ridx-100):ridx+400]
    print('Context:')
    print(ctx.decode('utf-8', errors='replace'))
else:
    print('Resource\item\i50125711.bml: 50125711 NOT FOUND')