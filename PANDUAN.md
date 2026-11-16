# Panduan Lengkap SA-MP Admin Chat Splitter (0.3.DL-R1)

Alat ini memisahkan log admin, anti-cheat, report, dan ask dari chatbox in-game GTA SA-MP ke jendela-jendela CMD terpisah di monitor kedua. Saat kamu sedang fokus RP, chatbox game bersih dari spam admin, tapi kamu tetap bisa memantau semuanya secara *real-time*.

---

## 1. Persyaratan & Cara Instalasi

### A. Persyaratan (Requirements)
1. **GTA San Andreas + SA-MP versi `0.3.DL-R1`**.
2. **ASI Loader** sudah terpasang di folder GTA kamu (biasanya sudah otomatis ada jika kamu memakai CLEO, ModLoader, atau WindowedMode—ditandai dengan adanya `vorbisFile.dll` / `vorbisHooked.dll` atau `dinput8.dll` di folder GTA).
3. **Python 3** untuk Windows (tidak butuh `pip install` library tambahan, cukup bawaan Python standar).
4. **Setting Terminal Windows (Agar Jendela Bisa Tersusun Grid Otomatis):**
   - Buka **Windows Settings** → **System** (atau *Privacy & security*) → **For developers**.
   - Pada bagian **Terminal**, ubah dari *Windows Terminal* menjadi **Windows Console Host**.

---

### B. Cara Instalasi (Ada 2 Cara)

#### Cara 1: Instalasi Otomatis (Direkomendasikan)
1. Buka game GTA SA-MP kamu (dari folder GTA mana saja di PC kamu).
2. Double-click file **`start_monitor.bat`** di folder project.
3. Program akan otomatis mendeteksi lokasi folder `gta_sa.exe` yang sedang berjalan, lalu **otomatis meng-copy `AdminFilter.asi` dan `AdminFilter.ini`** ke folder GTA tersebut!
   *(Catatan: Jika GTA sudah terlanjur jalan saat pertama kali dipasang, restart GTA sekali saja supaya `AdminFilter.asi` ter-load oleh game).*
4. **Punya banyak folder GTA?** Cukup tekan tombol **`G`** di Control Panel, lalu masukkan path folder GTA lain—file `.asi` dan `.ini` akan otomatis dipasang ke sana.

#### Cara 2: Instalasi Manual (Misal Mau Dipindah ke PC Lain)
1. Copy **2 file** berikut ke dalam folder utama GTA San Andreas (satu folder dengan `gta_sa.exe` dan `samp.dll`):
   - `build\AdminFilter.asi` → taruh di `FolderGTA\AdminFilter.asi`
   - `config\AdminFilter.ini` → taruh di `FolderGTA\AdminFilter.ini`
