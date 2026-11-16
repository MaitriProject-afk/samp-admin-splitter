"""viewer.py - live terminal for one AdminFilter channel.

Usage: python viewer.py --ini "C:\\...\\AdminFilter.ini" --channel anticheat [--geom x,y,w,h]
"""
import argparse
import ctypes
import os
import sys
import threading
import time
import winsound

from common import (COLOR_CODE, channels, enable_vt, fg, get, hex_color, load_ini, log_dir)

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
INVERT = "\x1b[7m"


class Viewer:
    def __init__(self, ini, channel):
        self.ini = ini
        self.channel = channel
        self.count = 0
        self.ini_mtime = 0
        self.last_beep = 0
        # Hold kernel event while this CMD window is open so AdminFilter.asi knows it's active
        evt_name = f"Local\\AdminFilter_Ch_{self.channel.lower()}"
        self._event_handle = ctypes.windll.kernel32.CreateEventW(None, True, True, evt_name)
        self.reload()

    # ------------------------------------------------------------ config
    def reload(self):
        try:
            self.ini_mtime = os.path.getmtime(self.ini)
            cp = load_ini(self.ini)
        except Exception as e:
            print(f"[viewer] gagal baca INI: {e}")
            return
        sec = dict(channels(cp, include_disabled=True)).get(self.channel)
        sec = sec if sec is not None else {}
        mon = cp["Monitor"] if cp.has_section("Monitor") else {}
        self.title = get(sec, "Title", self.channel.upper())
        self.color = hex_color(get(sec, "Color", "white"))
        beep = get(sec, "Beep", "")
        try:
            f, d = (int(x) for x in beep.split(","))
            self.beep = (f, d)
        except ValueError:
            self.beep = None
        self.highlight = [h.strip().lower() for h in get(mon, "Highlight", "").split("|") if h.strip()]
        self.tail_lines = int(get(mon, "TailLines", "30") or 30)
        self.path = os.path.join(log_dir(cp, self.ini), f"{self.channel}.log")
        self.set_title()

    def set_title(self):
        ctypes.windll.kernel32.SetConsoleTitleW(f"[{self.count}] {self.title}")

    # ------------------------------------------------------------ output
    def do_beep(self, freq, dur):
        now = time.time()
        if now - self.last_beep < 0.8:  # anti spam
            return
        self.last_beep = now
        threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()

    def header(self):
        os.system("cls")
        bar = "=" * 60
        print(f"{fg(self.color)}{BOLD}{bar}\n  {self.title}\n{bar}{RESET}")
        print(f"{DIM}  {self.path}  (Tutup jendela ini untuk kembalikan chat ke in-game){RESET}\n")

    def render(self, raw, live):
        parts = raw.rstrip("\r\n").split("\t", 4)
        if len(parts) < 5:
            return
        ts, color, _tag, prefix, text = parts
        plain = COLOR_CODE.sub("", text)
        hit = any(h in plain.lower() for h in self.highlight)
        body = fg(color if len(color) == 6 else "FFFFFF") + COLOR_CODE.sub(lambda m: fg(m.group(1)), text)
        pre = f"{prefix}: " if prefix else ""
        line = f"{DIM}{ts}{RESET} {pre}{body}{RESET}"
        if hit:
            line = f"{INVERT}{BOLD}>>{RESET} {line}"
        print(line)
        self.count += 1
        if live:
            self.set_title()
            if hit:
                self.do_beep(1500, 250)
            elif self.beep:
                self.do_beep(*self.beep)

    # ------------------------------------------------------------ loop
    def run(self):
        self.header()
        while not os.path.exists(self.path):
            time.sleep(0.3)
            self.check_ini()
        f = open(self.path, "r", encoding="cp1252", errors="replace", newline="")
        lines = f.readlines()
        for l in lines[-self.tail_lines:]:
            self.render(l, live=False)
        if lines:
            print(f"{DIM}{'-' * 25} live {'-' * 25}{RESET}")
        pos = f.tell()
        buf = ""
        while True:
            chunk = f.read()
            if chunk:
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    self.render(line, live=True)
                pos = f.tell()
            else:
                time.sleep(0.1)
                try:
                    if os.path.getsize(self.path) < pos:  # file truncated/rotated
                        f.seek(0)
                        pos = 0
                except OSError:
                    pass
                self.check_ini()

    def check_ini(self):
        try:
            if os.path.getmtime(self.ini) != self.ini_mtime:
                old = self.path
                self.reload()
                if self.path != old:
                    raise SystemExit("LogDir berubah - buka ulang jendela")
        except OSError:
            pass


def place_window(geom):
    try:
        x, y, w, h = (int(v) for v in geom.split(","))
    except ValueError:
        return
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.SetProcessDPIAware()
        ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ini", required=True)
    ap.add_argument("--channel", required=True)
    ap.add_argument("--geom", default="")
    a = ap.parse_args()
    enable_vt()
    if a.geom:
        place_window(a.geom)
    try:
        Viewer(a.ini, a.channel).run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
