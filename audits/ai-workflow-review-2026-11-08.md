# AI-workflow review: kiadás előtti átvilágítás (2026-11-08)

> Hatókör: CLAUDE.md, `.claude/rules/`, a skillek SKILL.md-i és a scriptek (a külső `graphify` és `design-taste-frontend` skill kivételével), install.sh/ps1, README, usage, todo, audits, torvenytar összefoglalók.
> Módszer: a fájlokat és a scriptek kódját elolvastam, a jogi hivatkozásokat a `torvenytar/` letöltött szövegével vetettem össze (Áfa tv. 163. §, 169. § n), Szja tv. 29. §, 47. § (5)). **A scripteket nem futtattam**, ezért a futásidejű viselkedésről csak a kód alapján állítok. Amit nem néztem meg, azt jelzem.
> Nem adótanácsadás: a jogi pontoknál az a kérdés, ellentmond-e a repó önmagának vagy a letöltött törvényszövegnek; a jogértelmezést a könyvelő/NAV dönti el.

---

## 1. rész: vállalkozás-specifikus adat a sablonban (ellenőrzőlista)

A sablon kiadása előtt ellenőrizni kell, hogy a fejlesztő saját vállalkozásának adata nem maradt-e bent. A vizsgálatkor az alábbi **kategóriákat** találtam; ezeket a takarítás után újra kell ellenőrizni (`grep`-pel a vállalkozás nevére, ügyfeleire, könyvelőjére, településére, dátumaira, összegeire):

1. `.env`: élő API-kulcs. Nincs git-repó, mappamásolással kiszivárog; a kiadásból mindig kizárandó.
2. `.claude/memory/`: a generált vállalkozói profil (ügyfélnevek, könyvelő, időrend, települések). **A kapu is erre épül** (lásd B2): ha bent marad, a kapu eleve nyitva van idegen profillal.
3. Személyes levelek, teendőlisták, korábbi auditok a gyökérben és az `audits/` alatt (saját számok, nevek, település).
4. Vállalkozásra szabott összefoglalók a `torvenytar/` alatt (saját bevétel, kezdődátum, tevékenységre szabott háttérelemzés, a székhely szerinti önkormányzati rendelet).
5. Közös szabályfájlokba került személyes tények (pl. az `afa.md`-ben a számlázóprogram-státusz, a közösségi adószám igazolása).
6. Scriptekben beégetett saját tények: kiírt figyelmeztetések konkrét dátumokkal, a tesztekben valós havi bevételek, saját esetre kódolt űrlap-besorolások, beégetett évszámok.
7. A SKILL.md-kben mintaként használt konkrét településnevek.
8. Harmadik fél szerzői joggal védett tartalma (pl. blogcikk az adónaptárhoz).
9. `__pycache__` és más generált fájlok (a beégetett szövegeket is tartalmazhatják).

Azonosítót (adószám, adóazonosító, e-mail, telefon, bankszámla, cím) a vizsgálatkor nem találtam. A `docs/` ábráin és forrás-JSON-jaiban nem volt személyes adat.

**Javaslat:** a kiadás tiszta exporttal, fehérlistával készüljön új mappába; a fejlesztő saját munkamappája érintetlen marad. A takarítás megtörtént; a fenti kategóriák a jövőbeli kiadásoknál is ellenőrzőlistaként használhatók.

---

## 2. rész: logikai ellentmondások, működési hibák, jogi eltérések

Súlyosság: **B** = kiadási blokkoló, **M** = ügyfeleknél hibás eredményt vagy téves állítást ad, **K** = kisebb/dokumentációs.

### B1. A `config/` üres, és semmi nem hozza létre a sablonjait (B)
- A CLAUDE.md, README, adatkezeles.md szerint a `config/vallalkozas.json`, `config/szabalyok_<év>.json`, `config/iratrend.json` létezik. A repóban csak `config/.gitkeep` van, és **egyetlen script/telepítő sem generálja őket** (a `grep` a `.py/.sh/.ps1` fájlokban csak olvasást/módosítást talált).
- Következmény (kódból): `adoellenorzes.py:118` kezeletlen `FileNotFoundError`; `dokumentumok.py:351/500/524/536` ugyanígy; `adoszamitas.py:56-58` leáll („hiányzik a szabályparaméter-fájl”). Az első lépés (`vallalkozas-dokumentumok`) a `config/iratrend.json`-ra épül (`dokumentumok.py:35`); azt, hogy hiányában mit csinál, **nem néztem meg**.
- A `usage.md`/`install.*` „következő lépések” szerint az ügyfél a skillekkel kezd: ez ma elakad. Kell: `vallalkozas.example.json` (null mezőkkel, mert a CLAUDE.md szerint a `null`-t a felhasználó tölti), `szabalyok_2026.json` (a `.claude/rules/atalanyado.md` és `jarulek-szocho.md` számaiból), `iratrend.json` általános szabályokkal.

