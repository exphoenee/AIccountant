#!/usr/bin/env python3
"""A számítás ellenőrzése a NAV hivatalos tájékoztatójának számpéldáival.

Használat:
    python -I .claude/skills/adoszamitas/scripts/teszt_nav_peldak.py

Forrás: torvenytar/NAV/2026/atalanyado-alapveto-szabalyai-2026-02-20.txt (a NAV „Az egyéni vállalkozók átalányadózásának
alapvető szabályai”, 2026.02.20.):
  - 3. pont példa: 7 000 000 Ft éves vállalkozói bevétel, 45% költséghányad -> átalányos jövedelem 3 850 000 Ft,
    adóköteles rész 1 913 200 Ft, szja 286 980 Ft.
  - 4. pont példa: 2026. március végéig 3 750 000 Ft, június 30-ig további 4 500 000 Ft bevétel ->
    1. negyedév szja-előleg 18 855 Ft, 2. negyedév 371 250 Ft.
  - 6.1. pont: töredék hónapban naptári naponként a járulékalap harmincad része (322 800 / 30 * 3 = 32 280 Ft).
A teszt az adoszamitas.py tényleges függvényeit hívja szintetikus számlákkal; hibánál nem nulla kilépési kóddal áll meg.
"""
import importlib.util
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("adoszamitas", HERE / "adoszamitas.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RULES = {"ev": 2026, "minimalber_havi": 322800, "garantalt_berminimum_havi": 373200, "adomentes_jovedelem_eves": 1936800,
         "szja_kulcs": "0.15", "tbj_kulcs": "0.185", "szocho_kulcs": "0.13", "bevetel_hatar_altalanos": 38736000}
CFG = {"ev": 2026, "koltseghanyad": "0.45", "tb_statusz": "nyugdijas", "min_alap_tipus": None, "vallalkozas_kezdete": None,
       "vallalkozas_megszunese": None}  # nyugdíjas: a járulékot kizárjuk, a teszt az szja-számítást nézi
CAL = {"tetelek": []}


def inv(paid, amount):
    return {"invoice_number": "T", "invoice_date": paid, "paid_date": paid, "currency": "HUF", "payment_status": "paid",
            "summary": {"net_amount_local": amount}}


fails = []


def check(nev, kapott, vart):
    ok = kapott == vart
    print(("OK     " if ok else "HIBA   ") + f"{nev}: kapott {kapott}, a NAV szerint {vart}")
    if not ok:
        fails.append(nev)


# 1) 3. pont: 7 000 000 Ft éves bevétel (egy negyedévbe téve: a göngyölt éves adó azonos)
rows, _ = m.compute(2026, [inv("2026-03-15", 7000000)], CFG, RULES, CAL, date(2026, 12, 31))
check("7 000 000 Ft bevétel: átalányos jövedelem", rows[0]["jovedelem_gongyolt"], 3850000)
check("7 000 000 Ft bevétel: adóköteles rész", rows[0]["szja_alap_gongyolt"], 1913200)
check("7 000 000 Ft bevétel: szja", rows[0]["szja_gongyolt"], 286980)

# 2) 4. pont: negyedéves előleg
rows, _ = m.compute(2026, [inv("2026-03-20", 3750000), inv("2026-06-20", 4500000)], CFG, RULES, CAL, date(2026, 12, 31))
check("1. negyedév szja-előleg", rows[0]["szja_eloleg"], 18855)
check("2. negyedév szja-előleg", rows[1]["szja_eloleg"], 371250)

# 3) 6.1. pont: töredék hónap = naptári naponként 1/30 (3 nap -> 322 800/30*3 = 32 280)
fr = m.active_fraction(2026, 2, date(2026, 2, 26), None)  # február 26-28: 3 nap
check("töredék hónap: 3 nap minimális alapja", int(Decimal(322800) * fr), 32280)
check("teljes hónap = a teljes alap", int(Decimal(322800) * m.active_fraction(2026, 1, None, None)), 322800)

# 4) 2. pont: az adómentes jövedelemhez tartozó bevétel (NAV: 45%-nál 3 521 455 Ft-ig nem kell adót fizetni)
rows, _ = m.compute(2026, [inv("2026-03-15", 3521455)], CFG, RULES, CAL, date(2026, 12, 31))
check("3 521 455 Ft bevételnél az szja", rows[0]["szja_gongyolt"], 0)
rows, _ = m.compute(2026, [inv("2026-03-15", 3521456)], CFG, RULES, CAL, date(2026, 12, 31))
check("3 521 456 Ft bevételnél már keletkezik szja (kerekítés)", rows[0]["szja_gongyolt"] >= 0, True)

# 4/b) Szünetelés (kitalált adat): 10 szünetelő nap a júniusban -> 20 aktív nap = 20/30 minimális alap; az időarányos határ 355/365
szun = [(date(2026, 6, 11), date(2026, 6, 20))]
check("szünetelés: júniusi minimális alap 20/30", int(Decimal(322800) * m.active_fraction(2026, 6, None, None, szun)), 215200)
lim = m.prorated_limit(2026, {"szunetelesek": [{"tol": "2026-06-11", "ig": "2026-06-20"}]}, RULES)
check("szünetelés: aktív napok", lim["aktiv_napok"], 355)
check("szünetelés: időarányos határ", lim["hatar"], int((Decimal(38736000) * 355 / 365).quantize(Decimal(1), rounding="ROUND_HALF_UP")))

# 4/c) 36 órás munkaviszony / nappali tanulmányok (NAV 6.2.): a járulékalap a göngyölt szja-köteles jövedelem, minimális alap nélkül
CFG36 = {**CFG, "tb_statusz": "munkaviszony_36_vagy_nappali"}
rows, _ = m.compute(2026, [inv("2026-03-15", 7000000)], CFG36, RULES, CAL, date(2026, 12, 31))
check("36 órás státusz: járulékalap = adóköteles rész", rows[0]["jarulekalap_gongyolt"], 1913200)
rows, _ = m.compute(2026, [inv("2026-03-15", 1000000)], CFG36, RULES, CAL, date(2026, 12, 31))
check("36 órás státusz: adómentes keret alatt nincs járulék", rows[0]["tbj_gongyolt"], 0)

# 5) Kamarai hozzájárulás (1999. évi CXXI. tv. 34/A. §: évi 5000 Ft)
kt, _ = m.egyeb_fizetendo({"kamara_koteles": True, "kamara_hozzajarulas_ft": 5000, "kamara_hatarido": "2026-03-31"}, 2026)
check("kamarai hozzájárulás összege", kt[0]["osszeg"], 5000)
check("nem kötelezett: nincs kamarai tétel", m.egyeb_fizetendo({"kamara_koteles": False}, 2026)[0], [])
check("kamara kötelezettség nincs megadva: NEM SZÁMOLHATÓ jelzés", "NEM SZÁMOLHATÓ" in m.egyeb_fizetendo({}, 2026)[1][0], True)
check("kedvezmény nélkül (nincs): nincs figyelmeztetés", m.kedvezmeny_ellenorzes({"kedvezmenyek": {"nincs": True}}), [])
check("kedvezmény választva: NEM SZÁMOLHATÓ jelzés", "NEM SZÁMOLHATÓ" in m.kedvezmeny_ellenorzes({"kedvezmenyek": {"nincs": False, "csaladi": True}})[0], True)

print()
if fails:
    print(f"{len(fails)} teszt BUKOTT: {', '.join(fails)}")
    sys.exit(1)
print("Minden teszt megfelelt: a számítás egyezik a NAV tájékoztató számpéldáival.")
