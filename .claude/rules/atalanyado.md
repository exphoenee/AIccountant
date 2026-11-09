# Átalányadózás (egyéni vállalkozó) – 2026

> Forrás: `torvenytar/docs/atalanyado-szabalyok-osszefoglalo.md` (NAV, Szja tv.). Az évente változó számokat itt kell frissíteni, a többi fájl ide hivatkozik.

## Alapszámok (2026)

| Adat | Érték |
|---|---:|
| Havi minimálbér | 322 800 Ft |
| Garantált bérminimum (középfokú végzettséget igénylő főtevékenység) | 373 200 Ft |
| Éves minimálbér | 3 873 600 Ft |
| Éves bevételi határ (általános) | 38 736 000 Ft (10 × éves minimálbér) |
| Éves bevételi határ (kizárólag kiskereskedelem / postai közreműködő) | 193 680 000 Ft (50 ×) |
| Adómentes jövedelemrész (éves minimálbér fele) | 1 936 800 Ft |
| Szja-kulcs az adóköteles rész után | 15% |

- **Év közbeni kezdés, megszűnés vagy szünetelés esetén a bevételi értékhatár időarányos** (NAV: `torvenytar/docs/NAV/2026/atalanyado-alapveto-szabalyai-2026-02-20.txt`; Szja tv. 50. § (8): a tevékenység folytatásának napjaival időarányosan). Számítás: határ × aktív napok / az adóév napjai. A törvény a nevezőt nem mondja ki; a naptári napok / 365 értelmezést használjuk, ez **nem ellenőrzött**.
- **Az adómentes jövedelemkeret (1 936 800 Ft) év közbeni kezdésnél nem arányosítandó** (ugyanott: „nem kell arányosítani, akkor is az 1 936 800 forintos határral számolhat").
- A tbj/szocho minimális alapja töredék hónapban naptári naponként a járulékalap **harmincad része** (ugyanott); lásd `jarulek-szocho.md`.

## Költséghányad és jövedelem

**Jövedelem = vállalkozói bevétel × (100% − költséghányad)**

| Tevékenység | Költséghányad | Jövedelem |
|---|---:|---:|
| Minden egyéb tevékenység | 45% | bevétel 55%-a |
| Meghatározott ipari, mezőgazdasági, szolgáltatási tev. (építőipar, fodrászat, gépjárműjavítás, vendéglátás, taxi, oktatás stb.) | 80% | bevétel 20%-a |
| Kizárólag kiskereskedelem (vendéglátás kivételével), postai közreműködő | 90% | bevétel 10%-a |

- A tényleges költségek, értékcsökkenés és az elhatárolt veszteség **nem** vehető figyelembe; minden költséget az átalány elszámoltnak tekint. A korábbi veszteség nem csökkenti az átalányos jövedelmet.

## Szja számítása

1. Éves bevétel × (1 − költséghányad) = átalányos jövedelem.
2. Az átalányos jövedelem **1 936 800 Ft-ig adómentes**.
3. A fölötti rész az összevont adóalapba kerül, **15% szja**.
4. Az adókedvezmények (családi, 25 év alattiak, személyi kedvezmény) az adóköteles rész után érvényesíthetők.

**Példa:** bevétel 7 000 000 Ft → jövedelem (45%) 3 850 000 Ft → adómentes 1 936 800 Ft → adóköteles 1 913 200 Ft → szja 286 980 Ft.

45% költséghányadnál az adómentes sáv kb. **3 521 455 Ft** éves bevételig tart (1 936 800 / 0,55). Efölött keletkezik szja-előleg-kötelezettség.

## Jogosultság

- Az egyéni vállalkozói tevékenység egészére választható; év közben kezdő is bejelentheti a NAV-nak; az előző évi bevételt nem vizsgálják.
- **Megszűnik**, ha a NAV számla- vagy nyugtaadási mulasztás miatt mulasztási bírságot szab ki.
- Ha a jogosultság év közben megszűnik (pl. bevételi határ túllépése), az **az adóév elejéig visszamenőleg** szűnik meg: részletes bevételi és költségnyilvántartást/pénztárkönyvet kell vezetni, és a teljes évre vállalkozói szja-szabályok szerint kell adózni.
  - Ezért a bevételi határ közelítésekor **mindig figyelmeztess** (lásd `bevetel-nyilvantartas.md`).

## Ellenőrizendő / nyitott pontok

- **89%-os szabály (Szja tv. 29. §, 47. § (5)):** a letöltött törvényszöveg szerint, ha a magánszemély szocho-fizetésre kötelezett, a megállapított jövedelem 89%-át kell figyelembe venni; a NAV számpéldája és a repó számítása ezt nem alkalmazza. **Feloldatlan**, az `adoszamitas` minden futásnál kiírja; döntés: könyvelő / NAV.
- **Alkalmazási évek:** a repó a 2026. adóévre készült (űrlapkódok: 2658, 25SZJA, 25HIPAK; a számok a `config/szabalyok_<év>.json`-ban). Új évhez új szabályfájl és az adónaptár kell.

- **Megerősítve (NAV, 2026):** a 45%-os költséghányad 2026. január 1-jétől érvényes, **2027-től 50%** (`torvenytar/docs/NAV/2026/kedvezo-valtozasok-az-atalanyadozasban.txt`; 2025. évi LXXXIV. törvény 3. § a) pont). Ugyanott: 45%-os költséghányadnál az adómentes bevétel 2026-ban 3 521 455 Ft-ig tart.
- A költséghányad nem a bejelentett tevékenységtől, hanem attól függ, mely tevékenységből származik a bevétel, ami a kiállított bizonylatból állapítható meg (NAV PDF, 3.).
- A vállalkozás TEÁOR-ja és a bizonylatokon szereplő tevékenység alapján erősítsd meg a költséghányad-kategóriát (a NAV „bármely tevékenység” szövege nem sorolja fel külön az egyes szakmákat).
- Külföldi (EU) vevők felé számlázva (pl. fordítottan adózó ügylet) az adónaptár hatályán kívüli teendők is lehetnek (pl. összesítő nyilatkozat) – egyeztess könyvelővel.

