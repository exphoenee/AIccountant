---
name: nav-forrasok
description: NAV-oldalak, NAV-tájékoztatók (PDF) és jogszabályok (njt.hu) letöltése módosítás nélkül a torvenytar/docs/NAV/<év>/ és torvenytar/docs/<törvény>/<év>/ mappákba; minden PDF-ből Markdown a PDF saját mappájába (pdf-markdown skill); a Graphify-korpusz előállítása; majd a Graphify skill futtatása, hogy elkészüljön a törvények közötti térkép (tudásgráf). Használd, ha új hivatalos forrást kell eltenni, ha egy szabály forrását kell ellenőrizni, vagy ha a törvények kapcsolatait kell feltérképezni.
---

# NAV- és jogszabály-források: letöltés, Markdown, törvénytérkép

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## A teljes folyamat (sorrendben)

| # | Lépés | Ki végzi | Eredmény |
|---|---|---|---|
| 1 | Letöltés módosítás nélkül | `scripts/forras_letoltes.py` | `torvenytar/docs/NAV/<év>/`, `torvenytar/docs/<törvény>/<év>/`: eredeti `.pdf`/`.html` + gépies `.txt` + `.forras.json` |
| 2 | **Minden PDF-ből Markdown a PDF saját mappájába** | ugyanaz a script, a `pdf-markdown` skill scriptjével | `<név>.md` a `<név>.pdf` mellett (az eredeti PDF nem módosul) |
| 3 | Graphify-korpusz előállítása + a **közös azonosító-szótár és alias-tábla** generálása | ugyanaz a script | `data/graphify/torvenyek/` (másolatok; lásd lent), `data/graphify/torvenyek_reszek.json`, `graphify-out/.graphify_corpus_rules.md` (a `references/korpusz-szabalyok.md` sablonból és a `references/torvenyek-aliasok.json`-ból) |
| 4 | **A Graphify skill futtatása a korpuszon**, hogy elkészüljön a törvények közötti térkép | az `graphify` skill (Claude + alügynökök) | munkakönyvtár: `data/graphify/torvenyek/graphify-out/` (nem verziózott: gyorsítótár, alügynök-fájlok, nyers kimenet) |
| 5 | **Az INFERRED élek szöveges ellenőrzése** (gráfjavítás) **és a gráf közzététele** | `scripts/graf_ellenorzes.py` (vagy `forras_letoltes.py --graf-ellenoriz`) | kifejezett idézettel igazolható élek EXTRACTED-re lépnek elő; a kész gráf a **`torvenytar/graph/`** mappába kerül (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, `inferred_ellenorzes.json`, `korpusz-szabalyok.md`, `forras-terkep.json`, `README.md`): ez **verziózott, a repó része** |

A 4. lépés az egyetlen, amelyet nem script végez: a szöveges dokumentumok szemantikus kinyerését a Graphify a Claude-munkamenettel, alügynökökkel futtatja. Az 1–3. lépés egy paranccsal megy, a 4. lépés előtt **mondd ki a felhasználónak a korpusz méretét** (a script kiírja), mert a futás sok tokent használ.

## Futtatás

```
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py                 # 1-3. lépés: letöltés (ami még nincs) + PDF->Markdown + korpusz
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --ujra          # mindent újra letölt (változás-ellenőrzés: hasonlítsd az SHA-256-ot)
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --korpusz       # csak a korpusz újraépítése, letöltés nélkül
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --hivatkozasok  # a NAV-szövegekben idézett törvények (számmal és rövidítéssel)
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --graf-ellenoriz # a gráf INFERRED éleinek szöveges ellenőrzése (a gráf felépítése után)
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --ellenoriz     # a források állapota + a szabályfájlok törvényhivatkozásainak ellenőrzése
```

### Mellékletek és hatályos állapot (miért két forrás van egy törvényhez)

Az njt.hu főoldali szövege **a törvény törzsét** adja, a **mellékleteket nem** (pl. az Szja tv. 1., 4., 10. számú melléklete, az Áfa tv. 4/A. melléklete). Ezért minden `-00-00` végű njt-törvényhez a script a **net.jogtar.hu** (Hatályos Jogszabályok Gyűjteménye) azonos törvényét is letölti kiegészítésként: `<név>.jogtar.html/.txt` + `<név>.jogtar.forras.json` (a mellékletek jegyzékével és a `Hatály: (…)` sorral). Az azonosítót a script számolja (`99500117.tv` az 1995. évi 117-hez, `a1700150.tv` a 2017. évi 150-hez); kézzel felülírható a jegyzék `jogtar_url` mezőjével, `jogtar_url: false` kikapcsolja (ha az automatikus azonosító 404-et ad). A kiegészítés a törvény szövegét **másodforrásként** adja: állítás előtt az njt.hu-s szöveggel is vesd össze.

