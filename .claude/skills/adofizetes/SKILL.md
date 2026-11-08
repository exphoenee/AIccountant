---
name: adofizetes
description: A NAV adószámla (tételes XML) feldolgozása és jelentés arról, mennyi adót fizettem be eddig adónemenként (szja, szocho, tb-járulék, áfa), mennyi az egyenleg, és határidőre fedezett volt-e. Használd, ha új NAV-kivonat került az input/nav-egyenleg/ mappába, vagy ha a befizetésekre kérdeznek.
---

# Adófizetés – befizetések a NAV adószámla alapján

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Mit csinál

A `scripts/nav_egyenleg.py`:

1. feldolgozza az `input/nav-egyenleg/*.xml` fájlokat (NAV „Adónem tételes" adószámla-export),
2. az eredményt a `data/nav-egyenleg/nav_egyenleg_<lekérdezés>.json` fájlba menti (az adózó neve, címe, azonosítója és a számlajelzők nélkül),
3. **csak sikeres feldolgozás után** áthelyezi az XML-t az `archive/nav-egyenleg/` mappába,
4. jelentést készít: adónemenként befizetések, kiutalások, előírások, a tételekből számított egyenleg, és határidőnként, hogy a befizetés időben fedezte-e az esedékes összeget. A jelentést menti: `data/nav-egyenleg/jelentes_<lekérdezés>.json`.

## Futtatás

```
python -I .claude/skills/adofizetes/scripts/nav_egyenleg.py             # új XML feldolgozása + jelentés
python -I .claude/skills/adofizetes/scripts/nav_egyenleg.py --jelentes  # csak jelentés a már feldolgozott adatból
```

## NAV-bevallások és kivonatok PDF-ben (duplikáció nélkül)

Az `input/nav-egyenleg/` mappába PDF-ek is kerülhetnek (2658, 25SZJA, 25EGYSZA, helyi adó kivonat). Ezeket a `scripts/bevallasok.py` dolgozza fel: a **típust és az időszakot a szövegből** állapítja meg, és a nyilvántartással (`data/nav-egyenleg/bevallasok.json`, a könyvelői iratokból előtöltve) összeveti. Azonos típus + időszak + azonos tartalom/kulcsadat = **duplikátum**: nem dolgozza fel újra, az `archive/nav-egyenleg/duplikatumok/` mappába kerül. Azonos időszak, **eltérő** kulcsadat (TBJ/SZOCHO összeg) = ellentmondás: a fájl az `input/`-ban marad, a script 3-as kódal megáll, és **a felhasználótól kérdezni kell**. Új irat az `archive/vallalkozas-iratok/04-adozas/` alá, Markdown a `data/vallalkozas/iratok-md/` alá kerül.

```
python -I .claude/skills/adofizetes/scripts/bevallasok.py
```

## Szabályok ehhez a skillhez

1. A befizetési összegeket **kizárólag a script kimenetéből** idézd. Az XML-t ne olvasd ki és ne összegezd kézzel.
2. A kimenetben szereplő „Megjegyzések (nem ellenőrzött pontok)" részt add át a felhasználónak: az egyenleg a tételek összege (a NAV nem közöl összesített egyenleget), az „A" jelzés pontos jelentése nem ellenőrzött, az szja-előleg nem biztos, hogy előírásként megjelenik.
3. Ha a kivonat >1 napos, mondd ki, hogy azóta történt befizetések nem szerepelnek benne; új kivonatot a felhasználó tud másolni az `input/nav-egyenleg/` mappába.
4. Ha a script hibát ír (nem NAV-export, ismeretlen formátum), a fájl az `input/`-ban marad. Idézd a hibát; ne javítsd az XML-t, ne pótolj adatot.
5. Archivált XML-t törölni vagy átnevezni csak a felhasználó kérésére szabad.
6. Az „adófizetési kötelezettség vs. befizetés" összevetéshez az `adoellenorzes` skillt használd.
- **Azonosító-ellenőrzés:** a NAV-kivonat (XML) és a bevallások (PDF) a vállalkozás adószáma/adóazonosítója szerint ellenőrződnek; másik adózó dokumentumánál a script megáll, a fájl az `input/`-ban marad, és utasítást ad.
