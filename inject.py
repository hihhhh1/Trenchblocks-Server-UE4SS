import ctypes
import os
import sys
import time
import subprocess
from ctypes import wintypes

PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
PAGE_READWRITE = 0x04

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

VirtualAllocEx = kernel32.VirtualAllocEx
VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
VirtualAllocEx.restype = wintypes.LPVOID

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

GetProcAddress = kernel32.GetProcAddress
GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
GetProcAddress.restype = wintypes.LPVOID

GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
GetModuleHandleW.restype = wintypes.HMODULE

CreateRemoteThread = kernel32.CreateRemoteThread
CreateRemoteThread.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
CreateRemoteThread.restype = wintypes.HANDLE

WaitForSingleObject = kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
WaitForSingleObject.restype = wintypes.DWORD

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

def find_server_paths():
    current = os.path.abspath(os.getcwd())
    candidates = [
        os.path.join(current, "TrenchblocksServer-Win64-Shipping.exe"),
        os.path.join(current, "Trenchblocks", "Binaries", "Win64", "TrenchblocksServer-Win64-Shipping.exe"),
        os.path.join(current, "Binaries", "Win64", "TrenchblocksServer-Win64-Shipping.exe"),
    ]
    
    for exe in candidates:
        if os.path.exists(exe):
            bin_dir = os.path.dirname(exe)
            dll = os.path.join(bin_dir, "ue4ss", "UE4SS.dll")
            if not os.path.exists(dll):
                dll = os.path.join(bin_dir, "UE4SS.dll")
            return exe, bin_dir, dll
            
    for root, dirs, files in os.walk(current):
        if "TrenchblocksServer-Win64-Shipping.exe" in files:
            exe = os.path.join(root, "TrenchblocksServer-Win64-Shipping.exe")
            bin_dir = root
            dll = os.path.join(bin_dir, "ue4ss", "UE4SS.dll")
            if not os.path.exists(dll):
                dll = os.path.join(bin_dir, "UE4SS.dll")
            return exe, bin_dir, dll
            
    return None, None, None

def inject_dll(pid, dll_path):
    print(f"[*] Injecting '{dll_path}' into PID {pid}...")
    
    if not os.path.exists(dll_path):
        print(f"[-] Error: DLL not found at {dll_path}")
        return False
        
    dll_path_encoded = os.path.abspath(dll_path).encode('utf-16le') + b'\x00\x00'
    path_len = len(dll_path_encoded)
    
    h_process = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        print(f"[-] OpenProcess failed: {ctypes.get_last_error()}")
        return False
        
    try:
        remote_mem = VirtualAllocEx(h_process, None, path_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not remote_mem:
            return False
            
        bytes_written = ctypes.c_size_t(0)
        if not WriteProcessMemory(h_process, remote_mem, dll_path_encoded, path_len, ctypes.byref(bytes_written)):
            return False
            
        h_k32 = GetModuleHandleW("kernel32.dll")
        load_library_w = GetProcAddress(h_k32, b"LoadLibraryW")
        if not load_library_w:
            return False
            
        h_thread = CreateRemoteThread(h_process, None, 0, load_library_w, remote_mem, 0, None)
        if not h_thread:
            return False
            
        WaitForSingleObject(h_thread, 5000)
        CloseHandle(h_thread)
        print("[+] UE4SS.dll successfully injected into Dedicated Server!")
        return True
    finally:
        CloseHandle(h_process)

def main():
    print("==================================================")
    print("  Trenchblocks Dedicated Server Launcher & UE4SS  ")
    print("==================================================")
    
    server_exe, bin_dir, ue4ss_dll = find_server_paths()
    if not server_exe or not os.path.exists(server_exe):
        print("[-] Error: Could not locate 'TrenchblocksServer-Win64-Shipping.exe'.")
        print("    Please run this script from the server root or Trenchblocks/Binaries/Win64/.")
        sys.exit(1)
        
    if not ue4ss_dll or not os.path.exists(ue4ss_dll):
        print(f"[-] Error: Could not locate UE4SS.dll in '{bin_dir}' or '{bin_dir}\\ue4ss'.")
        sys.exit(1)
        
    cmd = [server_exe] + sys.argv[1:]
    print(f"[*] Found Server Exe: {server_exe}")
    print(f"[*] Found UE4SS DLL:  {ue4ss_dll}")
    print(f"[*] Launching: {' '.join(cmd)}")
    
    proc = subprocess.Popen(cmd, cwd=bin_dir)
    print(f"[*] Server process started (PID: {proc.pid})")
    
    # 1.0s golden time for server initialization
    time.sleep(1.0)
    
    if inject_dll(proc.pid, ue4ss_dll):
        print("[+] Dedicated Server and UE4SS are running perfectly!")
    else:
        print("[-] Injection failed.")

if __name__ == "__main__":
    main()
