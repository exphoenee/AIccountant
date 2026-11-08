---
name: adoszamitas
description: Kiszámolja, mennyi adó (szja előleg, tb-járulék, szocho) keletkezett eddig a kiállított és kifizetett Billingo számlák alapján, negyedéves göngyölítéssel, bevételi határ és adómentes keret kihasználtsággal. Használd, ha az adókötelezettség összegére, a bevételre vagy a limitekre kérdeznek.
---

# Adószámítás a kiállított számlák alapján

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket. A számítás szabályai: [`atalanyado.md`](../../rules/atalanyado.md), [`jarulek-szocho.md`](../../rules/jarulek-szocho.md), [`bevetel-nyilvantartas.md`](../../rules/bevetel-nyilvantartas.md).

## Mit csinál

A `scripts/adoszamitas.py` Decimal aritmetikával, **AI-beavatkozás nélkül** számol:

- bevétel = kiegyenlített (`payment_status=paid`), nem stornózott számlák nettó forintértéke a **kifizetés napja** szerint; stornó bizonylatok, stornózott számlák és kifizetetlen számlák kimaradnak (a kimenet listázza az okot),
- átalányos jövedelem = göngyölt bevétel × (1 − költséghányad), szja = (jövedelem − adómentes keret) × 15%,
- tbj/szocho: a minimális alap (időarányosan az induló hónapra) és a jövedelemalapú járulékalap közül a nagyobb, göngyölve,
- negyedéves előleg = a göngyölt érték különbsége az előző negyedévhez képest,
- a határidők a feldolgozott adónaptárból jönnek (`data/adonaptar/<év>.json`).

Bemenet: `data/szamlak/` (skill: `szamlak`), `data/adonaptar/` (skill: `adonaptar`), `config/vallalkozas.json`, `config/szabalyok_<év>.json`. Kimenet: képernyő + `data/szamitas/adoszamitas_<év>.json`.

## Futtatás

```
python -I .claude/skills/adoszamitas/scripts/adoszamitas.py
```

Ha nincs az évet lefedő számlafájl vagy adónaptár, a script megáll, és megmondja, melyik skillt kell előbb futtatni.

## Hiányzó beállítások

A `config/vallalkozas.json` `null` mezői (`tb_statusz`, `min_alap_tipus`, `vallalkozas_kezdete`) a felhasználó adatai. Amíg `null`, a script a tbj/szocho számítást **nem végzi el** („NEM SZÁMOLHATÓ"). **Ne töltsd ki helyette**, ne találj ki értéket, és a NAV-adatokból se következtess rá a felhasználó helyett. Kérdezd meg a felhasználót, és csak az ő válasza alapján írd be.

## Kamarai hozzájárulás és kedvezmények

A script az `egyeb_fizetendo` listában adja a kamarai hozzájárulást (config: `kamara_koteles`, `kamara_hozzajarulas_ft`; forrás: 1999. évi CXXI. tv. 34/A. §), és jelzi, ha a befizetés nincs igazolva. A kedvezmények (`kedvezmenyek`) jogosultságát a vállalkozói profil készítésekor kell megadni; „nincs” esetén a számítás nem csökken, kedvezmény megadásakor `NEM SZÁMOLHATÓ` jelzés van (a képletek nincsenek implementálva). Hiányzó válasznál ugyanígy.

## Szabályok ehhez a skillhez

1. Minden számot a script kimenetéből vagy a mentett JSON-ból idézz; **te nem számolsz, nem kerekítesz, nem összegzel**.
2. A folyamatban lévő negyedév értéke az eddigi adatokkal számolt, nem végleges; ezt mindig mondd ki.
3. Add át a kimenet „Figyelmeztetések / nem ellenőrzött pontok" részét változatlanul (devizaárfolyam, Billingo dátumszűrő, kedvezmények hiánya, töredékhónap-módszer).
4. Ha a számlaadat >1 napos, mondd ki, és javasold a `szamlak` skill futtatását.
5. A számított érték nem NAV-előírás: a NAV-adószámlával való összevetést az `adoellenorzes` skill végzi. Eltérést ne magyarázz találgatással.
6. Nem adótanácsadás: kedvezmények, döntések kérdésében a válasz a könyvelő/NAV.
