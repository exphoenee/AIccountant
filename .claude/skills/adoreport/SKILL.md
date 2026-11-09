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
| Hero és áttekintés | az észrevételek **külön piros buborékokban** (egy észrevétel = egy buborék), adat-frissesség, hat mutató (a bevétel mutatón egy mini-vonal és egyetlen számláló) |
| Bevételek | havi bevétel + göngyölt bevétel (kombinált diagram, adómentes jövedelemhatár vonallal), két félkör-mérő (időarányos bevételi határ, adómentes keret), ügyfelenkénti fánk |
| Kiadások (PDF számlák is) | bejövő számlák havonta (Billingo `/spendings`), az átalány-költség és a rögzített kiadás összevetése |
| Adó | negyedéves számított szja/tbj/szocho, számított kötelezettség vs. NAV-befizetés, havi NAV-befizetések, következő fizetendő, adószámla-egyenleg |
| Vállalkozás adatai | a hero alatt: jogállás, adózás, főtevékenység, költséghányad, TB-státusz, minimális alap (megerősítettség), folytatás napja, ÁFA-státusz, IPA település és mód (config + profil; személyes azonosító nélkül) |
| Tennivalók (minden generáláskor újraértékelve) | a korábbi „Amit nem ellenőriztem” helyett: két oszlop, mit kell neked kideríteni (könyvelő, NAV, önkormányzat) és mit kell az AI-asszisztensnek megadni vagy futtatni, plusz a korlátok; a pontok a beállításokból és a számításból feltételesen jönnek |
| Könyvelői dokumentumok | a `data/konyvelo/` iratainak összegei (utalandó adók/járulékok, 2658) és a könyvelő számításai a számítottal összevetve adónemenként (SZJA, TBJ, SZOCHO); személyes azonosító és fájlnév nincs benne |
| Beküldött bevallások | a `data/nav-egyenleg/bevallasok.json` nyilvántartása (2658, 25SZJA, 25EGYSZA, kivonat; a duplikátumok száma) és a negyedéves bevallások időbelisége (irat megléte, NAV-előírás a határidő napjára); a beadás napját a report nem állítja |
| A vállalkozás története | a report alján: három fázis (működés, szünetelés, folytatás) és időrend a `data/vallalkozas/profil.json` forrással igazolt tényeiből (a `vallalkozas-dokumentumok` skill állítja elő); a források mappa-szintűek, személyes azonosító nincs benne |
| Határidők | a **közelgő** határidők táblázata; a **lejárt határidők alapból zárt, lenyitható blokkban** (fejléc: darabszám és állapot-összegzés); az **indulás előtti határidők külön, összecsukva, „nem releváns"-ként** |
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

## Elrendezési szabályok (a felhasználó kérése szerint)

### Észrevételek a dashboardon: egy észrevétel = egy piros buborék
- A dashboard tetején **nem egyetlen nagy piros sáv** foglalja össze a problémákat, hanem **minden észrevétel külön piros buborékot** kap (`<a class="banner bad">` a `.banners` tárolóban; a CSS-t az `assets/report.css` végén lévő „az észrevételek külön piros buborékok” blokk adja). A buborék a dátumot és a teendőt félkövéren, alatta az üzenetet mutatja, és a Határidők (vagy a Könyvelői dokumentumok) szakaszra ugrik.
- Észrevételnek számít, és saját buborékot kap: (1) minden lejárt, be nem fizetett vagy hiányosan befizetett tétel (`… befizetés: …` üzenet), (2) minden eltérés a számított és a NAV által előírt összeg között (`≠ NAV előírás`; adónemenként külön buborék), (3) minden nem számolható tétel (`NEM SZÁMOLHATÓ`), (4) a könyvelői ellenőrzés minden eltérése (`data/konyvelo/ellenorzes_<év>.json`, `szint: hiba`; negyedévenként és adónemenként külön buborék).
- Az észrevételeket **nem vonjuk össze** egy mondatba, és számot nem számolunk újra: a buborék szövege a `data/szamitas/ellenorzes_<év>.json` és a könyvelői ellenőrzés mentett üzenete. Ha nincs észrevétel, egyetlen semleges ✅ buborék jelenik meg („Nincs lejárt, be nem fizetett tétel…”).
- Az ❓ (nem ellenőrizhető) tételek **nem** piros buborékok; azok a Határidők szakaszban és a Tennivalók között látszanak.

### Határidők: a lejárt tételek lenyitható blokkban
- A Határidők szakasz táblázata csak a **még nem lejárt** határidőket mutatja. A **lejárt határidők** (az indulás előttiek nélkül) egy **alapból zárt** `<details class="dt past">` blokkba kerülnek, amelynek fejléce összegzi őket (pl. „14 lejárt határidő (✅ 4 · ✅? 2 · ❓ 7 · 🔴 1)”), a tábla a blokkban van. A vállalkozás indulása előtti határidők továbbra is külön, saját lenyitható blokkban vannak.
- Ha nincs közelgő határidő, a szakasz ezt kimondja („Nincs közelgő határidő az adónaptárban”), és a lejárt blokk marad. Ha egyáltalán nincs adat, a report az `adoellenorzes` futtatását kéri.
- A fontos (🔴) lejárt tétel a dashboardon buborékként így is látszik, ezért a lenyitható blokk nem rejti el az észrevételt.

## Szabályok ehhez a skillhez

1. A script csak összegez és csoportosít; **adót nem számol újra**. Az értékek az `adoszamitas` és `nav_egyenleg` kimeneteiből jönnek.
2. Új diagram: az `adoreport.py` adja a JSON-t és a `<canvas>`-t, a `report.js` a Chart.js beállítást. Minden diagramhoz tartozzon `aria-label`, tooltip és kinyitható adattábla; ha nincs adat, kimondott üres állapot.
3. A Chart.js-t nem frissítjük magunktól: új verzióhoz töltsd le a hivatalos csomagot külön, üres könyvtárba, ellenőrizd (licenc, hálózati hívások), és frissítsd az `INFO.txt`-t (SHA-256).
4. A reportban szereplő ügyfélnevek a Billingo partneradatai: a fájl a `tax-reports/` alatt van, nincs verziókezelve, ne másold külső szolgáltatásba.
5. A kiadások a Billingo `/spendings` végpontjából jönnek; a mezőnevek **nem ellenőrzöttek**, mert jelenleg nincs rögzített bejövő számla. Amint van, ellenőrizd a `data/kiadasok/` mezőit és a „Kiadások" szakaszt.
6. Átalányadózásnál a tényleges kiadás nem csökkenti az adóalapot; a report ezt kimondja, és a kiadást tájékoztató adatként kezeli.
7. A reportban nincs becslés: ami nem számolható, azt a report is „nem számolható"-nak jelöli.
8. **Az elrendezési szabályok kötelezőek** (lásd fent): az észrevételek külön piros buborékban jelennek meg a dashboardon, a lejárt határidők lenyitható blokkban vannak. Új észrevétel-típusnál (új ellenőrző skill kimenete) is az „egy észrevétel = egy buborék” elvet kell követni, a szöveget a mentett eredményből kell venni.
9. Az `adoreport.py --ev <év>` az **eddig kiszámolt** adatokból újragenerálja a reportot (új ellenőrzés nélkül); az adatok frissítéséhez az `adoellenorzes` kell.
