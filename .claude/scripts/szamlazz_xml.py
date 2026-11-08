#!/usr/bin/env python3
"""A Számla Agent számlalekérdezés (xmlszamlaxml) válaszának átalakítása a repó közös számlaformátumára (a Billingo-formára).

Forrás: https://docs.szamlazz.hu/agent/querying_xml/response (gyökér: <szamla>, névtér http://www.szamlazz.hu/szamla; hiba esetén
<xmlszamlavalasz> sikeres=false, hibakod, hibauzenet). Használja: szamlak (szamlazz_szamlak.py) és a bevételi fájlok feldolgozása.

A kimenet mezői megegyeznek azzal, amit az adoszamitas a Billingo-számlákból olvas: invoice_number, type, invoice_date, fulfillment_date,
paid_date, payment_status, currency, conversion_rate, summary{net_amount, net_amount_local, gross_amount_local, vat_amount_local}.
Nem kitalál: ami hiányzik, az None.
"""
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP

TIPUS = {"SZ": "invoice", "SS": "cancellation"}  # a többi típus szándékosan nem „invoice”: az adoszamitas kiveszi és jelzi


def _lokal(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _gyerek(e, nev):
    if e is None:
        return None
    for c in e:
        if _lokal(c.tag) == nev:
            return c
    return None


def _szoveg(e, nev):
    c = _gyerek(e, nev)
    return (c.text or "").strip() if c is not None and c.text else None


def _dec(x):
    if x is None or x == "":
        return None
    return Decimal(str(x).replace(" ", "").replace(",", "."))


def hiba_valasz(xml_text: str):
    """(True, hibakod, hibauzenet), ha a válasz hibát jelent; különben (False, None, None)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return True, None, "a válasz nem értelmezhető XML"
    if _lokal(root.tag) == "xmlszamlavalasz":
        return True, _szoveg(root, "hibakod"), _szoveg(root, "hibauzenet")
    return False, None, None


def normalizal(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    if _lokal(root.tag) != "szamla":
        raise ValueError(f"nem Számla Agent számla-XML (gyökér: {_lokal(root.tag)})")
    szallito, alap, vevo = _gyerek(root, "szallito"), _gyerek(root, "alap"), _gyerek(root, "vevo")
    osszegek = _gyerek(_gyerek(root, "osszegek"), "totalossz")
    netto, afa, brutto = (_dec(_szoveg(osszegek, k)) for k in ("netto", "afa", "brutto"))
    deviza = _szoveg(alap, "devizanem") or "HUF"
    arf = _dec(_szoveg(alap, "devizaarf")) if deviza != "HUF" else Decimal(1)
    kif = []
    kifs = _gyerek(root, "kifizetesek")
    if kifs is not None:
        for k in kifs:
            d, o = _szoveg(k, "datum"), _dec(_szoveg(k, "osszeg"))
            if d and o is not None:
                kif.append((d, o))
    kif.sort()
    paid_date, status, sum_ = None, "outstanding", Decimal(0)
    for d, o in kif:
        sum_ += o
        if brutto is not None and sum_ >= brutto - Decimal("0.5") and paid_date is None:
            paid_date = d
    if paid_date:
        status = "paid"
    elif sum_ > 0:
        status = "partial"
    tipus = _szoveg(alap, "tipus") or ""

    def helyi(x):
        return int((x * (arf or Decimal(1))).quantize(Decimal(1), ROUND_HALF_UP)) if x is not None and arf is not None else None

    return {
        "forras": "szamlazz",
        "invoice_number": _szoveg(alap, "szamlaszam"),
        "type": TIPUS.get(tipus, f"szamlazz_{tipus or 'ismeretlen'}"),
        "cancelled": False,
        "invoice_date": _szoveg(alap, "kelt"),
        "fulfillment_date": _szoveg(alap, "telj"),
        "due_date": _szoveg(alap, "fizh"),
        "paid_date": paid_date,
        "payment_status": status,
        "currency": deviza,
        "conversion_rate": float(arf) if arf is not None else None,
        "summary": {"net_amount": float(netto) if netto is not None else None, "net_amount_local": helyi(netto),
                    "gross_amount_local": helyi(brutto), "vat_amount_local": helyi(afa)},
        "seller_tax_number": _szoveg(szallito, "adoszam"),
        "partner_tax_number": _szoveg(vevo, "adoszam"),
        "partner_name": _szoveg(vevo, "nev"),
        "kifizetesek": [{"datum": d, "osszeg": float(o)} for d, o in kif],
    }


def kulcs(szamlaszam: str) -> str:
    """Számlaszám normalizált kulcsa a duplikáció-kereséshez: nagybetű, csak betű/szám."""
    return re.sub(r"[^0-9A-Z]", "", (szamlaszam or "").upper())
