#!/usr/bin/env python3
"""Az összevont adóalapot csökkentő kedvezmények számítása átalányadózó egyéni vállalkozóra (Szja tv. 29/A.–29/H. §; 2025. évi XIII., XIV., XV. tv.).

Az adoszamitas.py hívja; önállóan is futtatható:
    python -I .claude/skills/adoszamitas/scripts/kedvezmenyek.py --pelda      # a config/vallalkozas.json "kedvezmenyek" mezőjének mintája

Minden képlet a letöltött törvényszövegből való (torvenytar/docs/szja-tv/2026/*.jogtar.txt, torvenytar/docs/2025-xiii-tv, 2025-xiv-tv, 2025-xv-tv); a
szakaszhivatkozásokat az eredmény tartalmazza. Szabályok: .claude/rules/kedvezmenyek.md, nincs-becsles.md: ha egy bemenet hiányzik vagy
a képlet nincs a szövegből igazolva, a jogcím NEM SZÁMOLHATÓ, és az egész kedvezményes adó nem jelenik meg (részeredményt nem adunk ki
"végső" adóként).

Az összeadás-kivonást Decimal végzi; az AI nem számol. A kedvezmény az ÉVES adóra (bevallás) vonatkozik; a negyedéves átalányadó-előleg
számítása változatlan (az előleg kedvezményes csökkentésének szabályát az Szja tv. 48. §-a a munkáltatóra/kifizetőre írja elő: az
átalányadózó saját előlegére nem ellenőriztük).
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP

D = Decimal

# 29/H. § (1): az adóalap-csökkentő kedvezmények érvényesítésének sorrendje (a támogatott jogcímek, a törvény sorrendjében)
SORREND = ["harmincalatti_anya", "negy_vagy_tobb_anya", "harom_anya", "ketto_anya", "huszonot_ev_alatti", "szemelyi", "elso_hazasok", "csaladi"]
ANYA_VALASZTHATO = ["negy_vagy_tobb_anya", "harom_anya", "ketto_anya"]  # 29/H. § (1) b): egymást kizáró jogcímek, (2) szerint egy választható
NEV = {"harmincalatti_anya": "30 év alatti anyák kedvezménye", "negy_vagy_tobb_anya": "négy vagy több gyermeket nevelő anyák kedvezménye",
       "harom_anya": "három gyermeket nevelő anyák kedvezménye", "ketto_anya": "két gyermeket nevelő anyák kedvezménye",
       "huszonot_ev_alatti": "25 év alatti fiatalok kedvezménye", "szemelyi": "személyi kedvezmény",
       "elso_hazasok": "első házasok kedvezménye", "csaladi": "családi kedvezmény"}
HELY = {"harmincalatti_anya": "2025. évi XIII. tv. 1. § (3)–(5); Szja tv. 29/H. § (1) a)",
        "negy_vagy_tobb_anya": "Szja tv. 29/D. § (2), (5)", "harom_anya": "2025. évi XV. tv. 1. § (2), (6)",
        "ketto_anya": "2025. évi XIV. tv. 1. § (2), (6)", "huszonot_ev_alatti": "Szja tv. 29/F. § (2), (3), (4)",
        "szemelyi": "Szja tv. 29/E. § (3), (4)", "elso_hazasok": "Szja tv. 29/C. § (3)–(5)", "csaladi": "Szja tv. 29/A. § (2), (2a); 29/B. §"}
NEM_TAMOGATOTT = {"csecsemogondozasi_dij": "a csecsemőgondozási díj, gyermekgondozási díj és örökbefogadói díj kedvezménye (29/H. § (1) c))"}


def rnd(x) -> Decimal:
    return D(x).quantize(D(1), rounding=ROUND_HALF_UP)


def _honapok(v, nev):
    """A jogosultsági hónapok: 1–12 közötti, egyedi egész számok listája. Hibánál ValueError."""
    if isinstance(v, bool) or not isinstance(v, (list, tuple)) or not v:
        raise ValueError(f"{nev}: a 'honapok' a jogosultsági hónapok listája kell legyen (1–12), pl. [1,2,3]")
    if any(isinstance(x, bool) or not isinstance(x, int) or not 1 <= x <= 12 for x in v) or len(set(v)) != len(v):
        raise ValueError(f"{nev}: a 'honapok' elemei 1–12 közötti, egymástól különböző egész számok lehetnek")
    return sorted(v)


def _resz(adat, nev):
    r = D(str(adat.get("sajat_resz", 1)))
    if not D(0) < r <= D(1):
        raise ValueError(f"{nev}: a 'sajat_resz' 0 és 1 között kell legyen (a házastársak/jogosultak döntése szerinti, általad érvényesített hányad)")
    return r


def _csaladi(adat, rules):
    ar = rules.get("csaladi_kedvezmeny_havi")
    nov = rules.get("csaladi_kedvezmeny_beteg_noveles_havi")
    if not ar or nov is None:
        raise ValueError("családi kedvezmény: a szabalyok_<év>.json nem tartalmazza a havi összegeket (csaladi_kedvezmeny_havi)")
    if adat.get("havi"):
        havi = {int(k): v for k, v in adat["havi"].items()}
        for k in havi:
            if not 1 <= k <= 12:
                raise ValueError("családi kedvezmény: a 'havi' kulcsai 1–12 közötti hónapok lehetnek")
    else:
        h = _honapok(adat.get("honapok"), "családi kedvezmény")
        havi = {m: {k: adat.get(k, 0) for k in ("eltartottak", "kedvezmenyezett_eltartottak", "tartosan_beteg_vagy_sulyosan_fogyatekos")} for m in h}
    osszeg, reszletek, csop = D(0), [], {}
    for m in sorted(havi):
        a = havi[m]
        el, ke, be = int(a.get("eltartottak", 0)), int(a.get("kedvezmenyezett_eltartottak", 0)), int(a.get("tartosan_beteg_vagy_sulyosan_fogyatekos", 0))
        if not (0 < ke <= el) or not 0 <= be <= ke:
            raise ValueError(f"családi kedvezmény, {m}. hónap: kell: 0 < kedvezményezett eltartottak ≤ eltartottak, és 0 ≤ tartósan beteg/súlyosan fogyatékos ≤ kedvezményezett eltartottak "
                             f"(kapott: eltartott {el}, kedvezményezett {ke}, beteg {be}); 29/A. § (4), (5)")
        rata = D(str(ar[str(min(el, 3))]))
        havi_ossz = ke * rata + be * D(str(nov))
        osszeg += havi_ossz
        csop.setdefault((ke, el, be, int(rata), int(havi_ossz)), []).append(m)
    for (ke, el, be, rata, hossz), hok in csop.items():
        reszletek.append(f"{len(hok)} hónap ({', '.join(str(x) for x in hok)}.): havonta {ke} kedvezményezett eltartott × {rata} Ft (az eltartottak száma: {el}) + {be} × {int(D(str(nov)))} Ft = {hossz} Ft")
    resz = _resz(adat, "családi kedvezmény")
    jk = D(str(adat.get("csaladi_jarulekkedvezmeny_ft", 0)))
    levon = D(0)
    if jk:
        # 29/B. § (6): az együttesen igénybe vett családi járulékkedvezmény az adó mértékével elosztott része (a törvény zárójelben 667 százalékot ír) csökkenti
        kulcs = D(str(rules["szja_kulcs"]))
        levon = jk / kulcs
        reszletek.append(f"29/B. § (6): a már igénybe vett családi járulékkedvezmény ({int(jk)} Ft) / {kulcs} = {int(rnd(levon))} Ft levonás (a törvény zárójeles 667%-a a kerekített érték; a képlet értelmezése: osztás az adókulccsal)")
    return max(D(0), osszeg * resz - levon), reszletek


def szamol(jovedelem, adoalap, kedv, rules, ev):
    """jovedelem: az átalányban megállapított (éves, az eddigi bevételből számolt) jövedelem; adoalap: az adómentes rész utáni összevont adóalap.
    kedv: a config 'kedvezmenyek' mezője. rules: szabalyok_<év>.json. Visszaad egy szótárat (lásd a modul leírását)."""
    jovedelem, adoalap = D(str(jovedelem)), D(str(adoalap))
    kulcs = D(str(rules["szja_kulcs"]))
    ered = {"ev": ev, "szamolhato": True, "tetelek": [], "nem_szamolhato": [], "megjegyzesek": [],
            "adoalap_elotte": int(rnd(adoalap)), "szja_kedvezmeny_nelkul": int(rnd(adoalap * kulcs)),
            "adoalap_utana": None, "szja_kedvezmennyel": None, "megtakaritas": None}
    for k, nev in NEM_TAMOGATOTT.items():
        if kedv.get(k):
            ered["nem_szamolhato"].append(f"{nev}: nincs implementálva (a szöveget nem olvastuk ki)")
    valasztott = [k for k in SORREND if kedv.get(k)]
    if len([k for k in ANYA_VALASZTHATO if kedv.get(k)]) > 1:
        ered["nem_szamolhato"].append("Több, egymást követően érvényesíthető anyai jogcím van megadva (négy+/három/két gyermek): a 29/H. § (2) szerint az év egészére egy jogcímet kell választani; "
                                      "hagyd meg a config-ban csak a választottat (a döntés a tiéd, a törvény az év első napján érvényesíthető kedvezményt írja elő).")
        valasztott = [k for k in valasztott if k not in ANYA_VALASZTHATO]
    szamitott = {}
    for k in valasztott:
        adat = kedv[k]
        try:
            if adat is True or not isinstance(adat, dict):
                raise ValueError(f"{NEV[k]}: csak igen/nem jelzés van megadva; kell a részletes adat (jogosultsági hónapok stb.): lásd kedvezmenyek.py --pelda")
            if k == "csaladi":
                ossz, leir = _csaladi(adat, rules)
            else:
                h = _honapok(adat.get("honapok"), NEV[k])
                n = len(h)
                if k in ("harmincalatti_anya", "negy_vagy_tobb_anya", "harom_anya", "ketto_anya"):
                    ossz = jovedelem * n / 12
                    leir = [f"{n} jogosultsági hónap: az átalányban megállapított jövedelem ({int(rnd(jovedelem))} Ft) jogosultsági hónapokkal arányos része (törvény: ha másként nem állapítható meg, az éves jövedelem hónapokkal arányos része)"]
                elif k == "huszonot_ev_alatti":
                    atl = rules.get("brutto_atlagkereset_elozo_julius")
                    if atl is None:
                        raise ValueError("25 év alatti fiatalok kedvezménye: a plafonhoz (jogosultsági hónapok × a tárgyévet megelőző év júliusára közzétett nemzetgazdasági bruttó átlagkereset) "
                                         f"kell a KSH-érték: töltsd ki a config/szabalyok_{ev}.json 'brutto_atlagkereset_elozo_julius' mezőjét (a KSH közleményéből; nem találom ki)")
                    plafon = n * D(str(atl))
                    arany = jovedelem * n / 12
                    ossz = min(arany, plafon)
                    leir = [f"{n} jogosultsági hónap: jövedelem arányos része {int(rnd(arany))} Ft, plafon {n} × {int(D(str(atl)))} Ft = {int(plafon)} Ft; a kisebbik számít"]
                elif k == "szemelyi":
                    havi = (D(str(rules["minimalber_havi"])) / 3 / 100).quantize(D(1), rounding=ROUND_HALF_UP) * 100
                    ossz = n * havi
                    leir = [f"{n} jogosultsági hónap × {int(havi)} Ft (a minimálbér egyharmada, 100 forintra kerekítve)"]
                elif k == "elso_hazasok":
                    ar, mx = D(str(rules["elso_hazasok_havi"])), int(rules["elso_hazasok_max_honap"])
                    eddig = int(adat.get("eddig_felhasznalt_honapok", 0))
                    if eddig + n > mx:
                        raise ValueError(f"első házasok kedvezménye: legfeljebb {mx} hónap vehető igénybe (29/C. § (4)); az eddig felhasznált {eddig} + az idei {n} hónap több")
                    resz = _resz(adat, NEV[k])
                    ossz = n * ar * resz
                    leir = [f"{n} jogosultsági hónap × {int(ar)} Ft × a te részed ({resz}); eddig felhasznált hónap: {eddig} / {mx}"]
            szamitott[k] = (max(D(0), D(ossz)), leir)
        except (ValueError, KeyError, TypeError) as e:
            ered["nem_szamolhato"].append(str(e))
    if ered["nem_szamolhato"]:
        ered["szamolhato"] = False
    # sorrendben csökkentjük az adóalapot (29/H. § (1)); egy kedvezmény csak az éppen megmaradt adóalapig alkalmazható
    maradt = adoalap
    for k in SORREND:
        if k not in szamitott:
            continue
        ossz, leir = szamitott[k]
        alk = min(ossz, maradt)
        maradt -= alk
        ered["tetelek"].append({"jogcim": k, "nev": NEV[k], "torvenyi_hely": HELY[k], "szamitott_kedvezmeny": int(rnd(ossz)), "alkalmazott": int(rnd(alk)),
                                "fel_nem_hasznalt": int(rnd(ossz - alk)), "leiras": leir})
    if ered["szamolhato"]:
        ered["adoalap_utana"] = int(rnd(maradt))
        ered["szja_kedvezmennyel"] = int(rnd(maradt * kulcs))
        ered["megtakaritas"] = ered["szja_kedvezmeny_nelkul"] - ered["szja_kedvezmennyel"]
    ered["megjegyzesek"] += [
        "A kedvezmény az éves adóra (bevallás) vonatkozik, az eddigi bevételből számolt jövedelemmel; az év további bevétele a keretet felhasználhatja. A negyedéves előleg számítása nem változik.",
        "A feltételek (jogosultság, nyilatkozat az adóbevallásban, adóazonosító jelek) teljesülését a repó nem ellenőrzi; a megadott hónapokat a megadás szerint fogadja el.",
        "A 89%-os szabály (Szja tv. 29. §, 47. § (5)) alkalmazhatósága nyitott kérdés: az adóalap (és így a kedvezmény hatása) emiatt eltérhet; lásd a figyelmeztetéseket.",
    ]
    return ered


PELDA = {
    "nincs": False,
    "ketto_anya": {"honapok": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]},
    "csaladi": {"honapok": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "eltartottak": 2, "kedvezmenyezett_eltartottak": 2,
                "tartosan_beteg_vagy_sulyosan_fogyatekos": 0, "sajat_resz": 1, "csaladi_jarulekkedvezmeny_ft": 0},
    "szemelyi": {"honapok": [1, 2, 3]},
    "elso_hazasok": {"honapok": [1, 2, 3, 4, 5, 6], "sajat_resz": 0.5, "eddig_felhasznalt_honapok": 0},
    "huszonot_ev_alatti": {"honapok": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]},
    "_megjegyzes": "Csak azokat a jogcímeket hagyd meg, amelyekre jogosult vagy; a többit töröld. Hónapok: a jogosultsági hónapok az adóévben (1–12). "
                   "Anyák kedvezményei közül (négy+: 'negy_vagy_tobb_anya', három: 'harom_anya', két: 'ketto_anya', 30 év alatti: 'harmincalatti_anya') a négy+/három/két gyermekes közül csak egy lehet. "
                   "A 'sajat_resz' a házastársak/jogosultak döntése szerinti, általad érvényesített hányad (1 = az egész)."
}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--pelda" in sys.argv:
        print(json.dumps({"kedvezmenyek": PELDA}, ensure_ascii=False, indent=2))
    else:
        print(__doc__)
