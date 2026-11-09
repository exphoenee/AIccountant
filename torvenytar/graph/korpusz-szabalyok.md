# Közös azonosító-szótár a törvénykorpuszhoz (minden alügynök köteles követni)

> Generált fájl: a `nav-forrasok` skill `forras_letoltes.py --korpusz` állítja elő a `references/korpusz-szabalyok.md` sablonból és a `references/torvenyek-aliasok.json`-ból. Kézzel ne szerkeszd; a sablont és a JSON-t szerkeszd.

A korpusz magyar jogszabályszöveg (törvények szakaszokra, bekezdésekre bontva) és NAV-tájékoztató. Hogy a különálló fájlokat olvasó alügynökök hivatkozásai összeérjenek, a KÖZÖS entitások azonosítója mindenhol ugyanaz (a node-ID szabály alól ez a kivétel: ezeknél NEM a fájlútvonal a prefix). Csupa kisbetű, ékezet nélkül (á->a, é->e, í->i, ó,ö,ő->o, ú,ü,ű->u), csak [a-z0-9_].

## 1. Törvények (id = a rövid név; label = a törvény neve)
szja_tv = 1995. évi CXVII. (Szja tv.) | szocho_tv = 2018. évi LII. (Szocho tv.) | tbj = 2019. évi CXXII. (Tbj.) | htv = 1990. évi C. (helyi adók, Htv.) | afa_tv = 2007. évi CXXVII. (Áfa tv.) | art = 2017. évi CL. (adózás rendje, Art.) | evectv = 2009. évi CXV. (Evectv.) | kata_tv = 2022. évi XIII. (Kata tv.) | kamarai_tv = 1999. évi CXXI. (gazdasági kamarák) | anya30_tv = 2025. évi XIII. (30 év alatti anyák kedvezménye) | anya2_tv = 2025. évi XIV. (két gyermeket nevelő anyák kedvezménye) | anya3_tv = 2025. évi XV. (három gyermeket nevelő anyák kedvezménye) | modosito_2025_lxxxiv = 2025. évi LXXXIV. (módosító törvény)
NAV-források: nav_atalanyado_2026 | nav_ev_szja_jarulek_2026 | nav_ado_afa | nav_adozasi_mod | nav_atalanyado_teendok | nav_kedvezo_valtozasok

## 2. Szakaszok: `<torveny>_<szakaszszam>_par`, a "/" jele "_" (29/A. § -> szja_tv_29_a_par; 47. § -> szja_tv_47_par; 4/A. melléklet -> afa_tv_4_a_melleklet). Bekezdést NE külön node-nak vedd fel, hanem a source_location-be írd (pl. "(4a)").
Egy hivatkozás másik törvény szakaszára ("Tbj. 43. §") a cél-törvény szakasz-ID-jára mutasson (tbj_43_par), akkor is, ha az a szakasz nem szerepel a te fájlodban: ilyenkor is hozd létre a node-ot (file_type: document, label: "Tbj. 43. §").

## 3. Fogalmak: `fogalom_<nev>` (egyetlen azonosító fogalmanként minden fájlban), pl.
fogalom_atalanyadozas, fogalom_koltseghanyad, fogalom_osszevont_adoalap, fogalom_adomentes_jovedelemresz, fogalom_eves_minimalber, fogalom_minimalber, fogalom_garantalt_berminimum, fogalom_csaladi_kedvezmeny, fogalom_elso_hazasok_kedvezmenye, fogalom_szemelyi_kedvezmeny, fogalom_25_ev_alatti_kedvezmeny, fogalom_anyak_kedvezmenye, fogalom_csaladi_jarulekkedvezmeny, fogalom_jogosultsagi_honap, fogalom_adoeloleg, fogalom_adoeloleg_alap, fogalom_szocialis_hozzajarulasi_ado, fogalom_jarulekalap, fogalom_minimalis_jarulekalap, fogalom_alanyi_adomentesseg, fogalom_forditott_adozas, fogalom_osszesito_nyilatkozat, fogalom_teljesites_helye, fogalom_szamla, fogalom_helyi_iparuzesi_ado, fogalom_teteles_adoalap, fogalom_kamarai_hozzajarulas, fogalom_egyeni_vallalkozo, fogalom_bevetel_megszerzese, fogalom_onadozas, fogalom_negyedeves_bevallas
Ha új, a fentiek közé nem illő fogalmat veszel fel: `fogalom_<ekezet_nelkuli_nev>`, rövid, főnévi alak, egyes szám.

## 4. Élek és a megbízhatóság (EXTRACTED / INFERRED / AMBIGUOUS)
- **EXTRACTED csak akkor, ha a hivatkozó szakasz szövegében kifejezett idézet van** a célról: azonos törvényen belül "47. §", más törvénynél "Tbj. 43. §" (rövidítés vagy törvényszám + szakasz), melléklet esetén "N. számú melléklet". A `source_location`-be írd a bekezdést és az idézett szövegrészt.
- **INFERRED**, ha a kapcsolat értelmezés (téma, fogalom, a szöveg nem idézi). Ilyenkor a `source_location`-ben mondd ki: "nincs kifejezett hivatkozás". Ne adj `semantically_similar_to` élt, csak ha a hasonlóság valóban nem nyilvánvaló és keresztbe vág.
- **AMBIGUOUS**, ha bizonytalan; ne hagyd ki.
- Szakasz -> törvény `references` él nem kell (a szakasz-ID tartalmazza a törvényt). Fontos élek: szakasz -> másik szakasz, szakasz -> fogalom, NAV-forrás -> a törvényszakasz, amelyre hivatkozik (EXTRACTED, ha a szövegben szerepel).
- Ne találj ki élt. A gráf elkészülte után a `graf_ellenorzes.py` minden INFERRED élet a forrásszövegben ellenőriz; csak kifejezett idézetre léptet elő EXTRACTED-re, ezért a hamisan EXTRACTED-nek jelölt él csak rontja a gráf hitelét.

## 5. Név-alias tábla (a törvényt a szöveg gyakran csak NEVÉVEL említi, szám nélkül)
Ha a szöveg a törvényt nem számmal vagy rövidítéssel idézi, hanem a nevével, a célpont az alábbi azonosító legyen (ne hagyd üresen és ne találj ki újat). A hivatkozás ilyenkor `INFERRED` (nem `EXTRACTED`), a `source_location`-be írd: "névvel említve: <a szövegben álló kifejezés>".
- "személyi jövedelemadóról szóló (törvény)", "Szja tv.", "Szja." -> szja_tv
- "szociális hozzájárulási adóról szóló" -> szocho_tv
- "társadalombiztosítási ellátásokra jogosultakról és a fedezetéről szóló" -> tbj
- "helyi adókról szóló" -> htv
- "általános forgalmi adóról szóló", "Áfa-törvény" -> afa_tv
- "adózás rendjéről szóló" -> art
- "egyéni vállalkozóról és az egyéni cégről szóló" -> evectv
- "kisadózó vállalkozások tételes adójáról szóló" -> kata_tv
- "gazdasági kamarákról szóló" -> kamarai_tv
- "30 év alatti anyák kedvezménye" -> anya30_tv
- "két gyermeket nevelő anyák kedvezménye" -> anya2_tv
- "három gyermeket nevelő anyák kedvezménye" -> anya3_tv
- négy vagy több gyermeket nevelő anyák kedvezménye -> szja_tv_29_d_par (az Szja tv. saját szakasza, nem külön törvény)
