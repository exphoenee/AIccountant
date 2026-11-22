---
name: konyvelo-dokumentumok
description: A könyvelőtől kapott iratok (input/konyvelo/: utalandó adók és járulékok, bérösszesítő, 2658-as bevallás PDF-ek) feldolgozása Markdownná és adatkivonattá, majd a könyvelő által számolt adók ellenőrzése adónemenként (SZJA, TBJ, SZOCHO) a számított értékekkel, és a bevallások időbeliségének ellenőrzése. Használd, ha új irat érkezett a könyvelőtől, vagy ha azt kell tudni, jól számolt-e a könyvelő, és elkészültek-e időben a bevallások.
---

# Könyvelői iratok: feldolgozás és ellenőrzés

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Mit csinál

| Lépés | Parancs | Eredmény |
|---|---|---|
| Feldolgozás | `--feldolgoz` | Az `input/konyvelo/` PDF-jeiből Markdown (`data/konyvelo/md/`) és adatkivonat (`data/konyvelo/konyvelo_adatok.json`: adónemenként és időszakonként az összeg, a 2658 nyomtatási dátuma); az eredeti PDF az `archive/konyvelo/` mappába kerül (mozgatás), az `input/konyvelo/` üres lesz |
| Ellenőrzés | `--ellenoriz [ÉV]` | Lezárt negyedévenként: könyvelő összege vs. az `adoszamitas` összege adónemenként (SZJA, TBJ, SZOCHO); a TBJ/SZOCHO összegből levezetett járulékalap; 2658 irat megléte és nyomtatási dátuma a határidőhöz képest; a NAV adószámlán van-e negyedéves bevallási előírás a határidő napjára. Mentés: `data/konyvelo/ellenorzes_<év>.json` |

Az `adoellenorzes` skill minden futáskor meghívja az `--ellenoriz` részt, és a kimenetet a saját kimenetébe fűzi.

## Futtatás

```
python -I .claude/skills/konyvelo-dokumentumok/scripts/konyvelo.py --feldolgoz
python -I .claude/skills/konyvelo-dokumentumok/scripts/konyvelo.py --ellenoriz 2026
python -I .claude/skills/konyvelo-dokumentumok/scripts/konyvelo.py --ujraosztalyoz   # korábban ismeretlen iratok újraosztályozása
```

Felismert irattípusok (a fájlnév alapján): `2658_*.pdf`, `Utalandó adók ÉÉÉÉ.HH.pdf`, `Utalandó járulékok ÉÉÉÉ.Qn.pdf`, `Bérösszesítő ÉÉÉÉ.Qn.pdf`, valamint a havi áfa-iratok: `2665A_*.pdf` (áfabevallás), `26A60_*.pdf` (összesítő nyilatkozat; a 26A60-03 lap az Áfa tv. 37. § (1) szerinti közösségi szolgáltatásnyújtás), `ÁFA lista ÉÉÉÉ.HH.NN-ÉÉÉÉ.HH.NN.pdf` és `Közösségi analitika ÉÉÉÉ.HH.NN-ÉÉÉÉ.HH.NN.pdf` (a könyvelőprogram belső listái, nem NAV-nyomtatványok). Más irat csak Markdownná alakul, kivonat nincs.

**Áfa-iratok:** a script csak az **időszakot** (a nyomtatvány `pdftotext -layout` szövegéből, a listáknál a fájlnévből) és a **nyomtatás napját** olvassa ki; az összegeket **nem** (a számmezők a szövegrétegből nem olvashatók ki megbízhatóan). Az `--ellenoriz` „ÁFA-iratok" szakasza hónaponként megmondja, melyik irat van meg, és hogy a nyomtatás a tárgyhót követő hó 20. napja előtt volt-e (forrás: NAV 26A60 kitöltési útmutató, `torvenytar/docs/NAV/2026/26a60-kitoltesi-utmutato.txt`; a munkaszüneti nap miatti eltolást nem számolja). A nyomtatás napja nem a beadás napja. Hogy a havi bevallás és az összesítő nyilatkozat rád kötelező-e, **nem ellenőrzött** (`afa.md`): könyvelő / NAV. Az `--ujraosztalyoz` az archívumban korábban `ismeretlen`-ként tárolt iratokat osztályozza újra (mozgatás nélkül).

## Szabályok ehhez a skillhez

1. **A script olvassa ki az összegeket**, te nem. Ha a tételek összege nem egyezik az irat „ÖSSZESEN” sorával, a script megáll, és az irat az `input/`-ban marad.
2. **A 2658 nyomtatvány számmezői** a szövegrétegből nem olvashatók ki megbízhatóan (mind 0-nak jönnek), ezért belőle összeget nem veszünk; az összeg az utalandó iratokból jön.
3. **A „Nyomtatva” dátum nem a beadás napja.** A bevallás időbeliségére bizonyíték a NAV adószámla negyedéves bevallási előírása (a megtörténtet igazolja, a beadás napját nem), vagy a NAV beküldési igazolás, amelyet kérni kell a könyvelőtől.
4. **Eltérésnél csak a számokat közöljük**, az okot csak akkor, ha az adatból bizonyítható. A levezetett járulékalap és a naptári napok szám (a minimálbér 1/30-ával) a script levezetése, nem a könyvelő adata.
5. A tevékenység folytatása előtt véget érő negyedévet nem ellenőrizzük (nincs kötelezettség).
6. Személyes azonosító (adószám, név, bankszámla) nem kerül a kivonatba; az `archive/` és `data/` nincs verziókezelve.
7. Jogértelmezési kérdésben (melyik minimális alap, helyesbítő bevallás) a válasz: egyeztess a könyvelővel vagy a NAV-val.
8. **Azonosító-ellenőrzés:** minden irat a vállalkozás adószáma/adóazonosítója szerint ellenőrződik (`.claude/scripts/azonosito.py`); másik vállalkozás irata esetén a script megáll, az irat az `input/`-ban marad, és utasítást ad.

## Bemeneti mappa: almappák is, és a maradék jelzése

Az `input/<mappa>/` **almappáit is feldolgozza** a script (rekurzívan; pl. `input/kiadasok/2026/…`), a kiterjesztés kis/nagybetűtől független (`.pdf` = `.PDF`); a közös segéd: `.claude/scripts/bemenet.py`. A feldolgozás után a kiürült almappák törlődnek. Az `input/` feldolgozás után **üres** kell legyen (`adatkezeles.md`): ami ott marad, az nem dolgozódott fel (azonosító-eltérés, ismeretlen irattípus, ellentmondás, nem támogatott formátum). Ezt az `adoellenorzes` minden futáskor kiírja, és a report Tennivalói között jelzi (`feldolgozatlan_input`).
