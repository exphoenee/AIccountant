# Elvárt mappa- és fájlstruktúra: skill, agent, rule, memory

Ha skillt, agentet, rule-t vagy memory fájlt kell készíteni, **mindig ezt a struktúrát kövesd**. Ha eltérsz, indokold meg a felhasználónak. Az alábbi minták a repó meglévő fájljain alapulnak.

## Közös elnevezési szabályok

- Fájl- és mappanév: **kisbetűs, ékezet nélküli, kötőjeles** (`adoszamitas`, `bevetel-nyilvantartas`). A frontmatter `name:` értéke megegyezik a fájl/mappa nevével.
- A tartalom nyelve magyar; a `description` egy mondat, amely megmondja, **mit csinál** és **mikor kell használni**.
- Egy fájl egy témáról szól.
- Titkot (`BILLING_API_KEY`), adószámot, nevet, címet, bankszámlaszámot egyik fájlba sem írunk.

## Összefoglaló

```
.claude/
├── skills/<skill-nev>/
│   ├── SKILL.md                  kötelező
│   └── scripts/<script>.py       csak ha a skill adatot dolgoz fel vagy számol
│   └── references/<reference>.md csak ha a skill adott skill által használt referencia
├── agents/<agent-nev>.md         egy fájl = egy agent
├── rules/<tema>.md               egy fájl = egy téma
├── scripts/<script>.py           csak ha a scriptet több skill is használja
├── references/<referencia>.md    csak ha a referencia több skill által használt
└── memory/
    ├── MEMORY.md                 index, egy sor / memory fájl
    └── <memory-nev>.md           egy fájl = egy tény
config/                           szabályparaméterek, beállítások (verziózott)
torvenytar/                             háttéranyag
input/ → data/ + archive/         lásd adatkezeles.md
```

## 1. Skill – `.claude/skills/<skill-nev>/`

```
.claude/skills/<skill-nev>/
├── SKILL.md
└── scripts/
    └── <script>.py
```

- `SKILL.md` frontmatter (kötelező): `name`, `description`.
- A törzs sorrendje: cím → **Kötelező szabályok** (hivatkozás a `adatkezeles.md`-re és `nincs-becsles.md`-re, ha a skill adatot dolgoz fel vagy számot ad) → **Mit csinál** → **Futtatás** (pontos parancs) → **Szabályok ehhez a skillhez**.
- **A script mindig az őt használó skill `scripts/` mappájába kerül**, soha a repó gyökerébe vagy más skillébe. Ha több skill is használja, az egyik skill mappájában él, a többi alprocesszként hívja (példa: `adoellenorzes`).
- Számolást, adatfeldolgozást script végez, a `SKILL.md` csak utasít. A script a repó gyökerét a saját helyéből számolja (`Path(__file__).resolve().parents[4]`), nem a futtatás helyéből, és standard könyvtárral működik.
- Futtatás: `python -I .claude/skills/<skill>/scripts/<script>.py` (az `-I` miatt a script nem importál a futtatási mappából).
- A skill eredménye a `data/` alá kerül, a feldolgozott nyers fájl az `archive/`-ba (`adatkezeles.md`).

## 2. Agent – `.claude/agents/<agent-nev>.md`

```
.claude/agents/<agent-nev>.md
```

- Egy fájl, mappa nélkül. Frontmatter: `name`, `description` (mikor kell hívni), opcionálisan `tools` (csak a szükséges eszközök; adóügyi agentnek ne legyen írási/hálózati joga, ha nem kell) és `model`.
- A törzs az agent rendszerutasítása: szerep, bemenet, kimenet formátuma.
- Az agentnek a `nincs-becsles.md` és `adatkezeles.md` szabályai ugyanúgy érvényesek: számolni nem ő számol, hanem a skill scriptje. Az agent **skillt hív vagy scriptet futtat**, nem másol be számítási logikát.
- Script csak akkor kerül az agenthez, ha nincs hozzá skill; ilyenkor is skill mappába tedd (új skillként), az agent azt hívja.

## 3. Rule – `.claude/rules/<tema>.md`

```
.claude/rules/<tema>.md
```

- Lapos mappa, almappa nélkül. Egy fájl egy témát szabályoz (pl. `atalanyado.md`, `hataridok.md`, `adatkezeles.md`).
- Szerkezet: `# Cím` → forrás idézése (`> Forrás: ...`) → szabályok számozott vagy tematikus listában → **Ellenőrizendő / nyitott pontok**, ha van.
- A rule szabályt és tényt tartalmaz, **végrehajtható kódot nem**. Évente változó számok a `config/szabalyok_<év>.json` fájlba is kerüljenek (a script onnan olvas), a rule-ban a magyarázat és a forrás marad.
- Új rule-t hozz létre, ha új témát szabályozol; meglévő témánál a meglévő fájlt bővítsd (ne legyen duplikáció).
- Rule-ban ne legyen ékezetes vagy szóközös fájlnév, és ne hivatkozz olyan mappára, amely nem létezik a repóban.

## 4. Memory – `.claude/memory/`

**Ebben a repóban kizárólag a saját `.claude/memory/` mappát használjuk memóriának. A Claude Code beépített memóriáját (`~/.claude/projects/.../memory/`) nem használjuk: oda nem írunk, onnan nem támaszkodunk semmire.** A memória a repó része marad (helyi, verziózható), a globális `~/.claude` mappába semmilyen memory fájl nem kerül. Ha valamit meg kell jegyezni, az ide kerül, az alábbi formában.

```
.claude/memory/
├── MEMORY.md
└── <memory-nev>.md
```

- Egy fájl egy tény. Frontmatter: `name`, `description` (egy sor), `metadata.type` (`user` | `feedback` | `project` | `reference`).
- `feedback` és `project` típusnál a törzs végén **Why:** és **How to apply:** sor. Kapcsolódó memory-ra `[[memory-nev]]` hivatkozással mutass.
- Minden új memory fájlhoz kerül egy egysoros mutató a `MEMORY.md`-be (`- [Cím](fajl.md) — hook`). A `MEMORY.md`-ben nincs frontmatter és nincs memory-tartalom, csak index.
- Mentés előtt nézd meg, nincs-e már ilyen memory: azt frissítsd, ne duplikálj. A téves memoryt töröld.
- Ami a kódból, a rule-okból, a `config/`-ból vagy a `data/` fájlokból levezethető, az **nem** memory.
- Generált memory (pl. `adonaptar-<év>.md`) a generáló script fejlécében jelzi, hogy kézzel nem szerkeszthető; ilyet a skill scriptje ír, nem az AI kézzel.
- Személyes adat (adószám, név, cím, számlaszám) memory-ba nem kerül.

## Ellenőrzőlista új fájl létrehozásakor

1. Jó helyre kerül? (skill / agent / rule / memory a fenti fa szerint)
2. A név kisbetűs, ékezet nélküli, kötőjeles, és egyezik a frontmatter `name:`-jével?
3. A frontmatter teljes, a `description` megmondja, mikor kell használni?
4. Ha adatot dolgoz fel vagy számot ad: hivatkozza a `adatkezeles.md`-t és a `nincs-becsles.md`-t, és a számítás scriptben van?
5. Frissült a `CLAUDE.md` táblázata (skill/mappa), illetve a `MEMORY.md` indexe?