## Hivatkozások

- [NAV: Az egyéni vállalkozók átalányadózásának alapvető szabályai – 2026.02.20. (PDF)](https://nav.gov.hu/pfile/file?path=/ugyfeliranytu/nezzen-utana/inf_fuz/2026/100.-Az-egyeni-vallalkozok-atalanyadozasanak-alapveto-szabalyai-2026.-02.-20)
- [NAV: Kedvező változások az átalányadózásban](https://nav.gov.hu/szja/ujdonsagok-tudnivalok/Kedvezo_valtozasok_az_atalanyadozasban)
- [NAV: Adózási mód választása](https://nav.gov.hu/Elethelyzetek-adozasa/vallalkozas/adozasi-mod-valasztasa)
- [NAV: Átalányadózással kapcsolatos teendők](https://nav.gov.hu/ado/katas-voltam/atalanyadozassal-kapcsolatos-teendok)
- [Szja tv. (1995. évi CXVII.)](https://njt.jog.gov.hu/jogszabaly/1995-117-00-00)

## Törvényi helyek (a letöltött szövegből olvasva, 2026-11-08)

> Forrás: `torvenytar/docs/szja-tv/2026/1995-evi-cxvii-torveny.jogtar.txt` (a mellékletekkel; hatály: 2026.X.1. – 2026.XII.31.). Az njt.hu főoldali szövege a mellékleteket nem tartalmazza, ezért kell a `.jogtar.txt`.

| Szabály | Törvényi hely (a szöveg szerint) |
|---|---|
| Az átalányos jövedelemnek az **éves minimálbér felét meg nem haladó része adómentes** (ez eddig csak NAV-tájékoztatóból volt igazolt) | Szja tv. **1. számú melléklet 4.48.** pont: „az átalányadózást alkalmazó egyéni vállalkozó e tevékenységéből származó jövedelmének az éves minimálbér felét meg nem haladó rész” |
| Nincs adóelőleg, amíg az előleg-alap az adóév elejétől összesítve az éves minimálbér felét nem haladja meg; utána csak a feletti rész után | Szja tv. **47. § (4a)** |
| A bevételeket a 10. melléklet szerint kell figyelembe venni; a **pénztárkönyv (naplófőkönyv) bevételi adatait vezeti**, ha áfa-levonási jogát nem érvényesíti; a költségbizonylatokat megőrzi | Szja tv. **51. § (1), (3)** |
| Bevétel: az ellenértékként vagy **előlegként befolyt** (vagy váltóval kiegyenlített) összeg | Szja tv. **10. számú melléklet I. 1.** pont |
| Alanyi adómentes áfa-státusznál a fizetendő áfa a bevételt nem csökkenti | Szja tv. **4. számú melléklet 3.** pont (a le nem vonható áfa költségnövelő tényezőként is szerepel; átalányadózónál a költség nem számít, ezért ebből költséget ne állíts) |
| **Átalányadó-előleg megfizetése: a negyedévet követő hó 12. napjáig**; az átalányadózó az adóját önadózással állapítja meg | Szja tv. **8. számú melléklet 8–9.** pont |
| Negyedéves bevallás (a foglalkoztatónak nem minősülő, Tbj. 6. § (1) d) szerinti egyéni vállalkozó): a tárgynegyedévet követő hónap 12. napjáig | Art. **50. § (1a)** (`torvenytar/docs/art/2026/`) |

**Még mindig nyitott:** az Szja tv. **29. §** és **47. § (5)** szerinti 89%-os szabály alkalmazhatósága az átalányadózóra (a tartalmi szöveget nem ez a melléklet-olvasás oldja fel); a bevétel időpontja kifizetői átutalásnál (9. § (2) a)); lásd `config/konyvelo-dontesek.json` és a `plans/` terv B fázisa.