- A `.forras.json`-ba kerül: `hatalyos_allapot` (az njt.hu cím alatti dátuma), `varhato_cim` és `cim_egyezik` (a letöltött oldal tényleg a kért törvény-e; eltérésnél 🔴 és a forrás nem használható).
- **`--ujra`** nem ír felül: a régi változat az `elozo/<letöltés dátuma>/` mappába kerül, és a script kimondja, ha a forrás **változott** (SHA-256). Változásnál futtasd az `--ellenoriz`-t, és nézd át a hivatkozott szakaszokat.
- **`--ellenoriz`**: törvényenként kiírja a hatályos állapotot, a letöltés korát (30 napnál régebbi: 🟡), a mellékletek jegyzékét és a hivatkozott, de nem található mellékleteket; majd a `.claude/rules/*.md`, `SKILL.md` és `CLAUDE.md` fájlokban idézett törvényhelyeket (`Szja tv. 47. §`, `Áfa tv. 4/A. melléklet`, …) kikeresi a letöltött szövegben. **Csak a szakasz vagy melléklet meglétét ellenőrzi, a tartalmi egyezést nem**: azt a szakasz elolvasásával kell eldönteni. Eredmény: `data/torvenytar/ellenorzes.json`; hiányzó hivatkozásnál 1-es kilépési kód. Futtasd új szabályfájl, törvénytár-frissítés és évváltás után.

**Forrás bevétele fájlból (`input/torveny/`):** ha egy jogszabály vagy NAV-oldal URL-jét tartalmazó fájlt (jegyzet, PDF, MD, TXT) teszel az `input/torveny/` mappába, a script (`forras_letoltes.py`) kigyűjti a hivatalos hivatkozásokat (`njt.hu` / `njt.jog.gov.hu` / `net.jogtar.hu` törvény-URL, `nav.gov.hu` oldal), felveszi őket a `torvenytar/forrasok.json`-ba, letölti és feldolgozza (txt, Markdown, Graphify-korpusz), a bemeneti fájlt pedig az `archive/torveny/` mappába teszi (nem hivatalos háttéranyag, csak a hivatkozásait használja). Hivatkozás nélküli fájlnál jelez, és az `input/`-ban hagyja. Csak a `-00-00` végű njt-URL-t (törvény) kezeli; rendeletet (pl. `2025-426-20-22`) kézzel kell felvenni. A fájlban lévő szöveget **nem** tekinti forrásnak.

Új forrás: vegyél fel egy elemet a `torvenytar/forrasok.json`-ba (`id`, `tipus`: `nav` vagy `torveny`, `mappa`, `nev`, `url`, `megjegyzes`). Jogszabály URL-je: `https://njt.hu/jogszabaly/<év>-<szám>-00-00`.

## 1. Letöltött fájlok (módosítás nélkül)

| Fájl | Tartalom |
|---|---|
| `<név>.pdf` vagy `.html` | az eredeti, **bájtra azonos** letöltés; soha nem módosítjuk |
| `<név>.txt` | gépies szövegkivonat (HTML: a `<main>` tartalma; PDF: `pdftotext -layout`); a szavak nem változnak, csak a jelölőnyelv hiányzik és a szóközök/üres sorok vannak összevonva |
| `<név>.md` | csak PDF-nél: tömör Markdown a `pdf-markdown` skill szerint (fejléc/lábléc/oldalszám nélkül, címsorokkal); **feldolgozott, nem módosítatlan szöveg**, a hivatalos szöveg az eredeti PDF/`.txt` |
| `<név>.forras.json` | URL, letöltés ideje, HTTP-állapot, tartalomtípus, SHA-256, méret; törvénynél a hatályos állapot és a cím-ellenőrzés |
| `<név>.jogtar.html/.txt/.forras.json` | törvénynél a net.jogtar.hu-s kiegészítés (a mellékletekkel); másodforrás |
| `elozo/<dátum>/` | `--ujra` előtt megőrzött régi változat |

## 3. A Graphify-korpusz (`data/graphify/torvenyek/`)

A korpusz **másolat**, a `torvenytar/docs/` forrásfájlok érintetlenek maradnak:

