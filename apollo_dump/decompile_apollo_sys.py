"""
Decompile key functions from Apollo.sys using Ghidra headless + PyGhidra.
Usage: D:\py\反编译\ghidra_12.0.1_PUBLIC\support\pyghidraRun.bat --script decompile_apollo_sys.py
"""
import sys
import os

# PyGhidra provides these automatically in headless mode
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

# ---- CONFIG ----
OUTPUT_DIR = r"D:\py\反编译\FreeStyle\apollo_dump\r2_output"
PROJECT_DIR = r"D:\ghidra_projects"
PROJECT_NAME = "ApolloSys"
PROGRAM_NAME = "Apollo.sys"

# Key functions to decompile (from killplan §13.6)
FUNCTIONS = {
    # P1 targets
    "DeviceIoControl_dispatch": 0x14008d00d,   # 30KB - likely DeviceIoControl dispatcher
    "Unknown_large_2":          0x14013663a,   # 16KB
    "DR_clear_area":            0x140001986,   # DR register operations area
    "Process_whitelist":        0x140001d48,   # PsLookupProcessByProcessId chain
    
    # Anti-debug
    "KdDisableDebugger_call":   0x1402399e8,   # Calls KdDisableDebugger in loop
    "KdDebuggerEnabled_check":  0x140239970,   # Checks KdDebuggerEnabled
    
    # Driver entry & dispatch
    "DriverEntry":              0x140239e6a,   # Driver entry point (618 bytes)
    
    # Opaque predicates / obfuscation
    "Opaque_predicate_1":       0x1400016b0,
    "Opaque_predicate_2":       0x1400016ca,
    
    # IRP dispatch stub
    "IRP_dispatch_stub":        0x1400017e0,
}

def decompile_single(decomp, program, addr, name):
    """Decompile a single function at given address."""
    func = program.getFunctionManager().getFunctionAt(program.getAddressFactory().getDefaultAddressSpace().getAddress(addr))
    if func is None:
        print(f"[SKIP] {name} @ {addr:#x}: no function found", file=sys.stderr)
        return None
    
    result = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
    if result is None or not result.decompileCompleted():
        print(f"[FAIL] {name} @ {addr:#x}: decompilation failed: {result.getErrorMessage() if result else 'null result'}", file=sys.stderr)
        return None
    
    c_code = result.getDecompiledFunction().getC()
    return c_code

def main():
    # Get the current program from PyGhidra
    from ghidra.framework.model import ProjectLocator
    from ghidra.framework.project import DefaultProjectManager
    from ghidra.program.flatapi import FlatProgramAPI
    
    # PyGhidra headless: currentProgram, currentLocation etc. are pre-set
    try:
        program = currentProgram  # noqa: F821
    except NameError:
        print("ERROR: currentProgram not available. Run this via pyghidraRun.bat with --script flag", file=sys.stderr)
        sys.exit(1)
    
    print(f"Program: {program.getName()}")
    print(f"Image base: {program.getImageBase()}")
    print(f"Functions total: {program.getFunctionManager().getFunctionCount()}")
    print()
    
    # Set up decompiler
    decomp = DecompInterface()
    decomp.openProgram(program)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for name, addr in FUNCTIONS.items():
        print(f"[DECOMPILE] {name} @ {addr:#010x} ...")
        c_code = decompile_single(decomp, program, addr, name)
        
        if c_code:
            out_path = os.path.join(OUTPUT_DIR, f"Apollo_sys_{name}.c")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(f"/* {name} @ 0x{addr:x} */\n")
                f.write(f"/* Function: {name} */\n")
                f.write(c_code)
                f.write("\n")
            print(f"  -> Saved to {out_path} ({len(c_code)} chars)")
            # Also print first 20 lines to console
            lines = c_code.split('\n')
            for line in lines[:20]:
                print(f"  | {line}")
            if len(lines) > 20:
                print(f"  | ... ({len(lines)} total lines)")
        print()
    
    decomp.dispose()
    print("Done. All output in:", OUTPUT_DIR)

if __name__ == "__main__":
    main()