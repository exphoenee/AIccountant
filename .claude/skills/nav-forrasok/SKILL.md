---
name: nav-forrasok
description: NAV-oldalak, NAV-tájékoztatók (PDF) és jogszabályok (njt.hu) letöltése módosítás nélkül a torvenytar/NAV/<év>/ és torvenytar/<törvény>/<év>/ mappákba; minden PDF-ből Markdown a PDF saját mappájába (pdf-markdown skill); a Graphify-korpusz előállítása; majd a Graphify skill futtatása, hogy elkészüljön a törvények közötti térkép (tudásgráf). Használd, ha új hivatalos forrást kell eltenni, ha egy szabály forrását kell ellenőrizni, vagy ha a törvények kapcsolatait kell feltérképezni.
---

# NAV- és jogszabály-források: letöltés, Markdown, törvénytérkép

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## A teljes folyamat (sorrendben)

| # | Lépés | Ki végzi | Eredmény |
|---|---|---|---|
| 1 | Letöltés módosítás nélkül | `scripts/forras_letoltes.py` | `torvenytar/NAV/<év>/`, `torvenytar/<törvény>/<év>/`: eredeti `.pdf`/`.html` + gépies `.txt` + `.forras.json` |
| 2 | **Minden PDF-ből Markdown a PDF saját mappájába** | ugyanaz a script, a `pdf-markdown` skill scriptjével | `<név>.md` a `<név>.pdf` mellett (az eredeti PDF nem módosul) |
| 3 | Graphify-korpusz előállítása | ugyanaz a script | `data/graphify/torvenyek/` (másolatok; lásd lent) + `data/graphify/torvenyek_reszek.json` |
| 4 | **A Graphify skill futtatása a korpuszon**, hogy elkészüljön a törvények közötti térkép | az `graphify` skill (Claude + alügynökök) | `data/graphify/torvenyek/graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`) |

A 4. lépés az egyetlen, amelyet nem script végez: a szöveges dokumentumok szemantikus kinyerését a Graphify a Claude-munkamenettel, alügynökökkel futtatja. Az 1–3. lépés egy paranccsal megy, a 4. lépés előtt **mondd ki a felhasználónak a korpusz méretét** (a script kiírja), mert a futás sok tokent használ.

## Futtatás

```
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py                 # 1-3. lépés: letöltés (ami még nincs) + PDF->Markdown + korpusz
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --ujra          # mindent újra letölt (változás-ellenőrzés: hasonlítsd az SHA-256-ot)
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --korpusz       # csak a korpusz újraépítése, letöltés nélkül
python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --hivatkozasok  # a NAV-szövegekben idézett törvények (számmal és rövidítéssel)
```

**Forrás bevétele fájlból (`input/torveny/`):** ha egy jogszabály vagy NAV-oldal URL-jét tartalmazó fájlt (jegyzet, PDF, MD, TXT) teszel az `input/torveny/` mappába, a script (`forras_letoltes.py`) kigyűjti a hivatalos hivatkozásokat (`njt.hu` / `njt.jog.gov.hu` / `net.jogtar.hu` törvény-URL, `nav.gov.hu` oldal), felveszi őket a `torvenytar/forrasok.json`-ba, letölti és feldolgozza (txt, Markdown, Graphify-korpusz), a bemeneti fájlt pedig az `archive/torveny/` mappába teszi (nem hivatalos háttéranyag, csak a hivatkozásait használja). Hivatkozás nélküli fájlnál jelez, és az `input/`-ban hagyja. Csak a `-00-00` végű njt-URL-t (törvény) kezeli; rendeletet (pl. `2025-426-20-22`) kézzel kell felvenni. A fájlban lévő szöveget **nem** tekinti forrásnak.

Új forrás: vegyél fel egy elemet a `torvenytar/forrasok.json`-ba (`id`, `tipus`: `nav` vagy `torveny`, `mappa`, `nev`, `url`, `megjegyzes`). Jogszabály URL-je: `https://njt.hu/jogszabaly/<év>-<szám>-00-00`.

## 1. Letöltött fájlok (módosítás nélkül)

| Fájl | Tartalom |
|---|---|
| `<név>.pdf` vagy `.html` | az eredeti, **bájtra azonos** letöltés; soha nem módosítjuk |
| `<név>.txt` | gépies szövegkivonat (HTML: a `<main>` tartalma; PDF: `pdftotext -layout`); a szavak nem változnak, csak a jelölőnyelv hiányzik és a szóközök/üres sorok vannak összevonva |
| `<név>.md` | csak PDF-nél: tömör Markdown a `pdf-markdown` skill szerint (fejléc/lábléc/oldalszám nélkül, címsorokkal); **feldolgozott, nem módosítatlan szöveg**, a hivatalos szöveg az eredeti PDF/`.txt` |
| `<név>.forras.json` | URL, letöltés ideje, HTTP-állapot, tartalomtípus, SHA-256, méret |

