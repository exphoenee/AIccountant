#!/usr/bin/env python3
"""A nyitott jogi kérdések nyilvántartása: mit kezel a repó jelenleg, mi a törvényi hely, kinek kell döntenie, és mi a rögzített döntés.

Az adoszamitas.py hívja; önállóan is használható:
    python -I .claude/skills/adoszamitas/scripts/jogi_kerdesek.py --lista
    python -I .claude/skills/adoszamitas/scripts/jogi_kerdesek.py --kerdeslista           # data/szamitas/konyvelo_kerdeslista.md (a könyvelőnek vihető lista)
    python -I .claude/skills/adoszamitas/scripts/jogi_kerdesek.py --rogzit ID ERTEK [--ki "könyvelő"] [--forras "irat/e-mail megnevezése"] [--megjegyzes "..."]
        ERTEK: jelenlegi_kezeles_elfogadva (a repó mostani kezelése a helyes) | mas (más a helyes: a számítás ezt NEM tudja, NEM SZÁMOLHATÓ jelzést ad)

A döntések a config/konyvelo-dontesek.json-ban vannak (személyes beállítás, nincs verziókezelve). A repó a kérdést nem dönti el: a döntés a könyvelőé / a NAV-é;
a script csak rögzíti, és a kimenetben az érintett számnál jelzi az állapotot (nincs-becsles.md). Egyes kérdések állapota a vallalkozas.json-ból jön
(min_alap_tipus_megerositve, ipa_tetelesen_bejelentve).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FAJL = ROOT / "config" / "konyvelo-dontesek.json"
KIMENET = ROOT / "data" / "szamitas" / "konyvelo_kerdeslista.md"

KERDESEK = [
    {"id": "89_szazalek", "kerdes": "Az átalányadózó egyéni vállalkozó átalányban megállapított jövedelmének 89%-át kell-e összevont adóalapként figyelembe venni, ha szocho-fizetésre kötelezett?",
     "hely": "Szja tv. 29. § (2. mondat), 47. § (5) (a letöltött szöveg szerint a 89% a szocho-köteles jövedelemre vonatkozik; a NAV 2026-os számpéldája nem alkalmazza)",
     "jelenlegi": "nem alkalmazzuk (a NAV számpéldájával egyezően)", "kinek": "könyvelő / NAV", "hatas": "az szja összege és a kedvezmények hatása"},
    {"id": "min_alap_tipus", "kerdes": "A járulékalap minimuma a minimálbér vagy a garantált bérminimum (a főtevékenység legalább középfokú végzettséget/szakképzettséget igényel-e)?",
     "hely": "Tbj. 3. § 14.2.; Szocho tv. 6. § (3)", "jelenlegi": "a config/vallalkozas.json min_alap_tipus értéke; az alternatív érték különbségét a számítás kiírja",
     "kinek": "könyvelő / NAV", "hatas": "a tbj és a szocho összege; már beadott bevallások helyesbítése", "allapot_cfg": "min_alap_tipus_megerositve"},
    {"id": "idoaranyos_nevezo", "kerdes": "Az időarányos bevételi határnál (és az IPA tételes adóalapnál) az arányosítás nevezője a naptári napok száma (365) vagy más?",
     "hely": "Szja tv. 50. § (8); Htv. 39/A. § (2) (a törvény a nevezőt nem mondja ki)", "jelenlegi": "naptári napok / az adóév napjai", "kinek": "könyvelő", "hatas": "a bevételi határ és az IPA tételes adóalap"},
    {"id": "szunetelesi_jarulek", "kerdes": "Fennáll-e a járulékfizetési jogalap a szünetelés alatt (a szünetelő napokra kell-e minimális alap)?",
     "hely": "Szocho tv. 6. § (3) (a jogállás fennállásának napjaira)", "jelenlegi": "a szünetelő napok kimaradnak a töredékhónapos minimális alapból", "kinek": "könyvelő / NAV", "hatas": "tbj és szocho minimális alapja"},
    {"id": "toredek_honap_napjai", "kerdes": "A töredékhónap napjainak száma egyezik-e a könyvelő számításával (a jogállás tényleges kezdete/vége)?",
     "hely": "Szocho tv. 6. § (3); NAV tájékoztató 2026.02.20.", "jelenlegi": "naptári napok × a járulékalap harmincad része", "kinek": "könyvelő", "hatas": "a negyedéves tbj/szocho"},
    {"id": "bevetel_idopont_atutalas", "kerdes": "A bevétel megszerzésének napja a Billingo paid_date (a jóváírás napja) akkor is, ha a kifizető átutalta a díjat?",
     "hely": "Szja tv. 9. § (2) a)", "jelenlegi": "a Billingo paid_date", "kinek": "könyvelő", "hatas": "melyik évre és negyedévre esik a bevétel"},
    {"id": "devizaarfolyam", "kerdes": "Külföldi vevős, alanyi adómentes ügyletnél a forintosításhoz a számlán alkalmazott árfolyam vagy az MNB-árfolyam az irányadó?",
     "hely": "Szja tv. 6. § (2a) a), (4) b)", "jelenlegi": "a számlán alkalmazott árfolyam (Billingo net_amount_local)", "kinek": "könyvelő", "hatas": "a devizás számlák forintösszege"},
    {"id": "osszesito_nyilatkozat", "kerdes": "Kell-e összesítő nyilatkozatot benyújtani az uniós (37. § szerinti) szolgáltatásnyújtásról, és milyen gyakorisággal (havi vagy negyedéves)?",
     "hely": "Áfa tv. 4/A. melléklet I. 1. e), I. 2. (határidő: a tárgyhót/tárgynegyedévet követő hónap 20. napja); a vonatkozás az áfa-státusztól függ",
     "jelenlegi": "nem kezeljük; a report Tennivalókban jelzi", "kinek": "könyvelő / NAV", "hatas": "bevallási kötelezettség és mulasztási bírság"},
    {"id": "tetelesipa_bejelentes", "kerdes": "Bejelentették-e a tételes iparűzési adóalap választását az adóév 5. hónapjának végéig (új tevékenységnél a bejelentkezési nyomtatványon)?",
     "hely": "Htv. 39/A. § (4)", "jelenlegi": "a számítás tételes adóalapot tételez fel, ha az ipa_adozasi_mod így van beállítva", "kinek": "te (a bejelentés igazolása) / könyvelő",
     "hatas": "az IPA összege (hagyományos adóalap lehet az érvényes)", "allapot_cfg": "ipa_tetelesen_bejelentve"},
]


def _betolt():
    try:
        return json.loads(FAJL.read_text(encoding="utf-8")) if FAJL.exists() else {}
    except ValueError:
        return {}


def allapotok(cfg=None):
    """Kérdésenként: állapot ('nyitott' | 'elfogadva' | 'mas') és a döntés adatai. cfg: a config/vallalkozas.json tartalma (egyes állapotok onnan jönnek)."""
    dont = _betolt()
    ki = []
    for k in KERDESEK:
        d = dont.get(k["id"]) or {}
        a = "nyitott"
        if k.get("allapot_cfg"):
            v = (cfg or {}).get(k["allapot_cfg"])
            a = "elfogadva" if v is True else ("mas" if v is False and k["id"] == "tetelesipa_bejelentes" else "nyitott")
        elif d.get("dontes") == "jelenlegi_kezeles_elfogadva":
            a = "elfogadva"
        elif d.get("dontes") == "mas":
            a = "mas"
        ki.append({**{x: k[x] for x in ("id", "kerdes", "hely", "jelenlegi", "kinek", "hatas")}, "allapot": a,
                   "dontes_adatai": {x: d.get(x) for x in ("ki_dontott", "datum", "forras", "megjegyzes")} if d else None})
    return ki


def kerdeslista_md(all_, ma=None):
    ma = ma or date.today().isoformat()
    nyitott = [x for x in all_ if x["allapot"] != "elfogadva"]
    L = [f"# Kérdéslista a könyvelőnek / a NAV-nak ({ma})", "",
         "Generált fájl (`jogi_kerdesek.py --kerdeslista`), kézzel ne szerkeszd. Minden pontnál a törvényi hely és az, hogy a repó jelenleg mit tesz. "
         "A döntést a könyvelő vagy a NAV adja; rögzítés: `python -I .claude/skills/adoszamitas/scripts/jogi_kerdesek.py --rogzit ID ERTEK`.", "",
         f"Nyitott vagy nem elfogadott: **{len(nyitott)}** / {len(all_)}.", ""]
    for i, x in enumerate(nyitott, 1):
        L += [f"## {i}. {x['kerdes']}", "", f"- **Törvényi hely:** {x['hely']}", f"- **A repó jelenlegi kezelése:** {x['jelenlegi']}",
              f"- **Mire hat:** {x['hatas']}", f"- **Kinek a döntése:** {x['kinek']}",
              f"- **Állapot:** {'más kezelés kell (a számítás ezt nem tudja)' if x['allapot'] == 'mas' else 'nincs döntés'}", f"- **Azonosító a rögzítéshez:** `{x['id']}`", ""]
    if not nyitott:
        L.append("Minden kérdésnél rögzített döntés van.")
    return "\n".join(L) + "\n"


def ment_kerdeslista(cfg=None):
    KIMENET.parent.mkdir(parents=True, exist_ok=True)
    KIMENET.write_text(kerdeslista_md(allapotok(cfg)), encoding="utf-8", newline="\n")
    return KIMENET


def rogzit(az, ertek, ki=None, forras=None, megjegyzes=None):
    ids = {k["id"] for k in KERDESEK}
    if az not in ids:
        sys.exit(f"HIBA: ismeretlen kérdés-azonosító: {az}. Lehetséges: {', '.join(sorted(ids))}")
    k = next(x for x in KERDESEK if x["id"] == az)
    if k.get("allapot_cfg"):
        sys.exit(f"HIBA: a(z) {az} állapota a config/vallalkozas.json '{k['allapot_cfg']}' mezőjéből jön; ott kell beállítani (igaz/hamis).")
    if ertek not in ("jelenlegi_kezeles_elfogadva", "mas"):
        sys.exit("HIBA: az érték 'jelenlegi_kezeles_elfogadva' vagy 'mas' lehet.")
    d = _betolt()
    d[az] = {"dontes": ertek, "ki_dontott": ki, "datum": date.today().isoformat(), "forras": forras, "megjegyzes": megjegyzes}
    FAJL.parent.mkdir(parents=True, exist_ok=True)
    FAJL.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rögzítve: {az} = {ertek}" + ("" if ki else " (figyelem: nincs megadva, ki döntött: --ki)"))
    if ertek == "mas":
        print("A számítás a 'más' kezelést nem tudja végrehajtani: az érintett szám NEM SZÁMOLHATÓ jelzést kap, amíg a kód nem készül el hozzá.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Nyitott jogi kérdések.")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--kerdeslista", action="store_true")
    ap.add_argument("--rogzit", nargs=2, metavar=("ID", "ERTEK"))
    ap.add_argument("--ki")
    ap.add_argument("--forras")
    ap.add_argument("--megjegyzes")
    a = ap.parse_args()
    cfgp = ROOT / "config" / "vallalkozas.json"
    cfg = json.loads(cfgp.read_text(encoding="utf-8")) if cfgp.exists() else {}
    if a.rogzit:
        rogzit(a.rogzit[0], a.rogzit[1], a.ki, a.forras, a.megjegyzes)
    if a.kerdeslista:
        print("Mentve:", ment_kerdeslista(cfg).relative_to(ROOT))
    if a.lista or not (a.rogzit or a.kerdeslista):
        for x in allapotok(cfg):
            print(f"{'✅' if x['allapot'] == 'elfogadva' else '🔴' if x['allapot'] == 'mas' else '❓'} {x['id']}: {x['allapot']}  [{x['kinek']}]  {x['hely']}")


if __name__ == "__main__":
    main()
