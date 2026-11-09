#!/usr/bin/env python3
"""Bevételi nyilvántartás (pénztárkönyv bevételi oldala) az átalányadózó egyéni vállalkozónak: Szja tv. 51. § (3).

A törvény szerint az átalányadót választó egyéni vállalkozó, ha az áfa-levonási jogát nem érvényesíti, a pénztárkönyv (naplófőkönyv) bevételi adatait vezeti
(a rovatokat lásd: .claude/rules/bevetel-nyilvantartas.md). Ez a script az egyesített, keresztvalidált számlákból (data/szamlak/egyesitett_*.json)
előállítja az adóévi bevételek időrendi nyilvántartását CSV-ben és HTML-ben.

Használat:
    python -I .claude/skills/adoszamitas/scripts/bevetel_nyilvantartas.py [--ev 2026] [--szamlak FÁJL] [--ma ÉÉÉÉ-HH-NN]
Kimenet: data/szamitas/bevetel_nyilvantartas_<év>.csv és .html

Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md.
- Bevétel = a kiegyenlített (paid), nem stornózott számla nettó forintértéke a KIFIZETÉS napja szerint (ugyanaz a szűrés, mint az adoszamitas.py-ban: classify()).
- Rovat, amelyhez nincs adat a számlában (pl. a bevétel jogcíme), "nincs adat"; nem találunk ki értéket. A nyilvántartás nem helyettesíti a banki kivonattal való egyeztetést.
- A nyitott pontok (bevétel időpontja kifizetői átutalásnál; devizaárfolyam) a fejlécben szerepelnek.
"""
import argparse
import csv
import html
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(HERE))
import adoszamitas as ado  # noqa: E402

D = Decimal


def sorok(docs, ev):
    counted, _unpaid, _excluded, _partial = ado.classify(docs, ev)
    counted.sort(key=lambda d: (d["paid_date"], str(d.get("invoice_number"))))
    out, gong = [], D(0)
    for i, d in enumerate(counted, 1):
        s = d.get("summary") or {}
        net = D(str(s["net_amount_local"]))
        brutto = s.get("gross_amount_local")
        gong += net
        partner = (d.get("partner") or {}).get("name") or "nincs adat"
        deviza = d.get("currency") or "nincs adat"
        megj = []
        if deviza != "HUF":
            megj.append(f"devizás számla ({deviza}, árfolyam: {d.get('conversion_rate') or 'nincs adat'}); a forintösszeg a számlán alkalmazott árfolyammal számolt (Szja tv. 6. § (2a) a): nyitott kérdés)")
        if d.get("invoice_date", "")[:4] < str(ev):
            megj.append(f"{ev - 1}. évi kiállítású, {ev}-ben kifizetett")
        out.append({"sorszam": i, "keltezes": d["paid_date"][:10], "bizonylat": str(d.get("invoice_number")), "ugyfel": partner,
                    "jogcim": "nincs adat (a számla szerinti ellenérték)", "netto_huf": net, "afa_huf": (D(str(brutto)) - net) if brutto is not None else None,
                    "brutto_huf": D(str(brutto)) if brutto is not None else None, "deviza": deviza, "gongyolt_netto_huf": gong, "megjegyzes": "; ".join(megj)})
    return out


