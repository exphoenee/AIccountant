#!/usr/bin/env python3
"""Önteszt a számla-megfelelőségi ellenőrzéshez (szintetikus számlákkal). Futtatás: python -I .claude/skills/szamlak/scripts/teszt_szamla_ellenorzes.py"""
import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sze", here / "szamla_ellenorzes.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
fails = []


def alap(**kw):
    sz = {"invoice_number": "T-1", "invoice_date": "2026-10-01", "fulfillment_date": "2026-10-11", "due_date": "2026-10-11", "currency": "EUR", "conversion_rate": 400.0,
          "organization": {"tax_number": "12345678-1-22", "name": "Teszt EV", "address": {"address": "Utca 1"}, "small_taxpayer": False},
          "partner": {"name": "Vevő BV", "taxcode": "NL123", "address": {"address": "Straat 2", "country_code": "NL"}},
          "items": [{"name": "Szolgáltatás", "quantity": 1, "net_unit_amount": 100, "vat": "ÁTHK", "vat_amount": 0, "entitlement": "EUFAD37", "comment": ""}],
          "comment": "Áfa tv. 37. § alapján másik tagállamban teljesített, fordított adózás. Billing period: 2026. 09. 16. - 2026. 09. 30."}
    sz.update(kw)
    return sz


def van(f, szint, kulcs):
    return any(x["szint"] == szint and kulcs in (x["szabaly"] + x["uzenet"]) for x in f)


def t(nev, ok):
    print(("OK    " if ok else "HIBA  ") + nev)
    if not ok:
        fails.append(nev)


f = m.ellenoriz(alap())
t("hibátlan uniós fordított adózású számla: nincs hiba/figyelmeztetés", not any(x["szint"] in ("hiba", "figyelmeztetés") for x in f))
t("időszakos elszámolás: a teljesítés = a fizetési határidő (58. § (1a) b)) rendben", any(x["szabaly"] == "Áfa tv. 58. §" and x["szint"] == "info" for x in f))
t("hibás teljesítési dátum: 58. § figyelmeztetés", van(m.ellenoriz(alap(fulfillment_date="2026-10-08")), "figyelmeztetés", "58. §"))
t("US vevő EU-s jogcímmel (EUFAD37): hiba", van(m.ellenoriz(alap(partner={"name": "X", "taxcode": "1", "address": {"address": "A", "country_code": "US"}})), "hiba", "EUFAD37"))
t("külföldi vevő adószám nélkül: figyelmeztetés (37. §)", van(m.ellenoriz(alap(partner={"name": "X", "taxcode": "", "address": {"address": "A", "country_code": "US"}}, items=[{"name": "s", "quantity": 1, "net_unit_amount": 1, "vat": "ÁTHK", "vat_amount": 0, "entitlement": "HO", "comment": ""}])), "figyelmeztetés", "37. §"))
t("hiányzó vevőcím: 169. § hiba", van(m.ellenoriz(alap(partner={"name": "X", "taxcode": "1", "address": {"country_code": "NL"}})), "hiba", "169. §"))
t("'fordított adózás' kifejezés hiányzik: 169. § n) figyelmeztetés", van(m.ellenoriz(alap(comment="Áfa tv. 37. § alapján fordítottan adózó ügylet. Period: 2026. 09. 16. - 2026. 09. 30.")), "figyelmeztetés", "169. § n)"))
t("alanyi adómentes eladó áthárított adóval: hiba (187. §)", van(m.ellenoriz(alap(organization={"tax_number": "1", "name": "n", "address": {"address": "a"}, "small_taxpayer": True},
                                                                             items=[{"name": "s", "quantity": 1, "net_unit_amount": 1, "vat": "27%", "vat_amount": 27, "entitlement": "", "comment": ""}])), "hiba", "187. §"))
t("AAM tétel, de az eladó a számlázóban nem alanyi adómentes: figyelmeztetés", van(m.ellenoriz(alap(partner={"name": "X", "taxcode": "1", "address": {"address": "A", "country_code": "HU"}}, currency="HUF",
                                                                                              items=[{"name": "s", "quantity": 1, "net_unit_amount": 1, "vat": "AAM", "vat_amount": 0, "entitlement": "AAM", "comment": ""}], comment="")), "figyelmeztetés", "187"))
t("devizás számla árfolyam nélkül: hiba (80. §)", van(m.ellenoriz(alap(conversion_rate=None)), "hiba", "80. §"))
t("58. § (1): időszak vége a teljesítés, ha a fizetési határidő nem későbbi", m.varhato_teljesites(__import__("datetime").date(2026, 9, 16), __import__("datetime").date(2026, 9, 30),
                                                                                        __import__("datetime").date(2026, 9, 30), None)[0] == __import__("datetime").date(2026, 9, 30))
print()
if fails:
    print(f"{len(fails)} teszt BUKOTT")
    sys.exit(1)
print("Minden számla-megfelelőségi teszt megfelelt.")
