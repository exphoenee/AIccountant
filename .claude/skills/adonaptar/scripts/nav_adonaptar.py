#!/usr/bin/env python3
"""A NAV általános adónaptárának letöltése az adott évre, és szűrt Markdown-naptár készítése az input/adonaptar/<év>.md fájlba.

Használat:
    python -I .claude/skills/adonaptar/scripts/nav_adonaptar.py                 # az aktuális év
    python -I .claude/skills/adonaptar/scripts/nav_adonaptar.py --ev 2026
    python -I .claude/skills/adonaptar/scripts/nav_adonaptar.py --ev 2026 --felulir   # meglévő input/adonaptar/<év>.md felülírása

Forrás: https://nav.gov.hu/fooldal-elemei/fooldali-csempek/adonaptar/altalanos-adonaptar/esmenyek/<év>/<hónap> (hivatalos NAV-oldal, 12 havi aloldal).
Az oldalak szerveroldalon renderelt események (data-date = tényleges határidő, a munkaszüneti nap miatti eltolással). A script a NAV összes
eseményéből **csak az átalányadózó egyéni vállalkozóra vonatkozó sorokat** írja a naptárba (a szűrés szabályai lent, a szur() függvényben);
a kihagyott sorok számát kiírja. A kimenet az `adonaptar.py` bemeneti formátuma; a feldolgozás külön lépés (python -I .../adonaptar.py).

Ami a NAV általános adónaptárában NINCS, és külön kell kezelni: a helyi iparűzési adó előlege (önkormányzati), a kamarai hozzájárulás
(1999. évi CXXI. tv. 34/A. §, március 31.), egyedi vállalkozói teendők. A script ezt a naptár fejlécében jelzi, nem találja ki.
Standard könyvtárral működik; csak a nyilvános oldalakat kéri le, személyes adatot nem küld.
"""
import argparse
import html
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "input" / "adonaptar"
BASE = "https://nav.gov.hu/fooldal-elemei/fooldali-csempek/adonaptar/altalanos-adonaptar/esmenyek"
HONAPOK = ["januar", "februar", "marcius", "aprilis", "majus", "junius", "julius", "augusztus", "szeptember", "oktober", "november", "december"]
# a határidő hónapja -> a megelőző negyedév (januárban az előző év IV. negyedéve)
NEGYEDEV = {1: "IV.", 4: "I.", 7: "II.", 10: "III."}

# Szűrő (átalányadózó egyéni vállalkozó); minden más NAV-sor kimarad. Az űrlapkód a "Nyomtatvány jele" oszlopból jön.
RE_2658 = re.compile(r"^(2658|2558)$")
RE_SZJA_BEV = re.compile(r"^\d\dSZJA$")
RE_HIPAK = re.compile(r"^\d\dHIPAK$")
RE_EV_ELOLEG = re.compile(r"egyéni vállalkozó.*adóelőleg", re.I)


