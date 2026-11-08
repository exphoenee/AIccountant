---
name: kiadasok-dokumentumok
description: A bejövő (kiadási) számlák PDF-jeinek feldolgozása az input/kiadasok/ mappából: számla és díjbekérő megkülönböztetése, sorszám, kelt, szállító, nettó/áfa/bruttó kiolvasása, duplikáció kiszűrése, archiválás és Markdown. A report Kiadások szakasza ebből is dolgozik. Használd, ha új szállítói számla (pl. Billingo-előfizetés, könyvelői díj) érkezett.
---

# Bejövő számlák (kiadások) PDF-ből

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Mit csinál

`scripts/kiadasok.py --feldolgoz` az `input/kiadasok/` minden PDF-jéből kiolvassa: típus (**számla** vagy **díjbekérő**), sorszám, kelt, teljesítés, fizetési határidő, szállító és adószáma, nettó, ÁFA, bruttó. Ellenőrzi, hogy nettó + ÁFA = bruttó, különben az irat az `input/`-ban marad.

- **Díjbekérő ≠ számla.** A díjbekérő nem kiadás, nem számít bele az összegekbe. Ha a számla hivatkozik rá („… díjbekérő alapján”), a két irat összekapcsolódik, hogy ne számolódjon duplán.
- **Duplikáció:** azonos típus + sorszám + kelt + összeg = duplikátum, nem dolgozza fel újra (`archive/kiadasok/duplikatumok/`). Azonos sorszám, eltérő kelt vagy összeg = ellentmondás: az irat az `input/`-ban marad, 3-as kilépési kód, **kérdezd meg a felhasználót**.
- Eredmény: `data/kiadasok/pdf_kiadasok.json`; eredeti PDF: `archive/kiadasok/<év>/`; Markdown: `data/kiadasok/md/`.

## Futtatás

```
python -I .claude/skills/kiadasok-dokumentumok/scripts/kiadasok.py --feldolgoz
python -I .claude/skills/kiadasok-dokumentumok/scripts/kiadasok.py --lista 2026
```

Az `adoreport` a Kiadások szakaszban a Billingo bejövő számlái mellett ezeket is megjeleníti (havi diagram a számla kelte szerinti bruttó összegből, és táblázat).

## Szabályok ehhez a skillhez

1. Az összeget a script olvassa ki, az AI nem. Ha a kiolvasás nem sikerül, az irat marad, és a felhasználót kell kérdezni.
2. **Átalányadózónál a tényleges költség az adót nem csökkenti** (a költséghányad az átalány); a kiadások tájékoztató jellegűek. Ne állítsd, hogy csökkentik az szja-t vagy a járulékot.
3. **ÁFA:** a számla ÁFA-t tartalmazhat. Alanyi adómentes vállalkozónál az ÁFA nem levonható; a vállalkozó ÁFA-státusza a profilban nyitott pont (a Billingo és az iratok eltértek), ezért a levonhatóságot ne állítsd, hanem a könyvelőt kérdezd.
4. A **fizetés napja** a számlából nem látszik (pl. díjbekérő alapján előre fizetett számla); ezt ne találd ki.
5. Személyes azonosítót (a vevő adatai) a report nem jelenít meg; a szállító neve és adószáma üzleti adat.
6. **Azonosító-ellenőrzés:** a számlának a vállalkozásra (vevő) kell szólnia; másik vállalkozás számlájánál a script megáll, az irat az `input/`-ban marad, és utasítást ad.
