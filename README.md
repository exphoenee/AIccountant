# AIccountant

Személyes adóügyi asszisztens átalányadózó egyéni vállalkozók számára. Claude Code-dal figyelmeztet az adófizetési határidőkre és egyéb teendőkre a Billingo számlák, a NAV adószámla, az adónaptár és a vállalkozás iratai alapján. **A számításokat Python scriptek végzik, nem az AI.** Ami nem ellenőrzött, azt a rendszer kimondja, nem becsül.

> **Először a vállalkozás adatait kell feldolgoztatni.** Az adóellenőrzés (`adoellenorzes`) addig nem fut le, amíg a memóriában (`.claude/memory/vallalkozasi-profil.md`) nincs feldolgozott vállalkozói profil. Lépésről lépésre: **[`usage.md`](usage.md)**.

## Telepítés

Két azonos működésű telepítő van a repó gyökerében:

| Rendszer | Parancs |
|---|---|
| Linux, macOS, Git Bash | `./install.sh` |
| Windows (PowerShell) | `.\install.ps1` |

A telepítő: ellenőrzi a Python 3.10+ és a `pdftotext` meglétét; létrehozza az `input/` almappákat (`vallalkozas-adatok`, `nav-egyenleg`, `adonaptar`, `konyvelo`, `kiadasok`, `bevetelek`, `torveny`, `pdf`), a `data/`, `archive/`, `tax-reports/`, `audits/` mappákat; kiegészíti a `.gitignore`-t az érzékeny mappákkal; **létrehozza a `.env` fájlt**: rákérdez a **Billingo** és a **Számlázz.hu** API-kulcsra (a bevitel rejtett, Enter = kihagyás); végül lefuttatja a számítás önellenőrző tesztjét.
Kulcs nélkül az adott forrás adatait a rendszer **csendben átugorja**. Meglévő `.env` esetén a kitöltött értékeket megtartja. Nem interaktív használat: `BILLING_API_KEY=... SZAMLAZZ_API_KEY=... ./install.sh --nem-interaktiv` (PowerShell: környezeti változók, majd `.\install.ps1 -NemInteraktiv`).

## Gyors indulás

> **Ez egy sablon:** nem tartalmaz senki vállalkozásának adatát. A saját beállításaid a `config/vallalkozas.json`-ba (a telepítő a `config/vallalkozas.example.json` sablonból készíti; nincs verziókezelve), a feldolgozott adataid a `data/`, `archive/` és `.claude/memory/` mappákba kerülnek (szintén nem verziózottak). **2026-os adóévre készült**: új évhez új `config/szabalyok_<év>.json` és adónaptár kell. Az adónaptárat a `nav_adonaptar.py` tölti le a NAV oldaláról (`input/adonaptar/ÉÉÉÉ.md`), vagy saját forrásból másolod be; a repó nem tartalmaz harmadik féltől származó naptárat. A `helyi-ipa` skill a település rendeletét az interneten keresi meg (WebSearch/WebFetch): a településnevet ilyenkor külső szolgáltatás látja.

1. Futtasd a telepítőt (lásd fent), vagy kézzel hozd létre a `.env`-et: `BILLING_API_KEY=`, `SZAMLAZZ_API_KEY=` (Billingo **csak olvasási** API-kulcs; Számlázz.hu Számla Agent kulcs; sablon: `.env.example`).
2. A vállalkozás iratait másold az `input/vallalkozas-adatok/` mappába, majd futtasd a `vallalkozas-dokumentumok` skillt (leltár, PDF→Markdown, terv, áthelyezés, **profil a memóriába**).
3. Adónaptár: `input/adonaptar/ÉÉÉÉ.md`; NAV adószámla XML: `input/nav-egyenleg/`.
4. Futtasd az adóellenőrzést (a Claude-tól vagy parancssorból): `python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py [év]`. Ebből készül a `tax-reports/adoreport_<év>.html` (világos/sötét módú, diagramos, határidőkkel és a vállalkozás történetével).
5. A rád váró, nyitott teendők a report Tennivalók szakaszában vannak.

A teljes útmutató (mit hova másolj, milyen sorrendben, hibaelhárítás): [`usage.md`](usage.md).

## Skillek (`.claude/skills/<skill>/`, a scriptek a skill `scripts/` mappájában)

