#!/usr/bin/env python3
"""Számlázz.hu (Számla Agent) kimenő számlák lekérése időszakra, csak olvasás.

Használat:
    python -I .claude/skills/szamlak/scripts/szamlazz_szamlak.py TOL IG [--sorozat "ABC-2026-{n}" --n-tol 1 --n-ig 200]
    python -I .claude/skills/szamlak/scripts/szamlazz_szamlak.py TOL IG --szamlaszam ABC-2026-1 ABC-2026-2

FONTOS KORLÁT (https://docs.szamlazz.hu/agent/querying_xml/request): a Számla Agent csak EGY számlát tud lekérdezni számlaszám,
rendelésszám vagy külső azonosító alapján; időszak szerinti listázást nem ad. Ezért a script a számlaszám-sorozatot járja végig
(--sorozat, vagy a .env SZAMLAZZ_SOROZAT értéke; a {n} helyére a sorszám kerül), és a keltezés alapján szűr az időszakra.
A listázást igénylő, tömeges exportot a Számlázz.hu felületéről kell kérni, és az input/bevetelek/ mappába másolni.

Kulcs: .env SZAMLAZZ_API_KEY (Számla Agent kulcs). Ha nincs megadva, a script CSENDBEN kilép (0), nem ír ki semmit.
Személyes adatot nem ír a kimenetre. Szabályok: .claude/rules/adatkezeles.md, nincs-becsles.md.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import azonosito  # noqa: E402
import szamlazz_xml  # noqa: E402

URL = "https://www.szamlazz.hu/szamla/"
OUT = ROOT / "data" / "szamlak"


def env_ertek(nev: str):
    p = ROOT / ".env"
    if p.exists():
        for sor in p.read_text(encoding="utf-8").splitlines():
            sor = sor.strip()
            if sor.startswith(nev + "="):
                v = sor.split("=", 1)[1].strip().strip('"').strip("'")
                return v or None
    return None


def kerdez(kulcs: str, szamlaszam: str):
    """-> ('ok', xml) | ('nincs', uzenet) | ('hiba', uzenet). Egy számla lekérdezése számlaszám alapján, PDF nélkül."""
    kerelem = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<xmlszamlaxml xmlns="http://www.szamlazz.hu/xmlszamlaxml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
               'xsi:schemaLocation="http://www.szamlazz.hu/xmlszamlaxml https://www.szamlazz.hu/szamla/docs/xsds/agentxml/xmlszamlaxml.xsd">\n'
               f"<szamlaagentkulcs>{kulcs}</szamlaagentkulcs>\n<szamlaszam>{szamlaszam}</szamlaszam>\n<pdf>false</pdf>\n</xmlszamlaxml>\n")
    hatar = "----szamlak" + uuid.uuid4().hex
    test = (f"--{hatar}\r\nContent-Disposition: form-data; name=\"action-szamla_agent_xml\"; filename=\"kerdes.xml\"\r\n"
            f"Content-Type: text/xml\r\n\r\n{kerelem}\r\n--{hatar}--\r\n").encode("utf-8")
    rq = urllib.request.Request(URL, data=test, headers={"Content-Type": f"multipart/form-data; boundary={hatar}"})
    try:
        with urllib.request.urlopen(rq, timeout=40) as r:
            szoveg = r.read().decode("utf-8", "replace")
            fejlec_hiba = r.headers.get("szlahu_error")
    except urllib.error.HTTPError as e:
        return "hiba", f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return "hiba", f"a Számlázz.hu nem érhető el ({type(e.reason).__name__})"
    hiba, kod, uzenet = szamlazz_xml.hiba_valasz(szoveg)
    if hiba or fejlec_hiba:
        return "nincs", (uzenet or fejlec_hiba or "ismeretlen hiba") + (f" ({kod})" if kod else "")
    return "ok", szoveg


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    kulcs = env_ertek("SZAMLAZZ_API_KEY")
    if not kulcs:
        sys.exit(0)  # nincs kulcs: csendben átugorjuk az adatok beszerzését
    ap = argparse.ArgumentParser(description="Számlázz.hu számlák lekérése időszakra (számlaszám-sorozat alapján).")
    ap.add_argument("tol", type=date.fromisoformat)
    ap.add_argument("ig", type=date.fromisoformat)
    ap.add_argument("--sorozat", help='számlaszám-minta, pl. "ABC-2026-{n}"')
    ap.add_argument("--n-tol", type=int, default=1)
    ap.add_argument("--n-ig", type=int, default=300)
    ap.add_argument("--szamlaszam", nargs="*", default=[])
    ap.add_argument("--megallas", type=int, default=5, help="ennyi egymás utáni hiányzó számla után a sorozat vége")
    a = ap.parse_args()
    if a.tol > a.ig:
        sys.exit("Hiba: a kezdő dátum későbbi, mint a záró dátum.")
    sorozat = a.sorozat or env_ertek("SZAMLAZZ_SOROZAT")
    szamok = list(a.szamlaszam)
    if not szamok and not sorozat:
        print("ℹ️ Számlázz.hu: a Számla Agent nem listáz számlákat, csak számlaszám alapján kérdez. Add meg a számlaszám-mintát "
              "(--sorozat \"ABC-2026-{n}\" vagy SZAMLAZZ_SOROZAT a .env-ben), vagy exportáld a számlákat a Számlázz.hu felületéről az input/bevetelek/ mappába.")
        return
    try:
        sajat = azonosito.megvan_vagy_leall("szamlak")
    except azonosito.AzonositoHiba as e:
        print(e)
        sys.exit(4)
    sajat_tors = re.sub(r"\D", "", sajat["adoszam"])[:8]

    talalt, kihagyott_tartomanyon_kivul, uzenet_elso = [], 0, None

    def feldolgoz(szam):
        nonlocal uzenet_elso
        allapot, tartalom = kerdez(kulcs, szam)
        if allapot == "hiba":
            print(f"Hiba: {tartalom}. A lekérés megszakadt, adatot nem mentettem.")
            sys.exit(1)
        if allapot == "nincs":
            uzenet_elso = uzenet_elso or tartalom
            return None
        rec = szamlazz_xml.normalizal(tartalom)
        elado = re.sub(r"\D", "", rec.get("seller_tax_number") or "")[:8]
        if elado and elado != sajat_tors:
            print("MEGÁLLTAM (szamlak): a SZAMLAZZ_API_KEY másik vállalkozás Számlázz.hu-fiókjához tartozik, mint a vállalkozói profilod "
                  f"(a számla eladójának adószáma {azonosito.maszk(rec['seller_tax_number'])}, a profilé {azonosito.maszk(sajat['adoszam'])}). "
                  "Mit tegyél: ellenőrizd a .env fájlban a SZAMLAZZ_API_KEY-t (a saját fiókod Számla Agent kulcsa kell). Számlát nem mentettem.")
            sys.exit(4)
        return rec

    if szamok:
        for sz in szamok:
            r = feldolgoz(sz)
            if r:
                talalt.append(r)
    else:
        ures = 0
        for n in range(a.n_tol, a.n_ig + 1):
            r = feldolgoz(sorozat.replace("{n}", str(n)))
            if r:
                talalt.append(r)
                ures = 0
            else:
                ures += 1
                if talalt and ures >= a.megallas:
                    break
    bent = [r for r in talalt if r["invoice_date"] and a.tol <= date.fromisoformat(r["invoice_date"]) <= a.ig]
    OUT.mkdir(parents=True, exist_ok=True)
    fajl = OUT / f"szamlazz_{a.tol}_{a.ig}.json"
    fajl.write_text(json.dumps({"lekerve": datetime.now().isoformat(timespec="seconds"), "tol": str(a.tol), "ig": str(a.ig),
                                "sorozat": sorozat, "szamlak": bent}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Számlázz.hu: {len(talalt)} számla található a sorozatban, ebből {len(bent)} az időszakban ({a.tol} – {a.ig}).")
    if not talalt and uzenet_elso:
        print(f"ℹ️ A Számlázz.hu első válasza: {uzenet_elso}. Ellenőrizd a számlaszám-mintát és a kulcsot.")
    print(f"Mentve: {fajl.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
