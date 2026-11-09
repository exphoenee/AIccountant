# AIccountant – adóügyi asszisztens

Ez a repo egy magyar átalányadózó egyéni vállalkozó adóügyeinek követésére szolgál. A feladatod: a feldolgozott adatok alapján **figyelmeztetni** a felhasználót az adófizetési határidőkre és egyéb teendőkre.

Nyelv: **magyar** (kommunikáció, riportok, dokumentáció is).

## Alapszabályok (mindig érvényesek)

1. **Számolni mindig Python script számol, soha nem az AI.** Minden szám, dátum, összeg script kimenetből jöjjön.
2. **Nem becslünk, nem találunk ki értéket.** Amit nem ellenőriztél, azt nem mondod. Ha nem tudsz valamit, nyersen mondd ki: „ezt nem tudom".
3. Részletek: [`.claude/rules/nincs-becsles.md`](.claude/rules/nincs-becsles.md) és [`.claude/rules/adatkezeles.md`](.claude/rules/adatkezeles.md). Olvasd el őket, mielőtt adatot dolgozol fel vagy számot mondasz.
4. Skill, agent, rule vagy memory fájl létrehozása előtt olvasd el: [`.claude/rules/struktura.md`](.claude/rules/struktura.md) (elvárt mappa- és fájlstruktúra).
5. **Először a vállalkozás adatait kell feldolgozni.** Az `adoellenorzes` skill addig **nem dolgozhat** (a script leáll), amíg a `.claude/memory/vallalkozasi-profil.md` (a vállalkozás feldolgozott profilja, a `vallalkozas-dokumentumok` skill generálja) nincs meg. Ezt a kaput nem szabad megkerülni.
6. **Minden beérkező dokumentumot a vállalkozói azonosítóval validálunk** (`.claude/scripts/azonosito.py`, `data/vallalkozas/azonosito.json`). Ha a dokumentum nem a vállalkozásé (másik adószám, nincs azonosító, másik fiók API-kulcsa), a skill **megáll**, és érthető utasítást ad; a fájl nem dolgozódik fel. Azonosító nélkül a beérkező dokumentumokat és API-adatot feldolgozó skillek (szamlak, adofizetes, konyvelo-dokumentumok, kiadasok-dokumentumok, vallalkozas-dokumentumok) nem dolgoznak: előbb `vallalkozas-dokumentumok --billingo`. A számítás- és reportskillek (adoszamitas, adoreport, helyi-ipa) már validált `data/` fájlokból dolgoznak. Az adóazonosító jelet az iratokból csak jelöltként olvassuk ki; ellenőrzésre a felhasználó által megerősített érték használható.
7. A használatot (mit hova kell másolni, sorrend, parancsok) a [`usage.md`](usage.md) írja le; a rád váró nyitott pontokat az `adoreport` Tennivalók szakasza listázza.

## Skillek (`.claude/skills/<skill>/`, a scriptek a skill `scripts/` mappájában)

