# AIccountant

Személyes adóügyi asszisztens átalányadózó egyéni vállalkozók számára. Claude Code-dal figyelmeztet az adófizetési határidőkre és egyéb teendőkre a Billingo számlák, a NAV adószámla, az adónaptár és a vállalkozás iratai alapján. **A számításokat Python scriptek végzik, nem az AI.** Ami nem ellenőrzött, azt a rendszer kimondja, nem becsül. **Nem helyettesíti a könyvelőt és a jogi szakértőt: lásd a [DISCLAIMER.md](DISCLAIMER.md) fájlt.**

> ## ⚖️ Nem helyettesíti a könyvelőt és a jogi szakértőt
> Ez az eszköz a vállalkozás törvényi és számviteli ügyeit **követi**, és **kérdéseket vet fel** a könyvelő és a jogi képviselő felé. **Nem ad adótanácsot, nem dönt jogértelmezési kérdésekben, és nem helyettesíti a könyvelőt, az adótanácsadót vagy a jogi szakértőt.** A számított értékek tájékoztató jellegűek. Olvasd el a teljes nyilatkozatot: **[DISCLAIMER.md](DISCLAIMER.md)**.

> ## ⚠️ Figyelem: amit az AI beolvas, azt a modellszolgáltató is megkapja
> Ez az eszköz Claude Code-dal (AI) dolgozik. **Minden fájlt és adatot, amelyet az AI a munka közben elolvas, a modellszolgáltatóhoz (Anthropic) kerül feldolgozásra**, nem csak a chatben megjelenő szöveget. Ide tartozik: a vállalkozói iratok és szerződések Markdown-változata, a NAV- és könyvelői iratok, számlák, a `data/` fájljai, a profil és a script-kimenetek, amelyeket az AI kiolvas.
> - Ezek az iratok tartalmazhatnak **adószámot, adóazonosító jelet, TAJ-számot, nevet, címet, bankszámlaszámot, ügyfél- és könyvelőneveket**. A repó **nem maszkolja** a beolvasott szöveget; a „nem írom ki a chatbe” szabályok csak a kimenetre vonatkoznak.
> - A `.gitignore` a GitHubra kerülést akadályozza, **a modellszolgáltatóhoz kerülést nem**.
> - Csak akkor használd, ha vállalod ezt. Add az AI-nak csak azokat az iratokat, amelyek a feladathoz kellenek (az `input/` mappába ne tegyél fölöslegeset), és ellenőrizd a szolgáltatód adatkezelési feltételeit (megőrzés, tanításra használat).
> - Mi marad helyben: a számításokat Python scriptek végzik a saját gépeden; a `.env` kulcsait a script olvassa, az AI nem.
> - A `helyi-ipa` skill ezen felül az interneten keres (a településnevet külső szolgáltatás látja), a `nav-forrasok` és az `adonaptar` csak nyilvános oldalakat tölt le, személyes adat nélkül.

> **Először a vállalkozás adatait kell feldolgoztatni.** Az adóellenőrzés (`adoellenorzes`) addig nem fut le, amíg a memóriában (`.claude/memory/vallalkozasi-profil.md`) nincs feldolgozott vállalkozói profil.

## Gyors indulás

> **Ez egy sablon:** nem tartalmaz senki vállalkozásának adatát. **2026-os adóévre készült**: új évhez új `config/szabalyok_<év>.json` és adónaptár kell. A saját beállításaid (`config/vallalkozas.json`) és a feldolgozott adataid (`data/`, `archive/`, `.claude/memory/`) nincsenek verziókezelve.

1. Telepítés: `./install.sh` (Linux, macOS, Git Bash) vagy `.\install.ps1` (Windows PowerShell). Létrehozza a mappákat és a `.env`-et (Billingo és Számlázz.hu API-kulcs, Enter = kihagyás), és lefuttatja az önellenőrző tesztet.
2. A vállalkozás iratait másold az `input/vallalkozas-adatok/` mappába, és kérd a `vallalkozas-dokumentumok` skillt (**profil a memóriába**).
3. Adónaptár, NAV adószámla, számlák, kiadások, könyvelői iratok: a megfelelő `input/` mappába.
4. Adóellenőrzés: `python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py [év]`. Ebből készül a `tax-reports/adoreport_<év>.html`; a rád váró teendők a report Tennivalók szakaszában vannak.

**A teljes útmutató** (mit hova másolj, sorrend, parancsok, skillek, mappák, hibaelhárítás, a `vallalkozas.json` mezői): **[`usage.md`](usage.md)**.

## Diagramok és auditok

- [AI-workflow](docs/ai-workflow.html) és [Mappák és adatfolyam](docs/mappak-adatfolyam.html) (Archify; források: `docs/*.json`).
- Az `audits/` mappában a repó kiadott auditjai vannak (személyes adat nélkül, verziózva); a saját auditjaid is ide kerülnek, a telepítő a `.gitignore`-t ezekre **nem** módosítja. Push előtt ellenőrizd, hogy nincs bennük ügyfélnév, összeg vagy azonosító.

## Licenc és jogi nyilatkozat

- **Licenc:** MIT, lásd a [LICENCE.md](LICENCE.md) fájlt. A harmadik féltől származó részekre (Chart.js, a `design-taste-frontend` skill és fényképei, a `torvenytar/` hivatalos szövegei) a saját licencük vonatkozik; a részleteket a LICENCE.md tartalmazza.
- **Nem adótanácsadás:** a repó nem helyettesíti a könyvelőt és a jogi szakértőt, lásd a [DISCLAIMER.md](DISCLAIMER.md) fájlt.

## Személyes adatok és a GitHub

A személyes és pénzügyi adatok (`.env`, `input/`, `data/`, `archive/`, `tax-reports/`, `config/vallalkozas.json`, a generált vállalkozói profil és adónaptár-kivonat) a `.gitignore` miatt **nem kerülnek verziókezelésbe**; a telepítő is beírja őket. A `.gitignore` kategóriánként jelöli, mi **kötelező** (titkok, személyes adatok, a saját vállalkozást azonosító beállítások) és mi **ajánlott** (generált és gépfüggő fájlok; a saját auditokat, teendőlistákat és levélvázlatokat a telepítő nem teszi a `.gitignore`-ba, azt te döntöd el).

**Az ajánlott sorokat te döntöd el:** ízlés kérdése, hogy ki mit tesz fel a saját GitHub-repójába. Ha a saját auditjaidat vagy jegyzeteidet is verziózni akarod, vedd ki a sorukat, de előbb olvasd át őket, hogy nincs-e bennük ügyfélnév, összeg vagy más személyes adat. A kötelező sorokat ne töröld. A repó nem ellenőrzi, mit commitolsz: push előtt nézd át a `git status` kimenetét.

## Alapelvek

Számítást csak script végez, nincs becslés; személyes azonosító nem kerül a chatbe, a memóriába vagy a reportba; a `torvenytar/docs/` nem módosul; nem adótanácsadás. Részletek: [`usage.md`](usage.md) 7. fejezet, [`CLAUDE.md`](CLAUDE.md) és `.claude/rules/`. A skillek és mappák teljes listája a `CLAUDE.md`-ben van.
