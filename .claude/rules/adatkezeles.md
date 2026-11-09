# Adatkezelés – hová kerül mi, ki számol

Minden adatot feldolgozó skill és script **köteles** ezt a szabályt követni, és a `SKILL.md`-jében hivatkozni rá.

## Adatfolyam

```
input/            nyers, a felhasználó által bemásolt fájlok (NAV XML, adónaptár)
   │  script feldolgozza
   ├──► data/     a feldolgozott eredmény (JSON/CSV) – ebből dolgozik minden további számítás
   ├──► archive/  a feldolgozott nyers fájl ide kerül át (mozgatás, nem törlés)
   └──► .claude/memory/   csak az adónaptár olvasható kivonata (lásd lent)
```

| Mappa | Tartalom | Verziózott? |
|---|---|---|
| `input/nav-egyenleg/`, `input/adonaptar/` | feldolgozásra váró nyers fájlok (**az almappákat is feldolgozzák**, `.claude/scripts/bemenet.py`); sikeres feldolgozás után **üresnek kell lennie**; ami marad, azt az `adoellenorzes` jelzi | nem |
| `data/szamlak/` | Billingo számlák (JSON + CSV), `szamlak_<tol>_<ig>.*` | nem |
| `data/nav-egyenleg/` | feldolgozott NAV adószámla-tételek (JSON) | nem |
| `data/adonaptar/` | feldolgozott adónaptár (JSON) | nem |
| `data/kiadasok/` | Billingo bejövő számlák/kiadások (JSON, nyers) | nem |
| `data/pdf/` | PDF-ekből készült tömör Markdown (`<név>.md` + `.json`), mappa-módban az eredeti mappaszerkezettel | nem |
| `data/graphify/<korpusz>/` | a Graphify **munkakönyvtára** (korpusz-másolatok, `graphify-out/`: gyorsítótár, alügynök-fájlok); a kész gráfot a közzétételi lépés a `torvenytar/graph/`-ba másolja | nem |
| `torvenytar/graph/` | a **kész Graphify törvénytérkép** (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, `inferred_ellenorzes.json`, `korpusz-szabalyok.md`, `forras-terkep.json`, `README.md`); nyilvános jogszabályszövegből készül, személyes adatot nem tartalmaz; generált, kézzel ne szerkeszd | **igen** |
| `data/vallalkozas/` | a vállalkozói iratok leltára, besorolási terve, áthelyezési naplója, profilja (`profil.md/json`) és a PDF-ek Markdown-ja (`iratok-md/`) | nem |
| `input/konyvelo/` | a könyvelőtől kapott PDF-ek; feldolgozás (`konyvelo-dokumentumok`) után **üres**, az eredetik az `archive/konyvelo/`-ba kerülnek | nem |
| `data/konyvelo/` | a könyvelői iratok Markdown-ja (`md/`), adatkivonata (`konyvelo_adatok.json`) és az ellenőrzés eredménye (`ellenorzes_<év>.json`) | nem |
| `input/bevetelek/` | a kimenő számlák nyers fájljai (PDF, XML, CSV); feldolgozás után **üres**, az eredetik az `archive/bevetelek/<év>/`-ba kerülnek | nem |
| `data/szamlak/` | Billingo (`szamlak_*`), Számlázz.hu (`szamlazz_*`), fájlokból (`bevetelek_szamlak.json`) és az **egyesített, keresztvalidált** `egyesitett_*.json` (ezt olvassa az adoszamitas); `bevetelek-md/`: Markdown | nem |
| `data/szamitas/` | az `adoszamitas` és `adoellenorzes` skill eredménye (JSON) | nem |
| `tax-reports/adoreport_<év>.html` | az `adoreport` skill HTML reportja; minden `adoellenorzes` futás után újragenerálódik | nem |
| `archive/nav-egyenleg/`, `archive/adonaptar/`, `archive/pdf/` | már feldolgozott nyers fájlok | nem |
| `archive/vallalkozas-iratok/` | a vállalkozói iratok **keletkezésük éve szerint** csoportosítva: `<év>/<témakör>/…` (`01-alapadatok` … `06-egyeb`, a témakört a `config/iratrend.json` adja), a témakörbe nem sorolhatók `<év>/besorolatlan/` alatt | nem |
| `torvenytar/docs/NAV/<év>/`, `torvenytar/docs/<törvény>/<év>/` | hivatalos források **módosítás nélkül** (eredeti fájl + gépies `.txt` + `.forras.json`); jegyzék: `torvenytar/forrasok.json` | nem |
| `.claude/memory/` | adónaptár-kivonat (`adonaptar-<év>.md`), a **vállalkozói profil** (`vallalkozasi-profil.md`, az `adoellenorzes` kapuja) + `MEMORY.md` index; csak generált, azonosító- és névmentes adat (ügyfél-, szolgáltató-, könyvelőnevek nem). A profil és az adónaptár-kivonat **nem verziózott** (`.gitignore`), a `MEMORY.md` index igen | részben |
| `config/` | szabályparaméterek (`szabalyok_<év>.json`), besorolási szabályok (`iratrend.json`) és a `vallalkozas.example.json` sablon: igen. A vállalkozó saját `vallalkozas.json`-ja személyes beállításokat tartalmaz: **nem verziózott** (`.gitignore`) | részben |