def txt(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def letolt(url: str) -> str:
    rq = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AIccountant adonaptar)", "Accept-Language": "hu"})
    with urllib.request.urlopen(rq, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def esemenyek(oldal: str):
    """-> [(tényleges dátum, cím, [(szakasz, megnevezés, űrlapkód, index)])]"""
    out = []
    for e in re.split(r'<div class="content-list-elements calendarevent"', oldal)[1:]:
        d = re.search(r'data-date="(\d{4}-\d\d-\d\d)', e)
        c = re.search(r"<h3[^>]*>(.*?)</h3>", e, re.S)
        if not d or not c:
            continue
        sor, szakasz = [], ""
        for r in re.findall(r"<tr.*?</tr>", e, re.S):
            cells = [txt(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) == 1:
                szakasz = cells[0]
            elif cells and cells[0] != "Kötelezettség":
                sor.append((szakasz, cells[0], cells[1] if len(cells) > 1 else "", cells[2] if len(cells) > 2 else ""))
        out.append((d.group(1), txt(c.group(1)), sor))
    return out


def szur(esem):
    """A releváns sorok: [(dátum, adónem, teendő, megjegyzés)], és a kihagyott sorok száma."""
    rows, kihagyva = [], 0
    for datum, cim, sorok in esem:
        honap = int(datum[5:7])
        eredeti = re.search(r"\(([^)]+)\)", cim)
        eredeti_txt = (f"A NAV-naptár szerinti eredeti határidő: {eredeti.group(1)} (a tényleges határidő munkaszüneti nap miatt tolódik)."
                       if eredeti else "")
        tb_van = szja_van = False
        for szakasz, nev, kod, _idx in sorok:
            if szakasz == "Bevallás" and RE_2658.match(kod) and honap in NEGYEDEV and not tb_van:
                tb_van = True
                rows.append((datum, "TBJ, SZOCHO",
                             f"{NEGYEDEV[honap]} negyedévi TBJ és SZOCHO befizetése, valamint a **{kod}** bevallás beadása", eredeti_txt))
            elif szakasz == "Bevallás" and RE_SZJA_BEV.match(kod):
                rows.append((datum, "SZJA", f"**{kod}** bevallás beadása", eredeti_txt))
            elif szakasz == "Bevallás" and RE_HIPAK.match(kod):
                rows.append((datum, "IPA", f"Iparűzési adóbevallás (**{kod}**) beadása",
                             ("Normál IPA-t választóknak és a NAV-naptár szerinti egyéb eseteknél; a feltételeket a helyi-ipa skill / könyvelő tisztázza. "
                              + eredeti_txt).strip()))
            elif szakasz == "Befizetés" and RE_EV_ELOLEG.search(nev) and honap in NEGYEDEV and not szja_van:
                szja_van = True
                rows.append((datum, "SZJA", f"{NEGYEDEV[honap]} negyedévi SZJA előleg befizetése",
                             ("Átalányadózónál csak akkor, ha a göngyölt átalányos jövedelem meghaladja az adómentes keretet. " + eredeti_txt).strip()))
            else:
                kihagyva += 1
    return rows, kihagyva


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="NAV általános adónaptár letöltése és szűrése átalányadózó egyéni vállalkozóra.")
    ap.add_argument("--ev", type=int, default=date.today().year)
    ap.add_argument("--felulir", action="store_true", help="a meglévő input/adonaptar/<év>.md felülírása")
    a = ap.parse_args()
    out = INPUT / f"{a.ev}.md"
    if out.exists() and not a.felulir:
        sys.exit(f"HIBA: már van {out.relative_to(ROOT)}; felülíráshoz: --felulir")
    esem, hibak = [], []
    for h in HONAPOK:
        try:
            esem += esemenyek(letolt(f"{BASE}/{a.ev}/{h}"))
        except Exception as e:  # noqa: BLE001
            hibak.append(f"{h}: {e}")
    if hibak or not esem:
        sys.exit("HIBA: a NAV-oldal letöltése nem sikerült (" + "; ".join(hibak or ["nincs esemény az oldalakon"]) + "). Nem írtam fájlt.")
    rows, kihagyva = szur(esem)
    if not rows:
        sys.exit("HIBA: a szűrés után nem maradt releváns határidő; a NAV-oldal szerkezete megváltozhatott. Nem írtam fájlt.")
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    L = [f"# {a.ev}-os adónaptár átalányadózó egyéni vállalkozóra (a NAV általános adónaptárából szűrve)", "",
         f"> Forrás: NAV általános adónaptár, {BASE}/{a.ev}/<hónap> · letöltve: {datetime.now():%Y-%m-%d %H:%M} · "
         f"a NAV {len(esem)} napi eseményéből a releváns sorok; {kihagyva} sor kimaradt.",
         "> A szűrés szabályai: `nav_adonaptar.py` (2658/2558 bevallás, SZJA-bevallás, HIPAK, az egyéni vállalkozó adóelőlege). "
         "Eltérésnél a NAV oldala az irányadó.",
         "> **Nem szerepel benne** (nincs a NAV általános adónaptárában): a helyi iparűzési adó előlege (önkormányzati; `helyi-ipa` skill), "
         "a kamarai hozzájárulás (1999. évi CXXI. tv. 34/A. §, március 31.), egyedi teendők.", "",
         "| Határidő | Adónem | Teendő | Megjegyzés |", "|---|---|---|---|"]
    for d, ad, te, mj in rows:
        L.append(f"| **{d[:4]}.{d[5:7]}.{d[8:10]}.** | {ad} | {te} | {mj} |")
    INPUT.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"NAV-adónaptár {a.ev}: {len(esem)} napi esemény, {len(rows)} releváns sor -> {out.relative_to(ROOT)} ({kihagyva} sor kihagyva)")
    print("Következő lépés: python -I .claude/skills/adonaptar/scripts/adonaptar.py")


if __name__ == "__main__":
    main()
