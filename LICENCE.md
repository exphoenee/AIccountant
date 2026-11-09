# Licenc (MIT)

A licenc jogilag mérvadó szövege az angol nyelvű alábbi szöveg; a magyar összefoglaló csak tájékoztató.

> **Röviden (nem jogi szöveg):** a repó saját kódját és dokumentációját szabadon használhatod, másolhatod, módosíthatod és terjesztheted, akár kereskedelmi célra is, ha a szerzői jogi sort és ezt a licencszöveget megtartod. A szoftver „ahogy van”, garancia nélkül áll rendelkezésre. **Nem adótanácsadás:** lásd a [DISCLAIMER.md](DISCLAIMER.md) fájlt.

---

MIT License

Copyright (c) 2026 exphoenee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Harmadik féltől származó részek (ezekre NEM ez a licenc vonatkozik)

Az MIT licenc a repó **saját** kódjára és dokumentációjára vonatkozik. A repó az alábbi, külön licencű anyagokat is tartalmazza vagy használja; ezekre a saját licencük érvényes, és a felhasználásukkor azt kell betartani.

| Rész | Hely | Licenc / státusz |
|---|---|---|
| **Chart.js** v4.4.7 (a reportba ágyazott diagramkönyvtár) | `.claude/skills/adoreport/assets/chart.umd.js` | MIT; a szerzői jogi sor a fájl fejlécében van, a forrás és az ellenőrző összeg: `chart.umd.js.INFO.txt` |
| **design-taste-frontend** skill (a report arculatának alapja) | `.claude/skills/design-taste-frontend/` | MIT (Copyright (c) 2026 Leonxlnx; lásd a mappában lévő `LICENSE` fájlt). A skill külön licencű **fényképeit és rasztergrafikus képeit eltávolítottuk** (lásd a mappában a `KEPEK-ELTAVOLITVA.md` fájlt); a vektoros SVG-ikonok és a skill kódja maradt. Az `assets/photos/photos.json` a törölt képek leírása és licencadata, dokumentációként maradt |
| **Graphify** (tudásgráf eszköz) | `.claude/skills/graphify/` (a SKILL.md; a Python-csomag a saját, nem verziózott `.venv` mappában van) | Apache-2.0 (PyPI: `graphifyy`); a csomagot a repó nem tartalmazza, a saját licencét a telepítéskor kapod |
| **Jogszabályszövegek, NAV-oldalak és -tájékoztatók** | `torvenytar/` | Hivatalos források módosítatlan másolatai (njt.hu, net.jogtar.hu, nav.gov.hu); a forrás URL-je és a letöltés ideje fájlonként a `*.forras.json`-ban van. A felhasználás feltételeit a forrásoldalak határozzák meg; ezekre nem az MIT licenc vonatkozik, és a repó szerzője nem vállal rájuk jogot. A letöltött szöveg lehet elavult: a hatályos állapotot a `.forras.json` jelzi |
| **Gépi kivonatok és fordítások** | `torvenytar/**/*.txt`, `*.md` (PDF-ből) | A fenti hivatalos forrásokból gépiesen készült kivonatok; a hivatalos szöveg az eredeti fájl |

## A felhasználó saját adatai
A `data/`, `archive/`, `input/`, `tax-reports/`, a `config/vallalkozas.json`, a `config/konyvelo-dontesek.json` és a `.env` a **felhasználó saját, személyes adatai**; nem részei a szoftvernek, nincsenek verziókezelésben, és nem esnek a fenti licenc alá. Lásd a [README.md](README.md) adatvédelmi figyelmeztetését.
