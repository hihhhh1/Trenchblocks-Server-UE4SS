# Trenchblocks Server UE4SS

UE4SS configuration and PE binary injector for **Trenchblocks Dedicated Server** (Unreal Engine 5.7).

Dedicated server builds do not load graphical proxy DLLs (such as `dwmapi.dll`). This repository provides custom UE 5.7 member signatures along with `inject.py` to add `UE4SS.dll` directly to the server executable's Import Address Table (IAT).

---

## Installation

1. Copy the `ue4ss/` folder to your server directory:
   `<server_root>/Trenchblocks/Binaries/Win64/ue4ss/`
2. Place `UE4SS.dll` in the same directory as the server executable:
   `<server_root>/Trenchblocks/Binaries/Win64/UE4SS.dll`
3. Run `inject.py` from the server root (or inside `Win64/`):
   ```bash
   python inject.py
   ```
4. Start `TrenchblocksServer-Win64-Shipping.exe`. UE4SS will automatically initialize on startup.

---

## Restoring Backup

`inject.py` automatically creates a backup (`.exe.bak`) before modifying the binary. To revert:
```bash
cp TrenchblocksServer-Win64-Shipping.exe.bak TrenchblocksServer-Win64-Shipping.exe
```

---

## Credits
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS)
- [Dumper-7](https://github.com/Encryqed/Dumper-7)