## Szabályok

1. **A script feldolgoz, az AI nem.** Szám, dátum, összeg csak script kimenetből származhat. Az AI nem olvassa ki fejből/szemmel a nyers fájlból az értékeket, hogy aztán összeadja őket.
2. **Scriptek helye:** mindig az őket használó skill mappáján belül: `.claude/skills/<skill>/scripts/`. A repo gyökerében nincs `scripts/` mappa.
3. **Sorrend:** feldolgozás → eredmény a `data/` alá → csak ezután kerülhet a nyers fájl az `archive/` mappába. Hibánál a nyers fájl az `input/`-ban marad, az archiválás elmarad.
4. **Archiválás = mozgatás.** Ha az `archive/`-ban már van azonos nevű fájl, a script nem írja felül, hanem időbélyeges előtagot ad az új fájlnak. Archivált fájlt törölni csak a felhasználó kérésére szabad.
5. **Az eredmény mindig a `data/` alatt él.** Riport, összefoglaló, számítás: a script `data/` alá menti, a chatben csak ennek a tartalmát adjuk vissza. A `tax-reports/` mappa csak ember által olvasandó, a felhasználó kérésére készülő riportoknak való (az `adoreport` skill HTML reportja ilyen); a riport mindig a `data/` fájlokból készül, és nem tartalmaz újraszámolt adót.
6. **Az adónaptár és a vállalkozói profil kivétel a „csak data" alól:** a feldolgozott adónaptár olvasható kivonata a `.claude/memory/adonaptar-<év>.md` fájlba is kerül (a `MEMORY.md` indexszel), a gépi változata pedig `data/adonaptar/<év>.json`.
7. **Frissesség:** minden kimenet írja ki, melyik fájlból, mikori adatból készült (Billingo letöltés ideje, NAV lekérdezés időpontja). Ha az adat régebbi egy napnál, a skill ezt kiírja, és nem állítja, hogy az érték „aktuális".
8. **Újrafuttathatóság:** a script ugyanarra a bemenetre ugyanazt az eredményt adja; a `data/` fájlok felülírhatók, az `archive/` nem.
9. **Titkok és személyes adatok:** a `BILLING_API_KEY` értékét soha nem írjuk ki. Adószám, név, cím, bankszámla-azonosító nem kerül a chat kimenetbe és nem kerül a `.claude/memory/` fájlba, csak a `data/`-ba, ha a számításhoz kell. A `data/`, `archive/`, `input/` nincs verziókezelve (`.gitignore`).
10. **Mappa-mód kivétel:** ha a felhasználó egy általa rendezett mappát (pl. `input/vállalkozas-adatok/`, `torvenytar/`) kér feldolgozni, az eredeti fájlok a helyükön maradnak (nem kerülnek az `archive/`-ba), az eredmény a `data/` alatt a mappaszerkezetet követi. A `torvenytar/` forrásfájljait soha nem módosítjuk.
11. **Hiányzó adat:** ha egy szükséges adat (beállítás, fájl, határidő) nincs meg, a script megáll vagy a hiányt nevesíti a kimenetben; nem tölt fel alapértelmezést, nem becsül. Lásd: `nincs-becsles.md`.
12. **A vállalkozás azonosítója kötelező ellenőrzés.** Minden beérkező dokumentumnál (könyvelői irat, NAV-irat, számla, API-adat) a skill a `.claude/scripts/azonosito.py` segítségével megnézi, hogy a vállalkozás adószáma vagy adóazonosító jele szerepel-e benne. Ha nem (másik vállalkozás vagy magánszemély dokumentuma, hiányzó azonosító, másik fiók API-kulcsa), a skill megáll, a fájl az `input/`-ban marad, és a felhasználó egyértelmű utasítást kap. Az azonosítót csak maszkolva (utolsó 3 számjegy) szabad kiírni.
13. **Egy számla csak egyszer könyvelhető.** A számlák a számlaszám (normalizálva) szerint egyesülnek; azonos számlaszám + eltérő adat, vagy különböző számlaszám + azonos kelt/összeg/pénznem különböző forrásokban megállítja az egyesítést (`szamlak_egyesites.py`).
