---
name: adoellenorzes
description: Összeveti a kiállított számlákból számított adókötelezettséget a NAV adószámlával és az adónaptár határidőivel; jelzi az elmaradást, eltérést, a közelgő határidőket, és kiszámolja a következő adófizetési kötelezettséget. Használd rendszeres ellenőrzéshez, "mi a helyzet az adóimmal", "van-e elmaradás", "mennyit kell legközelebb fizetni" kérdésekre.
---

# Adó-ellenőrzés (revision)

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket. Figyelmeztetési szintek (🔴/🟡/🟢): [`hataridok.md`](../../rules/hataridok.md).

## Mit csinál

Az `scripts/adoellenorzes.py` **először a többi skill scriptjével beszerzi a friss adatot**, és csak utána ellenőriz:

| Lépés | Skill | Mit tesz |
|---|---|---|
| 1 | `szamlak` | Billingo számlák és bejövő számlák (kiadások) lekérése az év elejétől az év végéig. Ha nem sikerül (hálózat, kulcs), a meglévő adattal dolgozik, és ezt 🔴-vel kiírja. |
| 2 | `adonaptar` | Új naptárfájl feldolgozása az `input/adonaptar/` mappából, ha van. |
| 3 | `adofizetes` | Új NAV-kivonat feldolgozása az `input/nav-egyenleg/` mappából, ha van. A NAV-kivonatot **a felhasználó tölti le és másolja be**, a script nem tudja lekérni; ha nincs új, a legutóbbit használja és kiírja a korát. |
| 4 | `adoszamitas` | Kötelezettség kiszámítása a friss adatból. |

Majd a mentett `data/` fájlokból összeveti:

1. **Lejárt határidők:** számított kötelezettség vs. NAV előírás (tbj, szocho) és a határidőre befizetett összeg; szja-előlegnél a számított göngyölt összeg vs. az adószámlán lévő jóváírás. Állapot: ✅ rendben, ✅? rendben, de a NAV általi elszámolás nem ellenőrizhető, 🔴 elmaradás/eltérés, ❓ nem számolható/nem ellenőrizhető.
2. **Közelgő határidők** a következő 60 napban, 🔴 ≤7 nap, 🟡 8–30 nap, 🟢 fölötte.
3. **Következő adófizetési kötelezettség:** a következő negyedéves határidő, a számított összeg, az adószámlán ma lévő jóváírás és a még fedezetlen rész.
4. Kintlévő számlák, bevételi határ és adómentes keret kihasználtsága.

5. **Könyvelői ellenőrzés** (`konyvelo-dokumentumok` skill, `--ellenoriz`): lezárt negyedévenként a könyvelő által számolt adó adónemenként (SZJA, TBJ, SZOCHO) a számított értékkel; a bevallások (2658) időbelisége (irat megléte, nyomtatás dátuma, a NAV adószámlán a negyedéves bevallási előírás). Az új könyvelői iratokat előbb fel kell dolgoztatni (`--feldolgoz`, `usage.md`); ha nincs feldolgozott irat, ez a rész kimarad, és ezt kiírja.

Kimenet: képernyő + `data/szamitas/ellenorzes_<év>.json` + `data/konyvelo/ellenorzes_<év>.json`.

**Minden futás végén** a script meghívja az `adoreport` skillt, amely a friss adatokból elkészíti a `tax-reports/adoreport_<év>.html` fájlt (bevétel, kiadás, adó diagramok és a határidők állapota). A futás utolsó sora a report útvonala; ha nem sikerült, 🔴-vel kiírja.

## Futtatás

```
python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py                    # előbb frissít, aztán ellenőriz
python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py --nincs-frissites  # frissítés nélkül (offline / teszt)
```

A frissítés a `.env`-ben lévő `BILLING_API_KEY`-t használja (a script olvassa, te ne). A `--nincs-frissites` kapcsolót csak a felhasználó kérésére vagy teszteléshez használd.

## Kapu: előbb a vállalkozás feldolgozott adatai

**Az `adoellenorzes` addig nem dolgozik**, amíg a memóriában nincs feldolgozott vállalkozói profil (`.claude/memory/vallalkozasi-profil.md`, legalább 1 igazolt tény). Hiányában a script leáll (kilépési kód 2) és kiírja a teendőt. A profilt a [`vallalkozas-dokumentumok`](../vallalkozas-dokumentumok/SKILL.md) skill készíti el (`--leltar`, `--konvertal`, `--terv`, `--vegrehajt`, `--profil`). **Ne kerüld meg a kaput**, és ne készíts profilt kézzel; ha hiányzik, mondd meg a felhasználónak, hogy előbb dolgoztassa fel a vállalkozás iratait (`usage.md`).

**Adóév:** a script az adóévet első argumentumként fogadja (`adoellenorzes.py 2026`); ha nincs megadva, az aktuális év. Mindig lekéri az előző év számláit is (a tavaly kiállított, idén kifizetett számla az idei év bevétele, Szja tv. 9. § (2) a)).

## Hogyan válaszolj

1. Futtasd a scriptet (alapból frissít). Az „Adatfrissítés" blokkot add át: mi frissült, mi nem, és ha a NAV-kivonat nem friss, kérd meg a felhasználót, hogy töltsön le újat az `input/nav-egyenleg/` mappába.
2. A válaszban a script kimenetét foglald össze: előbb a 🔴 tételeket, aztán a ≤30 napos határidőket, aztán a következő kötelezettséget. **Minden szám a kimenetből jöjjön**, te nem számolsz.
3. Az „NEM SZÁMOLHATÓ" és „nem ellenőrizhető" sorokat add át nyersen, és nevezd meg a hiányzó adatot (pl. `tb_statusz` a `config/vallalkozas.json`-ban). Ne tölts ki értéket helyette.
4. Eltérésnél (számított ≠ NAV) csak a számokat közöld; az okot csak akkor, ha a kimenet bizonyítja. Különben: „az okát nem tudom megállapítani".
5. Mindig jelezd a „Nem ellenőrzött / ismert korlátok" listát, különösen: devizaárfolyam, a Billingo dátumszűrő, a folyamatban lévő negyedév nem végleges, az IPA/kamarai tételek nem ellenőrizhetők.
6. A válasz végén add meg a report útvonalát (`tax-reports/adoreport_<év>.html`), és mondd el, hogy a report ugyanazokból a script-kimenetekből készült.
7. Ha a felhasználó döntést vagy jogértelmezést kér, a válasz: egyeztessen a könyvelővel vagy a NAV-val.

## Feldolgozatlan bemeneti fájlok

A futás végén az `adoellenorzes` megnézi az `input/` mappákat (a vállalkozói iratok mappáját kivéve): ami ott feldolgozás után is megmaradt, azt mappánként, típus szerint kiírja („Feldolgozatlan fájlok az input/ alatt”), a `data/szamitas/ellenorzes_<év>.json` `feldolgozatlan_input` mezőbe menti, és a report Tennivalói között jelzi. Az ok a megfelelő skill üzenetében van (azonosító-eltérés, ismeretlen irattípus, ellentmondás, nem támogatott formátum). A skillek az almappákat is feldolgozzák (`.claude/scripts/bemenet.py`).
