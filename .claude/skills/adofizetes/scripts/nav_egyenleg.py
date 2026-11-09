#!/usr/bin/env python3
"""NAV adószámla (tételes XML) feldolgozása és befizetési jelentés.

Használat:
    python -I .claude/skills/adofizetes/scripts/nav_egyenleg.py            # új XML-ek feldolgozása + jelentés
    python -I .claude/skills/adofizetes/scripts/nav_egyenleg.py --jelentes # csak jelentés a már feldolgozott adatból

Folyamat (lásd .claude/rules/adatkezeles.md):
    input/nav-egyenleg/*.xml  ->  data/nav-egyenleg/nav_egyenleg_<lekérdezés>.json
                              ->  archive/nav-egyenleg/  (csak sikeres feldolgozás után)
    jelentés                  ->  data/nav-egyenleg/jelentes_<lekérdezés>.json + képernyő

Csak a Python standard könyvtárát használja. Nem becsül: amit nem tud kiszámolni, azt kimondja.
Az adózó neve, címe, azonosítója és a bankszámla-/számlajelző azonosítók NEM kerülnek az eredménybe.
"""
import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "input" / "nav-egyenleg"
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import bemenet  # noqa: E402
bemenet.takarit_kilepeskor(INPUT)
DATA = ROOT / "data" / "nav-egyenleg"
ARCHIVE = ROOT / "archive" / "nav-egyenleg"
NS = {"a": "adoszamlaafr:export"}


def ft(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " Ft"


def pdate(s):
    """'2026.07.13' -> '2026-07-13' (ISO), None ha nincs."""
    if not s:
        return None
    m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})\.?", s.strip())
    if not m:
        raise ValueError(f"Ismeretlen dátumformátum: {s!r}")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def pdatetime(s):
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})\.\s*(\d{2}):(\d{2}):(\d{2})", (s or "").strip())
    if not m:
        raise ValueError(f"Ismeretlen lekérdezési időpont: {s!r}")
    y, mo, d, h, mi, se = map(int, m.groups())
    return datetime(y, mo, d, h, mi, se)


def to_int(s):
    return None if s is None or s.strip() == "" else int(s.strip())


# ----------------------------------------------------------------- feldolgozás

def parse_xml(path: Path) -> dict:
    root = ET.parse(path).getroot()
    tab = root.find(".//a:tablazat", NS)
    par = root.find(".//a:parameterek", NS)
    if tab is None or par is None:
        raise ValueError("Nem NAV adószámla-export (hiányzik a tablazat/parameterek elem).")
    tipus = par.findtext("a:adoszamlaTipusa", default="", namespaces=NS)
    if "tételes" not in tipus.lower():
        raise ValueError(f"Nem 'Adónem tételes' kivonat (típus: {tipus!r}).")
    lek = pdatetime(par.findtext("a:lekerdezesIdopontja", namespaces=NS))
    idoszak = par.findtext("a:idoszak", default="", namespaces=NS)
    m = re.fullmatch(r"(\d{4}\.\d{2}\.\d{2})-(\d{4}\.\d{2}\.\d{2})", idoszak)
    if not m:
        raise ValueError(f"Ismeretlen időszak: {idoszak!r}")

    def g(t, tag):
        return t.findtext(f"a:{tag}", default=None, namespaces=NS)

    adonemek = []
    for ad in tab.findall("a:adonemek/a:adonem", NS):
        nev = ad.get("megnevezes", "")
        tetelek = []
        for t in ad.findall("a:tetel", NS):
            tetelek.append({
                "kotelezettseg_datum": pdate(g(t, "kotelezettsegDatum")),
                "kotelezettseg_megnevezes": g(t, "kotelezettsegMegnevezes"),
                "kotelezettseg_atvezetes": g(t, "kotelezettsegAtvezetes"),
                "eloiras": to_int(g(t, "kotelezettsegEloiras")),
                "teljesites_datum": pdate(g(t, "penzforgalomTeljesites")),
                "tetel_tipus": g(t, "penzforgalomTetelTipus"),
                "penzforgalom_atvezetes": g(t, "penzforgalomAtvezetes"),
                "penzforgalom": to_int(g(t, "penzforgalomBefizetes")),
            })
        adonemek.append({"kod": nev.split(" - ")[0].strip(), "nev": nev.split(" - ", 1)[-1].strip(),
                         "tetelek": tetelek})
    varo = root.findall(".//a:tablazat_konyvelesre/a:adonemek/a:adonem", NS)
    return {
        "forras_fajl_tipus": "NAV adószámla tételes XML",
        "riport_azonosito": par.findtext("a:riportAzonosito", default=None, namespaces=NS),
        "lekerdezes": lek.isoformat(),
        "idoszak": {"tol": pdate(m.group(1)), "ig": pdate(m.group(2))},
        "konyvelesre_varo_adonemek_szama": len(varo),
        "adonemek": adonemek,
    }


