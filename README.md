# Trenchblocks Server UE4SS

UE4SS configuration and launcher injector for **Trenchblocks Dedicated Server** (Unreal Engine 5.7).

Since dedicated server builds do not load graphical proxy DLLs (such as `dwmapi.dll`), this package provides custom UE 5.7 member signatures along with `inject.py` to launch the server and inject `UE4SS.dll` safely into memory.

---

## Installation & Running

1. Copy the `ue4ss/` folder into your server directory:
   `<server_root>/Trenchblocks/Binaries/Win64/ue4ss/`
2. Place `inject.py` in the server root (or inside `Win64/`).
3. Run the server using `inject.py`:
   ```bash
   python inject.py
   ```
   *(Any command line arguments passed to `inject.py` will be forwarded directly to the server executable).*

---

## Directory Structure

```text
Trenchblocks/Binaries/Win64/
├── TrenchblocksServer-Win64-Shipping.exe
├── inject.py
└── ue4ss/
    ├── UE4SS.dll
    ├── UE4SS-settings.ini
    ├── MemberVariableLayout.ini
    ├── VTableLayout.ini
    ├── UE4SS_Signatures/
    └── Mods/
        └── mods.txt
```

---

## Credits
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS)
- [Dumper-7](https://github.com/Encryqed/Dumper-7)
