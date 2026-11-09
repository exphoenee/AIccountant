# AI-workflow review (második kör): ellentmondások, működési hibák, adatkezelés (2026-11-08)

> Módszer: a CLAUDE.md-t, a `.claude/rules/` fájlokat, a SKILL.md-ket, az `adoellenorzes.py`, `adoszamitas.py`, `azonosito.py`, `konfig.py`, `dokumentumok.py` (memória-rész) kódját, az `install.sh`/`install.ps1`-t, a README-t, a usage.md-t és a `docs/` JSON-t olvastam el. Az előző kör (`ai-workflow-review-2026-11-08.md`) pontjai közül az újraellenőrzöttek javítva vannak (konfig-sablonok léteznek, kapu köti a profilt a `profil.json`/`azonosito.json`-hoz, szünetelés modellezve, 36 órás TB-státusz kezelve, a memória nem tartalmaz ügyfélneveket).
> **A scripteket nem futtattam**, a megállapítások kód- és szövegolvasásból valók. Nem néztem meg: `szamla_ellenorzes.py`, `bevetelek.py`, `konyvelo.py`, `kiadasok.py`, `ipa.py`, `adoreport.py` belső logikáját, a külső `graphify` és `design-taste-frontend` skillt.
> A `.env` értékét nem olvastam ki (csak a változónevet és hogy nem üres-e).

Súlyosság: **M** = hibás/félrevezető eredményt vagy szabálysértést okozhat, **K** = kisebb.

## 1. Személyes adatok kezelése

**M1. A szabályok csak a kimenetet védik, a bemenetet nem.**
- `adatkezeles.md` 9. és CLAUDE.md: adószám, név, cím ne kerüljön „a chat kimenetbe”, és „ne küldj külső szolgáltatásnak”. Közben a `vallalkozas-dokumentumok` SKILL 6. szabálya előírja, hogy az AI olvassa ki a tényeket az iratok Markdown-jából (`pdf_markdown.py --kereses/--olvas`). Amit az AI beolvas, az a modellszolgáltatóhoz kerül; ezt sem a README, sem a szabályok nem mondják ki.
- A beolvasott szövegeket semmi nem maszkolja (a `pdf-markdown` skillben nincs maszkolás/anonimizálás; a `grep` csak `azonosito.py`-ban talál maszkolást).
- Javaslat: kimondani a README-ben és az `adatkezeles.md`-ben; maszkoló réteg a `pdf_markdown.py --olvas` kimenetén (adószám, TAJ, bankszámla, e-mail, telefon); a „külső szolgáltatás” szabályt pontosítani.

**M2. A `data/vallalkozas/azonosito.json` az adószámot és a nevet nyíltan tárolja.** Nincs verziókezelve, ez rendben van, de sem titkosítás, sem fájljogosultság-beállítás nincs (a `.env`-nél van: `chmod 600` / `icacls`). Következetlen védelem.

**K1. `adoszamitas_<év>.json` a teljes beállítást (`beallitasok`) és az IPA-települést is tartalmazza.** `data/` alatt marad, de a report/bármely export innen ne másoljon személyes mezőt.

## 2. Ellentmondások a dokumentáció és a kód között

**M3. A `szamlak` SKILL rossz lekérési időszakot ír elő.**
- SKILL: „mindig az év elejétől az év végéig kérd le (pl. 2026-01-01 2026-12-31), mert az `adoszamitas` csak az évet teljesen lefedő fájlt fogadja el.”
- Kód (`adoszamitas.py`, `find_invoice_file`): a fájl kezdete legyen ≤ `ev-1`-01-01 (tavaly kiállított, idén kifizetett számla miatt). Az `adoellenorzes.py` is `ev-1`-től kér.
- Következmény: a SKILL szerint kért fájlt az `adoszamitas` elutasítja, és a hibaüzenet maga is a rossz időszakot javasolja (`{ev}-01-01 – {ev}-12-31`). Körbe-körbe küldi a felhasználót. A `usage.md` példája helyes (2025-01-01 …).