def archive_file(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        dest = dest_dir / f"{datetime.now():%Y%m%dT%H%M%S}_{src.name}"
    shutil.move(str(src), str(dest))
    return dest


def process_new() -> list[Path]:
    done = []
    DATA.mkdir(parents=True, exist_ok=True)
    for xml in sorted(bemenet.fajlok(INPUT, (".xml",)), key=lambda p: p.stat().st_mtime):
        try:
            sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
            import azonosito
            azonosito.ellenoriz(xml.read_text(encoding="utf-8", errors="ignore"), xml.name, "adofizetes", "NAV-adószámla")
            d = parse_xml(xml)
            d["feldolgozva"] = datetime.now().isoformat(timespec="seconds")
            d["eredeti_fajlnev"] = xml.name
            stem = datetime.fromisoformat(d["lekerdezes"]).strftime("%Y%m%dT%H%M%S")
            out = DATA / f"nav_egyenleg_{stem}.json"
            out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:  # a nyers fájl az input-ban marad
            if type(e).__name__ == "AzonositoHiba":
                print(f"🔴 {e}")
            else:
                print(f"HIBA: {xml.name} feldolgozása sikertelen: {e}. A fájl az input/-ban maradt.")
            continue
        a = archive_file(xml, ARCHIVE)
        print(f"Feldolgozva: {xml.name} -> {out.relative_to(ROOT)}")
        print(f"Archiválva:  {a.relative_to(ROOT)}")
        done.append(out)
    return done


def latest_data():
    files = sorted(DATA.glob("nav_egyenleg_*.json"))
    if not files:
        return None, None
    best = max(files, key=lambda p: json.loads(p.read_text(encoding="utf-8"))["lekerdezes"])
    return best, json.loads(best.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- elemzés

def analyze(ad: dict, today: date) -> dict:
    tet = ad["tetelek"]
    elo = [(t["kotelezettseg_datum"], t["eloiras"]) for t in tet
           if t["eloiras"] is not None and t["kotelezettseg_datum"]]
    pf = [(t["teljesites_datum"], t["penzforgalom"], t) for t in tet
          if t["penzforgalom"] is not None and t["teljesites_datum"]]
    sum_elo = sum(v for _, v in elo)
    befiz = [(d, -v, t) for d, v, t in pf if (t["tetel_tipus"] or "").startswith("01") and v < 0]
    kiutal = [(d, v, t) for d, v, t in pf if (t["tetel_tipus"] or "").startswith("02")]
    egyeb = [(d, v, t) for d, v, t in pf if not (t["tetel_tipus"] or "").startswith(("01", "02"))
             or ((t["tetel_tipus"] or "").startswith("01") and v > 0)]
    egyenleg = sum_elo + sum(v for _, v, _ in pf)

    checks = []
    due_dates = sorted({d for d, v in elo if v > 0 and date.fromisoformat(d) <= today})
    for D in due_dates:
        due = sum(v for d, v in elo if d <= D)
        paid = -sum(v for d, v, _ in pf if d <= D)
        row = {"hatarido": D, "esedekes_gongyolt": due, "befizetve_hataridoig": paid}
        if paid >= due:
            row["allapot"] = "rendben"
        else:
            later = sorted({d for d, _, _ in pf if d > D})
            cover = next((P for P in later if -sum(v for d, v, _ in pf if d <= P) >= due), None)
            if cover:
                row["allapot"] = "késve fedezve"
                row["fedezve"] = cover
                row["keses_nap"] = (date.fromisoformat(cover) - date.fromisoformat(D)).days
            else:
                row["allapot"] = "nincs fedezve"
                row["hiany"] = due - paid
        checks.append(row)

    return {
        "kod": ad["kod"], "nev": ad["nev"],
        "eloirasok_osszesen": sum_elo,
        "pozitiv_eloirasok": sum(v for _, v in elo if v > 0),
        "jovairasok_negativ_eloiras": sum(v for _, v in elo if v < 0),
        "befizetesek_osszesen": sum(v for _, v, _ in befiz),
        "ebbol_A_jelzesu": sum(v for _, v, t in befiz if t["penzforgalom_atvezetes"] == "A"),
        "kiutalasok_osszesen": sum(v for _, v, _ in kiutal),
        "egyeb_penzforgalom_osszesen": sum(v for _, v, _ in egyeb),
        "szamitott_egyenleg": egyenleg,  # + tartozás, − túlfizetés
        "befizetesek": [{"datum": d, "osszeg": v, "A_jelzes": t["penzforgalom_atvezetes"] == "A"}
                        for d, v, t in sorted(befiz, key=lambda x: x[0])],
        "hatarido_ellenorzes": checks,
    }


def report(path: Path, data: dict, today: date) -> dict:
    lek = datetime.fromisoformat(data["lekerdezes"])
    age_h = (datetime.now() - lek).total_seconds() / 3600
    results = [analyze(ad, today) for ad in data["adonemek"]]
    out = {"forras": path.name, "lekerdezes": data["lekerdezes"], "idoszak": data["idoszak"],
           "jelentes_datuma": today.isoformat(), "adonemek": results,
           "osszes_befizetes": sum(r["befizetesek_osszesen"] for r in results)}
    stem = path.stem.replace("nav_egyenleg_", "")
    (DATA / f"jelentes_{stem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"== NAV adószámla – befizetések ({data['idoszak']['tol']} – {data['idoszak']['ig']}) ==")
    print(f"Forrás: {path.relative_to(ROOT)}  |  NAV lekérdezés: {lek:%Y-%m-%d %H:%M}  "
          f"({age_h/24:.1f} napja)")
    if age_h > 24:
        print("FIGYELEM: a kivonat több mint 1 napos; azóta történt befizetések nem szerepelnek benne.")
    if data.get("konyvelesre_varo_adonemek_szama"):
        print(f"FIGYELEM: a kivonatban 'könyvelésre váró tétel' is van ({data['konyvelesre_varo_adonemek_szama']} "
              "adónemnél); ezeket nem dolgoztam fel.")
    if data["idoszak"]["tol"] > f"{today.year}-01-01":
        print(f"FIGYELEM: a kivonat időszaka nem az év elejétől indul ({data['idoszak']['tol']}).")
    print()
    for r in results:
        print(f"-- {r['kod']} – {r['nev']}")
        if not (r["befizetesek"] or r["kiutalasok_osszesen"] or r["eloirasok_osszesen"]):
            print("   Nincs tétel (nulla nyitóegyenleg, nincs befizetés).\n")
            continue
        print(f"   Befizetések összesen:   {ft(r['befizetesek_osszesen'])}  "
              f"(ebből 'A' jelzésű: {ft(r['ebbol_A_jelzesu'])})")
        for b in r["befizetesek"]:
            print(f"     {b['datum']}  {ft(b['osszeg']):>14}{'  [A]' if b['A_jelzes'] else ''}")
        if r["kiutalasok_osszesen"]:
            print(f"   Kiutalások összesen:    {ft(r['kiutalasok_osszesen'])}")
        if r["egyeb_penzforgalom_osszesen"]:
            print(f"   Egyéb pénzforgalom:     {ft(r['egyeb_penzforgalom_osszesen'])}")
        print(f"   Előírások összesen:     {ft(r['eloirasok_osszesen'])}  "
              f"(pozitív: {ft(r['pozitiv_eloirasok'])}, jóváírás: {ft(r['jovairasok_negativ_eloiras'])})")
        e = r["szamitott_egyenleg"]
        kind = "TARTOZÁS" if e > 0 else ("TÚLFIZETÉS" if e < 0 else "nulla")
        print(f"   Tételekből számított egyenleg: {ft(abs(e))} {kind}")
        for c in r["hatarido_ellenorzes"]:
            base = (f"   Határidő {c['hatarido']}: esedékes (göngyölt) {ft(c['esedekes_gongyolt'])}, "
                    f"befizetve a határidőig {ft(c['befizetve_hataridoig'])} -> ")
            if c["allapot"] == "rendben":
                print(base + "rendben")
            elif c["allapot"] == "késve fedezve":
                print(base + f"KÉSVE fedezve {c['fedezve']} ({c['keses_nap']} nap késés)")
            else:
                print(base + f"NINCS FEDEZVE, hiány {ft(c['hiany'])}")
        print()
    print(f"Összes befizetés minden adónemben: {ft(out['osszes_befizetes'])}")
    print("\nMegjegyzések (nem ellenőrzött pontok):")
    print("- Az egyenleg a kivonat tételeinek összege (előírás + pénzforgalom); a NAV nem közöl benne összesített egyenleget.")
    print("- Az 'A' jelzés a kivonat 'Átvezetés' oszlopából származik; a pontos jelentését nem ellenőriztem.")
    print("- Az szja-előleg (önbevalló) kötelezettség nem biztos, hogy előírásként megjelenik az adószámlán.")
    print(f"- Jelentés mentve: {(DATA / f'jelentes_{stem}.json').relative_to(ROOT)}")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="NAV adószámla XML feldolgozása és befizetési jelentés.")
    ap.add_argument("--jelentes", action="store_true", help="nem dolgoz fel új fájlt, csak jelent")
    ap.add_argument("--ma", type=date.fromisoformat, default=date.today(), help="teszteléshez: a mai nap (ÉÉÉÉ-HH-NN)")
    args = ap.parse_args()

    if not args.jelentes:
        new = process_new()
        if not new:
            print("Nincs új feldolgozandó XML az input/nav-egyenleg/ mappában; a legutóbb feldolgozott adatból jelentek.\n")
    path, data = latest_data()
    if not data:
        sys.exit("HIBA: nincs feldolgozott NAV adat. Másold a NAV adószámla XML-t az input/nav-egyenleg/ mappába.")
    report(path, data, args.ma)


if __name__ == "__main__":
    main()