- **Törvények:** csak a hatályos szöveg kerül be. A njt.hu-kivonat végén álló **lábjegyzet-blokk** (módosítási történet) kimarad, mert nem a hatályos szabály, és az Szja tv.-nél a kivonat 59%-át adja. A kihagyott sorok tartománya a `data/graphify/torvenyek_reszek.json`-ban van.
- **Nagy törvények szakaszhatáron kb. 1700 soros részekre** bontva (`..._01.txt`, `..._02.txt`), mert egy alügynök kontextusába nem fér be egy 8000 soros fájl.
- **NAV-források:** PDF-nél a Markdown, HTML-nél a szövegkivonat (`nav-*.md/.txt`), hogy a NAV-útmutató és a törvényhelyek összekapcsolódjanak.

## 4. A Graphify futtatása (törvénytérkép)

1. A Graphify CLI a skill saját, elszigetelt Python-környezetében van (`.claude/skills/graphify/.venv/`), **nincs a PATH-on, és nincsenek hookok**. Ne telepíts csomagot a rendszer Pythonba; a `.graphify_python` fájlba a venv Pythonja kerül.
2. Munkakönyvtár: `data/graphify/torvenyek/` (a `graphify-out/` ide kerül, nem a repó gyökerébe). A Graphify futása után a **kész gráfot közzé kell tenni** a `torvenytar/graph/` mappába: ezt az 5. lépés (`graf_ellenorzes.py`, vagy csak `graf_ellenorzes.py --publikal`) végzi. A közzétett mappa a repó része; csak nyilvános jogszabályszöveg alapú adatot tartalmaz (a script a helyi abszolút elérési utakat kiveszi), személyes adat nincs benne.
3. Futtasd a `graphify` skill eljárását a korpuszon (felismerés → gyorsítótár-ellenőrzés → chunkok → `general-purpose` alügynökök párhuzamosan → összefűzés → gráf, közösségek, riport, HTML).
4. **Közös azonosító-szótár a törvényekhez:** a `data/graphify/torvenyek/graphify-out/.graphify_corpus_rules.md` **generált** fájl (a `forras_letoltes.py --korpusz` írja a `references/korpusz-szabalyok.md` sablonból és a `references/torvenyek-aliasok.json`-ból; kézzel ne szerkeszd). Rögzíti, hogy a törvények (`szja_tv`, `tbj`, ...), a szakaszok (`szja_tv_47_par`) és a fogalmak (`fogalom_atalanyadozas`) minden chunkban ugyanazt az azonosítót kapják, mikor EXTRACTED az él (csak kifejezett idézetnél), és a név-alias táblát (a törvényt csak nevével említő szöveg INFERRED él). Minden alügynök prompthoz add hozzá ezt a fájlt. **Új törvény felvételekor** a `references/torvenyek-aliasok.json`-ba is fel kell venni (id, fájlnév-előtag, rövidítés-minta, név-alias).
5. A futás után ellenőrizd a lefedettséget (a skill B3.5 lépése): ha egy fájl csak részben lett elolvasva, mondd ki, és futtasd újra azt a chunkot.
5b. **Az INFERRED élek szöveges ellenőrzése:** a gráf elkészülte után futtasd: `python -I .claude/skills/nav-forrasok/scripts/graf_ellenorzes.py` (`--szaraz`: csak kiír). Minden INFERRED élnél megnézi, hogy a hivatkozó szakasz szövege kifejezetten idézi-e a célt (azonos törvényen belül „47. §”, más törvénynél „Tbj. 43. §”, törvénynél a rövidítés vagy a szám, mellékletnél „N. számú melléklet”); ha igen, az él EXTRACTED-re lép elő (az eredeti jelzés és a szövegrészlet az élen marad: `confidence_eredeti`, `ellenorzes`), egyébként INFERRED marad. A törvényt csak a nevével említő szöveg (alias-tábla: `.graphify_corpus_rules.md` 5. pont) nem lép elő, csak `nev_alapjan` jelzést kap. Fogalmi (`fogalom_*`) élet a script nem léptet elő. Eredmény: `graphify-out/inferred_ellenorzes.json`, frissített `graph.json`, `graph.html` és a jelentés összegző sora. A `graf_ellenorzes.py --fogalom-szaraz` **szárazon** (nem módosít) megmutatja, a fogalom–szakasz/NAV INFERRED élek hányadánál szerepel a fogalom neve szó szerint a szövegben (a lehetséges `szerepelteti` reláció előfeltétele); a `--hianyzo` a gráfban hivatkozott, de a törvénytárból hiányzó törvényeket listázza.
6. A kimenetből csak a Graphify által kért három részt (God Nodes, Surprising Connections, Suggested Questions) foglald össze; a teljes riportot nem kell a chatbe másolni.

