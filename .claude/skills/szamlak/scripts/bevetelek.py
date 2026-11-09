#!/usr/bin/env python3
"""A kimenő (bevételi) számlák feldolgozása az input/bevetelek/ mappából: Markdown + számlaadat, duplikáció nélkül.

Használat:
    python -I .claude/skills/szamlak/scripts/bevetelek.py --feldolgoz

Támogatott fájlok: PDF (Billingo- és Számlázz.hu-elrendezés), XML (Számla Agent számla-XML), CSV, Markdown/szöveg.
Minden fájl: (1) Markdown készül belőle (data/szamlak/bevetelek-md/), (2) a vállalkozás azonosítója ellenőrződik (másik vállalkozás
dokumentumánál a script megáll és utasítást ad), (3) a számlák kiolvasódnak és a nyilvántartásba (data/szamlak/bevetelek_szamlak.json)
kerülnek: azonos számlaszám + azonos adat = duplikátum (nem könyvelődik újra); azonos számlaszám + eltérő adat = ellentmondás (megáll).
A feldolgozott eredeti az archive/bevetelek/<év>/ mappába kerül. A díjbekérő nem számla, nem kerül a bevételek közé.
Szabályok: .claude/rules/adatkezeles.md, nincs-becsles.md. Az összeget a script olvassa ki, az AI nem.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import azonosito  # noqa: E402
import szamla_parser  # noqa: E402
import szamlazz_xml  # noqa: E402

IN = ROOT / "input" / "bevetelek"
import bemenet  # noqa: E402
bemenet.takarit_kilepeskor(IN)
ARCH = ROOT / "archive" / "bevetelek"
DATA = ROOT / "data" / "szamlak"
MD = DATA / "bevetelek-md"
REG = DATA / "bevetelek_szamlak.json"
PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"
DEVIZAK = ("EUR", "USD", "GBP", "CHF")
FIZ = re.compile(r"(?:Kiegyenlítve|Kiegyenlítés dátuma|Fizetés ideje|Fizetés dátuma|Fizetve|Teljesítve)\s*:?\s*(\d{4})\.\s?(\d\d)\.\s?(\d\d)", re.I)


def ft(n):
    return f"{int(n):,}".replace(",", " ") + " Ft"


def betolt():
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {"szamlak": [], "fajlok": []}


def szoveg_es_md(p: Path):
    """-> (szöveg, markdown). PDF: pdftotext -layout + pdf-markdown; CSV/XML/szöveg: tartalom."""
    ext = p.suffix.lower()
    if ext == ".pdf":
        txt = szamla_parser.pdf_szoveg(p)
        MD.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-I", str(PDFMD), "--fajl", str(p), "--ki", str(MD / (p.stem + ".md"))], capture_output=True, text=True, encoding="utf-8")
        return txt, None
    txt = p.read_text(encoding="utf-8-sig", errors="replace")
    return txt, txt


def rekord_pdf(txt: str, nev: str, sajat: dict):
    r = szamla_parser.parse(txt, re.sub(r"\D", "", sajat["adoszam"])[:11])
    if r["tipus"] == "dijbekero":
        return None, "díjbekérő (nem számla, nem bevétel)"
    if not r["sorszam"] or not r["kelt"] or r["brutto"] is None:
        raise ValueError("nem sikerült kiolvasni a sorszámot, keltet vagy összeget")
    if r["netto"] is not None and r["netto"] + (r["afa"] or 0) != r["brutto"]:
        raise ValueError(f"nettó + áfa ≠ bruttó ({ft(r['netto'])} + {ft(r['afa'] or 0)} ≠ {ft(r['brutto'])})")
    elado = szamla_parser.elado_neve(txt) or ""
    tokenek = [t for t in re.split(r"\W+", (sajat.get("nev") or "").casefold()) if len(t) > 2][:2]
    if tokenek and not all(t in elado.casefold() for t in tokenek):
        raise ValueError("a számla eladója nem a vállalkozás (ez valószínűleg BEJÖVŐ számla: az input/kiadasok/ mappába való)")
    deviza = next((c for c in DEVIZAK if re.search(rf"\b{c}\b", txt)), "HUF")
    fiz = FIZ.search(txt)
    paid = f"{fiz.group(1)}-{fiz.group(2)}-{fiz.group(3)}" if fiz else None
    huf = deviza == "HUF"
    return {"forras": "fajl", "invoice_number": r["sorszam"], "type": "invoice", "cancelled": False, "invoice_date": r["kelt"],
            "fulfillment_date": r["teljesites"], "due_date": r["fizetesi_hatarido"], "paid_date": paid,
            "payment_status": "paid" if paid else "outstanding", "currency": deviza, "conversion_rate": 1.0 if huf else None,
            "summary": {"net_amount": r["netto"], "net_amount_local": r["netto"] if huf else None,
                        "gross_amount_local": r["brutto"] if huf else None, "vat_amount_local": r["afa"] if huf else None},
            "kifizetes_igazolt": bool(paid)}, None


def rekord_xml(txt: str, sajat: dict):
    hiba, _, uz = szamlazz_xml.hiba_valasz(txt)
    if hiba:
        raise ValueError(f"az XML nem számla ({uz or 'ismeretlen'})")
    rec = szamlazz_xml.normalizal(txt)
    rec["forras"] = "fajl"
    elado = re.sub(r"\D", "", rec.get("seller_tax_number") or "")[:8]
    if elado and elado != re.sub(r"\D", "", sajat["adoszam"])[:8]:
        raise ValueError("a számla eladója másik vállalkozás (az adószáma nem egyezik a vállalkozói profilban lévővel)")
    return rec


def rekordok_csv(txt: str):
    """CSV: fejlécsor + számlasorok; az oszlopok neve szerint ismeri fel (ékezettől függetlenül). Hiányzó adat: None."""
    mintavetel = txt[:2000]
    elv = ";" if mintavetel.count(";") >= mintavetel.count(",") else ","
    rd = list(csv.reader(io.StringIO(txt), delimiter=elv))
    # a fejlécsor az első, amelyben van számlaszám-oszlop
    def norm(x):
        return re.sub(r"[^a-z0-9]", "", (x or "").casefold().translate(str.maketrans("áéíóöőúüű", "aeiooouuu")))
    hi = next((i for i, row in enumerate(rd) if any(norm(c) in ("szamlaszam", "invoicenumber", "sorszam") for c in row)), None)
    if hi is None:
        raise ValueError("a CSV-ben nincs 'számlaszám' oszlop")
    fej = [norm(c) for c in rd[hi]]

    def oszlop(*nevek):
        for n in nevek:
            for i, h in enumerate(fej):
                if n in h:
                    return i
        return None
    ix = {k: oszlop(*v) for k, v in {"szam": ("szamlaszam", "invoicenumber", "sorszam"), "kelt": ("kelt", "kiallitas", "invoicedate"),
                                    "telj": ("teljesit", "fulfillment"), "netto": ("netto", "net"), "afa": ("afa", "vat"),
                                    "brutto": ("brutto", "gross"), "deviza": ("penznem", "deviza", "currency"),
                                    "paid": ("kiegyenlit", "fizetesideje", "fizetesdatum", "paid"), "arf": ("arfolyam", "rate")}.items()}

    def nev_datum(x):
        m = re.search(r"(\d{4})[.\-/ ]+(\d{1,2})[.\-/ ]+(\d{1,2})", x or "")
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None

    def szam(x):
        x = re.sub(r"[^\d,.\-]", "", x or "")
        if not x:
            return None
        if "," in x and "." in x:
            x = x.replace(".", "").replace(",", ".")
        else:
            x = x.replace(",", ".")
        return float(x)
    ki = []
    for row in rd[hi + 1:]:
        if ix["szam"] is None or ix["szam"] >= len(row) or not row[ix["szam"]].strip():
            continue
        g = lambda k: row[ix[k]] if ix[k] is not None and ix[k] < len(row) else None  # noqa: E731
        kelt, netto = nev_datum(g("kelt")), szam(g("netto"))
        deviza = (g("deviza") or "HUF").strip().upper() or "HUF"
        arf = szam(g("arf")) if deviza != "HUF" else 1.0
        helyi = (round(netto * arf) if netto is not None and arf else None)
        paid = nev_datum(g("paid"))
        if not kelt or netto is None:
            raise ValueError(f"a(z) {row[ix['szam']]} számlánál hiányzik a kelte vagy a nettó összeg")
        ki.append({"forras": "fajl", "invoice_number": row[ix["szam"]].strip(), "type": "invoice", "cancelled": False, "invoice_date": kelt,
                   "fulfillment_date": nev_datum(g("telj")), "due_date": None, "paid_date": paid,
                   "payment_status": "paid" if paid else "outstanding", "currency": deviza, "conversion_rate": arf,
                   "summary": {"net_amount": netto, "net_amount_local": helyi, "gross_amount_local": None, "vat_amount_local": None},
                   "kifizetes_igazolt": bool(paid)})
    return ki


def kulcs(num):
    return szamlazz_xml.kulcs(num)


def feldolgoz() -> int:
    fajlok = bemenet.fajlok(IN)  # almappákkal együtt
    if not fajlok:
        print("Nincs feldolgozandó fájl az input/bevetelek/ mappában.")
        return 0
    try:
        sajat = azonosito.megvan_vagy_leall("szamlak/bevetelek")
    except azonosito.AzonositoHiba as e:
        print(f"🔴 {e}")
        return 4
    reg = betolt()
    ismert_sha = {f["sha256"] for f in reg["fajlok"]}
    konfl = 0
    for p in fajlok:
        raw = hashlib.sha256(p.read_bytes()).hexdigest()
        if raw in ismert_sha:
            (ARCH / "duplikatumok").mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(ARCH / "duplikatumok" / p.name))
            print(f"= DUPLIKÁTUM: {p.name} már feldolgozott fájl (azonos tartalom); nem dolgoztam fel újra, áthelyezve: archive/bevetelek/duplikatumok/")
            continue
        ext = p.suffix.lower()
        if ext not in (".pdf", ".xml", ".csv", ".md", ".txt"):
            print(f"❓ {p.name}: nem támogatott formátum ({ext or 'kiterjesztés nélkül'}). Mentsd CSV-ként vagy PDF-ként; a fájl az input/-ban maradt.")
            konfl += 1
            continue
        try:
            txt, md = szoveg_es_md(p)
            azonosito.ellenoriz(txt, p.name, "szamlak/bevetelek", "bevételi irat")
            if ext == ".pdf":
                rec, megj = rekord_pdf(txt, p.name, sajat)
                recs = [rec] if rec else []
            elif ext == ".xml":
                recs, megj = [rekord_xml(txt, sajat)], None
            elif ext == ".csv":
                recs, megj = rekordok_csv(txt), None
            else:
                raise ValueError("a Markdown/szöveg fájlból nem olvasok ki számlát megbízhatóan; küldd PDF, XML vagy CSV formában")
        except azonosito.AzonositoHiba as e:
            print(f"🔴 {e}")
            konfl += 1
            continue
        except ValueError as e:
            print(f"🔴 {p.name}: {e}. A fájl az input/-ban maradt.")
            konfl += 1
            continue
        if md is not None:
            MD.mkdir(parents=True, exist_ok=True)
            (MD / (p.stem + ".md")).write_text(md if ext != ".csv" else f"# {p.name}\n\n```\n{md}\n```\n", encoding="utf-8")
        if not recs:
            print(f"ℹ️ {p.name}: {megj}; nem került a bevételek közé.")
        uj = dup = 0
        elutasit = False
        for r in recs:
            k = kulcs(r["invoice_number"])
            e = next((x for x in reg["szamlak"] if kulcs(x["invoice_number"]) == k), None)
            if e is None:
                reg["szamlak"].append({**r, "forrasfajl": p.name})
                uj += 1
            elif e["invoice_date"] == r["invoice_date"] and e["summary"]["net_amount"] == r["summary"]["net_amount"]:
                dup += 1
                if r.get("paid_date") and not e.get("paid_date"):
                    e["paid_date"], e["payment_status"], e["kifizetes_igazolt"] = r["paid_date"], "paid", True
            else:
                print(f"🔴 ELLENTMONDÁS: {r['invoice_number']} ({p.name}): azonos számlaszám, de eltérő kelt vagy nettó összeg a már nyilvántartottal "
                      f"({e['invoice_date']}, {e['summary']['net_amount']} ≠ {r['invoice_date']}, {r['summary']['net_amount']}). A fájl az input/-ban maradt; kérdés: melyik a helyes?")
                elutasit = True
        if elutasit:
            konfl += 1
            # a hozzáadott (új) tételeket visszavonjuk, hogy a fájl újrafuttatáskor ne duplázódjon
            reg["szamlak"] = [x for x in reg["szamlak"] if x.get("forrasfajl") != p.name]
            continue
        ev = (recs[0]["invoice_date"][:4] if recs else "ismeretlen")
        cel = ARCH / ev
        cel.mkdir(parents=True, exist_ok=True)
        dst = cel / p.name
        if dst.exists():
            dst = cel / f"{raw[:8]}_{p.name}"
        shutil.move(str(p), str(dst))
        reg["fajlok"].append({"fajl": p.name, "sha256": raw, "szamlak": len(recs), "feldolgozva": datetime.now().isoformat(timespec="seconds")})
        ismert_sha.add(raw)
        print(f"+ {p.name}: {uj} új számla" + (f", {dup} már nyilvántartott (nem könyvelődik újra)" if dup else "") + f" -> archive/bevetelek/{ev}/")
    DATA.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return 3 if konfl else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--feldolgoz", action="store_true")
    a = ap.parse_args()
    if a.feldolgoz:
        sys.exit(feldolgoz())
    ap.print_help()


if __name__ == "__main__":
    main()