## 3. A Graphify-korpusz (`data/graphify/torvenyek/`)

A korpusz **másolat**, a `torvenytar/` forrásfájlok érintetlenek maradnak:

- **Törvények:** csak a hatályos szöveg kerül be. A njt.hu-kivonat végén álló **lábjegyzet-blokk** (módosítási történet) kimarad, mert nem a hatályos szabály, és az Szja tv.-nél a kivonat 59%-át adja. A kihagyott sorok tartománya a `data/graphify/torvenyek_reszek.json`-ban van.
- **Nagy törvények szakaszhatáron kb. 1700 soros részekre** bontva (`..._01.txt`, `..._02.txt`), mert egy alügynök kontextusába nem fér be egy 8000 soros fájl.
- **NAV-források:** PDF-nél a Markdown, HTML-nél a szövegkivonat (`nav-*.md/.txt`), hogy a NAV-útmutató és a törvényhelyek összekapcsolódjanak.

## 4. A Graphify futtatása (törvénytérkép)

1. A Graphify CLI a skill saját, elszigetelt Python-környezetében van (`.claude/skills/graphify/.venv/`), **nincs a PATH-on, és nincsenek hookok**. Ne telepíts csomagot a rendszer Pythonba; a `.graphify_python` fájlba a venv Pythonja kerül.
2. Munkakönyvtár: `data/graphify/torvenyek/` (a `graphify-out/` ide kerül, nem a repó gyökerébe).
3. Futtasd a `graphify` skill eljárását a korpuszon (felismerés → gyorsítótár-ellenőrzés → chunkok → `general-purpose` alügynökök párhuzamosan → összefűzés → gráf, közösségek, riport, HTML).
4. **Közös azonosító-szótár a törvényekhez:** a `data/graphify/torvenyek/graphify-out/.graphify_corpus_rules.md` rögzíti, hogy a törvények (`szja_tv`, `tbj`, ...), a szakaszok (`szja_tv_47_par`) és a fogalmak (`fogalom_atalanyadozas`) minden chunkban ugyanazt az azonosítót kapják; enélkül a külön fájlokat olvasó alügynökök hivatkozásai nem érnének össze. Minden alügynök prompthoz add hozzá ezt a fájlt.
5. A futás után ellenőrizd a lefedettséget (a skill B3.5 lépése): ha egy fájl csak részben lett elolvasva, mondd ki, és futtasd újra azt a chunkot.
6. A kimenetből csak a Graphify által kért három részt (God Nodes, Surprising Connections, Suggested Questions) foglald össze; a teljes riportot nem kell a chatbe másolni.

## Szabályok ehhez a skillhez

1. **A forrásfájlokat soha ne szerkeszd, ne fordítsd, ne foglald össze bennük.** Az értelmezés külön dokumentumba megy (pl. `torvenytar/vallalkozasomra-vonatkozo-szabalyok-2026.md`).
2. **Állítást csak olvasott szövegrészletre alapozz.** A forrást célzottan olvasd (`Grep` a `.txt`-ben, majd a találat környéke); a törvények nagyok (az Szja tv. kivonata kb. 690 000 karakter), ne töltsd be egészben.
3. **A gráf nem helyettesíti a forrást.** Egy gráf-állítás (él, fogalom, mérték) előtt a gráf által megjelölt szakaszt a `torvenytar/` forrásszövegben ellenőrizd. Az `INFERRED`/`AMBIGUOUS` élekre ezt mondd is ki.
4. A rövidítéssel idézett törvény (pl. „Tbj.") számát a **letöltött cím alapján** erősítsd meg, ne emlékezetből.
5. Az njt.hu oldalon a cím alatti dátum a hatályos állapot dátuma; jelöld, ha egy szabály egy adott időpontra vonatkozik.
6. Elavult oldalt (pl. a NAV „Teendők" oldala, 2022-es adatokkal) jelezz elavultként, és ne használd 2026-os számításhoz.
7. A letöltés külső hálózati kérés, csak a jegyzékben szereplő URL-ekre. Személyes adatot nem küld.
8. A Graphify szemantikus feldolgozása (alügynökök) tokenigényes: új vagy megváltozott forrásnál a gyorsítótár miatt csak az új/változott fájlok kerülnek újra feldolgozásra (`--update`); a teljes újraépítés előtt kérdezd meg a felhasználót.
