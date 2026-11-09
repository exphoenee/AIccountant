#!/usr/bin/env python3
"""Bejövő (kiadási) számlák PDF-ben (input/kiadasok/): feldolgozás duplikáció nélkül.

Használat:
    python -I .claude/skills/kiadasok-dokumentumok/scripts/kiadasok.py --feldolgoz   # új PDF-ek feldolgozása
    python -I .claude/skills/kiadasok-dokumentumok/scripts/kiadasok.py --lista [ÉV]  # a nyilvántartott kiadások

Minden PDF-ről kiolvassa a típust (számla / díjbekérő), a sorszámot, a keltet, a szállítót, a nettó/áfa/bruttó összeget; ellenőrzi,
hogy nettó + áfa = bruttó. A DÍJBEKÉRŐ nem számla és nem kiadás: nyilvántartásba kerül, de az összegekbe nem számít bele, és ha egy számla
hivatkozik rá ("... díjbekérő alapján"), a kettő összekapcsolódik (nem számolódik duplán). Azonos sorszámú, azonos összegű irat duplikátum
(archive/kiadasok/duplikatumok/); azonos sorszám, eltérő összeg ellentmondás: az irat az input/-ban marad, a script 3-as kóddal megáll.
Eredmény: data/kiadasok/pdf_kiadasok.json; az eredeti PDF az archive/kiadasok/<év>/ alá kerül, a Markdown a data/kiadasok/md/ alá.
Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md. Az összegeket a script olvassa ki, nem az AI.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
IN = ROOT / "input" / "kiadasok"
REG = ROOT / "data" / "kiadasok" / "pdf_kiadasok.json"
MD = ROOT / "data" / "kiadasok" / "md"
ARCH = ROOT / "archive" / "kiadasok"
DUP = ARCH / "duplikatumok"
PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"
SZERV = ROOT / "data" / "vallalkozas" / "billingo-szervezet.json"


def ft(n):
    return f"{int(n):,}".replace(",", " ") + " Ft"


sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import azonosito  # noqa: E402
import bemenet  # noqa: E402
bemenet.takarit_kilepeskor(IN)  # az almappák is feldolgozódnak; a kiürült almappák törlődnek
from szamla_parser import parse, pdf_szoveg, num  # noqa: E402


def load():
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {"iratok": []}


def feldolgoz():
    pdfs = bemenet.fajlok(IN, (".pdf",))  # almappákkal együtt, kis/nagybetű független
    if not pdfs:
        print("Nincs feldolgozandó PDF az input/kiadasok/ mappában.")
        return 0
    sajat = ""
    if SZERV.exists():
        sajat = re.sub(r"\D", "", json.loads(SZERV.read_text(encoding="utf-8"))["szamla_szervezet"].get("tax_number") or "")
    reg = load()
    konfl = 0
    for p in pdfs:
        raw = hashlib.sha256(p.read_bytes()).hexdigest()
        txt = pdf_szoveg(p)
        try:
            azonosito.ellenoriz(txt, p.name, "kiadasok-dokumentumok", "számla")
        except azonosito.AzonositoHiba as e:
            print(f"🔴 {e}")
            konfl += 1
            continue
        r = parse(txt, sajat[:11])
        if not r["sorszam"] or not r["kelt"] or r["brutto"] is None:
            tipp = next((m for kulcs_, m in (("kamarai hozzájárulás", "kamarai igazolás: az input/vallalkozas-adatok/ mappába való (vallalkozas-dokumentumok skill)"),
                                             ("BEVALLÁS", "NAV-bevallás: az input/nav-egyenleg/ mappába való (adofizetes skill)"),
                                             ("ADÓSZÁMLA KIVONAT", "adószámla-kivonat: az input/nav-egyenleg/ mappába való (adofizetes skill)"),
                                             ("Bérösszesítő", "könyvelői irat: az input/konyvelo/ mappába való (konyvelo-dokumentumok skill)"),
                                             ("Utalandó", "könyvelői irat: az input/konyvelo/ mappába való (konyvelo-dokumentumok skill)"))
                         if kulcs_.casefold() in txt.casefold()), None)
            if tipp:
                print(f"🔴 {p.name}: ez nem kiadási számla, hanem {tipp}. A fájl az input/kiadasok/-ban maradt: vidd át a megfelelő mappába.")
            else:
                print(f"❓ {p.name}: nem sikerült kiolvasni a sorszámot, keltet vagy összeget; az input/-ban maradt. Mi ez az irat?")
            konfl += 1
            continue
        if r["netto"] is not None and r["netto"] + (r["afa"] or 0) != r["brutto"]:
            print(f"🔴 {p.name}: nettó + áfa ≠ bruttó ({ft(r['netto'])} + {ft(r['afa'] or 0)} ≠ {ft(r['brutto'])}); a kiolvasás nem megbízható, az irat az input/-ban maradt.")
            konfl += 1
            continue
        key = f"{r['tipus']}|{r['sorszam']}"
        e = next((x for x in reg["iratok"] if x["kulcs"] == key), None)
        if e:
            if e["brutto"] == r["brutto"] and e["kelt"] == r["kelt"]:
                DUP.mkdir(parents=True, exist_ok=True)
                dst = DUP / p.name
                if dst.exists():
                    dst = DUP / (datetime.now().strftime("%Y%m%dT%H%M%S_") + p.name)
                shutil.move(str(p), str(dst))
                e.setdefault("duplikatumok", []).append(p.name)
                print(f"= DUPLIKÁTUM: {p.name} ({r['sorszam']}) már nyilvántartva; nem dolgoztam fel újra, áthelyezve: archive/kiadasok/duplikatumok/")
            else:
                print(f"🔴 ELLENTMONDÁS: {p.name} ({r['sorszam']}): azonos sorszám, de eltérő kelt/összeg a nyilvántartottal ({ft(r['brutto'])} ≠ {ft(e['brutto'])}). "
                      "Az irat az input/-ban maradt; kérdés a felhasználónak: melyik a helyes?")
                konfl += 1
            continue
        ev = r["kelt"][:4]
        dest = ARCH / ev
        dest.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.-]+", "_", r["sorszam"])
        dst = dest / f"{r['tipus']}_{safe}.pdf"
        if dst.exists():
            dst = dest / f"{r['tipus']}_{safe}_{raw[:8]}.pdf"
        shutil.move(str(p), str(dst))
        if hashlib.sha256(dst.read_bytes()).hexdigest() != raw:
            print(f"HIBA: hash eltérés áthelyezés után: {dst.name}")
            return 1
        MD.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-I", str(PDFMD), "--fajl", str(dst), "--ki", str(MD / (dst.stem + ".md"))], capture_output=True, text=True, encoding="utf-8")
        r.update({"kulcs": key, "sha256": raw, "archivalt": str(dst.relative_to(ROOT)).replace("\\", "/"), "feldolgozva": datetime.now().isoformat(timespec="seconds")})
        reg["iratok"].append(r)
        print(f"+ ÚJ: {'DÍJBEKÉRŐ (nem kiadás)' if r['tipus'] == 'dijbekero' else 'számla'} {r['sorszam']}, {r['szallito']}, kelt {r['kelt']}, bruttó {ft(r['brutto'])}")
    # díjbekérő <-> számla összekapcsolás
    for x in reg["iratok"]:
        x["dijbekero_szamla"] = None
    for x in reg["iratok"]:
        if x["tipus"] == "szamla" and x.get("dijbekero_hivatkozas"):
            d = next((y for y in reg["iratok"] if y["tipus"] == "dijbekero" and y["sorszam"] == x["dijbekero_hivatkozas"]), None)
            if d:
                d["dijbekero_szamla"] = x["sorszam"]
                same = d["brutto"] == x["brutto"]
                print(f"  ↔ A(z) {d['sorszam']} díjbekérő a(z) {x['sorszam']} számlához tartozik; az összeg {'azonos' if same else 'NEM azonos'}; csak a számla számít kiadásnak.")
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return 3 if konfl else 0


def lista(ev):
    reg = load()
    for x in sorted(reg["iratok"], key=lambda x: x["kelt"]):
        if ev and not x["kelt"].startswith(str(ev)):
            continue
        print(x["kelt"], x["tipus"], x["sorszam"], x["szallito"], ft(x["brutto"]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--feldolgoz", action="store_true")
    ap.add_argument("--lista", nargs="?", const="0")
    a = ap.parse_args()
    if a.feldolgoz:
        sys.exit(feldolgoz())
    if a.lista is not None:
        lista(int(a.lista) or None)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
