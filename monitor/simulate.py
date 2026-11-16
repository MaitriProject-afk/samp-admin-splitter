"""simulate.py - tulis pesan palsu ke log channel untuk tes tampilan terminal
tanpa membuka game.   python simulate.py   (Ctrl+C untuk berhenti)"""
import os
import random
import time

from common import channels, load_ini, log_dir

HERE = os.path.dirname(os.path.abspath(__file__))
ini = open(os.path.join(HERE, "ini_path.txt"), encoding="utf-8").read().strip()
cp = load_ini(ini)
d = log_dir(cp, ini)
os.makedirs(d, exist_ok=True)

SAMPLES = {
    "anticheat": ["{FF0000}[AC]{FFFFFF} John_Doe (ID: 12) suspected {FFFF00}SpeedHack", "[AC] Budi_S (ID: 45) Teleport"],
    "report": ["[REPORT] Andi_W (ID: 8): ada yg DM di pershing", "[REPORT] Rina (ID: 33): bug kendaraan"],
    "adminwarn": ["AdmWarn: Agus (ID: 5) money jump +$500.000", "AdmWarn: NamaAdminKamu dipanggil di /a"],
    "adminchat": ["[A] Admin_Rizky: standby semua", "[A] Admin_Dewi: ada yg cek report #12?"],
    "adminactivity": ["Agus has been jailed by Admin_Rizky (10 min)", "Budi_S has been banned by Admin_Dewi"],
}
names = [n for n, _ in channels(cp)]
print("Menulis ke:", d)
while True:
    n = random.choice(names)
    msg = random.choice(SAMPLES.get(n, [f"pesan contoh untuk {n}"]))
    with open(os.path.join(d, f"{n}.log"), "a", encoding="cp1252") as f:
        f.write(time.strftime("%H:%M:%S") + f"\tC8C8C8\t{n}\t\t{msg}\n")
    print(n, "<-", msg)
    time.sleep(random.uniform(0.5, 2.0))