### B2. A „kapu” egy szövegminta, és a kiadott profil megkerüli (B)
- `adoellenorzes.py:103-116`: a kapu azt vizsgálja, hogy létezik-e a memóriafájl, és szerepel-e benne az „Igazolt tények száma: N” szöveg N ≥ 1. Nem ellenőrzi, hogy a profil az adott `config/vallalkozas.json`-hoz/azonosítóhoz tartozik.
- Ha a mostani profil bent marad (1. rész, 2. kategória), az ügyfél kapuja nyitva van egy **idegen vállalkozás** adataival. A CLAUDE.md 5. szabálya („ezt a kaput nem szabad megkerülni”) így a kiadott állapotban már maga is megkerülve érkezik.

### B3. Adatvédelmi tervezési ellentmondás: a személyes profil „verziózott” (B)
- adatkezeles.md: `config/` és `.claude/memory/` **verziózott = igen**; a profil és a `vallalkozas.json` viszont ügyfélneveket, időrendet, települést, státuszt tartalmaz. A `.gitignore` ezeket nem védi (csak `.env`, a venv, `graphify-out/`; az install a `data/ archive/ input/ tax-reports/` sorokat adja hozzá, a profilt, `config/vallalkozas.json`-t, `todo.md`-t, `level-*.md`-t nem).
- Ellentmond a CLAUDE.md-nek (adószám/név ne kerüljön a `.claude/memory/`-ba), és az adatkezeles.md 9. szabályának: a profilban **ügyfélnevek és a könyvelő neve** szerepelnek („Szerződések, ügyfelek, szolgáltatók”). A profil fejléce szerint „személyes azonosítót nem tartalmaz”, ami az adószámra/címre igaz, de a névre nem.
- Ha az ügyfél a repót GitHubra tolja (a repó erre van felkészítve), a saját profilja és az ügyfelei nevei publikussá válnak. Javaslat: a profil és a `vallalkozas.json` kerüljön `.gitignore`-ba, a repóban csak `*.example.*` sablon legyen.

### B4. A scriptek minden ügyfélnek a fejlesztő saját tényeit állítják (B)
- `adoszamitas.py:293-298` feltétel nélkül kiírta egy konkrét vállalkozás szünetelési időszakát és egy rögzített napra datált „ellenőrizve” állítást (azóta általánosítva). Egy másik vállalkozásnál ez **hamis állítás**, ami sérti a `nincs-becsles.md` 3–4. pontját. A 297. sorban hivatkozott „ellenőrzés” egyetlen napon, egyetlen Billingo-fiókon történt, a szöveg mégis általános ténynek hat.
- `bevallasok.py:82`: minden „25EGYSZA” nyomtatvány „2025”-ös és a `nav/2026/` mappába kerül; ez 2027-ben hibás. Az „ADÓSZÁMLA KIVONAT” feltétel nélkül „épitmenyado-kivonat”.
- A kódban több beégetett évszám van (2025/2026, `25SZJA`, `25HIPAK`, `2658` űrlapszámok): az eszköz **2026-os adóévre** készült. Ezt a README nem mondja ki; 2027-től (költséghányad 50%, új űrlapkódok, új minimálbér) minden évben kézi frissítés kell.

### M1. Az indulás előtti határidők eltüntetése ellentmond a profilnak (M)
- `adoellenorzes.py:204-210`: minden, a `vallalkozas_kezdete` előtti határidő „nem releváns”, nem ellenőrzett és nem jelzett. De a `vallalkozas_kezdete` az **újraindulás** napja (a vállalkozás lehet régebbi, szünetelés után folytatódó).
- Így kiesik pl. a márc. 31-i kamarai hozzájárulás (ha a profil szerint kötelezett), az előző évi éves bevallás (máj. 20.) és a január 12-i határidők, miközben ezekhez a profilban igazolt tények lehetnek. Ugyanez a „kezdés” logika az `adoszamitas.py`-ban is egyetlen `start`-ként szerepel.
- A kettő különválasztandó: első indulás, újraindulás, szünetelés.