2. Folder **`monitor\`** (berisi `launcher.py`, `viewer.py`, `common.py`, `analyze.py`) dan **`start_monitor.bat`** bebas ditaruh di mana saja (di Desktop, Documents, atau di dalam folder GTA).
3. Jalankan **`start_monitor.bat`**, lalu masukkan lokasi folder GTA kamu saat ditanya pertama kali.

---

### C. Cara Mengecek Apakah Plugin `.asi` Sudah Aktif
Setelah masuk ke dalam game sekali, cek folder **`AdminFilter`** yang otomatis terbuat di dalam folder GTA kamu, lalu buka **`AdminFilter\AdminFilter.log`**.
Jika instalasi sukses, isinya akan seperti ini:
```text
[09:10:42] ===== AdminFilter.asi loaded =====
[09:10:42] samp.dll @ 03E70000, entry point 0xFDB60 (expected 0xFDB60)
[09:10:42] Hooked CChat::AddEntry @ 03ED7650
```

---

## 2. Cara Menjalankan Sehari-hari

1. **Buka Game GTA SA-MP** seperti biasa.
   *(Selama Control Panel belum dibuka, semua chat akan masuk ke in-game seperti normal).*
2. **Double-click `start_monitor.bat`** (bisa dari `C:\Game RP\GTA\start_monitor.bat` atau dari folder project).
3. **Jendela Control Panel** akan terbuka, dan otomatis membuka jendela CMD untuk setiap channel yang berstatus **`[ON -> CMD]`** di Monitor 2.
4. **Selesai main / mau full di in-game:**
   - Cukup tekan **`Q`** atau klik tombol **`X`** di jendela Control Panel.
   - Semua jendela CMD channel akan tertutup otomatis, dan semua chat kembali muncul di in-game seperti biasa.

---

## 3. Fungsi Tombol di Control Panel

Saat jendela **AdminFilter Control Panel** aktif, tekan tombol keyboard berikut (tanpa perlu tekan Enter):

| Tombol | Fungsi |
| :--- | :--- |
| **`1` s/d `9`** | **ON / OFF Channel tertentu.**<br>• Kalau **ON**: Buka jendela CMD channel tersebut & sembunyikan pesannya dari in-game.<br>• Kalau **OFF**: Tutup jendela CMD channel tersebut & kembalikan pesannya ke in-game. |
| **`SPACE` (Spasi)** | **Master ON / OFF.**<br>Matikan sementara semua filter (semua chat masuk ke in-game) atau nyalakan kembali tanpa harus menutup Control Panel. |
| **`A`** | Nyalakan (**ON**) semua channel sekaligus. |
| **`N`** | Matikan (**OFF**) semua channel sekaligus. |
| **`W`** | **Wizard Tambah Channel Baru** langsung dari Control Panel. |
| **`D`** | **Hapus Channel** dari daftar. |
| **`E`** | **Buka `AdminFilter.ini` di Notepad** untuk edit manual. |
| **`T`** | **Susun Ulang Grid (Re-tile)** posisi jendela-jendela CMD di Monitor 2. |
| **`G`** | **Ganti / Pasang ke Folder GTA Lain** (otomatis mendeteksi juga jika kamu menjalankan GTA dari folder lain). |
| **`Q`** | **Keluar** (menutup semua jendela CMD dan mengembalikan semua chat ke in-game). |

> **Tips:** Kalau kamu menutup salah satu jendela CMD channel secara langsung (klik tombol **X** di pojok kanan atas jendela channel itu), Control Panel otomatis mendeteksinya dan mengembalikan chat channel itu ke in-game!

---

## 4. Instruksi Lengkap Cara Menambah Channel Baru

Untuk memisahkan jenis log baru, kamu hanya perlu tahu **teks awal** atau **kata kunci** dari pesan yang muncul di game.

### Langkah A: Cari Tahu Teks Pesannya
Perhatikan pesan di game atau buka file `AdminFilter\logs\_all.log` di dalam folder GTA kamu.
Contoh pesan di server GTA: Central:
- `(AntiCheat) Jayden_Love possible vehicle teleport...` -> Awalannya adalah **`(AntiCheat)`**
- `[ASK] (Noah Albert - ID: 13) min...` -> Awalannya adalah **`[ASK]`**
- `(Kill Log) Budi killed Andi (DEagle)` -> Awalannya adalah **`(Kill Log)`**
- `AdmInfo: Sanctuary is now duty as an admin.` -> Awalannya adalah **`AdmInfo:`**

---

### Langkah B: Tambahkan Channel (Pilih Salah Satu Cara)

#### Cara 1: Lewat Wizard di Control Panel (Paling Gampang)
1. Di jendela **AdminFilter Control Panel**, tekan huruf **`W`**.
2. Isi pertanyaan satu per satu lalu tekan **Enter**:
   - **Nama (tanpa spasi):** Nama singkat untuk file log, misalnya `killlog`
   - **Judul jendela:** Judul yang tampil di atas CMD, misalnya `KILL & DEATH LOG`
   - **StartsWith (pisah dengan `|`):** Teks awalan pesan yang mau ditangkap, misalnya `(Kill Log)|[KILL]`
     *(Kosongkan saja lalu Enter kalau kata kuncinya bukan di awal kalimat).*
   - **Match / mengandung (pisah dengan `|`):** Isi kalau kata kuncinya ada di tengah kalimat, misalnya `has killed|dibunuh oleh`
     *(Kosongkan saja kalau tadi sudah isi `StartsWith`).*
   - **Action (`move`/`copy`/`drop`):** Tekan **Enter** untuk default (`move` = hilang dari game & pindah ke CMD).
     *(Pilih `copy` kalau mau tampil di CMD **sekaligus** tetap muncul di in-game).*
   - **Warna:** Ketik warna (`red`, `green`, `yellow`, `cyan`, `magenta`, `orange`, `white`) atau kode hex (`FF8000`).
   - **Beep:** Isi `1000,100` kalau mau bunyi beep saat pesan masuk, atau tekan **Enter** (kosong) kalau tanpa suara.
3. Begitu selesai, jendela CMD barunya **langsung terbuka** dan filter langsung jalan detik itu juga tanpa perlu restart game!

---

#### Cara 2: Edit Manual Lewat Notepad (Untuk Kustomisasi Lanjutan)
1. Di jendela **AdminFilter Control Panel**, tekan huruf **`E`** (atau buka `AdminFilter.ini` di folder GTA kamu).
2. Scroll ke paling bawah, lalu tambahkan blok baru dengan format berikut:

```ini
[Channel:killlog]
Title=KILL & DEATH LOG
Enabled=1
Window=1
StartsWith=(Kill Log)|[KILL]
Match=
Exclude=
Action=move
Color=red
Beep=900,100
```

3. Tekan **Ctrl + S (Save)** di Notepad.
4. **Selesai!** Dalam 0.25 detik, game dan Control Panel langsung menerapkan perubahanmu secara otomatis.

---

### Penjelasan Aturan Pencocokan di `AdminFilter.ini`

| Pengaturan | Fungsi & Contoh |
| :--- | :--- |
| **`StartsWith=`** | Menangkap pesan yang **diawali** teks tertentu. Paling aman agar tidak salah tangkap.<br>Contoh: `StartsWith=[REPORT]|(Report)` (gunakan `\|` untuk lebih dari 1 pola). |
| **`Match=`** | Menangkap pesan yang **mengandung** kata tertentu di bagian mana saja.<br>Contoh: `Match=has been banned|has been jailed|has been kicked` |
| **`Exclude=`** | **Pengecualian.** Jika pesan mengandung kata di `Exclude`, pesan itu **batal** ditangkap oleh channel ini (tetap di game atau lanjut dicek channel bawahnya).<br>Contoh: Di `adminfo`, kamu isi `Exclude=has paid` supaya log transfer uang tidak ikut masuk. |
| **`Action=`** | • `move` *(default)*: Sembunyikan dari in-game, tampilkan di CMD.<br>• `copy`: Tampilkan di CMD, tapi **tetap muncul** juga di in-game.<br>• `drop`: Buang/sembunyikan dari in-game tanpa membuka jendela CMD (cocok untuk menyembunyikan iklan/spam server). |
| **`Color=`** | Warna header & teks default di CMD: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `orange`, `white`, atau kode hex 6 digit seperti `FF6347`. |
| **`Beep=`** | Bunyi notifikasi `frekuensi_hz,durasi_ms`.<br>• `1200,150` = bunyi tinggi (cocok untuk Anti-Cheat)<br>• `800,120` = bunyi sedang (cocok untuk Report)<br>• Kosongkan jika tidak ingin bunyi. |
