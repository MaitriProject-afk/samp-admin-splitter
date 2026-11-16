# SA-MP Admin Splitter (0.3.DL)

Memisahkan chat admin / anti-cheat / report dari chatbox in-game ke jendela-jendela terminal terpisah di monitor kedua.

```
samp.dll ──AddEntry──> AdminFilter.asi ──cocok channel?──┬─ tidak → chatbox game (RP bersih)
                                                         └─ ya    → AdminFilter\logs\<channel>.log
                                                                     └─> viewer.py (1 jendela CMD per channel)
```

## Instalasi
1. `build.bat` → hasil di `build\AdminFilter.asi` (sudah ter-build).
2. Copy `build\AdminFilter.asi` + `config\AdminFilter.ini` ke folder GTA SA (sebelah `gta_sa.exe`, butuh ASI Loader).
3. Main game sekali, cek `AdminFilter\AdminFilter.log` → harus ada `Hooked CChat::AddEntry`.
4. Jalankan `start_monitor.bat`, isi path folder GTA (disimpan di `monitor\ini_path.txt`).

## Menyesuaikan dengan server
- `CaptureAll=1` menyalin semua chat ke `logs\_all.log` (kolom ke-3 = channel yang cocok, `-` = tidak ada yang cocok). Lihat format asli server kamu di situ, lalu tulis `StartsWith`/`Match`/`Regex`.
- Tambah channel: tulis section `[Channel:nama]` di INI **atau** tekan `A` di launcher. Filter in-game & jendela baru langsung aktif tanpa restart.
- Tes tampilan tanpa game: `python monitor\simulate.py`.

## Catatan
- Window tiling (`TileMonitor`) butuh default terminal = **Windows Console Host** (Settings → Privacy & security → For developers → Terminal). Kalau Windows Terminal, jendela akan jadi tab dan tidak bisa diposisikan.
- Hanya untuk 0.3.DL-R1. Versi lain = entry point beda → plugin otomatis tidak meng-hook (aman, tidak crash).
- Chat yang diketik pemain (type CHAT) tidak pernah difilter kecuali `PlayerChat=1`.
