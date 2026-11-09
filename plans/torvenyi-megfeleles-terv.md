# Terv: hogyan feleljen meg jobban az AI-workflow a törvényeknek

> Forrás: `audits/torvenyi-megfeleloseg-audit-2026-11-08.md` (jelölések: ✅ megfelel, 🟡 csak NAV-tájékoztatóból igazolt, ❓ homályos/ellentmondó, ⛔ nem fedett). Kapcsolódó: `audits/ai-workflow-review-2026-11-08-b.md`.
> Alapelv (nincs-becsles.md): az AI nem dönt jogértelmezésről, és nem tölti ki a hiányt. A terv célja nem az, hogy az AI „megoldja” a nyitott kérdéseket, hanem hogy (a) hiányzó jogforrás ne maradjon ki, (b) a kód csak ellenőrzött szabályt alkalmazzon, (c) a nyitott kérdés mindig látható legyen az érintett számnál, (d) a könyvelői döntés rögzíthető legyen és a számítás ahhoz igazodjon.
> Állapot (2026-11-08, frissítve): **megvalósult:** A1–A4 (jogforrások, mellékletek, hatályos állapot), D1–D3, D4 (sablon: `config/szabalyok.example.json`), B1–B4 (`jogi_kerdesek.py`, `config/konyvelo-dontesek.json`, kérdéslista, report-jelzés), C1 (bevételi nyilvántartás), **C2 (kedvezmények számítása, `kedvezmenyek.py`)**, E (tesztek: `teszt_kedvezmenyek.py`), M2. A mellékletek célzott olvasása megtörtént (lásd `atalanyado.md`, `afa.md`, `hataridok.md`). **Nyitva (felhasználói teendő vagy külső adat):** a B fázis döntései (könyvelő/NAV), C3 (összesítő nyilatkozat vonatkozása), C4 (helyesbítő bevallás), C5 (tételes IPA bejelentés ténye), a 2027-es hivatalos értékek, a KSH bruttó átlagkereset (25 év alatti kedvezmény).

## Mi akadályozza ma a megfelelést (összefoglalva)

1. **Hiányzó jogforrások** (⛔): Art. (adózás rendje), Szja tv. 1., 4., 10. melléklet, az összesítő nyilatkozat szabálya (Áfa tv. 4/A. melléklet). Ezekre épülő állítások csak NAV-tájékoztatón vagy az adónaptáron nyugszanak.
2. **Feloldatlan jogi kérdések** (❓), amelyek számot változtatnak: 89%-os szabály, minimális alap típusa, időarányosítás nevezője, szünetelés hatása a járulékra, bevétel időpontja átutalásnál.
3. **Nem implementált kötelezettségek** (⛔): bevételi nyilvántartás (Szja tv. 51. § (3)), kedvezmények, helyesbítő bevallás, összesítő nyilatkozat.
4. **A kimenet nem jelzi az ellenőrizetlen alapot** az érintett számnál; a ✅/✅? jel a nyitott kérdés mellett is megjelenik.
5. **A beállítások nem évhez kötöttek** (költséghányad 2027-től 50%), és a könyvelői döntéseknek nincs strukturált helye.

## A. fázis: jogforrások pótlása (forrás nélkül nincs állítás) – megvalósítva

A letöltés megvan; **hátra van** a mellékletek célzott elolvasása és a szabályfájlok (`atalanyado.md`, `afa.md`, `bevetel-nyilvantartas.md`, `hataridok.md`) frissítése a tényleges szöveg alapján.

