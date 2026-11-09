#!/usr/bin/env python3
"""A vállalkozás azonosítója és a beérkező dokumentumok „ez a mi vállalkozásunké?” ellenőrzése.

Több skill használja (konyvelo-dokumentumok, kiadasok-dokumentumok, adofizetes, szamlak), ezért él a .claude/scripts/ alatt.
Importálás: sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import azonosito

Az azonosító a data/vallalkozas/azonosito.json fájlban van (nem verziózott; adószám, adóazonosító jel, név). Forrása a Billingo
cégadata (billingo-szervezet.json, a vallalkozas-dokumentumok --billingo hozza létre) és az iratokból kiolvasott adóazonosító jel.
Személyes azonosítót ez a modul a kimenetre NEM ír ki: eltérésnél csak maszkolt, utolsó 3 számjegyet mutat.

Az adóazonosító jelet az iratokból csak JELÖLTKÉNT olvassuk ki (heurisztika: a leggyakoribb 10 jegyű szám az "Azonosító:" után), mert egy ügyfél vagy a
könyvelő azonosítója is lehet. Ellenőrzésre csak a felhasználó által MEGERŐSÍTETT adóazonosító jel használható (--megerosit-adoazonosito).

CLI:
    python -I .claude/scripts/azonosito.py --frissit                  # azonosito.json előállítása (adószám a Billingóból; adóazonosító jel: jelölt)
    python -I .claude/scripts/azonosito.py --megerosit-adoazonosito   # a jelölt megerősítése (a felhasználó látta a maszkolt számot, és a sajátja)
    python -I .claude/scripts/azonosito.py --allapot                  # megvan-e
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAJL = ROOT / "data" / "vallalkozas" / "azonosito.json"
RE_ADOSZAM = re.compile(r"\b(\d{8})\s?-\s?(\d)\s?-\s?(\d{2})\b")
RE_ADOAZON = re.compile(r"(?:adóazonosító\s*(?:jel\w*)?|Azonosító)\s*:?\s*(\d{10})\b", re.I)


class AzonositoHiba(Exception):
    """A dokumentum nem a vállalkozásé, vagy nincs azonosító; az üzenet a felhasználónak szóló utasítás."""


def _vedett(p: Path) -> None:
    """A személyes azonosítókat tartalmazó fájl csak a jelenlegi felhasználó számára olvasható (Windows: icacls, egyébként chmod 600). Hiba nem állítja meg a futást."""
    try:
        if os.name == "nt":
            user = os.environ.get("USERNAME")
            if user:
                subprocess.run(["icacls", str(p), "/inheritance:r", "/grant:r", f"{user}:(R,W)"], capture_output=True, timeout=20)
        else:
            os.chmod(p, 0o600)
    except Exception:
        pass


def betolt():
    return json.loads(FAJL.read_text(encoding="utf-8")) if FAJL.exists() else None


def maszk(s: str) -> str:
    d = re.sub(r"\D", "", s)
    return "…" + d[-3:] if len(d) >= 3 else "…"


def frissit() -> dict:
    """azonosito.json előállítása a Billingo-cégadatból és az iratok Markdown-jából."""
    szerv = ROOT / "data" / "vallalkozas" / "billingo-szervezet.json"
    if not szerv.exists():
        raise AzonositoHiba("Nincs data/vallalkozas/billingo-szervezet.json. Futtasd: python -I .claude/skills/vallalkozas-dokumentumok/"
                            "scripts/dokumentumok.py --billingo (a .env-ben BILLING_API_KEY kell), vagy rögzítsd az azonosítót kézzel: "
                            "data/vallalkozas/azonosito.json {\"adoszam\": \"...\", \"adoazonosito\": \"...\", \"nev\": \"...\"}.")
    o = json.loads(szerv.read_text(encoding="utf-8")).get("szamla_szervezet", {})
    adoszam = o.get("tax_number") or ""
    azon = None
    md = ROOT / "data" / "vallalkozas" / "iratok-md"
    if md.exists():
        from collections import Counter
        c = Counter()
        for f in md.rglob("*.md"):
            for m in RE_ADOAZON.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                c[m.group(1)] += 1
        if c:
            # a leggyakoribb jelölt, de csak ha legalább 2 iratban előfordul (egyetlen irat más személy azonosítóját is hozhatja); a felhasználó
            # ellenőrizze (a kimenet csak maszkolva mutatja)
            jelolt, db = c.most_common(1)[0]
            azon = jelolt if db >= 2 else None
    regi = betolt() or {}
    # a már megerősített adóazonosító jel megmarad, ha a jelölt azonos vele; más jelölt nem írja felül (a felhasználónak kell újra megerősítenie)
    megerositett = regi.get("adoazonosito") if regi.get("adoazonosito_megerositve") else None
    if megerositett and azon and azon != megerositett:
        print(f"FIGYELEM: az iratokból kiolvasott adóazonosító-jelölt ({maszk(azon)}) eltér a megerősítettől ({maszk(megerositett)}); a megerősítettet tartom meg.")
    d = {"adoszam": adoszam, "adoazonosito": megerositett, "adoazonosito_megerositve": bool(megerositett),
         "adoazonosito_jelolt": azon if not megerositett else None, "nev": o.get("name"), "ev_szam": o.get("ev_number")}
    FAJL.parent.mkdir(parents=True, exist_ok=True)
    FAJL.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    _vedett(FAJL)
    return d


def megvan_vagy_leall(skill: str) -> dict:
    """Az azonosító kötelező: nélküle nem lehet eldönteni, kié a dokumentum. Utasítás a felhasználónak, ha hiányzik."""
    d = betolt()
    if not d or not d.get("adoszam"):
        raise AzonositoHiba(
            f"Megállok ({skill}): a vállalkozás azonosítója még nincs rögzítve, ezért nem tudom ellenőrizni, hogy a dokumentum a te "
            "vállalkozásodé-e. Előbb a vállalkozás adatait kell feldolgoztatni: másold az iratokat az input/vallalkozas-adatok/ mappába, "
            "futtasd a vallalkozas-dokumentumok skillt (--profil), vagy legalább: dokumentumok.py --billingo.")
    return d


def tobb_azonosito(szoveg: str):
    """A szövegben talált adószámok (normalizált 'xxxxxxxx-y-zz') és adóazonosító jelek."""
    ado = {f"{a}-{b}-{c}" for a, b, c in RE_ADOSZAM.findall(szoveg)}
    az = {m.group(1) for m in RE_ADOAZON.finditer(szoveg)}
    return ado, az


def ellenoriz(szoveg: str, fajlnev: str, skill: str, mit: str = "dokumentum") -> None:
    """Kivételt dob (AzonositoHiba) érthető utasítással, ha a dokumentum nem a vállalkozásé."""
    d = megvan_vagy_leall(skill)
    sajat_ado = re.sub(r"\D", "", d.get("adoszam") or "")
    sajat_az = (d.get("adoazonosito") or "") if d.get("adoazonosito_megerositve") else ""  # csak megerősített adóazonosító jel számít
    ado, az = tobb_azonosito(szoveg)
    ado_digits = {re.sub(r"\D", "", x) for x in ado}
    # Határolt keresés: a saját azonosító csak önálló számként (nem hosszabb számjegyfolyam részeként) fogadható el.
    def onallo(azon, minta):
        return bool(azon) and re.search(r"(?<!\d)" + minta + r"(?!\d)", szoveg) is not None
    # NAV-nyomtatványok cellás mezői: a számjegyek külön cellákban állnak ("6 8 6 8 9 4 8 1 1 2 2 8 4 0 9 ..."), a szomszédos mezők (adószám,
    # adóazonosító jel) a nyers szövegkivonatban egyetlen, térközzel tagolt számsorrá folynak össze. Az ilyen számsor digitjeit összeolvasztjuk,
    # és a saját azonosító akkor fogadható el, ha a számsor ELEJÉN vagy VÉGÉN áll (egy hosszabb számsor közepén nem).
    futamok = [re.sub(r"\D", "", m.group(0)) for m in re.finditer(r"(?<!\d)(?:\d\s{1,2}){9,}\d(?!\d)", szoveg)]

    def szokozos(azon):
        return bool(azon) and any(f.startswith(azon) or f.endswith(azon) for f in futamok)
    ado_minta = r"\s?-?\s?".join([sajat_ado[:8], sajat_ado[8:9], sajat_ado[9:11]]) if len(sajat_ado) == 11 else re.escape(sajat_ado)
    megvan = (sajat_ado and (sajat_ado in ado_digits or onallo(sajat_ado, ado_minta))) or (sajat_az and (sajat_az in az or onallo(sajat_az, re.escape(sajat_az)))) or szokozos(sajat_ado) or szokozos(sajat_az)
    if megvan:
        return
    mas = sorted(ado | az)
    if mas:
        raise AzonositoHiba(
            f"MEGÁLLTAM ({skill}): a(z) '{fajlnev}' {mit} NEM a te vállalkozásodra szól. Nem találtam benne a vállalkozás adószámát vagy "
            f"adóazonosító jelét, viszont másik azonosító szerepel benne ({', '.join(maszk(x) for x in mas[:3])}). "
            "Valószínűleg tévedésből másik vállalkozás vagy magánszemély dokumentuma került a mappába. Mit tegyél: ellenőrizd a fájlt, "
            "töröld vagy vidd át a helyes helyre, majd futtasd újra. A fájlt nem dolgoztam fel, az eredeti helyén maradt.")
    raise AzonositoHiba(
        f"MEGÁLLTAM ({skill}): a(z) '{fajlnev}' {mit}ban nem találtam semmilyen adószámot vagy adóazonosító jelet, ezért nem tudom "
        "megállapítani, hogy a vállalkozásodé-e. Mit tegyél: nézd meg a fájlt (szkennelt vagy hiányos PDF lehet), és ha biztosan a tied, "
        "másolj be olvasható változatot. A fájlt nem dolgoztam fel, az eredeti helyén maradt.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if "--megerosit-adoazonosito" in sys.argv:
            d = betolt() or {}
            j = d.get("adoazonosito_jelolt")
            if not j:
                print("Nincs megerősíthető adóazonosító-jelölt (futtasd előbb: --frissit, és legyen legalább 2 irat, amely tartalmazza).")
                sys.exit(1)
            d.update(adoazonosito=j, adoazonosito_megerositve=True, adoazonosito_jelolt=None)
            FAJL.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            _vedett(FAJL)
            print(f"Adóazonosító jel megerősítve ({maszk(j)}); ettől kezdve az ellenőrzés használja.")
        elif "--frissit" in sys.argv:
            d = frissit()
            if d.get("adoazonosito_jelolt"):
                print(f"Adóazonosító-JELÖLT az iratokból: {maszk(d['adoazonosito_jelolt'])} (utolsó 3 számjegy). Kérdezd meg a felhasználót, hogy ez a sajátja-e; "
                      "ha igen: --megerosit-adoazonosito. Addig csak az adószám alapján ellenőrzök.")
            print("azonosito.json kész: adószám:", "megvan" if d.get("adoszam") else "HIÁNYZIK", "; adóazonosító jel:",
                  "megerősítve" if d.get("adoazonosito") else "nincs megerősítve (csak adószámmal ellenőrzök)", "; név:", "megvan" if d.get("nev") else "HIÁNYZIK")
        else:
            d = betolt()
            print("azonosito.json:", "megvan" if d else "HIÁNYZIK (--frissit)")
    except AzonositoHiba as e:
        print(e)
        sys.exit(4)


if __name__ == "__main__":
    main()