def ft(x):
    return "nincs adat" if x is None else f"{int(x):,}".replace(",", " ") + " Ft"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Bevételi nyilvántartás (Szja tv. 51. § (3)).")
    ap.add_argument("--ev", type=int)
    ap.add_argument("--szamlak", help="számla JSON (alapból az egyesített, az évet lefedő)")
    ap.add_argument("--ma", type=date.fromisoformat, default=date.today())
    a = ap.parse_args()
    ev = a.ev or a.ma.year
    p = ado.find_invoice_file(ev, a.szamlak, a.ma)
    docs = json.loads(p.read_text(encoding="utf-8"))
    nyers = getattr(ado.find_invoice_file, "nyers", False) and not a.szamlak
    rows = sorok(docs, ev)
    kor = (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 3600
    fej = [f"Forrás: {p.name} ({kor / 24:.1f} napos számlaadat); adóév: {ev}; előállítva: {a.ma.isoformat()}"]
    if nyers:
        fej.append("🔴 FIGYELEM: nincs egyesített, keresztvalidált számlafájl: csak a Billingo-adatból készült; Számlázz.hu-s vagy fájlból jövő bevétel hiányozhat.")
    fej += ["A bevétel a pénz megérkezésének (a számla kiegyenlítésének) napján szerepel (Szja tv. 10. számú melléklet I. 1.: az ellenértékként/előlegként befolyt összeg); "
            "a kifizetői átutalás esetére a 9. § (2) a) kivételt tartalmaz: a Billingo paid_date ettől eltérhet (nyitott kérdés, jogi_kerdesek: bevetel_idopont_atutalas).",
            "A nyilvántartás nem helyettesíti a banki kivonattal való egyeztetést; a részben fizetett számlák és a kintlévőségek nem szerepelnek benne."]
    outd = ROOT / "data" / "szamitas"
    outd.mkdir(parents=True, exist_ok=True)
    cp = outd / f"bevetel_nyilvantartas_{ev}.csv"
    cols = ["sorszam", "keltezes", "bizonylat", "ugyfel", "jogcim", "netto_huf", "afa_huf", "brutto_huf", "deviza", "gongyolt_netto_huf", "megjegyzes"]
    with cp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        for l in fej:
            w.writerow(["# " + l])
        w.writerow(["Sorszám", "Keltezés (a pénz beérkezése)", "Bizonylat", "Ügyfél", "Bevétel jogcíme", "Nettó összeg (HUF)", "Áfa (HUF)", "Bruttó összeg (HUF)", "Deviza", "Göngyölt nettó (HUF)", "Megjegyzés"])
        for r in rows:
            w.writerow(["" if r[c] is None else str(r[c]) for c in cols])
        w.writerow([])
        w.writerow(["Összesen", "", "", "", "", str(rows[-1]["gongyolt_netto_huf"]) if rows else "0"])
    hp = outd / f"bevetel_nyilvantartas_{ev}.html"
    tr = "".join("<tr>" + "".join(f"<td>{html.escape(ft(r[c]) if isinstance(r[c], Decimal) or (c in ('afa_huf', 'brutto_huf') and r[c] is None) else str(r[c]))}</td>" for c in cols) + "</tr>" for r in rows)
    hp.write_text("<!doctype html><meta charset=utf-8><title>Bevételi nyilvántartás " + str(ev) + "</title>"
                  "<style>body{font:14px system-ui;margin:2rem;color:#222}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:4px 8px}th{background:#eee}</style>"
                  f"<h1>Bevételi nyilvántartás {ev}</h1>" + "".join(f"<p>{html.escape(l)}</p>" for l in fej)
                  + "<table><tr><th>Sorszám<th>Keltezés<th>Bizonylat<th>Ügyfél<th>Jogcím<th>Nettó<th>Áfa<th>Bruttó<th>Deviza<th>Göngyölt nettó<th>Megjegyzés</tr>" + tr + "</table>"
                  + f"<p><strong>Összesen (nettó, HUF): {html.escape(ft(rows[-1]['gongyolt_netto_huf']) if rows else '0 Ft')}</strong></p>", encoding="utf-8")
    print(f"Bevételi nyilvántartás {ev}: {len(rows)} tétel, összesen {ft(rows[-1]['gongyolt_netto_huf']) if rows else '0 Ft'} (nettó) a(z) {p.name} alapján.")
    if nyers:
        print("🔴 Nincs egyesített számlafájl: csak Billingo-adat. Futtasd a szamlak_egyesites.py-t.")
    print(f"Mentve: {cp.relative_to(ROOT)}, {hp.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
