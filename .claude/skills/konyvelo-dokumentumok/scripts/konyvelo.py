#!/usr/bin/env python3
"""A könyvelőtől kapott iratok (input/konyvelo/) feldolgozása és a könyvelői számítások ellenőrzése.

Használat:
    python -I .claude/skills/konyvelo-dokumentumok/scripts/konyvelo.py --feldolgoz        # PDF -> Markdown + adatkivonat, archiválás
    python -I .claude/skills/konyvelo-dokumentumok/scripts/konyvelo.py --ellenoriz [ÉV]   # a könyvelő adói vs. számított, bevallások

Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md. Csak szabványos könyvtár; a PDF-szöveget a pdftotext adja.
A kivonat csak az iratokból kiolvasott összeg (adónemenként, időszakonként); adószám, név, bankszámla nem kerül a kimenetbe.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import azonosito  # noqa: E402
IN = ROOT / "input" / "konyvelo"
import bemenet  # noqa: E402
bemenet.takarit_kilepeskor(IN)
ARCH = ROOT / "archive" / "konyvelo"
DATA = ROOT / "data" / "konyvelo"
KIV = DATA / "konyvelo_adatok.json"
REGF = ROOT / "data" / "nav-egyenleg" / "bevallasok.json"
PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"
ADONEM = {"103": "SZJA", "406": "TBJ", "258": "SZOCHO"}
KULCS = {"TBJ": "0.185", "SZOCHO": "0.13"}


def ft(n):
    return f"{int(n):,}".replace(",", " ") + " Ft"


def pdftotext() -> str:
    exe = shutil.which("pdftotext")
    if exe:
        return exe
    for c in (r"C:\Program Files\Git\mingw64\bin\pdftotext.exe", r"C:\Program Files\Git\usr\bin\pdftotext.exe"):
        if Path(c).exists():
            return c
    sys.exit("HIBA: nincs pdftotext")


def raw_text(pdf: Path) -> str:
    r = subprocess.run([pdftotext(), "-raw", "-enc", "UTF-8", "-q", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def idoszak_a_nevbol(nev: str):
    """'Utalandó adók 2026.07' / 'Utalandó járulékok 2026.Q2' -> (ev, 'M7' | 'Q2')."""
    m = re.search(r"(20\d\d)\.(Q[1-4]|\d{2})", nev)
    if not m:
        return None, None
    p = m.group(2)
    return int(m.group(1)), (p if p.startswith("Q") else "M" + str(int(p)))


def negyedev_of(per: str):
    if per.startswith("Q"):
        return int(per[1])
    return (int(per[1:]) - 1) // 3 + 1


def parse_utalando(txt: str):
    """Tételsor: <megnevezés> <mérték> <bankszámla 8-8 jegy> <összeg>; az adónemkód a következő sorok egyikében."""
    sorok = [s.strip() for s in txt.splitlines() if s.strip()]
    tetelek = []
    for i, s in enumerate(sorok):
        m = re.search(r"\d{8}-\d{8}\s+(\d{1,3}(?: \d{3})*)\s*$", s)
        if not m:
            continue
        kod = None
        for j in range(i + 1, min(i + 3, len(sorok))):
            if sorok[j] in ADONEM:
                kod = sorok[j]
                break
        tetelek.append({"adonem_kod": kod, "adonem": ADONEM.get(kod), "osszeg": int(m.group(1).replace(" ", ""))})
    tot = None
    for i, s in enumerate(sorok):
        if "ÖSSZESEN FIZETENDŐ" in s:
            for c in (sorok[i - 1] if i else "", sorok[i + 1] if i + 1 < len(sorok) else ""):
                if re.fullmatch(r"\d{1,3}(?: \d{3})*", c):
                    tot = int(c.replace(" ", ""))
    kelt = re.search(r"(20\d\d\.\d\d\.\d\d) \d\d:\d\d:\d\d", txt)
    return tetelek, tot, (kelt.group(1).replace(".", "-") if kelt else None)


def parse_2658(txt: str):
    t = txt.replace("\n", " ")
    nyomt = re.search(r"Nyomtatva: (20\d\d\.\d\d\.\d\d)", t)
    idosz = None
    for s in txt.splitlines():
        d = s.replace(" ", "")
        if re.fullmatch(r"20\d{6}20\d{6}", d):
            idosz = (d[:8], d[8:])
            break
    # A nyomtatvány számmezőit a szövegréteg nem adja megbízhatóan (mind 0), ezért összeget nem olvasunk ki belőle.
    f = lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}"
    return {"nyomtatva": nyomt.group(1).replace(".", "-") if nyomt else None,
            "idoszak_tol": f(idosz[0]) if idosz else None, "idoszak_ig": f(idosz[1]) if idosz else None}


def load():
    return json.loads(KIV.read_text(encoding="utf-8")) if KIV.exists() else {"iratok": []}


def feldolgoz():
    pdfs = bemenet.fajlok(IN, (".pdf",))  # almappákkal együtt, kis/nagybetű független
    if not pdfs:
        print("Az input/konyvelo/ mappa üres: nincs mit feldolgozni.")
        return 0
    DATA.mkdir(parents=True, exist_ok=True)
    ARCH.mkdir(parents=True, exist_ok=True)
    (DATA / "md").mkdir(exist_ok=True)
    adat = load()
    by = {x["fajl"]: x for x in adat["iratok"]}
    hiba = 0
    kesz = []
    for p in pdfs:
        txt = raw_text(p)
        try:
            azonosito.ellenoriz(txt, p.name, "konyvelo-dokumentumok", "irat")
        except azonosito.AzonositoHiba as e:
            print(f"🔴 {e}")
            hiba += 1
            continue
        kesz.append(p)
        ev, per = idoszak_a_nevbol(p.stem)
        rec = {"fajl": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
               "feldolgozva": datetime.now().isoformat(timespec="seconds")}
        if p.name.startswith("2658_"):
            rec.update({"tipus": "2658", **parse_2658(txt)})
            if rec["idoszak_ig"]:
                rec["ev"] = int(rec["idoszak_ig"][:4])
                rec["negyedev"] = (int(rec["idoszak_ig"][5:7]) - 1) // 3 + 1
        elif p.name.startswith("Utalandó"):
            tet, tot, kelt = parse_utalando(txt)
            ok = tot is not None and sum(t["osszeg"] for t in tet) == tot
            rec.update({"tipus": "utalando", "ev": ev, "idoszak": per, "negyedev": negyedev_of(per) if per else None,
                        "tetelek": tet, "osszesen_fizetendo": tot, "osszeg_egyezik": ok, "kelt": kelt})
            if not ok:
                print(f"🔴 {p.name}: a tételek összege nem egyezik az ÖSSZESEN sorral, a kivonat nem megbízható")
                hiba += 1
        elif p.name.startswith("Bérösszesítő"):
            rec.update({"tipus": "berosszesito", "ev": ev, "idoszak": per, "negyedev": negyedev_of(per) if per else None})
        else:
            rec.update({"tipus": "ismeretlen"})
            print(f"❓ {p.name}: ismeretlen irattípus; csak Markdown készül, kivonat nincs")
        by[p.name] = rec
        subprocess.run([sys.executable, "-I", str(PDFMD), "--fajl", str(p), "--ki", str(DATA / "md" / (p.stem + ".md"))],
                       capture_output=True, text=True, encoding="utf-8")
        print(f"+ {p.name}: {rec['tipus']}" + (f", {rec.get('ev')} {rec.get('idoszak', '')}" if rec.get("ev") else ""))
    adat["iratok"] = sorted(by.values(), key=lambda x: x["fajl"])
    KIV.write_text(json.dumps(adat, ensure_ascii=False, indent=1), encoding="utf-8")
    if hiba:
        print("A hibás fájlok az input/konyvelo/-ban maradtak; a rendben lévők feldolgozása megtörtént.")
    for p in kesz:
        dst = ARCH / p.name
        if dst.exists():
            dst = ARCH / (datetime.now().strftime("%Y%m%dT%H%M%S_") + p.name)
        shutil.move(str(p), str(dst))
    print("Kivonat: data/konyvelo/konyvelo_adatok.json; Markdown: data/konyvelo/md/; eredetik: archive/konyvelo/")
    return 0


def ellenoriz(ev: int):
    if not KIV.exists():
        print("ℹ️ Könyvelői iratok: nincs feldolgozott irat (input/konyvelo/ -> --feldolgoz). A könyvelői ellenőrzés kimarad.")
        return {"allapot": "nincs_irat", "negyedevek": []}
    adat = load()
    szp = ROOT / "data" / "szamitas" / f"adoszamitas_{ev}.json"
    if not szp.exists():
        print(f"❓ Nincs data/szamitas/adoszamitas_{ev}.json: futtasd az adoszamitas skillt.")
        return {"allapot": "nem_szamolhato", "negyedevek": []}
    szam = json.loads(szp.read_text(encoding="utf-8"))
    rules = json.loads((konfig.szabalyok_ut(ev)).read_text(encoding="utf-8"))
    navs = sorted((ROOT / "data" / "nav-egyenleg").glob("nav_egyenleg_*.json"))
    nav = json.loads(navs[-1].read_text(encoding="utf-8")) if navs else None
    cfg = json.loads((konfig.vallalkozas_ut()).read_text(encoding="utf-8"))
    kezdes = cfg.get("vallalkozas_kezdete")
    ki = []
    print(f"=== Könyvelői ellenőrzés ({ev}): a könyvelő adói vs. számított, bevallások időben")
    for q in szam["negyedevek"]:
        n = q["negyedev"]
        if not q["allapot"].startswith("lez"):
            continue
        d = q["tb_hatarido"]
        if kezdes and q["ig"] < kezdes:
            print(f"-- {n}. negyedév: a tevékenység folytatása ({kezdes}) előtt ér véget; nincs kötelezettség, nem ellenőrzöm")
            continue
        sor = {"negyedev": n, "hatarido": d, "tetelek": []}
        print(f"-- {n}. negyedév (határidő: {d})")
        iratok = [x for x in adat["iratok"] if x.get("ev") == ev and x.get("negyedev") == n and x["tipus"] == "utalando"]
        if not iratok:
            print("   ❓ nincs a könyvelőtől kapott 'Utalandó' irat erre a negyedévre; a könyvelő adói nem ellenőrizhetők")
            sor["tetelek"].append({"szint": "nem_ellenorizheto", "szoveg": "nincs utalandó irat"})
        else:
            if any(not x["osszeg_egyezik"] for x in iratok):
                print("   ❓ egy irat tételeinek összege nem egyezik az ÖSSZESEN sorral; nem megbízható")
            for nem, kulcs in (("SZJA", "szja_eloleg"), ("TBJ", "tbj_eloleg"), ("SZOCHO", "szocho_eloleg")):
                konyv = sum(t["osszeg"] for x in iratok for t in x["tetelek"] if t["adonem"] == nem)
                szamolt = q[kulcs]
                diff = konyv - szamolt
                rec = {"adonem": nem, "konyvelo": konyv, "szamitott": szamolt, "elteres": diff,
                       "szint": "ok" if diff == 0 else "hiba"}
                if diff == 0:
                    print(f"   ✅ {nem}: a könyvelő {ft(konyv)} = számított {ft(szamolt)}")
                else:
                    print(f"   🔴 {nem}: a könyvelő {ft(konyv)} ≠ számított {ft(szamolt)} (eltérés {ft(diff)})")
                if nem in KULCS and konyv:
                    alap = (Decimal(konyv) / Decimal(KULCS[nem])).quantize(Decimal("1"), ROUND_HALF_UP)
                    napok = (alap / Decimal(rules["minimalber_havi"]) * 30).quantize(Decimal("0.01"))
                    rec["levezetett_alap"] = int(alap)
                    print(f"        a könyvelői adóból levezetett járulékalap: {ft(alap)} (a minimálbér havi 1/30-ával számolva {napok} nap; levezetés, nem a könyvelő adata)")
                sor["tetelek"].append(rec)
        # bevallás időbelisége
        b = [x for x in adat["iratok"] if x["tipus"] == "2658" and x.get("ev") == ev and x.get("negyedev") == n]
        if b:
            ny = b[0]["nyomtatva"]
            print(f"   2658 irat megvan, nyomtatva: {ny} ({'a határidő előtt' if ny and ny <= d else 'a határidő UTÁN'}); a nyomtatás napja nem a beadás napja")
            sor["tetelek"].append({"bevallas": "2658-irat", "nyomtatva": ny, "hatarido": d})
        elif (REGF.exists() and f"2658|{ev}-Q{n}" in json.loads(REGF.read_text(encoding="utf-8"))["bevallasok"]):
            e = json.loads(REGF.read_text(encoding="utf-8"))["bevallasok"][f"2658|{ev}-Q{n}"]
            ku = e.get("kulcsadatok", {})
            konyv = {nem: sum(t["osszeg"] for x in iratok for t in x["tetelek"] if t["adonem"] == nem) for nem in ("TBJ", "SZOCHO")}
            egy = ku.get("tbj") == konyv["TBJ"] and ku.get("szocho") == konyv["SZOCHO"]
            print(f"   2658 a NAV-ról letöltött bevallások között megvan ({e['forras']}); a benne lévő TBJ {ft(ku.get('tbj', 0))}, SZOCHO {ft(ku.get('szocho', 0))} "
                  + ("egyezik a könyvelő utalandó összegeivel ✅" if egy else "NEM egyezik a könyvelő utalandó összegeivel 🔴"))
            sor["tetelek"].append({"bevallas": "2658-nyilvantartas", "egyezik": egy})
        else:
            print("   ❓ nincs a könyvelőtől 2658-as bevallás irat erre a negyedévre")
            sor["tetelek"].append({"bevallas": "2658-irat", "szint": "nem_ellenorizheto"})
        if nav:
            ad = next((a for a in nav["adonemek"] if a["kod"] == "406"), None)
            van = bool(ad) and any(t["kotelezettseg_datum"] == d and "negyedéves bevallás" in (t["kotelezettseg_megnevezes"] or "")
                                   for t in ad["tetelek"])
            if van:
                print(f"   ✅? a NAV adószámlán van negyedéves bevallási előírás a {d} napra (a bevallás megtörtént; a beadás napját ez nem mondja meg)")
            else:
                print(f"   🔴 a NAV adószámlán nincs negyedéves bevallási előírás a {d} napra: a bevallás elkészültét nem tudom igazolni")
            sor["tetelek"].append({"bevallas": "nav-eloiras", "van": van})
        ki.append(sor)
    return {"allapot": "kesz", "ev": ev, "negyedevek": ki}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--feldolgoz", action="store_true")
    ap.add_argument("--ellenoriz", nargs="?", const=str(date.today().year))
    a = ap.parse_args()
    if a.feldolgoz:
        sys.exit(feldolgoz())
    if a.ellenoriz:
        r = ellenoriz(int(a.ellenoriz))
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / f"ellenorzes_{a.ellenoriz}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
