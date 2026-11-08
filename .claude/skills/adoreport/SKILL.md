---
name: adoreport
description: Önálló, modern HTML adóreportot készít a feldolgozott adatokból (bevétel, kiadás, adó, határidők) Chart.js diagramokkal, világos/sötét móddal. Az adoellenorzes skill minden futás végén meghívja; külön is használd, ha a reportot újra kell generálni, vagy ha a report kinézetét kell módosítani.
---

# Adóreport (HTML, Chart.js)

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Tennivalók felülvizsgálata minden generáláskor

A Tennivalók listát a script **minden generáláskor újraépíti** a beállításokból, a feldolgozott adatokból és a törvénytárból (pl. a hiányzó törvényi melléklet pont csak addig él, amíg a melléklet szövege tényleg hiányzik; a számlák megfelelőségi pontja csak akkor, ha van megállapítás; a korábbi évi számlák pontja csak akkor, ha a vállalkozás nem szünetelt). Minden tétel stabil azonosítót kap; a script összeveti az előző generálással (`data/szamitas/tennivalok_<év>.json`), és kiírja, mennyi **megoldódott** és mennyi az **új**. Egy pont lezárása: `python -I .claude/skills/adoreport/scripts/adoreport.py --lezar ID` (a `config/vallalkozas.json` `tisztazott_tennivalok` listájába kerül; a lezárt pontok külön kibontható listában maradnak).

## Mit csinál

A `scripts/adoreport.py` a `data/` alatti, már kiszámolt adatokból egyetlen önálló HTML fájlt ír: `tax-reports/adoreport_<év>.html` (felülírja az előzőt). A Python csak csoportosít (hónap, ügyfél, negyedév) és JSON-ban átadja az adatot; **a diagramokat a böngészőben a beágyazott Chart.js rajzolja**, nem a Python.

| Fájl | Szerep |
|---|---|
| `scripts/adoreport.py` | adatösszeállítás + HTML váz, az assetek beágyazása |
| `assets/report.css` | stílus (tokenek, világos/sötét, hero-belépő, hover-réteg) |
| `assets/report.js` | Chart.js diagramok, téma-kapcsoló, a hero számlálója |
| `assets/chart.umd.js` | Chart.js v4.4.7 (MIT), a letöltés adatai: `assets/chart.umd.js.INFO.txt` |

Nincs külső betöltés (se CDN, se webfont), a fájl offline és privát. Szakaszok:

| Szakasz | Tartalom |
|---|---|
| Hero és áttekintés | állapotsáv, adat-frissesség, hat mutató (a bevétel mutatón egy mini-vonal és egyetlen számláló) |
| Bevételek | havi bevétel + göngyölt bevétel (kombinált diagram, adómentes jövedelemhatár vonallal), két félkör-mérő (időarányos bevételi határ, adómentes keret), ügyfelenkénti fánk |
| Kiadások (PDF számlák is) | bejövő számlák havonta (Billingo `/spendings`), az átalány-költség és a rögzített kiadás összevetése |
| Adó | negyedéves számított szja/tbj/szocho, számított kötelezettség vs. NAV-befizetés, havi NAV-befizetések, következő fizetendő, adószámla-egyenleg |
| Vállalkozás adatai | a hero alatt: jogállás, adózás, főtevékenység, költséghányad, TB-státusz, minimális alap (megerősítettség), folytatás napja, ÁFA-státusz, IPA település és mód (config + profil; személyes azonosító nélkül) |
| Tennivalók (minden generáláskor újraértékelve) | a korábbi „Amit nem ellenőriztem” helyett: két oszlop, mit kell neked kideríteni (könyvelő, NAV, önkormányzat) és mit kell az AI-asszisztensnek megadni vagy futtatni, plusz a korlátok; a pontok a beállításokból és a számításból feltételesen jönnek |
| Könyvelői dokumentumok | a `data/konyvelo/` iratainak összegei (utalandó adók/járulékok, 2658) és a könyvelő számításai a számítottal összevetve adónemenként (SZJA, TBJ, SZOCHO); személyes azonosító és fájlnév nincs benne |
| Beküldött bevallások | a `data/nav-egyenleg/bevallasok.json` nyilvántartása (2658, 25SZJA, 25EGYSZA, kivonat; a duplikátumok száma) és a negyedéves bevallások időbelisége (irat megléte, NAV-előírás a határidő napjára); a beadás napját a report nem állítja |
| A vállalkozás története | a report alján: három fázis (működés, szünetelés, folytatás) és időrend a `data/vallalkozas/profil.json` forrással igazolt tényeiből (a `vallalkozas-dokumentumok` skill állítja elő); a források mappa-szintűek, személyes azonosító nincs benne |
| Határidők | a vállalkozás indulása utáni adónaptári tételek állapottal; az **indulás előtti határidők külön, összecsukva, „nem releváns"-ként** |
| Amit nem ellenőriztem | a számítási és adatforrás-korlátok |