| Skill | Feladat | Script |
|---|---|---|
| `szamlak` | Kimenő számlák: Billingo, Számlázz.hu (Számla Agent) és az `input/bevetelek/` fájljai (PDF, XML, CSV); egyesítés és keresztvalidálás (egy számla csak egyszer könyvelődik); bejövő számlák a Billingóból (csak olvasás). Kulcs nélkül kihagyja, és ezt a futás kiírja | `billingo_szamlak.py`, `billingo_kiadasok.py`, `szamlazz_szamlak.py`, `bevetelek.py`, `szamlak_egyesites.py` |
| `adofizetes` | NAV adószámla XML feldolgozása; mennyit fizettem be adónemenként; NAV-bevallás PDF-ek duplikáció nélküli feldolgozása | `nav_egyenleg.py`, `bevallasok.py` |
| `adonaptar` | Adónaptár letöltése a NAV-ról, feldolgozása, határidők listázása | `nav_adonaptar.py`, `adonaptar.py` |
| `adoszamitas` | Mennyi adó keletkezett a kiállított számlák alapján; kedvezmények számítása (`kedvezmenyek.py`, szabályok: `kedvezmenyek.md`); nyitott jogi kérdések nyilvántartása és könyvelői kérdéslista (`jogi_kerdesek.py`); bevételi nyilvántartás (`bevetel_nyilvantartas.py`, Szja tv. 51. § (3)) | `adoszamitas.py` |
| `adoellenorzes` | **Csak a memória-profil megléte után fut.** Frissíti az adatot a többi skill-lel (adóév argumentum, alapból az aktuális év), aztán számított kötelezettség vs. NAV vs. adónaptár: elmaradás, közelgő határidő, következő fizetendő; a végén elkészíti a reportot | `adoellenorzes.py` |
| `konyvelo-dokumentumok` | A könyvelő iratai (`input/konyvelo/`): PDF->Markdown, adatkivonat (`data/konyvelo/`), a könyvelő adóinak ellenőrzése adónemenként és a bevallások időbeliségének ellenőrzése (az `adoellenorzes` hívja) | `konyvelo.py` |
| `kiadasok-dokumentumok` | Bejövő (kiadási) számlák PDF-ben (`input/kiadasok/`): számla/díjbekérő, összegek, duplikáció-kiszűrés, archiválás; a report Kiadások szakasza használja | `kiadasok.py` |
| `helyi-ipa` | Helyi iparűzési adó: az illetékes önkormányzat (a vállalkozói profil kérdezi meg) szabályai és kulcsa forrással, tételes/hagyományos adóalap, éves IPA, határidők | `ipa.py` |
| `adoreport` | Modern HTML adóreport Chart.js diagramokkal, világos/sötét móddal a `tax-reports/` mappába | `adoreport.py` |
| `pdf-markdown` | PDF -> tömör Markdown, tokentakarékos célzott olvasással (vázlat, keresés, oldaltartomány) | `pdf_markdown.py` |
| `nav-forrasok` | NAV-oldalak és törvények letöltése módosítás nélkül (a törvények mellékleteivel, a hatályos állapot dátumával; `--ellenoriz`: a szabályfájlok törvényhivatkozásainak ellenőrzése; `--graf-ellenoriz`: a Graphify-gráf INFERRED éleinek szöveges ellenőrzése) a `torvenytar/docs/NAV/<év>/`, `torvenytar/docs/<törvény>/<év>/` mappába | `forras_letoltes.py` |
| `vallalkozas-dokumentumok` | **Az első lépés.** Vállalkozói iratok (`input/v…adatok`): leltár, PDF->Markdown, besorolási terv, áthelyezés visszaállítható naplóval, vállalkozói profil (`data/vallalkozas/`) és annak **memória-változata** (`.claude/memory/vallalkozasi-profil.md`) | `dokumentumok.py` |
| `graphify` | Külső (Graphify) skill: tudásgráf a jogszabályszövegekből (lásd a Graphify szakaszt) | (külső, venv) |
| `design-taste-frontend` | Külső (taste-skill) webes tervezési skill; a report arculatának alapja | (külső scriptek) |

Új script mindig az őt használó skill `scripts/` mappájába kerül.

## Mappastruktúra

| Útvonal | Tartalom |
|---|---|
| `.claude/rules/` | Magyar adóügyi szabályok és a működési szabályok. **Ezek az irányadók.** |
| `.claude/skills/` | Skillek és scriptjeik |
| `.claude/memory/` | Generált memória: `vallalkozasi-profil.md` (a vállalkozás adózási és jogi szempontból fontos, forrással igazolt adatai; az `adoellenorzes` kapuja), `adonaptar-<év>.md` + `MEMORY.md` index |
| `config/` | `szabalyok_<év>.json` (szabályparaméterek), `vallalkozas.example.json` (sablon) és `vallalkozas.json` (a vállalkozó saját beállításai, nincs verziókezelve; a telepítő/első futás a sablonból készíti, a `null` mezőket a felhasználónak kell kitöltenie), `iratrend.json` (általános iratbesorolás) |
| `torvenytar/` | Háttéranyagok és hivatalos források: **`docs/`** (a törvények és NAV-oldalak módosítatlan szövegei: `docs/NAV/<év>/`, `docs/<törvény>/<év>/`), **`graph/`** (a kész Graphify törvénytérkép: `graph.json`, `graph.html`, `GRAPH_REPORT.md`; verziózott, nyilvános szövegből készült, személyes adat nélkül), `forrasok.json`. Háttéranyagok (a `docs/` alatt): `atalanyado-szabalyok-osszefoglalo.md` (átalányadó szabályok, NAV-forrásokkal), `konyveles-szoftver-jegyzetek.md` (könyvelési jegyzetek) |
| `input/vallalkozas-adatok/`, `input/bevetelek/`, `input/konyvelo/`, `input/kiadasok/`, `input/torveny/`, `input/nav-egyenleg/`, `input/adonaptar/`, `input/pdf/` | A felhasználó által bemásolt, még feldolgozatlan nyers fájlok (részletek: `usage.md`) |
| `archive/` | Már feldolgozott nyers fájlok (mozgatás, nem törlés); a vállalkozói iratok rendezett helye: `archive/vallalkozas-iratok/` |
| `data/` | Minden feldolgozott eredmény: `szamlak/`, `kiadasok/` (PDF-kivonat és Markdown is), `nav-egyenleg/`, `adonaptar/`, `szamitas/`, `konyvelo/`, `ipa/` és `vallalkozas/` (leltár, terv, napló, profil, iratok Markdown-ja) |
| `tax-reports/` | Az `adoreport` skill HTML reportja (`adoreport_<év>.html`); nincs verziókezelve |
| `install.sh`, `install.ps1` | Telepítő: mappák, `.gitignore`, `.env` (Billingo és Számlázz.hu API-kulcs) |
| `.env` | Titkok (`BILLING_API_KEY`, `SZAMLAZZ_API_KEY`, `SZAMLAZZ_SOROZAT`). **Soha ne olvasd ki az értékét az outputba, ne commitold.** |
| `docs/`, `audits/` | `docs/`: Archify HTML-diagramok és forrás-JSON-jaik (AI-workflow, mappák adatfolyama); `audits/`: a repó kiadott auditjai (személyes adat nélkül, verziózva) és a felhasználó saját auditjai (ez utóbbiakat a telepítő a `.gitignore`-ba teszi) |
| `usage.md` | Használati útmutató |