## Hivatkozott, de hiányzó törvények (a törvénytár bővítése)

A törvénytárat a `torvenytar/forrasok.json` jegyzék határozza meg: a `forras_letoltes.py` azt tölti le, ami benne van. Ha a törvények között hivatkozott törvény hiányzik a törvénytárból, a Graphify-gráfban csonk-csomópontként jelenik meg (pl. `jovedeki_tv`, `szamv_tv`).

1. **Hiányzók felkutatása:** `python -I .claude/skills/nav-forrasok/scripts/graf_ellenorzes.py --hianyzo` kilistázza a gráfban hivatkozott, de a törvénytárban (alias-tábla) nem szereplő törvényeket (csak a törvény neve vagy a szakasz-előtag alapján, a hivatkozás számával). Új NAV-szövegek hivatkozásaihoz: `forras_letoltes.py --hivatkozasok`.
2. **Felvétel:** egy elem a `torvenytar/forrasok.json`-ba (`id`, `tipus: torveny`, `mappa: <rövid>/<év>`, `nev`, `url: https://njt.hu/jogszabaly/<év>-<szám>-00-00`, `megjegyzes`) **és** a `references/torvenyek-aliasok.json`-ba (azonosító, `fajl_elotag` (egyedi, a másik törvény előtagjával nem összetéveszthető), `rovidites`, `nev_alias`). A törvényszámot ne emlékezetből erősítsd meg: a letöltő a címből ellenőrzi (`cim_egyezik`).
3. **Letöltés:** `python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py` (a mellékletekkel és a hatályos állapot dátumával). Ellenőrzés: `--ellenoriz`.
4. **A gráf frissítése:** a Graphify `--update`-tel csak az új fájlok kerülnek feldolgozásra; utána `--graf-ellenoriz` és a közzététel (`torvenytar/graph/`).
5. Jelenleg felvett, korábban csonk törvények: Air. (2017. évi CLI.), Tao. tv. (1996. évi LXXXI.), Cst. (1998. évi LXXXIV.), Katv. (2012. évi CXLVII.; **nem** azonos a 2022. évi Kata tv.-vel). Még hiányzó csonkok: Jöt. (2016. évi LXVIII.), a kiskereskedelmi adóról szóló (2020. évi XLV.), Szt. (2000. évi C., számvitel), a távhőszolgáltatásról szóló (2008. évi LXVII.).

## Szabályok ehhez a skillhez

1. **A forrásfájlokat soha ne szerkeszd, ne fordítsd, ne foglald össze bennük.** Az értelmezés külön dokumentumba megy (pl. `torvenytar/vallalkozasomra-vonatkozo-szabalyok-2026.md`; az értelmező háttéranyagok (pl. `atalanyado-szabalyok-osszefoglalo.md`) szintén a `torvenytar/docs/` alatt vannak).
2. **Állítást csak olvasott szövegrészletre alapozz.** A forrást célzottan olvasd (`Grep` a `.txt`-ben, majd a találat környéke); a törvények nagyok (az Szja tv. kivonata kb. 690 000 karakter), ne töltsd be egészben.
3. **A gráf nem helyettesíti a forrást.** Egy gráf-állítás (él, fogalom, mérték) előtt a gráf által megjelölt szakaszt a `torvenytar/docs/` forrásszövegben ellenőrizd. Az `INFERRED`/`AMBIGUOUS` élekre ezt mondd is ki.
4. A rövidítéssel idézett törvény (pl. „Tbj.") számát a **letöltött cím alapján** erősítsd meg, ne emlékezetből.
5. A hatályos állapot dátuma a `.forras.json` `hatalyos_allapot` mezőjében van (njt.hu: a cím alatti dátum; net.jogtar.hu: `Hatály: (…)`); jelöld, ha egy szabály egy adott időpontra vonatkozik, és mondd ki, ha a letöltés 30 napnál régebbi. Melléklet tartalmára csak akkor hivatkozz, ha a `.jogtar.txt`-ben elolvastad.
6. Elavult oldalt (pl. a NAV „Teendők" oldala, 2022-es adatokkal) jelezz elavultként, és ne használd 2026-os számításhoz.
7. A letöltés külső hálózati kérés, csak a jegyzékben szereplő URL-ekre. Személyes adatot nem küld.
8. A Graphify szemantikus feldolgozása (alügynökök) tokenigényes: új vagy megváltozott forrásnál a gyorsítótár miatt csak az új/változott fájlok kerülnek újra feldolgozásra (`--update`); a teljes újraépítés előtt kérdezd meg a felhasználót.
