# Törvényi megfelelőségi audit: számítások és report-elemek (2026. adóév)

**Dátum:** 2026-11-08. **Hatókör:** a repó számításai (`adoszamitas`, `adoellenorzes`, `helyi-ipa`, `konyvelo-dokumentumok`, `kiadasok-dokumentumok`) és az `adoreport` elemei, egy átalányadózó, főfoglalkozású egyéni vállalkozóra (45% költséghányad).

> Nem adótanácsadás. Az audit azt rögzíti, hogy a repó logikájához találtam-e megfelelő szöveghelyet a `torvenytar/` módosítatlan forrásaiban, és mi az, amit nem találtam vagy nem egyértelmű. Döntési és jogértelmezési kérdésben a könyvelő vagy a NAV az illetékes.

## Módszer és jelölések

Az alábbi törvényszövegeket olvastam a `torvenytar/` mappából: Szja tv. (1995. évi CXVII.), Szocho tv. (2018. évi LII.), Tbj. (2019. évi CXXII.), Htv. (1990. évi C.), az önkormányzati IPA-rendelet (a vállalkozó illetékességi helye szerint), valamint a NAV 2026-os tájékoztatói (átalányadózás alapszabályai, 2026.02.20.; Egyéni vállalkozók szja- és járulékkötelezettsége, 2026.08.31.). A szakaszszámokat a letöltött szövegből vettem, nem emlékezetből. A számítás pontosságát a `teszt_nav_peldak.py` ellenőrzi a NAV számpéldáival (utolsó futás: minden teszt megfelelt).

| Jel | Jelentés |
|---|---|
| ✅ | a törvényszövegben megtaláltam a rendelkezést, és a repó logikája megfelel neki |
| 🟡 | csak NAV-tájékoztatóból vagy adónaptárból igazolt, a törvényi hely nem volt a szövegben |
| ❓ | homályos, a szöveg nem mondja ki, vagy a források ellentmondanak |
| ⛔ | nem szabályozott a repóban, vagy a szükséges törvény nincs a törvénytárban |

**Amit nem olvastam és nem is tárolunk:** az Art. (adózás rendjéről szóló törvény), az Áfa tv., a kamarai törvény, a Szja tv. 1., 4. és 10. számú melléklete. Ami ezektől függ, azt nem tudtam törvényből ellenőrizni.

## 1. Számítások