### M2. Szünetelés/megszakítás nincs modellezve, miközben a szabályfájl rá hivatkozik (M)
- `atalanyado.md`: „év közbeni kezdés, megszűnés **vagy szünetelés** esetén időarányos”. A kód (`adoszamitas.py:132-144, 120-129, 170-175`) csak `vallalkozas_kezdete` + `vallalkozas_megszunese` párt ismer, **év közbeni szünetelést nem**. Egy ügyfélnél, aki az év közben szünetelt, a minimális járulékalap és az időarányos határ hibás.
- `adoreport.py:~579` külön, a profilból olvasott szünetelés-logikát használ csak a szöveghez, az `adoszamitas` nem.

### M3. A szabályfájl és a kód ellentmond a TB-státuszban (M)
- `jarulek-szocho.md` táblázata felsorolja a „heti 36 órás munkaviszony vagy nappali tagozat melletti vállalkozót” (18,5% / 13%), a kód viszont (`adoszamitas.py:156-157`) csak `fofoglalkozasu` és `nyugdijas` értéket fogad el, mást `érvénytelen tb_statusz` hibával leállít. A **mellékállású** ügyfél (tipikus célcsoport) így nem használhatja az eszközt, és a szabályfájl ezt nem jelzi. Hogy náluk a minimális alap hogyan alakul, a repó szabályfájlja nem mondja ki; ezt nem tudom.

### M4. A 89%-os szabály a letöltött törvényszövegben van, a számításban és a figyelmeztetésekben nincs (M)
- Szja tv. 29. § (a repó törvényszövegében): ha a magánszemély szocho-fizetésre kötelezett, a megállapított jövedelem **89%-át** kell figyelembe venni; 47. § (5) ugyanez az adóelőleg-alapnál. A `adoszamitas.py` nem alkalmazza, és **nem is figyelmeztet rá**: a `grep` sem a scriptekben, sem a reportban nem talál „89”-et. A NAV 2026-os számpéldája sem alkalmazza, ezért az audit „ellenőrizetlen kockázatként” nyitva hagyta.
- Az ügyfél felé az eszköz az szja-számot a kimenetben ellenőrzöttként adja, a nyitott jogi kérdés csak az audits mappában van. A kiadott ügyfélverzióban a `adoszamitas` figyelmeztetései közé be kell tenni (a döntés a könyvelőé/NAV-é).

### M5. Csendes forráskihagyás alulszámolt bevételhez vezethet (M)
- `szamlazz_szamlak.py:13, 72-74`: kulcs nélkül „csendben kilép (0), nem ír ki semmit”; az `adoellenorzes.py:137-138` az ilyen sorokat el is dobja. Ha az ügyfél Számlázz.hu-t használ, de elfelejtette a kulcsot, a bevétel a Billingo-adatból **alulszámolva** jelenik meg, jelzés nélkül. Ez a `nincs-becsles.md` szellemével ellentétes. Javaslat: a riport mondja ki, mely bevételi források voltak beállítva és melyek hiányoztak. (A többi lekérő script kulcs nélküli kimenetét nem olvastam végig.)

### M6. Részben fizetett számla nem számít bevételnek (M, ismert korlát)
- `adoszamitas.py:111-112, 303-304`: a „partial” számla teljesen kimarad, holott a beérkezett rész már bevétel (a `bevetel-nyilvantartas.md` szerint a pénz beérkezése számít). A kód ezt figyelmeztetéssel jelzi, de a bevételi határ és az szja így alulszámolt lehet.

### M7. Az azonosító-ellenőrzés gyenge (M)
- `azonosito.py:89-90`: az ellenőrzés a teljes szövegből kiszedett számjegyfolyamban (`sima`) keresi a saját adószámot/azonosítót **részsztringként**; két szomszédos szám összefolyva álpozitívot adhat, és az átment egy olyan idegen dokumentum is, amely csak megemlíti a saját azonosítót.
- `azonosito.py:53-57`: az adóazonosító jelet az iratok szövegéből a leggyakoribb 10 jegyű, „Azonosító:”-val jelölt szám adja (`most_common`). Hogy ez valóban a vállalkozóé-e (nem egy ügyfél vagy a könyvelő azonosítója), nincs ellenőrizve.
- A CLAUDE.md 6. szabálya („minden dokumentumot validálunk”) így erősebbet állít, mint amit a kód garantál.

### M8. Az adónaptár forrása harmadik fél cikke, szűkebb hatállyal, mint az eszköz állítása (M)
- `input/adonaptar/2026.md` fejléce: a táblázat „alanyi adómentes, átalányadózóknak készült, akiknek **nincsenek külföldi ügyleteik és munkavállalóik**”, és a **szünetelést nem tartalmazza**. A `hataridok.md` szerint a feldolgozott adónaptár a határidők irányadó forrása. Egy külföldi vevőkkel dolgozó vagy szünetelő ügyfélnél ez a hatály nem teljesül, a report ezt mégsem jelzi.
- A szöveg szerzői joga és a szerző megnevezése miatt a terjesztése nem javasolt; az ügyfél töltse be a saját naptárát, vagy a `nav-forrasok` hivatalos NAV-forrásból készüljön.