| # | Teendő | Hogyan | Kész, ha |
|---|---|---|---|
| A1 ✅ | Art. (2017. évi CL.) letöltése | `nav-forrasok` skill, njt.hu → `torvenytar/docs/art/2026/` | a `torvenytar/forrasok.json`-ban szerepel; a határidő-szabályok (`hataridok.md`) hivatkozhatnak törvényi helyre |
| A2 ✅ | Szja tv. 1., 4., 10. számú melléklet szövege | az njt.hu-kivonat nem tartalmazza: külön letöltés vagy a NAV-oldalon közzétett forrás; ha nem érhető el, a `nyitott` listában marad | az „adómentes jövedelemrész” és a bevétel-elszámolás állítása törvényi helyre hivatkozik, vagy kimondja, hogy nem sikerült beszerezni |
| A3 ✅ | Áfa tv. 4/A. melléklet (összesítő nyilatkozat) | ugyanez | `afa.md` „Nyitott pontok” szakasza frissül |
| A4 ✅ | Hatályos állapot rögzítése | a `forras.json` mellett: az njt.hu állapot-dátuma | a szabályfájlok megmondják, melyik hatályos szövegből készültek |

Jegyzet: a Graphify-gráf csak keresőeszköz; állítás előtt a forrásfájlban kell ellenőrizni (CLAUDE.md).

## B. fázis: a nyitott jogi kérdések kezelése (könyvelői döntés strukturáltan)

A cél, hogy a kérdés ne a chatben, hanem adatként éljen, és a számítás ahhoz igazodjon.

1. **Új fájl: `config/konyvelo-dontesek.json` (nem verziózott)** – mezők: `kerdes_id`, `kerdes`, `dontes`, `ki_dontott` (könyvelő/NAV), `datum`, `forras` (irat útvonala). Kérdések: `89_szazalek`, `min_alap_tipus`, `idoaranyos_nevezo`, `szunetelés_jarulek`, `bevetel_idopont_atutalas`, `devizaarfolyam_6_2a`, `tetelesipa_bejelentve`.
2. **Script: `adoszamitas.py` olvassa a döntéseket.** Ha nincs döntés, a számítás a mai alapértelmezéssel fut, de a kimenet sorai **megjelölik az érintett számot** („ellenőrizetlen alap: 89%-os szabály”). Ha van döntés, a script a döntés szerint számol, és a döntés forrását kiírja. **A 89%-nál a script nem alkalmaz értéket, amíg a döntés nincs rögzítve**; a döntés bevitelekor jön a képlet (a törvényi képletet külön ellenőrizni kell a 29. és 47. § (5) szövegéből, nem emlékezetből).
3. **Report/`adoellenorzes`:** minden szja/járulék-sor mellett jelzés, ha az érintett kérdés nyitott; a ✅ jel nem jelenhet meg nyitott kérdéssel érintett összegnél (csak ✅? vagy ❓).
4. **Kérdéslista a könyvelőnek:** új parancs (`adoreport` Tennivalók vagy külön script) generálja a nyitott kérdések listáját egy oldalon, a szabályhivatkozással (Szja tv. 29. §, 47. § (5); Tbj. 3. § 14.2.; Szocho tv. 6. § (3); Htv. 39/A. § (4); stb.). Ez az audit 4. fejezetének gépi változata.
5. **`min_alap_tipus_megerositve`** logikája általánosul: minden nyitott döntésnél a script az alternatív számítást is megmutatja (ahogy ma a min. alapnál), hogy a kockázat összege látszódjon, ne csak a ténye.

## C. fázis: nem fedett kötelezettségek

| # | Teendő | Megjegyzés |
|---|---|---|
| C1 | **Bevételi nyilvántartás generálása** (Szja tv. 51. § (3), rovatok: `bevetel-nyilvantartas.md`) | új script az `adoszamitas`/`szamlak` mellett; csak az egyesített, keresztvalidált számlákból; az eredmény `data/szamitas/`, ember által olvasható CSV/HTML. A beérkezés napját a Billingo `paid_date` adja; az átutalásos kivétel (9. § (2) a)) nyitott pontként a fejlécben. |
| C2 | **Kedvezmények** | implementáció előtt a törvényi képlet forrásból; amíg nincs, ma is `NEM SZÁMOLHATÓ` (marad). |
| C3 | **Összesítő nyilatkozat** | A3 után; addig a report Tennivalókban „nem ellenőrzött: könyvelő” tétel külföldi (uniós) vevős számláknál. |
| C4 | **Helyesbítő/önellenőrző bevallás** | nem számolunk vele; ha a B fázisban min. alap vagy 89% döntés változtat a már beadott bevallásokon, a report jelezze, hogy mely negyedéveket érinti (a `konyvelo.py` ellenőrzése már negyedévenként összevet). |
| C5 | **Tételes IPA bejelentés** | `ipa_tetelesen_bejelentve` + igazolás-útvonal a profilban; hiányában a `ipa.py` a hagyományos adóalapot is megmutatja (Htv. 39/A. § (4)). |

