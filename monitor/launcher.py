"""launcher.py - Control Panel untuk AdminFilter.

Fitur:
* Pilih channel mana saja yang mau dibuka (tekan angka 1-9) atau dimatikan.
* Channel yang OFF / jendelanya ditutup otomatis kembali masuk ke chat in-game.
* Master ON/OFF (tekan SPACE): matikan sementara semua filter tanpa keluar.
* Saat launcher ditutup (tekan Q atau klik X), semua jendela otomatis tertutup
  dan semua chat kembali masuk ke in-game seperti GTA normal.
"""
import argparse
import atexit
import ctypes
import msvcrt
import os
import shutil
import subprocess
import sys
import time

from common import (COLOR_NAMES, channels, enable_vt, fg, find_running_gta_dir,
                    get, hex_color, is_true, load_ini, log_dir,
                    monitor_work_areas, update_ini_keys)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATH_FILE = os.path.join(HERE, "ini_path.txt")
VIEWER = os.path.join(HERE, "viewer.py")

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[38;2;64;255;64m"
RED = "\x1b[38;2;255;80;80m"
YELLOW = "\x1b[38;2;255;255;80m"
CYAN = "\x1b[38;2;80;255;255m"


def ensure_installed_in_gta(gta_dir, template_ini=None):
    """Ensure AdminFilter.asi and AdminFilter.ini exist in gta_dir."""
    asi_src = os.path.join(ROOT, "build", "AdminFilter.asi")
    ini_src = template_ini if (template_ini and os.path.exists(template_ini)) else os.path.join(ROOT, "config", "AdminFilter.ini")
    asi_dst = os.path.join(gta_dir, "AdminFilter.asi")
    ini_dst = os.path.join(gta_dir, "AdminFilter.ini")
    if os.path.exists(asi_src) and not os.path.exists(asi_dst):
        shutil.copy2(asi_src, asi_dst)
        print(f"[+] AdminFilter.asi otomatis dipasang ke: {gta_dir}")
    if os.path.exists(ini_src) and not os.path.exists(ini_dst):
        shutil.copy2(ini_src, ini_dst)
        print(f"[+] AdminFilter.ini otomatis dipasang ke: {gta_dir}")
    return ini_dst


def resolve_ini(arg):
    saved = open(PATH_FILE, encoding="utf-8").read().strip() if os.path.exists(PATH_FILE) else ""
    running_gta = find_running_gta_dir()

    if arg:
        path = arg
    elif running_gta:
        # Otomatis ikuti folder GTA yang sedang dimainkan saat ini!
        path = ensure_installed_in_gta(running_gta, saved)
    elif saved and os.path.exists(saved):
        path = saved
    else:
        print("Lokasi folder GTA San Andreas (yang ada gta_sa.exe):")
        gta = input("> ").strip().strip('"')
        path = ensure_installed_in_gta(gta, saved)

    if os.path.isdir(path):
        path = ensure_installed_in_gta(path, saved)
    if not os.path.exists(path):
        sys.exit(f"AdminFilter.ini tidak ditemukan: {path}")
    with open(PATH_FILE, "w", encoding="utf-8") as f:
        f.write(path)
    return os.path.abspath(path)


class Launcher:
    def __init__(self, ini):
        self.ini = ini
        self.procs = {}          # name -> Popen
        self.mtime = 0
        self.all_ch = []         # [(name, section), ...]
        self.wanted = []         # ordered channel names that should be open
        self.cp = None
        self.master_on = True
        self.master_event = None
        self.cleaned_up = False
        self._set_master_event(True)

    def _set_master_event(self, active):
        k32 = ctypes.windll.kernel32
        if active and not self.master_event:
            self.master_event = k32.CreateEventW(None, True, True, "Local\\AdminFilter_Master")
        elif not active and self.master_event:
            k32.CloseHandle(self.master_event)
            self.master_event = None

    def _write_ini(self, updates):
        update_ini_keys(self.ini, updates)
        try:
            self.mtime = os.path.getmtime(self.ini)
        except OSError:
            pass

    def read(self):
        self.mtime = os.path.getmtime(self.ini)
        self.cp = load_ini(self.ini)
        self.all_ch = channels(self.cp, include_disabled=True)
        self.wanted = []
        for n, s in self.all_ch:
            win_ok = is_true(get(s, "Window", "1"), True)
            en_ok = is_true(get(s, "Enabled", "1"), True)
            if win_ok and en_ok and get(s, "Action", "move").lower() != "drop":
                self.wanted.append(n)

    def activate_on_startup(self):
        """When launcher starts, set [General] Enabled=1 and sync channel Enabled with Window."""
        self.read()
        updates = [("General", "Enabled", "1"), ("General", "ReloadIntervalMs", "250")]
        for n, s in self.all_ch:
            win_ok = is_true(get(s, "Window", "1"), True)
            updates.append((f"Channel:{n}", "Enabled", "1" if win_ok else "0"))
            updates.append((f"Channel:{n}", "Window", "1" if win_ok else "0"))
        self._write_ini(updates)
        self.read()

    def geometry(self, index, total):
        mon = self.cp["Monitor"] if self.cp.has_section("Monitor") else {}
        try:
            mon_no = int(get(mon, "TileMonitor", "2"))
            cols = max(1, int(get(mon, "TileColumns", "2")))
        except ValueError:
            return ""
        if mon_no <= 0 or total == 0:
            return ""
        areas = monitor_work_areas()
        if not areas:
            return ""
        x, y, w, h = areas[min(mon_no, len(areas)) - 1]
        rows = (total + cols - 1) // cols
        cw, ch = w // cols, h // rows
        r, c = divmod(index, cols)
        return f"{x + c * cw},{y + r * ch},{cw},{ch}"

    def spawn(self, name):
        if not self.master_on or name not in self.wanted:
            return
        idx = self.wanted.index(name)
        cmd = [sys.executable, VIEWER, "--ini", self.ini, "--channel", name]
        geom = self.geometry(idx, len(self.wanted))
        if geom:
            cmd += ["--geom", geom]
        self.procs[name] = subprocess.Popen(cmd, cwd=HERE, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def kill(self, name):
        p = self.procs.pop(name, None)
        if p and p.poll() is None:
            p.terminate()

    def sync(self, reopen=False, retile=False):
        if not self.master_on:
            for n in list(self.procs):
                self.kill(n)
            return
        if retile:
            for n in list(self.procs):
                self.kill(n)
        for n in list(self.procs):
            if n not in self.wanted:
                self.kill(n)
        for n in self.wanted:
            p = self.procs.get(n)
            if p is None or (reopen and p.poll() is not None):
                self.spawn(n)

    def check_closed_windows(self):
        """If user manually clicked X on a channel window, mark it OFF so chat returns in-game."""
        if not self.master_on:
            return False
        updates = []
        for n in list(self.procs):
            p = self.procs.get(n)
            if p and p.poll() is not None:
                self.procs.pop(n, None)
                updates.append((f"Channel:{n}", "Enabled", "0"))
                updates.append((f"Channel:{n}", "Window", "0"))
        if updates:
            self._write_ini(updates)
            self.read()
            return True
        return False

    def toggle_channel(self, idx):
        if idx < 0 or idx >= len(self.all_ch):
            return
        name, sec = self.all_ch[idx]
        currently_on = name in self.wanted
        new_val = "0" if currently_on else "1"
        self._write_ini([
            (f"Channel:{name}", "Enabled", new_val),
            (f"Channel:{name}", "Window", new_val),
        ])
        self.read()
        self.sync(reopen=True)
        self.status()

    def set_all_channels(self, enable):
        val = "1" if enable else "0"
        updates = []
        for name, _ in self.all_ch:
            updates.append((f"Channel:{name}", "Enabled", val))
            updates.append((f"Channel:{name}", "Window", val))
        self._write_ini(updates)
        self.read()
        self.sync(reopen=True, retile=enable)
        self.status()

    def toggle_master(self):
        self.master_on = not self.master_on
        self._set_master_event(self.master_on)
        self._write_ini([("General", "Enabled", "1" if self.master_on else "0")])
        self.sync(reopen=True)
        self.status()

    def status(self):
        os.system("cls")
        m_badge = f"{GREEN}{BOLD}[ ON - FILTER KE CMD ]{RESET}" if self.master_on else f"{RED}{BOLD}[ OFF - SEMUA MASUK IN-GAME ]{RESET}"
        print(f"{CYAN}{BOLD}=================================================================={RESET}")
        print(f"  {BOLD}ADMIN FILTER CONTROL PANEL{RESET}   |   Master: {m_badge}")
        print(f"{CYAN}{BOLD}=================================================================={RESET}")
        running_dir = find_running_gta_dir()
        cur_dir = os.path.dirname(self.ini)
        gta_status = f"{GREEN}GTA Jalan ({running_dir}){RESET}" if running_dir else f"{DIM}GTA Belum Jalan{RESET}"
        print(f"  Folder GTA Aktif : {BOLD}{cur_dir}{RESET}  [{gta_status}]")
        print(f"{DIM}  Config File      : {self.ini}{RESET}\n")
        print(f"  {BOLD}Tekan angka [1-{min(9, len(self.all_ch))}] untuk pilih channel mana yang dibuka / ditutup:{RESET}\n")

        for i, (n, s) in enumerate(self.all_ch):
            key_label = str(i + 1) if i < 9 else ("0" if i == 9 else "-")
            title = get(s, "Title", n.upper())
            col = hex_color(get(s, "Color", "white"))
            p = self.procs.get(n)
            is_open = p is not None and p.poll() is None
            is_wanted = n in self.wanted

            if not self.master_on:
                st = f"{DIM}[PAUSE -> IN-GAME]{RESET}"
            elif is_wanted and is_open:
                st = f"{GREEN}{BOLD}[ON  -> CMD     ]{RESET}"
            elif is_wanted and not is_open:
                st = f"{YELLOW}[ON  -> STARTING]{RESET}"
            else:
                st = f"{DIM}[OFF -> IN-GAME ]{RESET}"

            print(f"   [{BOLD}{key_label}{RESET}] {st}  {fg(col)}{BOLD}{title:<24}{RESET} {DIM}({n}){RESET}")

        print(f"\n{CYAN}------------------------------------------------------------------{RESET}")
        print(f"  [{BOLD}SPACE{RESET}] Master ON/OFF (On = ke CMD, Off = semua masuk in-game)")
        print(f"  [{BOLD}1-9{RESET}]   Buka/tutup channel tertentu (yang OFF masuk ke in-game)")
        print(f"  [{BOLD}A{RESET}]     ON Semua Channel     [{BOLD}N{RESET}] OFF Semua Channel")
        print(f"  [{BOLD}W{RESET}]     Tambah Channel Baru  [{BOLD}D{RESET}] Hapus Channel")
        print(f"  [{BOLD}E{RESET}]     Buka Config (INI)    [{BOLD}G{RESET}] Ganti / Pasang ke Folder GTA Lain")
        print(f"  [{BOLD}T{RESET}]     Susun Ulang Grid     [{BOLD}Q{RESET}] Keluar (otomatis kembali ke in-game)")
        print(f"{CYAN}=================================================================={RESET}")

    # ---------------------------------------------------------- wizard
    def add_wizard(self):
        print("\n=== Tambah channel baru (kosongkan nama untuk batal) ===")
        name = input("Nama (tanpa spasi, mis. 'pm_log')   : ").strip().replace(" ", "_")
        if not name:
            self.status()
            return
        if any(n.lower() == name.lower() for n, _ in self.all_ch):
            print("Channel sudah ada.")
            time.sleep(1)
            self.status()
            return
        title = input(f"Judul jendela [{name.upper()}]      : ").strip() or name.upper()
        sw = input("StartsWith (pisah dengan |)       : ").strip()
        match = input("Match / mengandung (pisah dengan |): ").strip()
        if not sw and not match:
            print("Minimal isi StartsWith atau Match.")
            time.sleep(1)
            self.status()
            return
        action = input("Action move/copy/drop [move]      : ").strip().lower() or "move"
        color = input("Warna (red/cyan/RRGGBB) [white]   : ").strip() or "white"
        beep = input("Beep frek,ms (kosong = tanpa)     : ").strip()
        lines = [f"\n[Channel:{name}]", f"Title={title}", "Enabled=1", "Window=1"]
        if sw:
            lines.append(f"StartsWith={sw}")
        if match:
            lines.append(f"Match={match}")
        lines += [f"Action={action}", f"Color={color}"]
        if beep:
            lines.append(f"Beep={beep}")
        with open(self.ini, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.read()
        self.sync(reopen=True, retile=True)
        self.status()

    def delete_wizard(self):
        print("\n=== Hapus Channel ===")
        num = input(f"Ketik nomor channel [1-{len(self.all_ch)}] yang mau dihapus (Enter = batal): ").strip()
        if not num.isdigit():
            self.status()
            return
        idx = int(num) - 1
        if idx < 0 or idx >= len(self.all_ch):
            self.status()
            return
        name, _ = self.all_ch[idx]
        confirm = input(f"Yakin hapus channel '{name}'? (y/n): ").strip().lower()
        if confirm != "y":
            self.status()
            return
        self.kill(name)
        with open(self.ini, "r", encoding="utf-8-sig", errors="replace") as f:
            raw_lines = f.readlines()
        out = []
        skip = False
        target = f"[channel:{name.lower()}]"
        for line in raw_lines:
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                skip = (s.lower() == target)
            if not skip:
                out.append(line)
        with open(self.ini, "w", encoding="utf-8") as f:
            f.writelines(out)
        self.read()
        self.sync(reopen=True, retile=True)
        self.status()

    def switch_gta_wizard(self):
        print("\n=== Ganti / Pasang ke Folder GTA Lain ===")
        print("Masukkan path folder GTA (yang ada gta_sa.exe / samp.dll), kosongkan untuk batal:")
        new_gta = input("> ").strip().strip('"')
        if not new_gta or not os.path.isdir(new_gta):
            self.status()
            return
        for n in list(self.procs):
            self.kill(n)
        try:
            self._write_ini([("General", "Enabled", "0")])
        except Exception:
            pass
        new_ini = ensure_installed_in_gta(new_gta, self.ini)
        self.ini = os.path.abspath(new_ini)
        with open(PATH_FILE, "w", encoding="utf-8") as f:
            f.write(self.ini)
        self.activate_on_startup()
        self.sync(reopen=True, retile=True)
        self.status()

    def cleanup(self):
        if self.cleaned_up:
            return
        self.cleaned_up = True
        self._set_master_event(False)
        for n in list(self.procs):
            self.kill(n)
        try:
            self._write_ini([("General", "Enabled", "0")])
        except Exception:
            pass

    # ---------------------------------------------------------- main loop
    def run(self):
        self.activate_on_startup()
        self.sync(reopen=True)
        self.status()
        last_gta_check = time.time()
        last_running_dir = find_running_gta_dir()
        try:
            while True:
                time.sleep(0.2)
                if time.time() - last_gta_check > 2.0:
                    last_gta_check = time.time()
                    rdir = find_running_gta_dir()
                    if rdir != last_running_dir:
                        last_running_dir = rdir
                        if rdir and os.path.normcase(rdir) != os.path.normcase(os.path.dirname(self.ini)):
                            for n in list(self.procs):
                                self.kill(n)
                            new_ini = ensure_installed_in_gta(rdir, self.ini)
                            self.ini = os.path.abspath(new_ini)
                            with open(PATH_FILE, "w", encoding="utf-8") as f:
                                f.write(self.ini)
                            self.activate_on_startup()
                            self.sync(reopen=True, retile=True)
                        self.status()
                if self.check_closed_windows():
                    self.status()
                try:
                    if os.path.getmtime(self.ini) != self.mtime:
                        time.sleep(0.15)
                        self.read()
                        self.sync(reopen=True)
                        self.status()
                except Exception:
                    pass
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    k = ch.lower()
                    if k == "q":
                        break
                    elif ch == " ":
                        self.toggle_master()
                    elif k in "123456789":
                        self.toggle_channel(int(k) - 1)
                    elif k == "0":
                        self.toggle_channel(9)
                    elif k == "a":
                        self.set_all_channels(True)
                    elif k == "n":
                        self.set_all_channels(False)
                    elif k == "t":
                        self.sync(reopen=True, retile=True)
                        self.status()
                    elif k == "r":
                        self.sync(reopen=True)
                        self.status()
                    elif k == "l":
                        self.status()
                    elif k == "w":
                        self.add_wizard()
                    elif k == "d":
                        self.delete_wizard()
                    elif k == "e":
                        subprocess.Popen(["notepad.exe", self.ini])
                    elif k == "g":
                        self.switch_gta_wizard()
        finally:
            self.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ini", help="path ke AdminFilter.ini atau folder GTA")
    a = ap.parse_args()
    os.system("title AdminFilter Control Panel")
    enable_vt()
    launcher = Launcher(resolve_ini(a.ini))
    atexit.register(launcher.cleanup)

    # Catch console window close (clicking X button) so filter turns OFF cleanly
    HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
    def _console_ctrl(ctrl_type):
        launcher.cleanup()
        return 0
    _ctrl_ref = HandlerRoutine(_console_ctrl)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_ctrl_ref, 1)

    launcher.run()


if __name__ == "__main__":
    main()