**M4. Az `adoszamitas` az egyesítés/keresztvalidálás megkerülésével is futhat.**
- `find_invoice_file`: ha nincs `egyesitett_*.json`, a nyers `szamlak_*.json`-ra (csak Billingo) esik vissza, figyelmeztetés nélkül. Így Számlázz.hu- vagy fájlból jövő bevétel kimarad, és a CLAUDE.md „egy számla csak egyszer, keresztvalidálva” elve (adatkezeles.md 13.) nem érvényesül. A SKILL ezt a tartalékot nem említi.

**M5. Az évente változó paraméter egy része nem évhez kötött.**
- `struktura.md` 3.: évente változó szám a `config/szabalyok_<év>.json`-ba kerüljön. A költséghányad és a kamara összege/határideje viszont a `vallalkozas.json`-ban van (a `szabalyok_2026.json` fejléce ezt ki is mondja). 2027-től a költséghányad 50%: ha átírják, a 2026-os újraszámolás hibás lesz; ha nem, a 2027-es.
- `adoszamitas.py`: `cfg["ev"] = ev or cfg["ev"]`, így a „config és szabályfájl éve nem egyezik” ellenőrzés gyakorlatilag nem tud kiváltódni.

**K2. A CLAUDE.md 6. szabálya túlállít.** „Azonosító nélkül a skillek nem dolgoznak” – az azonosítót az adatot beemelő scriptek ellenőrzik; az `adoszamitas`, `adoreport`, `helyi-ipa`, `adonaptar` nem. Ez indokolt lehet, de a szabály szövegét pontosítani kell.

**K3. `audits/` státusza.** CLAUDE.md: „a felhasználó saját auditjai (generált, alapból üres)”; README: a `.gitignore` „ajánlott” sorai között a saját auditok. A tényleges `.gitignore`-ban nincs `audits/` (csak az installer adja hozzá), és két audit-fájl **verziózott** (`git ls-files audits/` = 2). Nyilvános sablonnál vagy `audits/` kerüljön a `.gitignore`-ba, vagy a szabály szövege változzon.

**K4. Terminológia.** `hataridok.md`: „sávos IPA”; `helyi-ipa` skill és Htv.: „tételes adóalap (39/A. §)”. Egyik névre kell egységesíteni. Ugyanott az „IPA-előleg (normál): március 15., szeptember 15.” a tételes ágon május 31. – a hatály a vállalkozó választásától függ, a táblázat ezt nem mondja ki.

## 3. Logikai hibák és csendes hibamódok

**M6. Az összegzés „Nem találtam elmaradást a számolható tételeknél” akkor is megjelenik, ha semmit nem lehetett ellenőrizni.** `adoellenorzes.py`: csak `hiba` és `nem_szamolhato` kerül a `findings` listába. A `nem_ellenorizheto` szint (ide tartozik: a NAV-kivonat nem fedi az évet; IPA, kamara és minden nem-NAV-tétel) nem számít. Ha a kivonat régi, minden lejárt határidő ❓, az összegzés mégis „nincs elmaradás”-t mond. A 🔴 sor fent kiírja, de az összegzés félrevezet.

**M7. Lejárt IPA/kamara/éves bevallás határidő sosem jelenik meg elmaradásként.** Ezekhez „nem ellenőrizhető” szint tartozik, és az összegzés nem listázza őket, a `kamara_befizetes_igazolva` pedig a reportban él. Az `adoellenorzes` kimenetében a fontos lejárt, igazolatlan tételek így elvesznek.

**M8. A kapu szövegfeltételre épül.** A `Igazolt tények száma: N` (N ≥ 1) szöveget keresi; egyetlen tény elég. Nem ellenőrzi, hogy a kötelező kérdések (kamara, kedvezmény, IPA-hely, ÁFA-státusz) meg vannak-e válaszolva. A „kapu” tehát azt igazolja, hogy a profil létrejött, nem azt, hogy teljes.

