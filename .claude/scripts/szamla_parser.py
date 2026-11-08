#!/usr/bin/env python3
"""Számla-PDF (szövegréteg) értelmezése: közös a kiadasok-dokumentumok és a szamlak (bevételek) skill között.

Két elrendezést ismer: Billingo-típusú (ELADÓ/VEVŐ oszlopok, "SZÁMLA KELTE", "NETTÓ ÖSSZEG") és Számlázz.hu-típusú (Sorszám:, Kiállítás
dátuma:, tételsor AAM/ÁFA-kulccsal). Amit nem tud kiolvasni, azt None-ként adja vissza; nem találgat.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path


def pdftotext() -> str:
    exe = shutil.which("pdftotext")
    if exe:
        return exe
    for c in (r"C:\Program Files\Git\mingw64\bin\pdftotext.exe", r"C:\Program Files\Git\usr\bin\pdftotext.exe"):
        if Path(c).exists():
            return c
    sys.exit("HIBA: nincs pdftotext (poppler/xpdf); telepítsd, vagy lásd install.sh / install.ps1")


def pdf_szoveg(pdf) -> str:
    return subprocess.run([pdftotext(), "-layout", "-enc", "UTF-8", "-q", str(pdf), "-"], capture_output=True, text=True,
                          encoding="utf-8").stdout


def num(s):
    return int(re.sub(r"\s", "", s))


def datum(m):
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


DATE = r"(\d{4})\.\s?(\d\d)\.\s?(\d\d)"


def parse(txt: str, sajat_adoszam: str):
    """-> dict vagy None. A szállító adószáma az első, nem a vevőé."""
    t = txt
    dijbekero = bool(re.search(r"^\s*Díjbekérő\b", t, re.M | re.I)) or "DÍJBEKÉRŐ KELTE" in t
    sorsz = None
    m = re.search(r"Sorszám:\s*([\w/ .-]+)", t)
    if m:
        sorsz = m.group(1).strip()
    else:
        m = re.search(r"\b([A-Z]{1,6} / [A-Z]?\d[\w-]+)", t)
        sorsz = m.group(1).replace(" ", "") if m else None
    kelt_m = (re.search(r"SZÁMLA KELTE\s*:\s*" + DATE, t) or re.search(r"DÍJBEKÉRŐ KELTE\s*:\s*" + DATE, t)
              or re.search(r"Kiállítás dátuma:\s*" + DATE, t))
    telj_m = re.search(r"TELJESÍTÉS KELTE:\s*" + DATE, t) or re.search(r"Teljesítés dátuma:\s*" + DATE, t)
    hat_m = re.search(r"FIZETÉSI HATÁRIDŐ:\s*" + DATE, t) or re.search(r"Fizetési határidő:\s*" + DATE, t)
    netto = afa = brutto = None
    kulcs = None
    m = re.search(r"NETTÓ ÖSSZEG:\s*([\d ]+) Ft", t)
    if m:
        netto = num(m.group(1))
        ma = re.search(r"(\d+)% ÁFA:\s*([\d ]+) Ft", t)
        kulcs, afa = (ma.group(1) + "%", num(ma.group(2))) if ma else (None, 0)
        mb = re.findall(r"FIZETENDŐ BRUTTÓ VÉGÖSSZEG:\s*([\d ]+) Ft", t)
        brutto = num(mb[-1]) if mb else None
    else:
        mo = re.search(r"^\s*Összesen:\s{2,}(\d[\d ]*?)\s{2,}(\d+)\s*$", t, re.M)
        mk = re.search(r"\s(AAM|\d+%)\s", t)
        mb = re.findall(r"([\d ]+) (?:Ft|HUF)\s*$", t, re.M)
        if mo and mb:
            netto, afa, brutto, kulcs = num(mo.group(1)), num(mo.group(2)), num(mb[-1]), (mk.group(1) if mk else None)
    # szállító: Billingo-típusú: az ELADÓ utáni sor; egyébként az első nem üres sor
    sorok = [s.strip() for s in t.splitlines() if s.strip()]
    szallito = None
    for sor in sorok:
        for seg in re.split(r"\s{2,}", sor):
            if re.search(r"(Kft|Zrt|Bt|Nyrt|Kkt)\.?", seg):
                szallito = seg.strip()
                break
        if szallito:
            break
    szall_ado = None
    for m in re.finditer(r"(?:ADÓSZÁM|Adószám):\s*(\d{8}-\d-\d\d)", t):
        if re.sub(r"\D", "", m.group(1)) != sajat_adoszam:
            szall_ado = m.group(1)
            break
    ref = re.search(r"([A-Z]{1,6} ?/ ?P\d+)\s+díjbekérő alapján", t)
    return {"tipus": "dijbekero" if dijbekero else "szamla", "sorszam": sorsz, "kelt": datum(kelt_m) if kelt_m else None,
            "teljesites": datum(telj_m) if telj_m else None, "fizetesi_hatarido": datum(hat_m) if hat_m else None,
            "szallito": szallito, "szallito_adoszam": szall_ado, "netto": netto, "afa_kulcs": kulcs, "afa": afa, "brutto": brutto,
            "dijbekero_hivatkozas": ref.group(1).replace(" ", "") if ref else None,
            "penzugyi_teljesitest_nem_igenyel": "nem igényel" in t and "pénzügyi teljesítést" in t}


def elado_neve(txt: str):
    """Az eladó neve: Billingo-típusnál az ELADÓ utáni sor bal oszlopa; Számlázz-típusnál az első nem üres sor bal oszlopa."""
    sorok = [x.strip() for x in txt.splitlines() if x.strip()]
    for i, x in enumerate(sorok):
        if re.match(r"^ELADÓ\b", x):
            for nx in sorok[i + 1:i + 4]:
                nm = re.split(r"\s{2,}", nx)[0]
                if nm and "ADÓSZÁM" not in nm and not nm.startswith("VEVŐ"):
                    return nm
    return re.split(r"\s{2,}", sorok[0])[0] if sorok else None

