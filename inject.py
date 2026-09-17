import os
import sys
import shutil
import struct

def find_server_exe():
    current = os.path.abspath(os.getcwd())
    candidates = [
        os.path.join(current, "Trenchblocks", "Binaries", "Win64", "TrenchblocksServer-Win64-Shipping.exe"),
        os.path.join(current, "Binaries", "Win64", "TrenchblocksServer-Win64-Shipping.exe"),
        os.path.join(current, "TrenchblocksServer-Win64-Shipping.exe")
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
            
    for root, dirs, files in os.walk(current):
        if "TrenchblocksServer-Win64-Shipping.exe" in files:
            return os.path.join(root, "TrenchblocksServer-Win64-Shipping.exe")
            
    return None

def align(val, alignment):
    return (val + alignment - 1) & ~(alignment - 1)

def inject_dll_to_pe(exe_path, dll_name="UE4SS.dll"):
    print(f"[*] Reading binary: {exe_path}")
    with open(exe_path, "rb") as f:
        data = bytearray(f.read())
        
    if data[:2] != b"MZ":
        raise ValueError("Invalid PE: Missing MZ header")
        
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
        raise ValueError("Invalid PE: Missing PE signature")
        
    num_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
    opt_header_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    opt_header_offset = pe_offset + 24
    
    magic = struct.unpack_from("<H", data, opt_header_offset)[0]
    if magic != 0x20B:
        raise ValueError("Only 64-bit PE binaries are supported")
        
    image_base = struct.unpack_from("<Q", data, opt_header_offset + 24)[0]
    section_alignment = struct.unpack_from("<I", data, opt_header_offset + 32)[0]
    file_alignment = struct.unpack_from("<I", data, opt_header_offset + 36)[0]
    size_of_image = struct.unpack_from("<I", data, opt_header_offset + 56)[0]
    size_of_headers = struct.unpack_from("<I", data, opt_header_offset + 60)[0]
    
    data_dir_offset = opt_header_offset + 112
    import_rva, import_size = struct.unpack_from("<II", data, data_dir_offset + 8)
    
    section_headers_offset = opt_header_offset + opt_header_size
    last_section_offset = section_headers_offset + (num_sections - 1) * 40
    
    last_sec_name, last_sec_vsize, last_sec_va, last_sec_raw_size, last_sec_raw_ptr = struct.unpack_from("<8sIIII", data, last_section_offset)
    
    # Check if already injected
    if b".ue4ss\x00\x00\x00" in data[section_headers_offset:section_headers_offset + num_sections * 40]:
        print("[!] Target binary already has .ue4ss section injected.")
        return False
        
    new_sec_offset = section_headers_offset + num_sections * 40
    if new_sec_offset + 40 > size_of_headers:
        raise ValueError("Not enough space in header for a new section")
        
    new_sec_va = align(last_sec_va + max(last_sec_vsize, last_sec_raw_size), section_alignment)
    new_sec_raw_ptr = align(len(data), file_alignment)
    
    existing_import_data = bytearray()
    if import_rva != 0 and import_size != 0:
        for i in range(num_sections):
            sec_offset = section_headers_offset + i * 40
            s_name, s_vsize, s_va, s_raw_size, s_raw_ptr = struct.unpack_from("<8sIIII", data, sec_offset)
            if s_va <= import_rva < s_va + s_raw_size:
                offset_in_file = s_raw_ptr + (import_rva - s_va)
                existing_import_data = bytearray(data[offset_in_file:offset_in_file + import_size])
                break
                
    if len(existing_import_data) >= 20 and existing_import_data[-20:] == b"\x00" * 20:
        existing_descriptor_count = len(existing_import_data) // 20 - 1
    else:
        existing_descriptor_count = 0
        
    payload = bytearray()
    
    num_descriptors = existing_descriptor_count + 1 + 1
    descriptor_table_size = num_descriptors * 20
    
    dll_name_bytes = dll_name.encode('ascii') + b"\x00"
    func_name_bytes = b"\x00\x00DummyExport\x00"
    
    dll_name_rel_offset = descriptor_table_size
    func_name_rel_offset = dll_name_rel_offset + len(dll_name_bytes)
    if func_name_rel_offset % 2 != 0:
        func_name_bytes = b"\x00" + func_name_bytes
        func_name_rel_offset += 1
        
    ilt_rel_offset = align(func_name_rel_offset + len(func_name_bytes), 8)
    iat_rel_offset = ilt_rel_offset + 16
    
    new_sec_payload_size = iat_rel_offset + 16
    
    if existing_descriptor_count > 0:
        payload.extend(existing_import_data[:existing_descriptor_count * 20])
        
    new_ilt_rva = new_sec_va + ilt_rel_offset
    new_name_rva = new_sec_va + dll_name_rel_offset
    new_iat_rva = new_sec_va + iat_rel_offset
    
    new_descriptor = struct.pack("<IIIII", new_ilt_rva, 0, 0, new_name_rva, new_iat_rva)
    payload.extend(new_descriptor)
    payload.extend(b"\x00" * 20)
    payload.extend(dll_name_bytes)
    
    if len(payload) < func_name_rel_offset:
        payload.extend(b"\x00" * (func_name_rel_offset - len(payload)))
    payload.extend(func_name_bytes)
    
    func_rva = new_sec_va + func_name_rel_offset
    if len(payload) < ilt_rel_offset:
        payload.extend(b"\x00" * (ilt_rel_offset - len(payload)))
        
    payload.extend(struct.pack("<Q", func_rva))
    payload.extend(struct.pack("<Q", 0))
    payload.extend(struct.pack("<Q", func_rva))
    payload.extend(struct.pack("<Q", 0))
    
    new_sec_raw_size = align(len(payload), file_alignment)
    new_sec_vsize = len(payload)
    
    payload.extend(b"\x00" * (new_sec_raw_size - len(payload)))
    
    sec_name = b".ue4ss\x00\x00"
    sec_characteristics = 0xC0000040
    
    struct.pack_into("<8sIIIIIIHHI", data, new_sec_offset,
                     sec_name,
                     new_sec_vsize,
                     new_sec_va,
                     new_sec_raw_size,
                     new_sec_raw_ptr,
                     0, 0, 0, 0,
                     sec_characteristics)
                     
    struct.pack_into("<H", data, pe_offset + 6, num_sections + 1)
    struct.pack_into("<I", data, opt_header_offset + 56, align(new_sec_va + new_sec_vsize, section_alignment))
    struct.pack_into("<II", data, data_dir_offset + 8, new_sec_va, descriptor_table_size)
    
    if len(data) < new_sec_raw_ptr:
        data.extend(b"\x00" * (new_sec_raw_ptr - len(data)))
        
    data.extend(payload)
    
    bak_path = exe_path + ".bak"
    if not os.path.exists(bak_path):
        print(f"[*] Creating backup: {bak_path}")
        shutil.copy2(exe_path, bak_path)
        
    print(f"[*] Writing patched PE to: {exe_path}")
    with open(exe_path, "wb") as f:
        f.write(data)
        
    print(f"[+] Successfully injected '{dll_name}' into {os.path.basename(exe_path)}!")
    return True

def main():
    print("==================================================")
    print("  Trenchblocks Dedicated Server - UE4SS Injector  ")
    print("==================================================")
    
    exe_path = find_server_exe()
    if not exe_path:
        print("[!] Error: Could not locate 'TrenchblocksServer-Win64-Shipping.exe'.")
        print("    Please run this script from the game root or Trenchblocks/Binaries/Win64/.")
        sys.exit(1)
        
    print(f"[*] Server Binary Found: {exe_path}")
    
    try:
        inject_dll_to_pe(exe_path, "UE4SS.dll")
        print("\n[+] Injection finished! You can now launch Trenchblocks Dedicated Server.")
    except Exception as e:
        print(f"\n[!] Injection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