**M9. `azonosito.py`: az adóazonosító jel heurisztikus.** A `RE_ADOAZON` az „Azonosító:” után bármely 10 jegyű számot elfogad (nem csak adóazonosító jelet), és a „leggyakoribb, legalább 2 iratban szereplő” szám lesz a vállalkozóé. Ha egy ügyfél vagy a könyvelő azonosítója gyakoribb, idegen azonosító kerül be, és idegen dokumentum átmegy. A kimenet csak maszkolva mutatja, a felhasználó nem kap kötelező megerősítési kérdést.

**K5. `install.sh` (és valószínűleg az `install.ps1`) a `.env`-et csak három változóval írja újra.** Minden más, a felhasználó által felvett változó elvész. (A `.sh` kódját ellenőriztem; a `.ps1` `WriteAllText` hívását nem néztem végig.)

**K6. A „csendben kihagyja” (kulcs nélkül)** a `usage.md`, README, SKILL szövegekben még szerepel, miközben az `adoellenorzes` már kiírja, mely forrás hiányzik. A dokumentáció elavult; a `nincs-becsles.md` szelleme a kiírást kívánja.

## 4. Törvényi megfelelés: ami az AI-workflow hibája, nem a törvényé

A részletes törvényi audit (`torvenyi-megfeleloseg-audit-2026-11-08.md`) pontjait lásd a `plans/torvenyi-megfeleles-terv.md`-ben. Ide csak a workflow-hibák kerülnek:

- **A 89%-os szabály** minden futásnál csak figyelmeztetés; a szja-összeg a reportban és az `adoellenorzes` összevetésében ✅/✅? jelzést kap. Az ellenőrizetlen alapra épülő „rendben” jelzést a nyitott kérdés mellett fel kell tüntetni az érintett sorokon.
- **A számlázási megfelelőség** (`szamla_ellenorzes.py`) a számlázóprogram mezőit vizsgálja; a nyomtatott számlát nem (szamlazas.md maga is kimondja). Az eredmény „figyelmeztetés”, nem jogi minősítés: jól jelezve van.
- **A bevételi nyilvántartás (Szja tv. 51. § (3))** nincs előállítva, pedig a `bevetel-nyilvantartas.md` leírja a rovatait; szabály nélkül működő kötelezettség.

## 5. Ami rendben van
- Számolás Decimal-lal, scriptben; a NAV-példák önteszttel.
- A kapu ma már a `profil.json`-hoz és az `azonosito.json`-hoz is köt.
- A memória-profil nem tartalmaz ügyfél- és könyvelőneveket (`write_memory`).
- A `.env` ki van zárva a verziókezelésből; a script nem írja ki az értékét.
- A keresztvalidálás megáll ellentmondásnál, a kilépési kódok következetesek (4: azonosító, 5: keresztvalidálás).

## 6. Javasolt sorrend
1. M3, M4, M6, M7 (kicsi, biztos javítások; félrevezető kimenetet szüntetnek meg).
2. M1, M2 (adatkezelési nyilatkozat + maszkolás).
3. M5 (paraméterek évhez kötése) – a 2027-es váltás előtt.
4. M8, M9 (kapu és azonosító erősítése).
5. K-pontok: dokumentáció egységesítése.

## 7. Javítási állapot (2026-11-08, ugyanaznap)

