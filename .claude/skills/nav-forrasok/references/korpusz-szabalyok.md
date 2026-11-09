# Közös azonosító-szótár a törvénykorpuszhoz (minden alügynök köteles követni)

> Generált fájl: a `nav-forrasok` skill `forras_letoltes.py --korpusz` állítja elő a `references/korpusz-szabalyok.md` sablonból és a `references/torvenyek-aliasok.json`-ból. Kézzel ne szerkeszd; a sablont és a JSON-t szerkeszd.

A korpusz magyar jogszabályszöveg (törvények szakaszokra, bekezdésekre bontva) és NAV-tájékoztató. Hogy a különálló fájlokat olvasó alügynökök hivatkozásai összeérjenek, a KÖZÖS entitások azonosítója mindenhol ugyanaz (a node-ID szabály alól ez a kivétel: ezeknél NEM a fájlútvonal a prefix). Csupa kisbetű, ékezet nélkül (á->a, é->e, í->i, ó,ö,ő->o, ú,ü,ű->u), csak [a-z0-9_].

## 1. Törvények (id = a rövid név; label = a törvény neve)
{{TORVENYEK}}
NAV-források: {{NAV}}

## 2. Szakaszok: `<torveny>_<szakaszszam>_par`, a "/" jele "_" (29/A. § -> szja_tv_29_a_par; 47. § -> szja_tv_47_par; 4/A. melléklet -> afa_tv_4_a_melleklet). Bekezdést NE külön node-nak vedd fel, hanem a source_location-be írd (pl. "(4a)").
Egy hivatkozás másik törvény szakaszára ("Tbj. 43. §") a cél-törvény szakasz-ID-jára mutasson (tbj_43_par), akkor is, ha az a szakasz nem szerepel a te fájlodban: ilyenkor is hozd létre a node-ot (file_type: document, label: "Tbj. 43. §").

## 3. Fogalmak: `fogalom_<nev>` (egyetlen azonosító fogalmanként minden fájlban), pl.
{{FOGALMAK}}
Ha új, a fentiek közé nem illő fogalmat veszel fel: `fogalom_<ekezet_nelkuli_nev>`, rövid, főnévi alak, egyes szám.

## 4. Élek és a megbízhatóság (EXTRACTED / INFERRED / AMBIGUOUS)
- **EXTRACTED csak akkor, ha a hivatkozó szakasz szövegében kifejezett idézet van** a célról: azonos törvényen belül "47. §", más törvénynél "Tbj. 43. §" (rövidítés vagy törvényszám + szakasz), melléklet esetén "N. számú melléklet". A `source_location`-be írd a bekezdést és az idézett szövegrészt.
- **INFERRED**, ha a kapcsolat értelmezés (téma, fogalom, a szöveg nem idézi). Ilyenkor a `source_location`-ben mondd ki: "nincs kifejezett hivatkozás". Ne adj `semantically_similar_to` élt, csak ha a hasonlóság valóban nem nyilvánvaló és keresztbe vág.
- **AMBIGUOUS**, ha bizonytalan; ne hagyd ki.
- Szakasz -> törvény `references` él nem kell (a szakasz-ID tartalmazza a törvényt). Fontos élek: szakasz -> másik szakasz, szakasz -> fogalom, NAV-forrás -> a törvényszakasz, amelyre hivatkozik (EXTRACTED, ha a szövegben szerepel).
- Ne találj ki élt. A gráf elkészülte után a `graf_ellenorzes.py` minden INFERRED élet a forrásszövegben ellenőriz; csak kifejezett idézetre léptet elő EXTRACTED-re, ezért a hamisan EXTRACTED-nek jelölt él csak rontja a gráf hitelét.

## 5. Név-alias tábla (a törvényt a szöveg gyakran csak NEVÉVEL említi, szám nélkül)
Ha a szöveg a törvényt nem számmal vagy rövidítéssel idézi, hanem a nevével, a célpont az alábbi azonosító legyen (ne hagyd üresen és ne találj ki újat). A hivatkozás ilyenkor `INFERRED` (nem `EXTRACTED`), a `source_location`-be írd: "névvel említve: <a szövegben álló kifejezés>".
{{ALIASOK}}
