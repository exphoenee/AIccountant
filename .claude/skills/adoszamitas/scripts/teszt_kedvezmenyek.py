#!/usr/bin/env python3
"""Önteszt a kedvezmények számításához (kitalált adatokkal). A várt értékeket a törvényszöveg számaiból egyszerű szorzatként írtuk ide,
a modul kódjától függetlenül (Szja tv. 29/A. § (2): 133 340 / 266 660 / 440 000 Ft; 29/C. § (3): 33 335 Ft; 29/E. § (3): minimálbér/3).
    python -I .claude/skills/adoszamitas/scripts/teszt_kedvezmenyek.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kedvezmenyek as k  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RULES = json.loads((ROOT / "config" / "szabalyok_2026.json").read_text(encoding="utf-8"))
HONAPOK12 = list(range(1, 13))
hibak = []


def check(nev, kapott, vart):
    ok = kapott == vart
    print(("OK     " if ok else "HIBA   ") + nev + ("" if ok else f": kapott {kapott!r}, várt {vart!r}"))
    if not ok:
        hibak.append(nev)


def alk(r, jogcim):
    return next(t["alkalmazott"] for t in r["tetelek"] if t["jogcim"] == jogcim)


r = k.szamol(10_000_000, 10_000_000, {"csaladi": {"honapok": HONAPOK12, "eltartottak": 2, "kedvezmenyezett_eltartottak": 2}}, RULES, 2026)
check("családi, 2 eltartott, 12 hónap: 2 × 266 660 × 12", alk(r, "csaladi"), 2 * 266660 * 12)
check("  adóalap utána", r["adoalap_utana"], 10_000_000 - 2 * 266660 * 12)
check("  szja kedvezménnyel (15%)", r["szja_kedvezmennyel"], round((10_000_000 - 2 * 266660 * 12) * 0.15))

r = k.szamol(10_000_000, 10_000_000, {"csaladi": {"honapok": HONAPOK12, "eltartottak": 1, "kedvezmenyezett_eltartottak": 1, "tartosan_beteg_vagy_sulyosan_fogyatekos": 1}}, RULES, 2026)
check("családi, 1 tartósan beteg eltartott: (133 340 + 133 340) × 12", alk(r, "csaladi"), (133340 + 133340) * 12)

r = k.szamol(10_000_000, 10_000_000, {"csaladi": {"honapok": HONAPOK12, "eltartottak": 3, "kedvezmenyezett_eltartottak": 3}}, RULES, 2026)
check("családi, 3 eltartott: a kedvezmény az adóalapig alkalmazható", alk(r, "csaladi"), 10_000_000)
check("  fel nem használt rész", r["tetelek"][0]["fel_nem_hasznalt"], 3 * 440000 * 12 - 10_000_000)
check("  szja 0", r["szja_kedvezmennyel"], 0)

r = k.szamol(5_000_000, 5_000_000, {"szemelyi": {"honapok": [1, 2, 3]}}, RULES, 2026)
check("személyi kedvezmény: 3 × (322 800 / 3 = 107 600)", alk(r, "szemelyi"), 3 * 107600)

r = k.szamol(5_000_000, 5_000_000, {"elso_hazasok": {"honapok": [1, 2, 3, 4, 5, 6], "sajat_resz": 0.5}}, RULES, 2026)
check("első házasok: 6 × 33 335 × 0,5 (a törvény szerinti összeg Ft-ra kerekítve)", alk(r, "elso_hazasok"), round(6 * 33335 * 0.5))
r = k.szamol(5_000_000, 5_000_000, {"elso_hazasok": {"honapok": [1, 2, 3, 4, 5, 6], "eddig_felhasznalt_honapok": 20}}, RULES, 2026)
check("első házasok: a 24 hónapos korlát túllépése NEM SZÁMOLHATÓ", r["szamolhato"], False)

r = k.szamol(5_000_000, 3_063_200, {"huszonot_ev_alatti": {"honapok": HONAPOK12}}, RULES, 2026)
check("25 év alatti: átlagkereset nélkül NEM SZÁMOLHATÓ (nem találunk ki értéket)", r["szamolhato"], False)
R2 = {**RULES, "brutto_atlagkereset_elozo_julius": 600000}
r = k.szamol(5_000_000, 3_063_200, {"huszonot_ev_alatti": {"honapok": HONAPOK12}}, R2, 2026)
check("25 év alatti: min(jövedelem 5 000 000, plafon 12 × 600 000) = 5 000 000, az adóalapig", alk(r, "huszonot_ev_alatti"), 3_063_200)
r = k.szamol(9_000_000, 7_063_200, {"huszonot_ev_alatti": {"honapok": HONAPOK12}}, {**RULES, "brutto_atlagkereset_elozo_julius": 500000}, 2026)
check("25 év alatti: a plafon (12 × 500 000) a kisebb", alk(r, "huszonot_ev_alatti"), 12 * 500000)

r = k.szamol(6_000_000, 4_063_200, {"ketto_anya": {"honapok": [1, 2, 3, 4, 5, 6]}}, RULES, 2026)
check("kétgyermekes anya, 6 hónap: a jövedelem 6/12-e", alk(r, "ketto_anya"), 3_000_000)
r = k.szamol(6_000_000, 4_063_200, {"ketto_anya": {"honapok": HONAPOK12}, "harom_anya": {"honapok": HONAPOK12}}, RULES, 2026)
check("két anyai jogcím egyszerre NEM SZÁMOLHATÓ (29/H. § (2): egyet kell választani)", r["szamolhato"], False)

r = k.szamol(500_000 + 1_936_800, 500_000, {"szemelyi": {"honapok": [1, 2, 3]}, "csaladi": {"honapok": [1], "eltartottak": 1, "kedvezmenyezett_eltartottak": 1}}, RULES, 2026)
check("sorrend (29/H.): először a személyi (322 800), utána a családi (133 340)", [t["jogcim"] for t in r["tetelek"]], ["szemelyi", "csaladi"])
check("  a családi csak a megmaradt adóalapig: 500 000 − 322 800 = 177 200 ≥ 133 340", alk(r, "csaladi"), 133340)
check("  szja: (500 000 − 322 800 − 133 340) × 15% = 43 860 × 15%", r["szja_kedvezmennyel"], round(43860 * 0.15))

r = k.szamol(5_000_000, 3_063_200, {"csaladi": {"honapok": [1], "eltartottak": 1, "kedvezmenyezett_eltartottak": 1, "csaladi_jarulekkedvezmeny_ft": 15000}}, RULES, 2026)
check("családi kedvezmény csökkentése a járulékkedvezménnyel: 133 340 − 15 000 / 0,15", alk(r, "csaladi"), 133340 - 100000)

r = k.szamol(5_000_000, 3_063_200, {"csaladi": True}, RULES, 2026)
check("csak igen/nem jelzés: NEM SZÁMOLHATÓ", (r["szamolhato"], r["szja_kedvezmennyel"]), (False, None))
r = k.szamol(5_000_000, 3_063_200, {"csaladi": {"honapok": [1, 13], "eltartottak": 1, "kedvezmenyezett_eltartottak": 1}}, RULES, 2026)
check("érvénytelen hónap (13): NEM SZÁMOLHATÓ", r["szamolhato"], False)
r = k.szamol(5_000_000, 3_063_200, {"csaladi": {"honapok": [1], "eltartottak": 1, "kedvezmenyezett_eltartottak": 2}}, RULES, 2026)
check("kedvezményezett eltartott > eltartott: NEM SZÁMOLHATÓ", r["szamolhato"], False)

print()
if hibak:
    print(f"{len(hibak)} teszt HIBÁS: {hibak}")
    sys.exit(1)
print("Minden kedvezmény-teszt megfelelt.")