| # | Számítás | Törvényi hely | Állapot | Megjegyzés |
|---|---|---|---|---|
| 1 | Átalányos jövedelem = bevétel × (1 − 45%) | Szja tv. 53. § (1) a): az egyéni vállalkozó 45 százalék költséghányad | ✅ | A 2027-től érvényes 50%-ot a NAV tájékoztatója a 2025. évi LXXXIV. törvényre hivatkozva közli; azt a törvényszöveget ebben az auditban nem olvastam. |
| 2 | Költség nem csökkenti az adót | Szja tv. 53. § (1) (a költséghányad az átalány) | ✅ | A report ezt a Kiadások szakaszban ki is mondja. |
| 3 | Bevételi határ = 10 × éves minimálbér | Szja tv. 52. § (1) a) | ✅ | Túllépésnél az átalányadózás jogosultsága megszűnik, az adóév egészére át kell térni a vállalkozói jövedelem szerinti adózásra: 52. § (2) ✅. A 80% / 95% figyelmeztetési küszöb a repó saját döntése, nem törvényi. |
| 4 | Időarányos bevételi határ (aktív napok / az adóév napjai) | Szja tv. 50. § (8): a tevékenységet év közben kezdő, megszüntető vagy szüneteltető vállalkozó a határt a tevékenység folytatásának napjaival időarányosan veheti figyelembe | ✅ az elv, ❓ a nevező | A törvény nem mondja ki, hogy az arányosítás nevezője 365 vagy más. |
| 5 | Adómentes jövedelemrész = éves minimálbér fele (1 936 800 Ft) | NAV tájékoztató („az éves minimálbér felét meg nem haladó része”) | 🟡 | A törvényi hely a Szja tv. 1. számú melléklete, amelynek szövege nincs a törvénytárban. Hogy év közbeni kezdésnél nem arányosítandó, ugyancsak NAV-állítás. |
| 6 | Szja = 15% | Szja tv. 8. § (1) | ✅ | |
| 7 | **89%-os szabály** | Szja tv. 29. §: ha a magánszemély szocho-fizetésre kötelezett, a megállapított jövedelem 89 százalékát kell figyelembe venni; 47. § (5): ugyanez az adóelőleg-alapnál | ❓ | **A repó nem alkalmazza**, és a NAV 2026-os számpéldája sem. A törvényszöveg és a NAV-példa látszólag ellentmond; a feloldást nem találtam meg a rendelkezésre álló szövegben. Lásd a 4. fejezetet. |
| 8 | Szja-előleg: nincs előleg-kötelezettség addig, amíg az előleg-alap az éves minimálbér felét nem haladja meg, utána csak a feletti rész után | Szja tv. 47. § (4a) | ✅ | |
| 9 | Negyedéves göngyölt előleg és bevallás | Szja tv. 46. § (9)–(10): a negyedéves előleget negyedéves bontásban kell bevallani | ✅ a negyedéves bontás, 🟡 a határidők | A határidők forrása az adónaptár és a NAV tájékoztató; az Art. nincs a törvénytárban. |
| 10 | A bevétel megszerzésének időpontja (jóváírás napja, Billingo `paid_date`) | Szja tv. 9. § (2) a) | ✅ | A szöveg kivételt is tartalmaz arra az esetre, ha a kifizető átutalja az összeget; a repó a Billingo `paid_date`-jét használja, ez a kifizető teljesítési napjától eltérhet. |
| 11 | Átalányadózó bevételének nyilvántartása | Szja tv. 51. § (1): a bevételeket a 10. számú melléklet szerint kell figyelembe venni | ❓ | A 10. számú melléklet szövege nincs meg. |
| 12 | Devizás bevétel forintosítása a számlán alkalmazott árfolyammal | Szja tv. 6. § (2a) a) és (4) b) | ✅ a szabály, ❓ az alkalmazhatósága | Nem ellenőrzött, hogy az alanyi adómentes, külföldi vevős ügyletnél az áfa-alap árfolyama alkalmazandó-e. |
| 13 | Tbj mértéke 18,5%, szocho mértéke 13% | Tbj. 25. § (1); Szocho tv. 2. § (1) | ✅ | |
| 14 | Szocho/tbj járulékalap negyedévente göngyölve: az átalányban megállapított, szja-köteles jövedelem, csökkentve a korábbi negyedévek alapjával, elosztva a jogviszony hónapjaival, de legalább a minimum | Szocho tv. 6. § (2) | ✅ | A repó képlete (`max(szja-alap − korábbi alap, minimum)`) megfelel ennek. |
| 15 | Minimális alap: legalább a minimálbér; a jogállás fennállásának minden napjára legalább a minimálbér harmincad része | Szocho tv. 6. § (3) | ✅ | Az 1/30 szabályt a NAV tájékoztatója is rögzíti. |
| 16 | **Melyik „minimálbér”: minimálbér vagy garantált bérminimum** | Tbj. 3. § 14.2.: járulékfizetési szabályoknál a garantált bérminimum, ha az egyéni vállalkozó személyesen végzett főtevékenysége legalább középfokú végzettséget vagy szakképzettséget igényel | ❓ | A repó jelenleg a minimálbérrel (322 800 Ft) számol, a felhasználó döntése alapján, megerősítés nélkül. Hogy egy adott tevékenység (pl. szoftverfejlesztés) középfokú végzettséget igényel-e, azt hivatalos forrás nem mondja ki. A Szocho tv. szövege a 6. § (3)-ban „minimálbért” mond, a garantált bérminimum fogalma ott nem szerepel. Lásd a 4. fejezetet. |
| 17 | IPA mértéke legfeljebb 2% | Htv. 40. § c) ✅; az önkormányzati rendelet mértéke ✅ | ✅ | A rendelet hatályos szövegét a `helyi-ipa` skill tölti le; az oldalak saját annotációi néhol következetlenek. |
| 18 | IPA tételes adóalap: bevétel ≤ 12 / 18 / 25 millió Ft → 2,5 / 6 / 8,5 millió Ft, 12 hónapnál rövidebb adóévnél napi arányosítással | Htv. 39/A. § (1)–(3) | ✅ | A sávot a script az időarányos határok szerint választja. |
| 19 | A tételes adózás bejelentése: az adóév 5. hónapjának végéig, új tevékenységnél a bejelentkezési nyomtatványon | Htv. 39/A. § (4) | ✅ a szabály, ❓ a teljesülése | A repó nem tudja, hogy a bejelentés megtörtént-e. |
| 20 | Tételes adózónál nincs mentesség, kedvezmény | önkormányzati rendelet (tételes adózó kizárása a kedvezményekből) | ✅ | |
| 21 | IPA-előleg és megfizetés: az adóév 5. hónapjának utolsó napjáig előleg, a következő év 5. hónapjának végéig az adó | Htv. 39/A. § (7), (9) | ✅ | Ha az előleg határideje a tevékenység (újra)indulása előtt volt, hogy ez előleg-kötelezettséget jelent-e, ❓. |
| 22 | Bevallások határideje (negyedév utáni hó 12-e, 25SZJA május 20.) | Szja tv. 12/C. § (6) említi a május 20-át a bevallási tervezetnél ✅; a 12-e az adónaptárból és a NAV tájékoztatóból | 🟡 | Az Art. nincs a törvénytárban. Az adónaptár a munkaszüneti napot már figyelembe veszi. |