| Pont | Állapot | Mi változott |
|---|---|---|
| M1 (bemeneti személyes adat) | tájékoztatás | a README elején figyelemfelkeltő keret: amit az AI beolvas, a modellszolgáltatóhoz kerül; nincs maszkolás. Maszkoló réteg nem készült (a tulajdonos döntése: elfogadott kockázat) |
| M2 | nyitva | az `azonosito.json` védelme (fájljogosultság) nem változott |
| M3 | javítva | `szamlak/SKILL.md`, `usage.md`, az `adoszamitas` hibaüzenete: az előző év elejétől kért lekérés |
| M4 | javítva | az `adoszamitas` 🔴 figyelmeztet, ha nyers (nem egyesített) számlafájlból számol |
| M5 | javítva | költséghányad és kamara a `config/szabalyok_<év>.json`-ban; a `vallalkozas.json` nem írja felül, eltérésnél figyelmeztet; a sablonból kikerült a költséghányad |
| M6, M7 | javítva | az `adoellenorzes` összegzése felsorolja a nem ellenőrizhető lejárt határidőket, és nem mond „nincs elmaradás”-t, ha ilyen van |
| M8 | javítva | a kapu leáll, ha a kamara-, kedvezmény- vagy IPA-hely kérdésre nincs válasz |
| M9 | javítva | az adóazonosító jel csak jelölt; ellenőrzésre a `--megerosit-adoazonosito` után használható |
| K2, K3, K4, K6 | javítva | CLAUDE.md 6. szabály pontosítva; `audits/` státusza egységes; IPA-terminológia (tételes/hagyományos); „csendben kihagyja” helyett kiírás (a szamlak scriptek üzenetet adnak) |
| K5 | javítva | az `install.sh` és `install.ps1` megőrzi a `.env` egyéb sorait |
| új hiba | javítva | az `install.ps1` 58–60. sorában vezérlőkarakter (`\v` helyett 0x0B) törte a `config\vallalkozas.json` sablonból való létrehozását Windowson |

Nem futtattam éles adattal (nincs `data/`); a `teszt_nav_peldak.py`, `teszt_keresztvalidalas.py`, `teszt_szamla_ellenorzes.py` lefutott, a `load_configs` új logikáját külön próbáltam (eltérő költséghányad: figyelmeztet, a szabályfájl érték nyer).

## 8. Második javítási kör (2026-11-08)

- **M2** javítva: az `azonosito.json` írásakor `icacls`/`chmod 600` (a `.env`-hez hasonlóan).
- **Mellékletek elolvasva** (Szja tv. 1. mell. 4.48., 4. mell., 8. mell. 8–9., 10. mell.; Áfa tv. 4/A. mell.; Art. 50. § (1a)): a törvényi helyek bekerültek az `atalanyado.md`, `afa.md`, `hataridok.md` fájlokba; a törvényi audit 5., 9., 11., 22. sora ezzel 🟡-ról ✅-ra emelhető (az adómentes jövedelemrész, a negyedéves előleg-határidő, a nyilvántartás-vezetés törvényi helye megvan).
- **Kedvezmények számítása elkészült** (`kedvezmenyek.py`, `kedvezmenyek.md`, `teszt_kedvezmenyek.py`): családi, első házasok, személyi, 25 év alatti, négy+/három/két gyermekes és 30 év alatti anyák kedvezménye, a 29/H. § sorrendjében; az éves szja-ra; a hiányzó adatnál NEM SZÁMOLHATÓ.
- **B fázis:** `jogi_kerdesek.py` (9 kérdés törvényi hellyel, a repó jelenlegi kezelésével, a döntés rögzítésével), a számítás és a report jelzi az állapotot; könyvelői kérdéslista: `data/szamitas/konyvelo_kerdeslista.md`.
- **C1:** `bevetel_nyilvantartas.py` (CSV + HTML), az `adoellenorzes` minden futáskor elkészíti.
- **D1–D4:** `nincs-becsles.md` 10–12. pont, jogi forrás szakaszok a SKILL-ekben, évváltási sablon (`config/szabalyok.example.json`).
- Hibajavítás közben: a hivatkozás-ellenőrző csak a törvényrövidítés közvetlen folytatását tulajdonítja a törvénynek.
