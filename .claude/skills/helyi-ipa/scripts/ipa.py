#!/usr/bin/env python3
"""Helyi iparűzési adó (IPA): az illetékes önkormányzat szabályai és a számítás.

Használat:
    python -I .claude/skills/helyi-ipa/scripts/ipa.py --allapot                       # mi van meg, mi hiányzik
    python -I .claude/skills/helyi-ipa/scripts/ipa.py --rogzit TELEPÜLÉS --kulcs 0.02 --forras URL [--ev 2026]
    python -I .claude/skills/helyi-ipa/scripts/ipa.py --mod tetelesen|hagyomanyos     # az adózás módja (a felhasználó döntése)
    python -I .claude/skills/helyi-ipa/scripts/ipa.py --szamol [--ev 2026] [--arbevetel N]

Bemenet: config/vallalkozas.json: ipa_telepules (a vallalkozas-dokumentumok skill kérdezi meg és rögzíti), ipa_telephelyek, ipa_adozasi_mod.
Az adókulcs az önkormányzat rendeletéből jön (config/ipa_telepulesek.json), forrással rögzítve; hiányában NEM SZÁMOLHATÓ.
Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md. Jogforrás: torvenytar/docs/htv/2026/1990-evi-c-torveny.txt
(Htv. 39/A. § tételes adóalap, 40. § a mérték felső határa).
"""
import argparse
import json
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
CFG = konfig.vallalkozas_ut()
RATES = ROOT / "config" / "ipa_telepulesek.json"
OUT = ROOT / "data" / "ipa"
# Htv. 39/A. § (1)-(2): tételes adóalap sávok (a bevétel felső határa, adóalap), napi arányosítással 12 hónapnál rövidebb adóévre
SAVOK = [(12_000_000, 2_500_000), (18_000_000, 6_000_000), (25_000_000, 8_500_000)]
MAX_KULCS = Decimal("0.02")  # Htv. 40. § c)


def ft(n):
    return f"{int(n):,}".replace(",", " ") + " Ft"


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def cmd_allapot(ev):
    c = load(CFG, {})
    r = load(RATES, {})
    print(f"=== IPA állapot ({ev})")
    print(f"Illetékességi település: {c.get('ipa_telepules') or 'NEM SZÁMOLHATÓ, hiányzik (vallalkozas-dokumentumok --ipa-javaslat / --ipa-beallit)'}")
    print(f"További telephelyek: {', '.join(c.get('ipa_telephelyek') or []) or 'nincs'}")
    print(f"Adózás módja: {c.get('ipa_adozasi_mod') or 'NEM SZÁMOLHATÓ, a felhasználónak kell megadni (tetelesen | hagyomanyos)'}")
    t = c.get("ipa_telepules")
    e = (r.get(str(ev)) or {}).get(t) if t else None
    print(f"Helyi adókulcs {ev}: " + (f"{e['kulcs']} (forrás: {e['forras']})" if e else "NEM SZÁMOLHATÓ, nincs rögzítve (a rendeletet be kell szerezni, majd --rogzit)"))


def cmd_rogzit(t, kulcs, forras, ev):
    k = Decimal(kulcs)
    if not (Decimal("0") <= k <= MAX_KULCS):
        sys.exit(f"HIBA: a kulcs 0 és {MAX_KULCS} között lehet (Htv. 40. § c): az adóalap 2%-a a felső határ).")
    if not forras.startswith("http") and not (ROOT / forras).exists():
        sys.exit("HIBA: forrás kell (URL vagy a torvenytar/ alatti fájl útvonala); forrás nélküli kulcsot nem rögzítek.")
    r = load(RATES, {})
    r.setdefault(str(ev), {})[t] = {"kulcs": str(k), "forras": forras, "rogzitve": date.today().isoformat()}
    RATES.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rögzítve: {t}, {ev}: {k} (forrás: {forras}).")


def cmd_mod(m):
    c = load(CFG, {})
    c["ipa_adozasi_mod"] = m
    CFG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Az IPA adózás módja: {m}")