## D. fázis: az AI viselkedése (utasítások, nem kód)

1. **`nincs-becsles.md` kiegészítése:** (a) törvényi hely nélkül nincs „törvény szerint” kezdetű állítás; (b) ha a törvényszöveg és a NAV-tájékoztató ellentmond (pl. 89%), az AI mindkettőt idézi, és nem választ; (c) kötelező megnevezni, hogy a forrás törvény (✅) vagy tájékoztató (🟡).
2. **Skill-szintű „jogi forrás” szakasz** az `adoszamitas`, `helyi-ipa`, `szamlak` SKILL.md-ben: melyik állításhoz melyik szakasz tartozik; ha a szabályfájl és a `torvenytar` szövege eltér, a `torvenytar` az irányadó, és az eltérést jelezni kell.
3. ✅ **Szabályfájl-ellenőrző script** (megvalósult: `forras_letoltes.py --ellenoriz`; csak a szakasz/melléklet létét ellenőrzi) (`.claude/skills/nav-forrasok/scripts/`): a `.claude/rules/*.md` szakaszhivatkozásait (pl. „Áfa tv. 163. § (2) a)”) kikeresi a `torvenytar/*.txt`-ben, és jelzi, ha a hivatkozott szakasz nincs meg. Futtatás: új szabályfájl vagy törvénytár-frissítés után. Ez az audit kézi ellenőrzésének automatizálása.
4. **Évváltási ellenőrzőlista** (2027: költséghányad 50%, új minimálbér, új űrlapkódok): `config/szabalyok_<év>.json` tartalmazza a költséghányadot is (lásd review M5); az `adoszamitas` az évhez tartozó szabályfájlból olvas, és hiányzó fájlnál megáll.

## E. fázis: teszt és bizonyíték

- Az `adoszamitas/scripts/teszt_nav_peldak.py` mintájára **tesztek a nyitott döntésekhez** (kitalált adatokkal): döntés nélkül jelölt sor; döntéssel a képlet szerinti érték.
- **Jogforrás-regressziós teszt:** a D3 script futtatása CI-szerűen az install önteszt részeként.
- **Dokumentálás:** minden döntés a `profil-tenyek.json`-ba tényként is bekerül (forrás: könyvelői irat), így a „A vállalkozás története” szakasz és a memória-profil is mutatja.

## Javasolt sorrend és hatás

1. **D1, D2, B3** – azonnal; csak szöveg és kimeneti jelölés, kockázat nélkül.
2. **A1–A3** – forrásbeszerzés (a skill már megvan).
3. **B1, B2, B4, B5** – a nyitott kérdések strukturálása; a 89%-os kérdés a legnagyobb (az szja összegét érinti).
4. **D3, D4, E** – automatizált védelem és évváltás előtti rend (2027).
5. **C1, C5** – bevételi nyilvántartás és tételes IPA.
6. **C2–C4** – akkor, ha a jogforrás és a könyvelői döntés megvan.

## Nem cél
- Az AI nem dönti el a 89%-os szabály, a minimális alap, a szünetelés vagy az árfolyam kérdését; ezek könyvelői/NAV döntések.
- Nem adunk hozzá becsült vagy „valószínűsíthető” értéket a hiányzó forrás helyére.
- A tervhez nem tartozik adószám, név vagy más személyes adat; a döntések és igazolások a `config/` (nem verziózott) és `data/` alatt élnek.
