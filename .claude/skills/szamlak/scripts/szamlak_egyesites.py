#!/usr/bin/env python3
"""A kimenő számlák egyesítése és keresztvalidálása: Billingo + Számlázz.hu + az input/bevetelek/ fájljai.

Használat:
    python -I .claude/skills/szamlak/scripts/szamlak_egyesites.py [--tol ÉÉÉÉ-HH-NN --ig ÉÉÉÉ-HH-NN]

Forrás: data/szamlak/szamlak_<tol>_<ig>.json (Billingo), szamlazz_<tol>_<ig>.json, bevetelek_szamlak.json.
Eredmény: data/szamlak/egyesitett_<tol>_<ig>.json (az adoszamitas ezt olvassa) és egyesites_jelentes.json.

Keresztvalidálás (egy számla tétele csak egyszer lehet lekönyvelve):
  - azonos számlaszám (normalizálva) = ugyanaz a számla: egy tétel lesz; a sorrend Billingo > Számlázz.hu > fájl;
    eltérő kelt vagy nettó összeg = ELLENTMONDÁS, a script megáll (5-ös kilépési kód), és kiírja, melyik számláról van szó;
  - eltérő számlaszám, de azonos kelt + nettó helyi összeg + pénznem + partner, és a két tétel forráskészlete eltér
    = GYANÚS DUPLIKÁCIÓ (pl. ugyanaz a számla két rendszerben, más számformátummal): a script megáll, és kérdez.
  - azonos forrás több fájlja (átfedő lekérések) ugyanazt a számlát többször is tartalmazhatja: ez egy tételnek számít.
Szabályok: .claude/rules/adatkezeles.md, nincs-becsles.md.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import szamlazz_xml  # noqa: E402

DATA = ROOT / "data" / "szamlak"
SORREND = {"billingo": 1, "szamlazz": 2, "fajl": 3}


def olvas(p):
    return json.loads(p.read_text(encoding="utf-8"))


def partner_kulcs(r):
    p = r.get("partner") or {}
    adoszam = r.get("partner_tax_number") or (p.get("taxcode") if isinstance(p, dict) else None)
    nev = r.get("partner_name") or (p.get("name") if isinstance(p, dict) else None)
    return re.sub(r"\W", "", (adoszam or nev or "").casefold())


def forrasok():
    """-> (rekordok, lefedett tartomány-jelöltek). Minden rekord kap 'forras' és '_fajl' jelölést."""
    ki, tartomanyok = [], []
    for p in sorted(DATA.glob("szamlak_*.json")):
        m = re.fullmatch(r"szamlak_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.json", p.name)
        if not m:
            continue
        tartomanyok.append((m.group(1), m.group(2)))
        for d in olvas(p):
            d["forras"] = "billingo"
            d["_fajl"] = p.name
            d["_ido"] = p.stat().st_mtime
            ki.append(d)
    for p in sorted(DATA.glob("szamlazz_*.json")):
        j = olvas(p)
        tartomanyok.append((j["tol"], j["ig"]))
        for d in j["szamlak"]:
            d["_fajl"] = p.name
            d["_ido"] = p.stat().st_mtime
            ki.append(d)
    reg = DATA / "bevetelek_szamlak.json"
    if reg.exists():
        for d in olvas(reg)["szamlak"]:
            d["forras"] = "fajl"
            d["_fajl"] = d.get("forrasfajl", "bevetelek_szamlak.json")
            d["_ido"] = reg.stat().st_mtime
            ki.append(d)
    return ki, tartomanyok


def helyi_netto(r):
    return (r.get("summary") or {}).get("net_amount_local")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol")
    ap.add_argument("--ig")
    a = ap.parse_args()
    rek, tart = forrasok()
    if not rek:
        print("Nincs számlaforrás (data/szamlak/): az egyesítés kimarad.")
        return
    # 1) azonos számlaszám: csoportosítás
    csoport = {}
    for r in rek:
        csoport.setdefault(szamlazz_xml.kulcs(r.get("invoice_number")), []).append(r)
    egyesitett, ellentmondasok, megj = [], [], []
    for k, lista in csoport.items():
        lista.sort(key=lambda r: (SORREND.get(r["forras"], 9), -r["_ido"]))
        fo = lista[0]
        for r in lista[1:]:
            if r["invoice_date"] != fo["invoice_date"] or helyi_netto(r) != helyi_netto(fo) and None not in (helyi_netto(r), helyi_netto(fo)):
                ellentmondasok.append(f"{fo['invoice_number']}: {fo['forras']} ({fo['_fajl']}): kelt {fo['invoice_date']}, nettó {helyi_netto(fo)} ≠ "
                                      f"{r['forras']} ({r['_fajl']}): kelt {r['invoice_date']}, nettó {helyi_netto(r)}")
            elif r["forras"] != fo["forras"]:
                megj.append(f"{fo['invoice_number']}: több forrásban is szerepel ({fo['forras']}, {r['forras']}); egy tételként számít")
        forrasok_ = sorted({r["forras"] for r in lista})
        t = {k2: v for k2, v in fo.items() if not k2.startswith("_")}
        t["forrasok"] = forrasok_
        egyesitett.append(t)
    if ellentmondasok:
        print("🔴 MEGÁLLTAM (szamlak): ugyanazzal a számlaszámmal eltérő adatú tétel van a forrásokban. Ez azt jelenti, hogy az egyik forrás hibás, "
              "vagy két különböző számla kapta ugyanazt a számot. Mit tegyél: nézd meg a felsorolt számlákat az eredeti rendszerben, javítsd vagy "
              "töröld a hibás forrásfájlt, majd futtasd újra. Az egyesített számlafájlt nem írtam felül.")
        for x in ellentmondasok:
            print("  - " + x)
        sys.exit(5)
    # 2) gyanús duplikáció: eltérő számlaszám, azonos kelt + összeg + pénznem + partner, KÜLÖN forrásból
    gyanus = []
    for i, x in enumerate(egyesitett):
        for y in egyesitett[i + 1:]:
            if x.get("type") != "invoice" or y.get("type") != "invoice":
                continue
            if set(x["forrasok"]) == set(y["forrasok"]):
                continue  # azonos forráskészlet: két külön, valódi számla lehet (ugyanabban a rendszerben két számlaszámot kapott)
            if (x["invoice_date"] == y["invoice_date"] and x.get("currency") == y.get("currency") and helyi_netto(x) is not None
                    and helyi_netto(x) == helyi_netto(y) and (partner_kulcs(x) == partner_kulcs(y) or not (partner_kulcs(x) and partner_kulcs(y)))):
                gyanus.append(f"{x['invoice_number']} ({'/'.join(x['forrasok'])}) és {y['invoice_number']} ({'/'.join(y['forrasok'])}): "
                              f"azonos kelt ({x['invoice_date']}), pénznem és nettó összeg")
    if gyanus:
        print("🔴 MEGÁLLTAM (szamlak): gyanús duplikáció: különböző számlaszámmal, de azonos kelettel, összeggel és pénznemmel két különböző forrásban is "
              "szerepel tétel. Ha ugyanaz a számla (pl. más számformátum), töröld az egyik forrásból (fájl: input/bevetelek vagy a lekérés); ha két külön "
              "számla, jelezd, és a megkülönböztetésükre külön szabályt veszünk fel. A bevételt addig nem könyvelem, az egyesített fájlt nem írtam felül.")
        for x in gyanus:
            print("  - " + x)
        sys.exit(5)
    # 3) kimenet
    ev_ek = [int(r["invoice_date"][:4]) for r in egyesitett if r.get("invoice_date")]
    tol = a.tol or (min(t[0] for t in tart) if tart else f"{min(ev_ek) - 1}-01-01")
    ig = a.ig or (max(t[1] for t in tart) if tart else f"{max(ev_ek)}-12-31")
    egyesitett.sort(key=lambda r: (r.get("invoice_date") or "", r.get("invoice_number") or ""))
    ut = DATA / f"egyesitett_{tol}_{ig}.json"
    ut.write_text(json.dumps(egyesitett, ensure_ascii=False, indent=1), encoding="utf-8")
    # a fájl "kora" (frissesség-jelzés az adoszamitasban) az API-források tényleges lekérési idejét tükrözze, ne az egyesítés idejét
    import os
    api_ido = [r["_ido"] for r in rek if r["forras"] in ("billingo", "szamlazz")] or [r["_ido"] for r in rek]
    os.utime(ut, (max(api_ido), max(api_ido)))
    jel = {"keszult": datetime.now().isoformat(timespec="seconds"), "tartomany": [tol, ig], "tetelek": len(egyesitett),
           "forrasonkent": {f: sum(1 for r in egyesitett if f in r["forrasok"]) for f in SORREND}, "megjegyzesek": megj,
           "nyers_rekordok": len(rek), "egyesitve_duplikalt": len(rek) - len(egyesitett)}
    (DATA / "egyesites_jelentes.json").write_text(json.dumps(jel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Számlák egyesítve: {len(egyesitett)} tétel ({len(rek)} nyers rekordból, {len(rek) - len(egyesitett)} duplikált rekord egyesítve) -> {ut.relative_to(ROOT)}")
    for m_ in megj[:5]:
        print("  ℹ️ " + m_)


if __name__ == "__main__":
    main()
