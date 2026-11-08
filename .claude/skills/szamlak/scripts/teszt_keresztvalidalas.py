#!/usr/bin/env python3
"""Önteszt: a bevételi fájlok feldolgozása és az egyesítés keresztvalidálása szintetikus adatokkal.

Futtatás: python -I .claude/skills/szamlak/scripts/teszt_keresztvalidalas.py
A teszt ideiglenes fájlokat tesz az input/bevetelek/ mappába, lefuttatja a scripteket, ellenőrzi a várt viselkedést (duplikátum nem
könyvelődik újra; ellentmondás, gyanús duplikáció és idegen vállalkozás dokumentuma megállít), majd MINDEN általa létrehozott fájlt
töröl, és visszaállítja az egyesített számlafájlt. A valódi számlaadatot nem módosítja.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[4]
SK = ROOT / ".claude" / "skills" / "szamlak" / "scripts"
IN = ROOT / "input" / "bevetelek"
DATA = ROOT / "data" / "szamlak"
# Ez a teszt a vállalkozó saját (már feldolgozott) adatán alapul: a vállalkozói azonosító és legalább egy Billingo-számla kell hozzá.
# Friss telepítésnél ezek nincsenek meg: a teszt ilyenkor kihagyja magát (nem hiba).
try:
    azon = json.loads((ROOT / "data" / "vallalkozas" / "azonosito.json").read_text(encoding="utf-8"))
    SAJAT = azon["adoszam"]
    bill = json.loads(sorted(DATA.glob("szamlak_*.json"))[-1].read_text(encoding="utf-8"))
    vals = next(x for x in bill if x["type"] == "invoice" and x["summary"].get("net_amount_local"))
except (OSError, IndexError, KeyError, StopIteration):
    print("KIHAGYVA: nincs vállalkozói azonosító (data/vallalkozas/azonosito.json) vagy feldolgozott Billingo-számla; a teszt a saját adaton fut.")
    sys.exit(0)
fails = []


def futtat(script, *args):
    r = subprocess.run([sys.executable, "-I", str(SK / script), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def ellenor(nev, ok, reszlet=""):
    print(("OK    " if ok else "HIBA  ") + nev + (f"  [{reszlet[:140]}]" if not ok and reszlet else ""))
    if not ok:
        fails.append(nev)


def csv(nev, sorok, adoszam=SAJAT):
    fej = "Számlaszám;Kelt;Nettó;Pénznem;Árfolyam;Kiegyenlítve;Eladó adószáma\n"
    (IN / nev).write_text(fej + "".join(sorok).replace("{ADO}", adoszam), encoding="utf-8")


def takarit():
    for p in IN.glob("teszt_*"):
        p.unlink()
    reg = DATA / "bevetelek_szamlak.json"
    if reg.exists():
        reg.unlink()
    for d in (ROOT / "archive" / "bevetelek", DATA / "bevetelek-md"):
        if d.exists():
            shutil.rmtree(d)


IN.mkdir(parents=True, exist_ok=True)
takarit()
try:
    num, kelt, netto, dev, arf = vals["invoice_number"], vals["invoice_date"], vals["summary"]["net_amount"], vals["currency"], vals["conversion_rate"]
    # 1) ugyanaz a számla a fájlban és a Billingóban: egy tétel
    csv("teszt_1.csv", [f"{num};{kelt};{netto};{dev};{arf};;{{ADO}}\n", "TESZT-1;2026-09-01;1000;HUF;1;2026-09-05;{ADO}\n"])
    rc, out = futtat("bevetelek.py", "--feldolgoz")
    ellenor("fájl feldolgozása (2 számla)", rc == 0 and "2 új számla" in out, out)
    rc, out = futtat("szamlak_egyesites.py")
    ellenor("azonos számlaszám Billingóban és fájlban: egy tétel", rc == 0 and "duplikált rekord egyesítve" in out, out)
    egy = json.loads(next(DATA.glob("egyesitett_*.json")).read_text(encoding="utf-8"))
    ellenor("a közös számla egyszer szerepel", sum(1 for x in egy if x["invoice_number"] == num) == 1)
    # 2) ugyanaz a fájl újra: duplikátum, nem könyvelődik újra
    csv("teszt_1b.csv", [f"{num};{kelt};{netto};{dev};{arf};;{{ADO}}\n", "TESZT-1;2026-09-01;1000;HUF;1;2026-09-05;{ADO}\n"])
    rc, out = futtat("bevetelek.py", "--feldolgoz")
    reg = json.loads((DATA / "bevetelek_szamlak.json").read_text(encoding="utf-8"))
    ellenor("azonos tartalmú újabb fájl: duplikátum, nincs új tétel", len(reg["szamlak"]) == 2 and "DUPLIKÁTUM" in out or "0 új számla" in out, out)
    # 3) ellentmondás: azonos számlaszám, más összeg
    csv("teszt_2.csv", ["TESZT-1;2026-09-01;2000;HUF;1;;{ADO}\n"])
    rc, out = futtat("bevetelek.py", "--feldolgoz")
    ellenor("azonos számlaszám, eltérő összeg: megáll", rc == 3 and "ELLENTMONDÁS" in out and (IN / "teszt_2.csv").exists(), out)
    (IN / "teszt_2.csv").unlink()
    # 4) idegen vállalkozás dokumentuma
    csv("teszt_3.csv", ["IDEGEN-1;2026-09-02;500;HUF;1;;{ADO}\n"], adoszam="99999999-2-41")
    rc, out = futtat("bevetelek.py", "--feldolgoz")
    ellenor("másik vállalkozás adószáma: megáll, utasítást ad", rc == 3 and "NEM a te vállalkozásodra szól" in out and (IN / "teszt_3.csv").exists(), out)
    (IN / "teszt_3.csv").unlink()
    # 5) gyanús duplikáció: más számlaszám, azonos kelt/összeg/pénznem, másik forrásból
    csv("teszt_4.csv", [f"ALT-77;{kelt};{netto};{dev};{arf};;{{ADO}}\n"])
    rc, out = futtat("bevetelek.py", "--feldolgoz")
    rc2, out2 = futtat("szamlak_egyesites.py")
    ellenor("gyanús duplikáció (más szám, azonos adatok, másik forrás): megáll", rc2 == 5 and "gyanús duplikáció" in out2, out2)
finally:
    takarit()
    futtat("szamlak_egyesites.py")  # az egyesített fájl visszaáll a valódi forrásokra

print()
if fails:
    print(f"{len(fails)} teszt BUKOTT: {', '.join(fails)}")
    sys.exit(1)
print("Minden keresztvalidálási teszt megfelelt.")