### M9. Hivatkozott szakaszok: amit ellenőriztem, és ami ellentmondás
- **Rendben:** Áfa tv. 163. § (2) a) (számla a teljesítés hónapját követő hónap 15. napjáig a fordított adózású esetben) és 169. § n) („fordított adózás” kifejezés) szövege megegyezik a `szamlazas.md` és a `szamla_ellenorzes.py` állításával (`163. §` szöveg az `afa-tv` fájlban).
- **Korlát:** a 163. § (2) a) ellenőrzés csak akkor fut, ha a vevő uniós, a tétel `ÁTHK` és a jogcím `EUFAD37` (Billingo-jelölések). Nem uniós (pl. amerikai) vevőnél a határidőt nem ellenőrzi; a `MENTES` lista a kód szerint „nem teljes”.
- **Nyitott:** az összesítő nyilatkozat (4/A. melléklet, Art.) nincs a törvénytárban; a repó ezt több helyen jelzi, rendben.

### K1. Belső ellentmondások a dokumentumokban (a vizsgálatkori állapot, általánosítva)
- Egy vállalkozásra szabott összefoglaló elavult adatokat tartalmazott (más kezdőnap és napszám, mint a többi fájlban; szünetelésről és Áfa-státuszról ellentmondó állítások). Ilyen fájl a sablonba ne kerüljön; az összefoglalókat a script generálja.
- A minimális alap típusáról több dokumentum ellentmondó állítást tett (beállított érték, döntés, megerősítettség). A beállítás egyetlen forrása a `config/vallalkozas.json` legyen, a dokumentumok csak hivatkozzanak rá.
- `adatkezeles.md`: a szabályok sorszámozása 10, 12, 13, 11 sorrendű; az `archive/` a CLAUDE.md szerint a feldolgozás után ürítené az `input/`-ot, de a memória-kivonat és a bent maradó nyers fájl állapota nem egyezett.
- `.claude/rules/struktura.md` kéri a CLAUDE.md táblázatának frissítését; a CLAUDE.md `data/kiadasok/`-t kétszer sorolja fel.

### K2. A `helyi-ipa` webes keresést használ a településnévvel
- `helyi-ipa/SKILL.md:18`: WebSearch/WebFetch a rendeletért. A CLAUDE.md tiltja a személyes adat külső szolgáltatásnak küldését; a településnév székhelyre utal. Kis kockázat, de a README „alapelvei” között nem szerepel, hogy a skill külső kérést indít.

---

## 3. Mi működik jól (a review során ellenőrizve)
- Minden skill hivatkozza az adatkezelési és a „nincs becslés” szabályt; a számítás Decimal-aritmetikával, a NAV számpéldáit tesztelő önteszttel készül.
- A gyors-számítási táblázat a `jarulek-szocho.md`-ben a megadott mértékekkel egyezik (a szorzatok megfelelnek).
- Az Áfa tv. hivatkozások (163., 169. § n), 187. § (2)) a letöltött szöveggel egyeznek.
- A beérkező dokumentumok azonosító-ellenőrzése, a keresztvalidálás megállása (4-es/5-ös kilépési kód) és a „NEM SZÁMOLHATÓ” kimenet a tervezett irányba mutat.

## 4. Javasolt sorrend a kiadás előtt
1. Tiszta export fehérlistával (1. rész); `.env` soha nem kerül bele.
2. B1: konfig-sablonok + a hiányzó fájlokat elegánsan kezelő hibaüzenetek.
3. B2/B3: profil és `vallalkozas.json` `.gitignore`-ba; a kapu a profilt a `vallalkozas.json`-hoz/azonosítóhoz kösse; a profilban ne legyenek ügyfélnevek.
4. B4: a beégetett üzenetek és az `bevallasok.py` speciális besorolások kivétele/paraméterezése; teszt valós adatok helyett kitalált adatokkal.
5. M1–M3: szünetelés/újraindulás modell, TB-státuszok, a 89%-os szabály figyelmeztetése.
6. M5, M7: forrásállapot a riportban, erősebb azonosító-ellenőrzés.
7. A README mondja ki: 2026-os adóévre készült, nem adótanácsadás, és mely forrásokat kell az ügyfélnek saját magának betöltenie (adónaptár).
