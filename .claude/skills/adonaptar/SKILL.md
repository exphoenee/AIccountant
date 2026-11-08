---
name: adonaptar
description: Az adónaptár (input/adonaptar/<év>.md) feldolgozása gépi JSON-ná és a .claude/memory/ alatti olvasható kivonattá, illetve a közelgő határidők listázása. Használd, ha új adónaptár fájl került az input/adonaptar/ mappába, vagy ha a határidőkről kérdeznek.
---

# Adónaptár feldolgozása és listázása

## Az adónaptár beszerzése a NAV-ról (az év eleji első lépés)

```
python -I .claude/skills/adonaptar/scripts/nav_adonaptar.py --ev 2026
```

Letölti a NAV általános adónaptárának 12 havi oldalát (`https://nav.gov.hu/fooldal-elemei/fooldali-csempek/adonaptar/altalanos-adonaptar/esmenyek/<év>/<hónap>`), és az átalányadózó egyéni vállalkozóra releváns sorokat (2658/2558 bevallás + befizetés, negyedéves SZJA-előleg, 25SZJA, HIPAK) az `input/adonaptar/<év>.md` fájlba írja a lent leírt formátumban; a tényleges (munkaszüneti nap miatt eltolt) határidőt használja, az eredetit a megjegyzésbe teszi. A kihagyott sorok számát kiírja. **Ami nincs a NAV általános adónaptárában:** a helyi iparűzési adó előlege (önkormányzati: `helyi-ipa` skill), a kamarai hozzájárulás (március 31., Gktv. 34/A. §, a `config/vallalkozas.json` és az `adoszamitas` kezeli), egyedi teendők; a januári határidő a következő év adónaptárában van (az éves oldal csak a naptári évet tartalmazza). A NAV-oldal szerkezetének megváltozásakor a script hibával áll meg és nem ír fájlt. Utána: `python -I .claude/skills/adonaptar/scripts/adonaptar.py` (feldolgozás).

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket. A határidő-értelmezés és a figyelmeztetési szintek: [`.claude/rules/hataridok.md`](../../rules/hataridok.md).

## Mit csinál

A `scripts/adonaptar.py`:

1. beolvassa az `input/adonaptar/<év>.md` táblázatsorait (félkövér dátumú sorok),
2. gépi változatot ír: `data/adonaptar/<év>.json` (határidő, adónem, teendő, megjegyzés, típus, negyedév),
3. olvasható kivonatot ír: `.claude/memory/adonaptar-<év>.md`, és frissíti a `.claude/memory/MEMORY.md` indexet,
4. **csak sikeres feldolgozás után** áthelyezi a forrásfájlt az `archive/adonaptar/` mappába.

## Futtatás

```
python -I .claude/skills/adonaptar/scripts/adonaptar.py                          # új naptárfájl feldolgozása
python -I .claude/skills/adonaptar/scripts/adonaptar.py --lista --napok 60       # következő 60 nap határidői
python -I .claude/skills/adonaptar/scripts/adonaptar.py --lista --ev 2026        # a teljes feldolgozott naptár
```

A fájlnév `ÉÉÉÉ.md` legyen (pl. `2027.md`). A napok kiszámítását (hány nap múlva / mióta lejárt) a script végzi.

## Szabályok ehhez a skillhez

1. Határidőt, dátumot csak a script kimenetéből vagy a `data/adonaptar/<év>.json` fájlból mondj. Memóriából (általános tudásból) soha, még „egyértelmű" dátumnál sem.
2. A hátralévő napokat a script számolja (`--lista`); ne számold fejben.
3. A `.claude/memory/adonaptar-<év>.md` generált fájl: kézzel ne szerkeszd; hiba esetén javítsd az `input/` forrást, és futtasd újra a scriptet.
4. Ha a script „nem találtam egyetlen határidősort sem" vagy oszlopszám-hibát jelez, a fájl az `input/`-ban maradt; idézd a hibát, és kérd a formátum javítását.
5. Új évre új fájl kell (`config/szabalyok_<év>.json` is). Ha az adott évhez nincs feldolgozott naptár, mondd ki: „ehhez az évhez nincs adónaptár".