def cmd_szamol(ev, arbevetel):
    c = load(CFG, {})
    r = load(RATES, {})
    hiany = []
    t = c.get("ipa_telepules")
    if not t:
        hiany.append("az illetékességi település (ipa_telepules)")
    if c.get("ipa_telephelyek"):
        hiany.append("az adóalap felosztása a székhely és a telephely(ek) között (a script nem találgat)")
    mod = c.get("ipa_adozasi_mod")
    if mod not in ("tetelesen", "hagyomanyos"):
        hiany.append("az adózás módja (ipa_adozasi_mod: tetelesen | hagyomanyos)")
    e = (r.get(str(ev)) or {}).get(t) if t else None
    if t and not e:
        hiany.append(f"{t} {ev}. évi IPA-kulcsa (rögzítés: --rogzit)")
    if hiany:
        print("NEM SZÁMOLHATÓ, hiányzik: " + "; ".join(hiany))
        return 2
    k = Decimal(e["kulcs"])
    nap = ev_nap = None
    if mod == "tetelesen":
        sz = load(ROOT / "data" / "szamitas" / f"adoszamitas_{ev}.json", None)
        if not sz:
            print(f"NEM SZÁMOLHATÓ, hiányzik: data/szamitas/adoszamitas_{ev}.json (adoszamitas skill)")
            return 2
        bh = sz["bevetel_hatar"]
        bevetel, nap, ev_nap = Decimal(bh["bevetel"]), Decimal(bh["aktiv_napok"]), Decimal(bh["ev_napjai"])
        ar = nap / ev_nap
        sav = None
        for hatar, alap in SAVOK:
            if bevetel <= Decimal(hatar) * ar:
                sav = (hatar, alap)
                break
        if sav is None:
            print(f"A tételes adóalap nem alkalmazható: a bevétel ({ft(bevetel)}) meghaladja az időarányos 25 millió Ft-ot (Htv. 39/A. § (1)); hagyományos adóalap kell.")
            return 3
        alap = (Decimal(sav[1]) * ar).quantize(Decimal("1"), ROUND_HALF_UP)
        ado = (alap * k).quantize(Decimal("1"), ROUND_HALF_UP)
        res = {"mod": mod, "bevetel": int(bevetel), "aktiv_napok": int(nap), "sav_felso_hatar": sav[0], "sav_adoalap": sav[1], "idoaranyos_adoalap": int(alap)}
        print(f"Tételes adóalap (Htv. 39/A. § (2)): bevétel {ft(bevetel)}, aktív napok {int(nap)}/{int(ev_nap)}; sáv: {ft(sav[0])} alatt (időarányosan), sáv adóalapja {ft(sav[1])}")
        print(f"  időarányos adóalap: {ft(alap)} (39/A. § (3), napi arányosítás)")
    else:
        if arbevetel is None:
            print("NEM SZÁMOLHATÓ, hiányzik: a nettó árbevétel (--arbevetel N); a Htv. 39. § szerinti csökkentő tételek sincsenek a repó adataiban.")
            return 2
        alap = Decimal(arbevetel)
        ado = (alap * k).quantize(Decimal("1"), ROUND_HALF_UP)
        res = {"mod": mod, "arbevetel": int(alap), "adoalap": int(alap)}
        print(f"Hagyományos adóalap: a megadott nettó árbevétel {ft(alap)} (a Htv. 39. § szerinti csökkentő tételek NINCSENEK levonva).")
    print(f"IPA-kulcs ({t}, {ev}): {k} (forrás: {e['forras']})")
    print(f"Éves IPA a fenti adatokkal: {ft(ado)}")
    if mod == "tetelesen":
        print(f"Határidők (Htv. 39/A. § (7), (9), torvenytar): az adóévre előleg az adóév 5. hónapjának utolsó napjáig = {ev}-05-31; az adó megfizetése az adóévet követő év 5. hónapjának utolsó napjáig = {ev + 1}-05-31.")
    else:
        print("Határidők: az előleg- és bevallási határidőket a hataridok.md és az adónaptár adja (március 15., szeptember 15., bevallás május 31.); a Htv. 41. §-ból nem ellenőriztem.")
    print("Nem ellenőrzött: a kerekítés módja; a napi arányosítás nevezője (365); hogy a szünetelés napjai az adókötelezettség napjai közé számítanak-e; az önkormányzati rendelet esetleges mentessége/kedvezménye (Htv. 39/C.); a kisvállalkozói választás bejelentése (Htv. 39/A. § (4)). Egyeztess a könyvelővel.")
    OUT.mkdir(parents=True, exist_ok=True)
    res.update({"ev": ev, "telepules": t, "kulcs": str(k), "kulcs_forras": e["forras"], "eves_ipa": int(ado), "szamolva": date.today().isoformat()})
    (OUT / f"ipa_{ev}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Mentve: data/ipa/ipa_{ev}.json")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--allapot", action="store_true")
    ap.add_argument("--rogzit", metavar="TELEPÜLÉS")
    ap.add_argument("--kulcs")
    ap.add_argument("--forras")
    ap.add_argument("--mod", choices=["tetelesen", "hagyomanyos"])
    ap.add_argument("--szamol", action="store_true")
    ap.add_argument("--arbevetel", type=int)
    ap.add_argument("--ev", type=int, default=date.today().year)
    a = ap.parse_args()
    if a.rogzit:
        if not (a.kulcs and a.forras):
            sys.exit("HIBA: --kulcs és --forras kell.")
        return cmd_rogzit(a.rogzit, a.kulcs, a.forras, a.ev)
    if a.mod:
        return cmd_mod(a.mod)
    if a.szamol:
        sys.exit(cmd_szamol(a.ev, a.arbevetel))
    cmd_allapot(a.ev)


if __name__ == "__main__":
    main()