Adatfolyam: `input/` → script feldolgozza → eredmény a `data/`-ba, nyers fájl az `archive/`-ba. Lásd: `adatkezeles.md`.

## Billingo integráció

- Az API kulcs a `.env`-ben van `BILLING_API_KEY` néven; a script maga olvassa, **te ne olvasd ki és ne írd ki**. Csak olvasási jogosultság: írási műveletet (számla létrehozás, módosítás, sztornó, küldés) soha ne kíséreljünk meg.
- Billingo API v3: `https://api.billingo.hu/v3`, `X-API-KEY` header, `GET /documents`.

## Fő feladatok

1. **Határidő-figyelés**: adónaptár alapján mi jön a következő 30–60 napban, napra pontosan (`adonaptar`, `adoellenorzes`).
2. **Befizetések / egyenleg**: NAV adószámla alapján mennyit fizettem be, van-e tartozás/túlfizetés (`adofizetes`).
3. **Keletkezett adó**: kiállított számlákból számított szja/tbj/szocho és a limitek kihasználtsága (`adoszamitas`).
4. **Ellenőrzés**: elmaradás, eltérés, közelgő határidő, következő fizetendő összeg (`adoellenorzes`).

## Munkamódszer

- Mindig a **mai dátumhoz** viszonyíts; a hátralévő napokat a script számolja.
- Minden figyelmeztetésnél jelöld a forrást (script / adónaptár-sor / szabályfájl).
- Rangsorolj: 🔴 lejárt vagy ≤7 nap, 🟡 8–30 nap, 🟢 30 nap felett.
- Hiányzó vagy elavult adatnál (beállítás, fájl, kivonat) mondd ki nyersen, mi hiányzik; ne tölts ki értéket.
- Az adóévi számokat a `.claude/rules/` és `config/` fájlokból vedd, ne memóriából.
- Nem vagy adótanácsadó: bizonytalan esetben könyvelő vagy NAV.

## Biztonság és adatvédelem

- A `.env`, `data/`, `archive/`, `input/`, `tax-reports/` érzékeny, nincs verziókezelve (lásd `.gitignore`).
- Adószámot, nevet, címet, számlaszámot, egyenlegeket ne küldj külső szolgáltatásnak, és ne írd a `.claude/memory/` fájlokba.

## Graphify (jogszabály-gráf)

- A [Graphify](https://github.com/Graphify-Labs/graphify) skill (`.claude/skills/graphify/`, PyPI: `graphifyy` 0.9.104, Apache-2.0) a letöltött jogszabályszövegekből (`torvenytar/docs/<törvény>/<év>/*.txt`) tudásgráfot épít, amelyből lekérdezni lehet a keresés helyett.
- A CLI a skill saját, elszigetelt Python-környezetében van: `.claude/skills/graphify/.venv/Scripts/graphify.exe`. **Nincs a PATH-on, és nincsenek hookok** (a telepítő által írt `.claude/settings.json`-t szándékosan töröltem). Futtatás előtt tedd a venv `Scripts` mappáját a PATH elejére, hogy a skill ezt a Pythont találja meg, és ne telepítsen csomagot a rendszer Pythonba.
- A Graphify **munkakönyvtára** (`graphify-out/`: gyorsítótár, alügynök-fájlok) a `data/graphify/<korpusz>/` alatt él (a futtatás munkakönyvtára ott van, nem verziózott). A **kész gráf** a `graf_ellenorzes.py` közzétételi lépésével a **`torvenytar/graph/`** mappába kerül, és a repó része (verziózott, a felhőbe is felmegy). A gráfot a futtatás után mindig közzé kell tenni: `forras_letoltes.py --graf-ellenoriz` (vagy `graf_ellenorzes.py --publikal`). Részletek: `adatkezeles.md`.
- A jogszabályszöveg **gráf-kivonata nem helyettesíti a forrást**: állítás előtt a gráf által megjelölt szakaszt a forrásfájlban kell ellenőrizni (`nincs-becsles.md`).
