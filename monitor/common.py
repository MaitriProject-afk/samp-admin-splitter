"""Shared helpers for launcher.py and viewer.py (stdlib only)."""
import configparser
import ctypes
import os
import re

COLOR_NAMES = {
    "red": "FF4040", "green": "40FF40", "yellow": "FFFF40", "blue": "4080FF",
    "magenta": "FF40FF", "cyan": "40FFFF", "white": "FFFFFF", "gray": "A0A0A0",
    "orange": "FF8000",
}

COLOR_CODE = re.compile(r"\{([0-9A-Fa-f]{6})\}")


def load_ini(path):
    cp = configparser.ConfigParser(interpolation=None, strict=False,
                                   comment_prefixes=(";", "#"), inline_comment_prefixes=None)
    cp.optionxform = str  # keep key case
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        cp.read_file(f)
    return cp


def get(sec, key, default=""):
    for k, v in sec.items():
        if k.lower() == key.lower():
            return v.strip()
    return default


def is_true(val, default=True):
    if not val:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def channels(cp, include_disabled=False):
    """Return ordered list of (name, section) for channels."""
    out = []
    for s in cp.sections():
        if not s.lower().startswith("channel:"):
            continue
        sec = cp[s]
        if not include_disabled and not is_true(get(sec, "Enabled", "1"), True):
            continue
        name = s.split(":", 1)[1].strip()
        if name:
            out.append((name, sec))
    return out


def update_ini_keys(path, updates):
    """Update [(section, key, value), ...] in-place while preserving comments."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()

    for target_sec, target_key, new_val in updates:
        sec_low = target_sec.lower()
        key_low = target_key.lower()
        in_sec = False
        sec_end_idx = None
        replaced = False

        for i, raw in enumerate(lines):
            s = raw.strip()
            if s.startswith("[") and s.endswith("]"):
                if in_sec:
                    sec_end_idx = i
                    break
                cur_sec = s[1:-1].strip().lower()
                in_sec = (cur_sec == sec_low)
                continue
            if in_sec and s and not s.startswith(";") and not s.startswith("#") and "=" in s:
                k = s.split("=", 1)[0].strip().lower()
                if k == key_low:
                    lines[i] = f"{target_key}={new_val}\n"
                    replaced = True
                    break

        if in_sec and not replaced:
            insert_at = sec_end_idx if sec_end_idx is not None else len(lines)
            while insert_at > 0 and lines[insert_at - 1].strip() == "":
                insert_at -= 1
            lines.insert(insert_at, f"{target_key}={new_val}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def log_dir(cp, ini_path):
    base = os.path.dirname(os.path.abspath(ini_path))
    ld = get(cp["General"], "LogDir", r"AdminFilter\logs") if cp.has_section("General") else r"AdminFilter\logs"
    return ld if os.path.isabs(ld) else os.path.join(base, ld)


def hex_color(value, default="FFFFFF"):
    v = (value or "").strip().lower()
    if v in COLOR_NAMES:
        return COLOR_NAMES[v]
    if re.fullmatch(r"[0-9a-f]{6}", v):
        return v.upper()
    return default


def fg(hexrgb):
    r, g, b = int(hexrgb[0:2], 16), int(hexrgb[2:4], 16), int(hexrgb[4:6], 16)
    return f"\x1b[38;2;{r};{g};{b}m"


def enable_vt():
    """Enable ANSI escape sequences in classic conhost."""
    k32 = ctypes.windll.kernel32
    h = k32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if k32.GetConsoleMode(h, ctypes.byref(mode)):
        k32.SetConsoleMode(h, mode.value | 0x0004)


# ---------------------------------------------------------------- monitors
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_uint32)]


def monitor_work_areas():
    """List of (left, top, width, height) work areas; primary monitor first."""
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    areas = []
    proc_t = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.POINTER(RECT), ctypes.c_void_p)

    def cb(hmon, hdc, rect, data):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi))
        w = mi.rcWork
        areas.append((bool(mi.dwFlags & 1), (w.left, w.top, w.right - w.left, w.bottom - w.top)))
        return 1

    user32.EnumDisplayMonitors(None, None, proc_t(cb), None)
    areas.sort(key=lambda a: not a[0])  # primary first
    return [a[1] for a in areas]
