---
name: szamlak
description: Kimenő számlák beszerzése és egyesítése: Billingo (csak olvasás), Számlázz.hu Számla Agent és az input/bevetelek/ mappába mentett fájlok (PDF, XML, CSV) Markdownná alakítása és feldolgozása; keresztvalidálás, hogy egy számla csak egyszer könyvelődjön; bejövő számlák a Billingóból. Kulcs nélkül a forrást csendben kihagyja. Használd, ha friss számlaadat kell, új számlafájl érkezett, vagy az adószámítás elavult számlaadatot jelez.
---

# Billingo számlák lekérése

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Mit csinál

A `scripts/billingo_szamlak.py` a Billingo API v3-ból (`GET /documents`, csak olvasás) lekéri az időszak számláit, és két fájlt ment a `data/szamlak/` mappába:

- `szamlak_<tol>_<ig>.json` – teljes nyers adat (tételekkel, partnerrel, `summary` forintértékekkel)
- `szamlak_<tol>_<ig>.csv` – összefoglaló (számlaszám, dátumok, fizetési státusz, deviza, árfolyam, nettó/bruttó összeg devizában és HUF-ban)

## Futtatás

```
python -I .claude/skills/szamlak/scripts/billingo_szamlak.py ÉÉÉÉ-HH-NN ÉÉÉÉ-HH-NN
```

Adóévi használathoz mindig az **év elejétől az év végéig** kérd le (pl. `2026-01-01 2026-12-31`), mert az `adoszamitas` skill csak az évet teljesen lefedő fájlt fogadja el.

## Bejövő számlák (kiadások)

A `scripts/billingo_kiadasok.py` a Billingo `/spendings` végpontjából kéri le a bejövő számlákat/kiadásokat, és a `data/kiadasok/kiadasok_<tol>_<ig>.json` fájlba menti (szűrés nélkül, nyers adat):

```
python -I .claude/skills/szamlak/scripts/billingo_kiadasok.py 2026-01-01 2026-12-31
```

Ellenőrizve: a végpont ezzel a kulccsal elérhető. **Nem ellenőrzött:** a dátumszűrő paraméterei és a tételek mezőnevei, mert jelenleg 0 bejövő számla van rögzítve a Billingóban. A szűrést és az értelmezést a `adoreport` végzi, és jelzi, ha mezőt nem talál.

## Számlázz.hu (Számla Agent)