## 2. Report-elemek

| Report-elem | Mire épül | Állapot |
|---|---|---|
| Hero mutatók (bevétel, számított szja, átalányos jövedelem) | 1., 6., 10. sor | ✅ |
| Bevételi határ és adómentes keret kihasználtság | 3., 4., 5. sor | ✅ a határ, 🟡 az adómentes keret, ❓ a nevező |
| Vállalkozás adatai | `config/vallalkozas.json` és profil | nem jogi tartalom; a minimális alap típusa „nem megerősített”-ként jelölt |
| Bevételek (havi, ügyfelenként, devizás) | 10., 12. sor | ✅ / ❓ |
| Kiadások (PDF számlák) | 2. sor; az ÁFA levonhatóságára az Áfa tv. kellene | ✅ a költség-szabály, ⛔ az ÁFA-levonás |
| Adó (negyedéves szja, tbj, szocho; NAV-befizetések) | 6., 8., 9., 13–16. sor | ✅, kivéve a 7. és 16. sort |
| Határidők | 22. sor | 🟡 |
| Könyvelői dokumentumok | a könyvelő összegeinek összevetése a számítottal; levezetett járulékalap | nem jogi; az eltérés ok-megállapítása a repó adataiból nem lehetséges |
| Beküldött bevallások | nyilvántartás a PDF-ekből; a NAV-előírás megléte | a beadás napját nem állítja; ez a törvényből nem is vezethető le |
| Iparűzési adó (éves összeg, kártya) | 17–21. sor | ✅ a számítás, ❓ a bejelentés és az előleg |
| Tennivalók | a feltételek a beállításokból és a számításból jönnek | segédelem |
| A vállalkozás története | irat-alapú tények forrással | nem jogi értelmezés; a szünetelés jogi hatása ❓ (4. fejezet) |

## 3. Kimondottan nem fedett terület

- **Bevételi nyilvántartás:** a Szja tv. 51. § (3) szerint az átalányadózó, ha az áfa-levonási jogát nem érvényesíti, a pénztárkönyv (naplófőkönyv) bevételi adatait vezeti, és a költségbizonylatokat megőrzi. A repó ilyen nyilvántartást nem állít elő ⛔; a rovatok csak a `bevetel-nyilvantartas.md` szabályfájlban vannak leírva.
- **Áfa:** az alanyi adómentesség, az uniós vevőkre vonatkozó összesítő nyilatkozat, az ÁFA levonhatósága a bejövő számláknál. Az Áfa tv. nincs a törvénytárban ⛔.
- **Kedvezmények** (családi, személyi, családi járulékkedvezmény): ha a felhasználó nem jogosult egyikre sem (rögzítve), a számítás helyes; ha jogosult, a számítás nincs implementálva ⛔ (frissítve 2026-11-08).
- **Kamarai hozzájárulás:** a kamarai törvény (1999. évi CXXI.) letöltve, a 34/A. § alapján a repó számolja (évi 5 000 Ft, március 31., a teljes évi szünetelés a mentesség); a befizetés igazolása hiányzik, a mentesség feltételeinek teljesülését a repó nem ellenőrzi (frissítve 2026-11-08, az audit eredeti állapota ⛔ volt).
- **Helyesbítő (önellenőrző) bevallás:** a repó nem számol vele.

## 4. Homályos vagy ellentmondó pontok, amelyeket tisztázni kell

