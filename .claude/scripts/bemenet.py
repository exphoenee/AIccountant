#!/usr/bin/env python3
"""Közös bemeneti-mappa segédek az input/ alatti mappákat feldolgozó skilleknek.

Importálás: sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import bemenet

- fajlok(mappa, kiterjesztesek=None): a mappa MINDEN fájlja, **az almappákat is beleértve** (a felhasználó évek, ügyfelek stb. szerint
  almappákba rendezheti az iratokat), rendezve; a .gitkeep nélkül; a kiterjesztés kis/nagybetűtől független (.pdf = .PDF).
- uresek_torlese(mappa): a feldolgozás után üressé vált almappák törlése (a gyökérmappa marad).
- takarit_kilepeskor(mappa): a script kilépésekor (sys.exit is) automatikusan törli az üres almappákat.
- maradek(input_gyoker): az input/ alatt még meglévő fájlok mappánként (az adoellenorzes jelzi őket a reportban).

Szabály: az input/ feldolgozása után **üresnek kell lennie** (adatkezeles.md); ami ott marad, az nem dolgozódott fel, és ennek okát ki kell mondani.
"""
import atexit
from collections import Counter
from pathlib import Path

# mappánként a feldolgozható kiterjesztések (None = bármi, a skill dönti el); a többi "nem támogatott formátum"
TAMOGATOTT = {
    "kiadasok": (".pdf",),
    "konyvelo": (".pdf",),
    "nav-egyenleg": (".xml", ".pdf"),
    "adonaptar": (".md",),
    "bevetelek": (".pdf", ".xml", ".csv"),
    "pdf": (".pdf",),
    "torveny": None,
    "vallalkozas-adatok": None,
}


def fajlok(mappa, kiterjesztesek=None):
    mappa = Path(mappa)
    if not mappa.exists():
        return []
    ext = tuple(e.lower() for e in kiterjesztesek) if kiterjesztesek else None
    return sorted(p for p in mappa.rglob("*") if p.is_file() and p.name != ".gitkeep" and (ext is None or p.suffix.lower() in ext))


def uresek_torlese(mappa):
    mappa = Path(mappa)
    if not mappa.exists():
        return
    for d in sorted((p for p in mappa.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            d.rmdir()  # csak az üres mappa törlődik; a nem üres hibát ad, azt hagyjuk
        except OSError:
            pass


def takarit_kilepeskor(mappa):
    atexit.register(uresek_torlese, mappa)


def maradek(input_gyoker):
    """{mappa: {"db": n, "tipusok": {".pdf": n, ...}, "nem_tamogatott": n}} az input/ alatti, feldolgozatlan fájlokról (üres mappa nincs benne)."""
    ki = {}
    gy = Path(input_gyoker)
    if not gy.exists():
        return ki
    for d in sorted(p for p in gy.iterdir() if p.is_dir()):
        fs = fajlok(d)
        if not fs:
            continue
        tam = TAMOGATOTT.get(d.name)
        tip = Counter(f.suffix.lower() or "(nincs)" for f in fs)
        nt = sum(1 for f in fs if tam is not None and f.suffix.lower() not in tam)
        ki[d.name] = {"db": len(fs), "tipusok": dict(tip), "nem_tamogatott": nt, "tamogatott_kiterjesztesek": list(tam) if tam else None}
    return ki