`scripts/szamlazz_szamlak.py TOL IG [--sorozat "ABC-2026-{n}"]`: a `.env` `SZAMLAZZ_API_KEY` kulcsával kérdez (csak olvasás). **Korlát (hivatalos dokumentáció):** a Számla Agent csak **egy számlát** ad vissza számlaszám, rendelésszám vagy külső azonosító alapján, időszak szerinti listázást nem. Ezért a script a számlaszám-sorozatot járja végig (`--sorozat`, vagy `SZAMLAZZ_SOROZAT` a `.env`-ben; `{n}` = sorszám), 5 egymás utáni hiányzó számlánál leáll, és a kelt alapján szűr az időszakra. Típusok: csak az `SZ` (számla) számít bevételnek; stornó külön; előleg-, vég-, helyesbítő, jóváíró számla és díjbekérő **nem kezelt típusként kimarad és jelzett** (a dupla könyvelés elkerülésére). Tömeges exportot a Számlázz.hu felületéről kell kérni, és az `input/bevetelek/` mappába tenni. **Kulcs nélkül a script csendben kilép.** A válasz XML mezőit a [hivatalos leírás](https://docs.szamlazz.hu/agent/querying_xml/response) szerint értelmezi; éles kulccsal még nem futtattam, ezért az első futásnál ellenőrizd a talált számlák számát.

## Bevételi fájlok (`input/bevetelek/`)

`scripts/bevetelek.py --feldolgoz`: a mappába mentett kimenő számlák (PDF Billingo- vagy Számlázz.hu-elrendezésben, Számla Agent XML, CSV) Markdownná alakulnak (`data/szamlak/bevetelek-md/`), kiolvasódnak a számlák (`data/szamlak/bevetelek_szamlak.json`), az eredeti az `archive/bevetelek/<év>/`-ba kerül. Ellenőrzések: a vállalkozás azonosítója szerepel-e (másik vállalkozás dokumentumánál megáll); a PDF eladója a vállalkozás-e (bejövő számla esetén megáll: az `input/kiadasok/` mappába való); nettó + áfa = bruttó; a díjbekérő nem bevétel. A **kifizetés napját** a számla csak akkor tartalmazza, ha feltünteti (pl. „Kiegyenlítve”); különben a számla kintlévőnek számít, amíg nincs igazolt kifizetés. CSV oszlopai: számlaszám, kelt, nettó (+ opcionálisan teljesítés, pénznem, árfolyam, kiegyenlítve), és a fájlban szerepelnie kell az adószámodnak (pl. oszlopként).

## Egyesítés és keresztvalidálás

`scripts/szamlak_egyesites.py` (az `adoellenorzes` minden futáskor meghívja): a három forrásból (`szamlak_*`, `szamlazz_*`, `bevetelek_szamlak`) egyesített, duplikációmentes `data/szamlak/egyesitett_<tol>_<ig>.json`-t ír; **az `adoszamitas` ezt olvassa**. Azonos számlaszám = egy tétel (Billingo > Számlázz.hu > fájl); azonos számlaszám, eltérő kelt/összeg = ellentmondás, a script megáll (5-ös kód); különböző számlaszám, de azonos kelt + nettó + pénznem + partner különböző forráskészletből = gyanús duplikáció, megáll. Önteszt: `scripts/teszt_keresztvalidalas.py`.

## Számlák megfelelősége (Áfa tv.)

`scripts/szamla_ellenorzes.py` (az `adoellenorzes` minden futáskor meghívja): az egyesített kimenő számlákat számlánként ellenőrzi az Áfa tv. szabályai szerint, szabályhivatkozással: kötelező adattartalom (169. §), a vevő adóalanyi minősége és a teljesítési hely (37. §), alanyi adómentesség (187. §), mentesség-jelölés (169. § m), „fordított adózás” kifejezés (169. § n), időszakonkénti elszámolás vagy folyamatos teljesítés (58. §), a kibocsátás határideje (163. § (2) a), devizás számla árfolyama (80. §). A szabályok és korlátok: [`.claude/rules/szamlazas.md`](../../rules/szamlazas.md). Eredmény: `data/szamlak/szamla_ellenorzes.json`, a report Bevételek szakaszában táblázat, a Tennivalókban tétel. A sztornózott számlát kihagyja (a javított számlát ellenőrzi). **A figyelmeztetés nem jogi minősítés**: a számlázóprogram adatait vizsgálja, nem a nyomtatott számlát; a hibás számlát az Áfa tv. 170. § szerinti okirattal kell javítani, a döntés a könyvelőé. Önteszt: `scripts/teszt_szamla_ellenorzes.py`.

## A vállalkozás azonosítása

Minden API-lekérés előtt a script ellenőrzi, hogy a kulcs a vállalkozói profilban rögzített vállalkozáshoz tartozik-e (Billingo: `/organization`; Számlázz.hu: a számla eladójának adószáma). Eltérésnél megáll (4-es kód), és megmondja, melyik kulcsot kell ellenőrizni a `.env`-ben. Azonosító nélkül (`data/vallalkozas/azonosito.json`) nem dolgozik: előbb `vallalkozas-dokumentumok --billingo`.

## Szabályok ehhez a skillhez

1. Az API kulcsok a `.env`-ben vannak (`BILLING_API_KEY`, `SZAMLAZZ_API_KEY`). **Ne olvasd ki, ne írd ki, ne add át paraméterként.** A script maga olvassa.
2. Csak olvasás. Soha ne próbálj számlát létrehozni, módosítani, sztornózni vagy küldeni.
3. A script **nem archivál** (nincs nyers input fájl): az eredmény közvetlenül a `data/szamlak/` alá kerül. Régi lekérést ne törölj a felhasználó kérése nélkül.
4. A számlák fájlból olvasott adataiból **ne számolj te**. Összegzéshez, bevételhez, adóhoz használd az `adoszamitas` skillt.
5. Hiba (401/403, hálózat, érvénytelen dátum) esetén idézd a script hibaüzenetét, ne találgass az okáról.
6. A lekérés után mondd el: hány számla jött, melyik fájlba mentve, és hogy a Billingo szűrője a kiállítás dátumára vonatkozik-e, **nem ellenőrzött** (előző évi kiállítású, idén kifizetett számla hiányozhat).