## Futtatás

```
python -I .claude/skills/adoreport/scripts/adoreport.py [--ev 2026]
```

Bemenet: `data/szamitas/adoszamitas_<év>.json` (kötelező), `ellenorzes_<év>.json` (határidő-állapot), `data/nav-egyenleg/`, `data/szamlak/`, `data/kiadasok/`. Frissített adathoz futtasd az `adoellenorzes` skillt: az előbb frissít, számol, ellenőriz, és a végén maga hívja ezt a scriptet.

## Arculat és tervezési elvek

A report a [`design-taste-frontend`](../design-taste-frontend/SKILL.md) skill rendszerelveit követi, adaptálva egy privát adatreportra:

- paletta: „Frost and slate" (`library/palettes.json`), egyetlen akcentszín (teal); egy térköz-skála, egy kártya-recept, egy hajszálvonal, hover: a kártya 2 px-et emelkedik, a sávok halványodnak,
- hero-belépő betöltéskor (soronként, 90 ms-os lépcsővel), egyetlen számláló a bevételen; görgetésre **semmi nem mozog** (nincs scroll-reveal), `prefers-reduced-motion` esetén nincs animáció,
- **mobil nézet:** 960 px alatt a menü egy gombbal nyíló, teljes képernyős lista (a gomb kimondja a nyitott/zárt állapotot, Esc, linkkattintás és szélesítés zárja, 56 px magas sorok); 640 px alatt egy oszlop, a táblázatok vízszintesen görgethetők; oldalirányú görgetés nincs.
- **világos és sötét mód:** a kezdő téma a böngésző színséma-beállításából jön (`prefers-color-scheme`), a jobb felső egyetlen ikon-gomb (hold/nap) váltja világos és sötét között; a választás a `localStorage`-ban (`adoreport-theme`) marad meg, automatikus mód nincs; téma-váltáskor a diagramok újrarajzolódnak az új színekkel; nyomtatáskor mindig világos,
- mondatkezdő nagybetű, 16 px-es szöveg, ikon + szöveg az állapotokhoz (nem csak szín), `skip` link, `lang="hu"`, diagramonként `aria-label` és „Adatok táblázatban" kinyitható táblázat.

A taste-skill többi része (céges weboldal-építés stock fényképekkel, böngészős „gate", szövegellenőrzés) erre a privát adatreportra **nem** vonatkozik. A Geist betűtípust nem töltjük be (külső kérés lenne), rendszerbetűtípus a tartalék.

## Szabályok ehhez a skillhez

1. A script csak összegez és csoportosít; **adót nem számol újra**. Az értékek az `adoszamitas` és `nav_egyenleg` kimeneteiből jönnek.
2. Új diagram: az `adoreport.py` adja a JSON-t és a `<canvas>`-t, a `report.js` a Chart.js beállítást. Minden diagramhoz tartozzon `aria-label`, tooltip és kinyitható adattábla; ha nincs adat, kimondott üres állapot.
3. A Chart.js-t nem frissítjük magunktól: új verzióhoz töltsd le a hivatalos csomagot külön, üres könyvtárba, ellenőrizd (licenc, hálózati hívások), és frissítsd az `INFO.txt`-t (SHA-256).
4. A reportban szereplő ügyfélnevek a Billingo partneradatai: a fájl a `tax-reports/` alatt van, nincs verziókezelve, ne másold külső szolgáltatásba.
5. A kiadások a Billingo `/spendings` végpontjából jönnek; a mezőnevek **nem ellenőrzöttek**, mert jelenleg nincs rögzített bejövő számla. Amint van, ellenőrizd a `data/kiadasok/` mezőit és a „Kiadások" szakaszt.
6. Átalányadózásnál a tényleges kiadás nem csökkenti az adóalapot; a report ezt kimondja, és a kiadást tájékoztató adatként kezeli.
7. A reportban nincs becslés: ami nem számolható, azt a report is „nem számolható"-nak jelöli.