| Skill | Feladat |
|---|---|
| `vallalkozas-dokumentumok` | A vállalkozás iratainak feldolgozása és rendezése, **vállalkozói profil a memóriába** (ez az első lépés) |
| `adoellenorzes` | Adatfrissítés a többi skill-lel, számítás, összevetés a NAV-val és az adónaptárral, report; **csak profil után fut** |
| `konyvelo-dokumentumok` | A könyvelő iratainak (`input/konyvelo/`) feldolgozása; a könyvelő adóinak ellenőrzése adónemenként és a bevallások időbeliségének ellenőrzése (az `adoellenorzes` hívja) |
| `kiadasok-dokumentumok` | Bejövő számlák PDF-ben (`input/kiadasok/`) feldolgozása duplikáció nélkül; a report Kiadások szakasza használja |
| `helyi-ipa` | Helyi iparűzési adó: az önkormányzat szabályai, kulcsa forrással, éves IPA |
| `adoszamitas` | Keletkezett szja, tbj, szocho a számlák alapján; bevételi határ és adómentes keret |
| `adofizetes` | NAV adószámla XML feldolgozása, befizetések |
| `adonaptar` | Adónaptár feldolgozása, határidők |
| `szamlak` | Kimenő számlák: Billingo, Számlázz.hu és az `input/bevetelek/` fájljai; egyesítés és keresztvalidálás (egy számla csak egyszer könyvelődik); bejövő számlák a Billingóból (csak olvasás) |
| `adoreport` | HTML adóreport (Chart.js, világos/sötét mód, vállalkozás története) |
| `pdf-markdown` | PDF → tömör Markdown, tokentakarékos célzott olvasás |
| `nav-forrasok` | NAV-oldalak és törvények módosítás nélkül a `torvenytar/` mappába, Markdown, törvénytérkép |
| `graphify` | Külső skill: tudásgráf a jogszabályszövegekből |
| `design-taste-frontend` | Külső skill: a report arculatának alapja |

## Diagramok (Archify, `docs/`)

- [AI-workflow](docs/ai-workflow.html): hogyan működik a folyamat, ki mit csinál, hol áll meg és kérdez.
- [Mappák és adatfolyam](docs/mappak-adatfolyam.html): melyik `input/` mappába mit kell tenni, melyik skill dolgozza fel, és mi történik az irattal.

A forrás-JSON-ok mellettük vannak (`docs/*.json`). A saját auditjaid az `audits/` mappába kerülnek.

## Mappák

```
.claude/rules/      adóügyi és működési szabályok (adatkezeles, nincs-becsles, struktura, atalanyado, ...)
.claude/skills/     skillek és scriptjeik
.claude/memory/     generált memória: vallalkozasi-profil.md, adonaptar-<év>.md, MEMORY.md
config/             szabalyok_<év>.json, vallalkozas.json, iratrend.json
input/              feldolgozásra váró nyers fájlok (vallalkozas-adatok, konyvelo, kiadasok, bevetelek, torveny, nav-egyenleg, adonaptar, pdf)
archive/            feldolgozott nyers fájlok (archive/vallalkozas-iratok: a rendezett iratok)
data/               feldolgozott eredmények (számlák, NAV, naptár, számítás, vallalkozas, pdf, graphify)
tax-reports/        adoreport_<év>.html
torvenytar/         NAV-források és törvények módosítás nélkül + összefoglalók
install.sh / install.ps1   telepítő (mappák, .env, API-kulcsok)
usage.md            használati útmutató
```

A `data/`, `archive/`, `input/`, `tax-reports/` és az `.env` érzékeny, nincs verziókezelve.

## Személyes adatok és a GitHub

A személyes és pénzügyi adatok (`.env`, `input/`, `data/`, `archive/`, `tax-reports/`, `config/vallalkozas.json`, a generált vállalkozói profil és adónaptár-kivonat) a `.gitignore` miatt **nem kerülnek verziókezelésbe**; a telepítő is beírja őket. A `.gitignore` kategóriánként jelöli, mi **kötelező** (titkok, személyes adatok, a saját vállalkozást azonosító beállítások) és mi **ajánlott** (saját auditok, teendőlisták, levélvázlatok, generált fájlok).

**Az ajánlott sorokat te döntöd el:** ízlés kérdése, hogy ki mit tesz fel a saját GitHub-repójába. Ha a saját auditjaidat vagy jegyzeteidet is verziózni akarod, vedd ki a sorukat, de előbb olvasd át őket, hogy nincs-e bennük ügyfélnév, összeg vagy más személyes adat. A kötelező sorokat ne töröld. A repó nem ellenőrzi, mit commitolsz: push előtt nézd át a `git status` kimenetét.

## Alapelvek

- **Számítást csak script végez**, nincs becslés és nincs kitalált érték.
- **Személyes azonosító** (adószám, TAJ, cím, bankszámla, API-kulcs) nem kerül a chatbe, a memóriába vagy a reportba.
- A **`torvenytar/` forrásfájljait** nem módosítjuk.
- **Nem adótanácsadás.** A döntést igénylő pontokat (minimális alap típusa, árfolyam, helyesbítő bevallás) a könyvelővel vagy a NAV-val kell tisztázni.

A részletes szabályok: [`CLAUDE.md`](CLAUDE.md) és `.claude/rules/`.