1. **89%-os szabály (Szja tv. 29. §, 47. § (5)) vs. NAV-példa.** A törvényszöveg a szocho-fizetésre kötelezett magánszemély jövedelmének 89%-át írja elő, a NAV 2026-os számpéldája és a repó ezt nem alkalmazza. Ha a törvényszöveg az átalányadózó egyéni vállalkozóra is vonatkozik, a számított szja (és az előleg) eltér. **Kinek: könyvelő / NAV.** Ez a legnagyobb, ellenőrizetlen kockázat a jövedelem-számításban.
2. **Minimális járulékalap típusa.** A Tbj. 3. § 14.2. a garantált bérminimumot írja elő, ha a főtevékenység legalább középfokú végzettséget vagy szakképzettséget igényel; a szoftverfejlesztésről hivatalos forrás nem mond semmit. Ha a garantált bérminimum az irányadó, a már beadott negyedéves bevallások helyesbítése szükséges lehet. **Kinek: könyvelő / NAV.**
3. **A töredék hónap napjai.** Ha a könyvelő összegéből levezetett járulékalap napjainak száma eltér a hivatalos iratok szerinti indulási naptól számítottól, tisztázni kell: a Szocho tv. 6. § (3) szerint az alap a jogállás fennállásának minden napjára számít. **Kinek: könyvelő.**
4. **A szünetelés jogi hatása.** A Szocho tv. 6. § (3) a „jogállás fennállására” épül. A repó a szünetelő időszakot kötelezettség nélkülinek tekinti, ha a NAV adószámláján nincs rá előírás, de azt, hogy a szünetelés alatt a jogállás fennáll-e a járulék szempontjából, ebben az auditban nem döntöttem el (az Evectv. szövege megvan, nem vizsgáltam). **Kinek: könyvelő / NAV.**
5. **Időarányosítás nevezője** (bevételi határ és IPA): a törvény nem mondja ki, a repó 365-tel számol, mindkét helyen. **Kinek: könyvelő.**
6. **Az adómentes jövedelemrész törvényi helye** (Szja tv. 1. számú melléklet) nincs a törvénytárban; csak a NAV tájékoztatóra támaszkodunk. A 4. és 10. számú melléklet hiánya ugyanígy érinti a bevétel-elszámolás szabályait.
7. **Bevétel időpontja kifizetői átutalásnál:** a 9. § (2) a) szövege kivételt ad arra az esetre, ha a kifizető átutal. A Billingo `paid_date` ettől eltérhet.
8. **Devizás számlák árfolyama:** a 6. § (2a) a) alkalmazhatósága alanyi adómentes, külföldi vevős ügyletnél nem ellenőrzött.
9. **Tételes IPA választása:** a repó nem tudja, hogy az adóév 5. hónapjáig bejelentették-e (Htv. 39/A. § (4)). Ennek hiányában a hagyományos adóalap lehet az érvényes; újrainduló vállalkozásnál az előleg-határidő a folytatás előtt is eshet.
10. **ÁFA-státusz:** ha a számlázóprogram adatai nem jelölik alanyi adómentesként az eladót, de az iratok szerint az, a számlázóprogram beállítását javítani kell; a közösségi adószám megállapítását igazoló irat és a számlázóprogram adata egyezését ellenőrizni kell. (Frissítve 2026-11-08: az Áfa tv. letöltve, a hatás: lásd a „Frissítés” szakaszt.)
11. **Határidők:** az Art. hiányában a határidők forrása az adónaptár és a NAV tájékoztató, nem a törvényszöveg.
12. **A „nem ellenőrzött” jelzések és a küszöbök** (80% / 95% figyelmeztetés) a repó saját döntései, nem törvényi előírások.

## 5. Javasolt következő lépések

1. Töltsd le a hiányzó jogforrásokat (Art., Áfa tv., a Szja tv. 1., 4., 10. melléklete, kamarai törvény) a `nav-forrasok` skillel, majd futtasd újra ezt az auditot.
2. Vidd a 2., 3., 4. és 5. pontot a könyvelőhöz; vedd fel a 89%-os kérdést is.
3. Generáld a bevételi nyilvántartást (Szja tv. 51. § (3)).
4. Kérd a könyvelőtől a tételes IPA-bejelentés igazolását és a beadási igazolásokat.

## Frissítés (2026-11-08): az Áfa tv. letöltve

Az `input/torveny/` mappába tett jegyzet hivatkozásából letöltöttük a 2007. évi CXXVII. törvényt (`torvenytar/afa-tv/2026/`). Az alábbi pontok a szövegből ellenőrzöttek (részletek: `.claude/rules/afa.md`):

| Pont | Törvényi hely | Állapot |
|---|---|---|
| Alanyi adómentesként nem vonható le a bejövő számla ÁFA-ja; csak ÁFA nélküli számla adható ki | Áfa tv. 187. § (2) | ✅ |
| Az alanyi adómentesség értékhatára 20 000 000 Ft (előző év tényleges, tárgyév várható/tényleges) | 188. § (1)–(2) | ✅; a tárgyévi bevételt az `adoszamitas` mutatja |
| Az értékhatárba a belföldön teljesített ügyletek számítanak; az uniós adóalanynak nyújtott szolgáltatás teljesítési helye másik tagállam | 2. § a); 37. § (1) | ✅ a szabály, ❓ a gyakorlati alkalmazása (könyvelő) |
| Összesítő nyilatkozat szolgáltatásnyújtásról | 4/A. számú melléklet, Art. | ⛔ a melléklet szövege és az Art. nincs a törvénytárban |
