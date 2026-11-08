#!/usr/bin/env python3
"""A kimenő számlák megfelelőségi ellenőrzése az Áfa tv. szabályai szerint (számlánként, hivatkozással).

Használat:
    python -I .claude/skills/szamlak/scripts/szamla_ellenorzes.py

Bemenet: data/szamlak/egyesitett_*.json (a szamlak_egyesites.py kimenete, Billingo-formájú számlák).
Kimenet: data/szamlak/szamla_ellenorzes.json és összegzés a képernyőn. Minden megállapítás szabályhivatkozást kap; a hivatkozott szakaszokat a
torvenytar/afa-tv/2026/2007-evi-cxxvii-torveny.txt szövegéből ellenőriztem (lásd .claude/rules/afa.md, .claude/rules/szamlazas.md).

Szintek: "hiba" = a kötelező tartalom hiányzik vagy egyértelműen ellentmond a szabálynak; "figyelmeztetés" = ellenőrizendő (a számlaadatból
nem dönthető el, vagy a törvényszöveg és a számlán szereplő kifejezés eltér); "info" = megfelelő. A script nem javít, nem becsül, nem dönt jogértelmezési
kérdésben: a figyelmeztetéseket a könyvelővel kell tisztázni. A PDF-ek kinézetét (a számla tényleges nyomtatott szövegét) nem látja, csak a számlázóprogram adatait.
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "data" / "szamlak"
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
MENTES = ("AAM", "ÁTHK", "EU", "TAM", "KBAET", "KBAUK", "EUKT", "EUFAD37", "HO", "ÁFAMENT")  # mentességet / hatályon kívüliséget jelző Billingo-jelölések (nem teljes lista)


def olvas(p):
    return json.loads(p.read_text(encoding="utf-8"))


def datum(x):
    return date.fromisoformat(x) if x else None


def idoszak(megj: str):
    """A számla megjegyzésében szereplő elszámolási időszak (angol vagy magyar formátum) -> (tól, ig) vagy None."""
    m = re.search(r"(\d{4})\.\s?(\d\d)\.\s?(\d\d)\.?\s*-\s*(\d{4})\.\s?(\d\d)\.\s?(\d\d)", megj)
    if m:
        a = [int(x) for x in m.groups()]
        return date(a[0], a[1], a[2]), date(a[3], a[4], a[5])
    m = re.search(r"(\d\d)/(\d\d)/(\d{4})\s*-\s*(\d\d)/(\d\d)/(\d{4})", megj)
    if m:
        a = [int(x) for x in m.groups()]
        return date(a[2], a[1], a[0]), date(a[5], a[4], a[3])
    return None


def varhato_teljesites(tol, ig, kelt, fizh):
    """Áfa tv. 58. § (1)–(1a): időszakonkénti elszámolásnál a teljesítés időpontja."""
    if fizh and fizh > ig:
        return min(fizh, ig + timedelta(days=60)), "58. § (1a) b): a fizetési határidő (legfeljebb az időszak vége utáni 60. nap)"
    if fizh and fizh < ig and kelt < ig:
        return kelt, "58. § (1a) a): a számla kibocsátásának napja (a fizetési határidő és a kibocsátás is az időszak vége előtt van)"
    return ig, "58. § (1): az elszámolási időszak utolsó napja"


def ellenoriz(sz):
    """-> lista: {szint, szabaly, uzenet}"""
    ki = []

    def add(szint, szabaly, uzenet):
        ki.append({"szint": szint, "szabaly": szabaly, "uzenet": uzenet})

    org, partner = sz.get("organization") or {}, sz.get("partner") or {}
    padr = partner.get("address") or {}
    it = sz.get("items") or []
    megj = (sz.get("comment") or "") + " " + " ".join((i.get("comment") or "") for i in it)
    orszag = (padr.get("country_code") or "").upper()
    kelt, telj, fizh = datum(sz.get("invoice_date")), datum(sz.get("fulfillment_date")), datum(sz.get("due_date"))
    jel = {(i.get("vat") or "").upper() for i in it}
    ent = {(i.get("entitlement") or "").upper() for i in it}
    mentes = bool(jel & set(MENTES)) or all((i.get("vat_amount") or 0) == 0 for i in it)

    # 1) kötelező adattartalom (Áfa tv. 169. §)
    hiany = []
    for nev, ertek in (("a kibocsátás kelte (a)", sz.get("invoice_date")), ("a sorszám (b)", sz.get("invoice_number")),
                       ("az eladó adószáma (c)", org.get("tax_number")), ("az eladó neve (e)", org.get("name")),
                       ("az eladó címe (e)", (org.get("address") or {}).get("address")), ("a vevő neve (e)", partner.get("name")),
                       ("a vevő címe (e)", padr.get("address")), ("a teljesítés időpontja (g)", sz.get("fulfillment_date"))):
        if not ertek:
            hiany.append(nev)
    for n, i in enumerate(it, 1):
        for mezo, nev in (("name", "megnevezés"), ("quantity", "mennyiség"), ("net_unit_amount", "nettó egységár"), ("vat", "az adó mértéke vagy a mentesség jelölése")):
            if i.get(mezo) in (None, ""):
                hiany.append(f"{n}. tétel: {nev} (f, i, j)")
    if not it:
        hiany.append("a tételek (f)")
    if hiany:
        add("hiba", "Áfa tv. 169. §", "hiányzó kötelező adat: " + "; ".join(hiany))

    # 2) a vevő azonosítása: adóalany-e (37. § (1) vs (2)) és uniós-e
    van_adoszam = bool(partner.get("taxcode"))
    if orszag and orszag != "HU" and not van_adoszam:
        add("figyelmeztetés", "Áfa tv. 37. § (1)–(2); 169. § d)",
            f"külföldi vevő ({orszag}) adószám/azonosító nélkül: a számlából nem igazolható, hogy a vevő adóalany (37. § (1): teljesítési hely a vevő letelepedése), "
            "nem adóalany vevőnél a teljesítési hely az eladónál van (37. § (2)), és ÁFA-t kellene felszámítani vagy alanyi adómentességre hivatkozni; a vevő adóalanyi minőségét igazoló dokumentum szükséges")
    if orszag and orszag != "HU" and "ÁTHK" in jel and any(e == "EUFAD37" for e in ent) and orszag not in EU:
        add("hiba", "Áfa tv. 37. §; Billingo-jelölés",
            f"a tétel jogcíme uniós fordított adózás (EUFAD37), de a vevő országa {orszag}, nem uniós tagállam: a jogcím és a vevő országa ellentmond egymásnak")
    if orszag in EU and orszag != "HU" and not (jel & {"ÁTHK"}):
        add("figyelmeztetés", "Áfa tv. 37. § (1)", f"uniós ({orszag}) vevő, de a tétel nem „ÁTHK”: ellenőrizd az ÁFA-kezelést")

    # 3) alanyi adómentesség / ÁFA (187. § (2))
    kisadozo = org.get("small_taxpayer")
    van_afa = any((i.get("vat_amount") or 0) > 0 for i in it)
    if kisadozo and van_afa:
        add("hiba", "Áfa tv. 187. § (2) c)", "alanyi adómentes eladó számláján áthárított adó szerepel; ilyen számla nem állítható ki")
    if "AAM" in jel and not kisadozo:
        add("figyelmeztetés", "Áfa tv. 187–188. §", "a tétel „AAM” (alanyi adómentes), de a számlázóprogramban az eladó nem alanyi adómentesként szerepel (small_taxpayer = false): a számlázóprogram beállítása és a számla tartalma ellentmond egymásnak")
    if "AAM" in jel and orszag == "HU" and not kisadozo:
        pass  # a fenti üzenet lefedi

    # 4) mentesség / hatályon kívüliség jelölése (169. § m)
    if mentes and not re.search(r"Áfa tv|Héa|alanyi adómentes|VAT Act|Article|hatályán kívül|fordított|reverse", megj, re.I) and not (jel & {"AAM"}):
        add("figyelmeztetés", "Áfa tv. 169. § m)",
            "mentesség/hatályon kívüliség esetén jogszabályi hivatkozás vagy egyértelmű utalás szükséges; a számlaadatban csak a jelölés („" + ", ".join(sorted(jel)) + "”) van, hivatkozás nincs: ellenőrizd a számla nyomtatott szövegét")
    if "AAM" in jel and not re.search(r"alanyi adómentes|AAM", megj, re.I):
        add("info", "Áfa tv. 169. § m)", "AAM jelölés a tételen; a megjegyzésben külön hivatkozás nincs (a jelölés maga lehet az egyértelmű utalás: ellenőrizd a PDF-en)")

    # 5) fordított adózás kifejezés (169. § n)
    fordit = orszag in EU and orszag != "HU" and "ÁTHK" in jel and "EUFAD37" in ent
    if fordit and not re.search(r"fordított adózás", megj, re.I):
        add("figyelmeztetés", "Áfa tv. 169. § n)",
            "a törvény a „fordított adózás” kifejezést írja elő, ha az adófizetésre a szolgáltatást igénybevevő kötelezett; a számlán a „fordítottan adózó ügylet” szerepel (lásd a megjegyzést): a könyvelővel erősítsd meg, hogy ez megfelel-e")

    # 6) teljesítés időpontja időszakonkénti elszámolásnál (58. §) és a kibocsátás határideje (163. §)
    per = idoszak(megj)
    if per and kelt and telj:
        vart, indok = varhato_teljesites(per[0], per[1], kelt, fizh)
        if vart != telj:
            add("figyelmeztetés", "Áfa tv. 58. §", f"elszámolási időszak {per[0]} – {per[1]}: a számlán a teljesítés {telj}, az 58. § szerint várható {vart} ({indok})")
        else:
            add("info", "Áfa tv. 58. §", f"időszakonkénti elszámolás ({per[0]} – {per[1]}): a teljesítés időpontja ({telj}) megfelel az 58. § szerint várt értéknek ({indok.split(':')[0]})")
    elif telj and kelt and fordit:
        pass
    if fordit and telj and kelt:
        hatar = date(telj.year + (1 if telj.month == 12 else 0), 1 if telj.month == 12 else telj.month + 1, 15)
        if kelt > hatar:
            add("hiba", "Áfa tv. 163. § (2) a)", f"fordított adózású szolgáltatásnál a számlát a teljesítés hónapját követő hónap 15. napjáig ({hatar}) kell kibocsátani; kelte {kelt}")

    if orszag and orszag != "HU" and orszag not in EU and "ÁTHK" in jel and telj and kelt:
        add("info", "Áfa tv. 163. §",
            "nem uniós vevő: a 163. § (2) a) (teljesítés hónapját követő hónap 15.) a Héa-irányelv 196. cikke szerinti uniós fordított adózásra szól, ezért itt nem "
            "ellenőrzöm; a kibocsátási határidő a 163. § (1) és (2) b)–c) szerint alakul, ezt a script nem vizsgálja (könyvelő)")

    # 7) devizás számla (80. §, 172. §)
    if sz.get("currency") not in (None, "HUF"):
        arf = sz.get("conversion_rate")
        if not arf or arf <= 0:
            add("hiba", "Áfa tv. 80. §", "devizás számlán nincs átváltási árfolyam")
        elif van_afa:
            add("info", "Áfa tv. 172. §", "devizás számla áthárított adóval: az adót forintban is fel kell tüntetni (ellenőrizd a PDF-en)")
        else:
            add("info", "Áfa tv. 80. §", f"devizás számla ({sz.get('currency')}), árfolyam megadva ({arf}); az árfolyam forrását (80. § (2)) a script nem ellenőrzi")
    return ki


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fajlok = sorted(DATA.glob("egyesitett_*.json"))
    if not fajlok:
        print("Nincs egyesített számlafájl: a megfelelőségi ellenőrzés kimarad.")
        return
    mind = [x for x in olvas(fajlok[-1]) if x.get("type") == "invoice"]
    stornozott = [x["invoice_number"] for x in mind if x.get("cancelled")]  # a sztornózott számla helyett kibocsátott javított számlát ellenőrizzük
    szamlak = [x for x in mind if not x.get("cancelled")]
    eredmeny = []
    for sz in sorted(szamlak, key=lambda x: (x.get("invoice_date") or "", x.get("invoice_number") or "")):
        f = ellenoriz(sz)
        eredmeny.append({"szamlaszam": sz["invoice_number"], "kelt": sz["invoice_date"], "megallapitasok": f})
    hiba = sum(1 for r in eredmeny for f in r["megallapitasok"] if f["szint"] == "hiba")
    fig = sum(1 for r in eredmeny for f in r["megallapitasok"] if f["szint"] == "figyelmeztetés")
    ok = sum(1 for r in eredmeny if not any(f["szint"] in ("hiba", "figyelmeztetés") for f in r["megallapitasok"]))
    (DATA / "szamla_ellenorzes.json").write_text(json.dumps({"forras": fajlok[-1].name, "szamlak": len(eredmeny), "stornozott_kihagyva": stornozott, "hiba": hiba, "figyelmeztetes": fig,
                                                              "eredmenyek": eredmeny}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Számlák megfelelősége (Áfa tv.): {len(eredmeny)} számla (+ {len(stornozott)} sztornózott kihagyva); {ok} kifogás nélkül, {hiba} hiba, {fig} figyelmeztetés -> data/szamlak/szamla_ellenorzes.json")
    for r in eredmeny:
        for f in r["megallapitasok"]:
            if f["szint"] in ("hiba", "figyelmeztetés"):
                print(f"  {'🔴' if f['szint'] == 'hiba' else '🟡'} {r['szamlaszam']} ({f['szabaly']}): {f['uzenet'][:170]}")


if __name__ == "__main__":
    main()
