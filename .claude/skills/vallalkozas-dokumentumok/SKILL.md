---
name: vallalkozas-dokumentumok
description: A vállalkozói iratok (input/v…adatok mappa) feldolgozása: fájlleltár és duplikátumkeresés, PDF-ek Markdownná alakítása, szabályalapú besorolási terv, áthelyezés logikus mappaszerkezetbe visszaállítható naplóval, és a vállalkozói profil elkészítése forrásokkal. Használd, ha új iratcsomagot kell rendezni, vagy ha a vállalkozás adatait (időrend, ügyfelek, szolgáltatók) a dokumentumokból kell összeállítani.
---

# Vállalkozói iratok: feldolgozás, rendezés, profil

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket. A mappastruktúra szabályai: [`struktura.md`](../../rules/struktura.md).

## Mit csinál (sorrendben)

| # | Lépés | Parancs | Módosít? |
|---|---|---|---|
| 1 | **Leltár:** minden fájl, méret, SHA-256, tartalmilag azonos másolatok | `--leltar` | nem |
| 2 | **PDF -> Markdown** a `pdf-markdown` skill mappa-módjával | `--konvertal` | csak a `data/pdf/`-ot írja |
| 3 | **Besorolási terv** a `config/iratrend.json` szabályai szerint | `--terv` | nem |
| 4 | **Áthelyezés** a terv szerint, napló, SHA-256 ellenőrzés | `--vegrehajt` | igen (visszaállítható) |
| 5 | **Vállalkozói profil** a `config/vallalkozas.json` és a forrással ellátott tények alapján; **a memóriába is kerül** (`.claude/memory/vallalkozasi-profil.md` + `MEMORY.md` index) | `--profil` | `data/vallalkozas/`, `.claude/memory/` |
| – | A Markdown-ok utólagos rendezése a napló szerint | `--md-rendez` | csak a `data/`-t írja |
| – | Az áthelyezés visszavonása | `--visszaallit` | igen |

## Futtatás

```
python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --leltar
python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --konvertal
python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --terv        # átnézni, mielőtt bármi mozdul
python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --vegrehajt
python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --profil
```

## Célstruktúra

Az eredeti iratok (feldolgozott nyers fájlok) az `archive/vallalkozas-iratok/` alá kerülnek, a Markdown-jaik és minden eredmény a `data/vallalkozas/` alá, **ugyanazzal a struktúrával**:

```
archive/vallalkozas-iratok/
├── 01-alapadatok/          ev-bejelentes, kamara, szekhely, tevekenysegi-korok, szuneteltetes-<dátum>, letoltesek-<dátum>
├── 02-szerzodesek/         ugyfelek/<ügyfél>/{szerzodes, teljesitesek/<év-hó>}, konyvelo, szolgaltatok/<szolgáltató>, egyeb-felek
├── 03-szamlak/             kiallitott/<év>, szamlazo-archivum, rontott
├── 04-adozas/              nav/<év>/<űrlapkód vagy eseménymappa>, nav/adoszamla-kivonatok, nav/jovedelemigazolasok,
│                           kata/, helyi-adok/<önkormányzat>/<év>
├── 05-konyveles/
├── 06-egyeb/
└── 99-ellenorizendo/       amit a szabályok nem tudtak besorolni (a felhasználó dönt)

data/vallalkozas/
├── leltar.json, athelyezesi-terv.json, athelyezes.json (napló), profil.json, profil.md, profil-tenyek.json
└── iratok-md/              a PDF-ek Markdown-ja, az archive/ szerkezetét követve
```

## Billingo-egyeztetés (a profil előtt, megállás eltérésnél)

A `--profil` (és külön a `--billingo`) lekéri a vállalkozás adatait a Billingóból (csak olvasás: `/organization`, a legutóbbi számla `organization` blokkja: név, adószám, EV-szám, székhely, közösségi adószám, alanyi adómentesség, pénzforgalmi jelző) és összeveti az iratokból kiolvasottal; az értékeket nem írja ki (`data/vallalkozas/billingo-szervezet.json`). **Eltérésnél a script leáll (4-es kilépési kód): kérdezd meg a felhasználót** (AskUserQuestion), melyik a helyes; a válaszát vedd fel a `profil-tenyek.json`-ba (tény + nyitott pont), és csak utána futtasd újra: `--profil --billingo-eltereseket-elfogadom`. Ha a Billingo nem érhető el, a lépés kimarad, és ezt kiírja.

**Adóazonosító jel:** a `--billingo`/`azonosito.py --frissit` az iratokból csak **jelöltet** olvas ki (a leggyakoribb 10 jegyű szám, legalább 2 iratban; lehet ügyfélé vagy a könyvelőé is). A maszkolt (utolsó 3 számjegy) jelöltet mutasd meg a felhasználónak (AskUserQuestion): ha a sajátja, `python -I .claude/scripts/azonosito.py --megerosit-adoazonosito`. Megerősítés nélkül az ellenőrzés csak az adószámot használja.

## Kamarai hozzájárulás és kedvezmények: kötelező kérdések

A profil készítésekor (a `--profil` kilistázza, ha még nincs válasz) **kérdezd meg a felhasználót** (AskUserQuestion):

1. **Köteles-e kamarai hozzájárulást fizetni?** (Évi 5 000 Ft, március 31., kivéve a teljes évi szünetelést: `kamarai-hozzajarulas.md`.) Rögzítés: `dokumentumok.py --kamara igen|nem [--kamara-osszeg N]`.
2. **Mely adó- és járulékkedvezményekre jogosult?** (családi, személyi, első házasok, 25 év alattiak, anyák kedvezményei, vagy egyik sem.) Rögzítés: `dokumentumok.py --kedvezmeny nincs` vagy `--kedvezmeny csaladi szemelyi ...`.

A válaszok a `config/vallalkozas.json`-ba és a memória-profilba kerülnek; az `adoszamitas` a kamarai hozzájárulást külön tételként számolja (`egyeb_fizetendo`). **Kedvezmény megadása esetén a számítás még nem implementált** (a törvényi képletek külön ellenőrzést igényelnek): a kimenet ezt `NEM SZÁMOLHATÓ` jelzéssel kimondja, nem hagyja csendben figyelmen kívül.

## Iparűzési adó illetékességi helye

A profil elkészítésekor **kérdezz rá az IPA illetékességi helyére** (székhely szerinti település). `--ipa-javaslat` jelölteket ad az iratokból és a helyi adó mappákból (ez nem bizonyíték). Kérdezd meg a felhasználót (AskUserQuestion): a székhely települése-e az IPA helye, van-e más telephely, vagy más (egyéni) válasz. Rögzítés: `--ipa-beallit "<település>" [--ipa-telephely "<település>"]`. Ez a [`helyi-ipa`](../helyi-ipa/SKILL.md) skill bemenete: az szerzi be az önkormányzat IPA-szabályait és számolja ki az adót.

## A memória-profil (az `adoellenorzes` kapuja)

A `--profil` a `.claude/memory/vallalkozasi-profil.md` fájlt is létrehozza: **minden adózási és jogi szempontból fontos adat** (jogállás, adózási mód, költséghányad, TB-státusz, minimális alap típusa, a vállalkozás időrendje: kezdés, szünetelés, folytatás, ÁFA-státusz és -események, KATA-időszak, kamara, helyi adó, ügyfelek és szolgáltatók, nyitott pontok), kategóriákba rendezve, forrással. A fájl **generált**, kézzel ne szerkeszd; személyes azonosítót (adószám, TAJ, cím, bankszámla) nem tartalmazhat. Az `adoellenorzes` ennek meglétét ellenőrzi indulás előtt.

A tényeket a `data/vallalkozas/profil-tenyek.json`-ba kell írni (`kategoria`: `jogi` | `adozas` | `helyi-ado-kamara` | `szerzodes`; `datum`; `allitas`; `ellenorzes`; `forras` mappa-szintű útvonalak), a nyitott pontokat a `nyitott` listába. Új irat feldolgozása után a tényeket bővíteni kell, és újra kell futtatni a `--profil` parancsot.

## Szabályok ehhez a skillhez

1. **A besorolás kizárólag az útvonal (mappa- és fájlnév) alapján történik** (`config/iratrend.json`); tartalom alapján nem. Ami nem illeszkedik szabályra, az `99-ellenorizendo/` alá kerül, ezt a felhasználó dönti el. Új szabályt a `config/iratrend.json`-ba írj, ne a scriptbe.
2. **Előbb mindig `--terv`, és a terv összesítését mutasd meg a felhasználónak** az áthelyezés előtt. A `--vegrehajt` nem ír felül semmit, névütközésnél `__2` utótagot ad, és minden fájl SHA-256-át ellenőrzi a célon.
3. **Nem töröl semmit.** A tartalmilag azonos másolatokat (a leltár listázza) megőrzi; a felesleges másolatok törlése a felhasználó döntése.
4. A **nem PDF fájlok** (docx, xlsx, msg, jar, jnlp, lnk, zip stb.) nem alakíthatók Markdownná (nincs hozzá eszköz), csak áthelyezhetők. A `.jar`, `.jnlp`, `.lnk` fájlokat **soha ne futtasd**. A szkennelt (szövegréteg nélküli) PDF-eknél OCR nincs; ezeket a script hibaként jelzi.
5. **Személyes adat:** az iratok adószámot, nevet, címet, bankszámlát tartalmazhatnak. Ezek **nem kerülnek a chatbe, a `.claude/memory/`-ba vagy a profilba**; a profil csak üzleti tényeket tartalmaz (időpont, esemény, szerződő fél), mindegyik mellett forrásdokumentummal.
6. **A profil tényeit forrásfájlból kell kiolvasni** (célzottan: `pdf_markdown.py --kereses/--olvas`), és a `data/vallalkozas/profil-tenyek.json`-ba kell írni (`allitas`, `datum`, `forras` = útvonalak listája, `ellenorzes` = `dokumentumból olvasva` | `mappanévből` | `felhasználótól`). A `--profil` csak a létező forrású tényeket fogadja el ellenőrzöttként; a többit „forrás nélküli"-ként külön listázza. Mappanévből vett dátum (pl. `2023-07-12`) nem azonos a dokumentumból ellenőrzött dátummal; ezt jelezd.
7. A besorolási szabályok **nem jogi értelmezések**: a „Mentor", „EGYKE", „Egyéb" típusú, jelentésükben bizonytalan mappák a `99-ellenorizendo/` alá kerülnek, amíg a felhasználó meg nem mondja, mik.
8. A profil tényei (`profil-tenyek.json`) bekerülnek az `adoreport` „A vállalkozás története” szakaszába is (a report aljára), ezért a forrásokat **mappa-szinten** add meg, és ne kerüljön beléjük adószám, TAJ-szám, cím vagy bankszámla (az iratok fájlnevei ilyet tartalmazhatnak).
9. A visszaállítás (`--visszaallit`) a naplóból az eredeti útvonalra teszi vissza a fájlokat és a Markdown-jaikat; ha az eredeti hely foglalt, kihagyja és jelzi.
