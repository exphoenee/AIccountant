---
name: pdf-markdown
description: PDF fájlok szövegének kinyerése és tömör Markdownná alakítása tokentakarékosan (fejléc/lábléc/oldalszám eltávolítás, sorösszefűzés, címsorok, táblázatok), majd célzott olvasás vázlat, keresés és oldaltartomány alapján. Használd, ha PDF-et kell feldolgozni vagy PDF-ből kell adatot kikeresni, és ne töltsd be a teljes szöveget a kontextusba.
---

# PDF -> Markdown (tokentakarékos)

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Mit csinál

A `scripts/pdf_markdown.py` a PDF szövegrétegéből (`pdftotext`, `-layout`) tömör Markdownt készít:

- az ismétlődő fejléc/lábléc és az oldalszámok kikerülnek, az elválasztott és tördelt sorok összeolvadnak, a felesleges üres sorok eltűnnek,
- címsorok (`1.2 Cím`, NAGYBETŰS sor), felsorolások és széles szóközzel tagolt táblázatok Markdown formát kapnak,
- minden oldal elé egy `<!-- p:N -->` jelölő kerül, hogy oldal szerint lehessen olvasni.

Folyamat: `input/pdf/*.pdf` -> `data/pdf/<név>.md` és `<név>.json` (oldalszám, szószám, vázlat) -> a PDF az `archive/pdf/` mappába kerül (csak sikeres feldolgozás után).

## Tokentakarékos használat (ez a lényeg)

**A teljes Markdownt soha ne olvasd be egyben.** A feldolgozás csak rövid összefoglalót ír a képernyőre (oldalszám, szószám, a címsorok első 12 sora). Utána csak azt kérd le, ami a feladathoz kell:

```
python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py                         # új PDF-ek feldolgozása
python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py --lista                 # mi van feldolgozva
python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py --vazlat <név>          # címsorok oldalszámmal
python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py --kereses <név> "<regex>" [--max 20]   # találatok: oldal + sor
python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py --olvas <név> --oldalak 3-5 [--max-karakter 6000]
```

Ajánlott sorrend: **vázlat -> keresés -> a releváns oldalak olvasása**. A `--olvas` kimenete alapból 6000 karakterre van vágva, és kiírja, hogyan folytatható. A név lehet a fájlnév eleje is, ha egyértelmű.

## Szabályok ehhez a skillhez

1. A PDF-ből csak azt idézd és összegezd, amit a script kimenete vagy a `--olvas` / `--kereses` adott. **Ne állíts a PDF tartalmáról olyat, amit nem olvastál el** (ne következtess a címsorokból a tartalomra).
2. Szám, dátum, összeg PDF-ből csak a pontos szövegrészlet alapján idézhető; ne számolj vele fejben, használj scriptet.
3. A script **nem értelmez képet, ábrát, bonyolult táblázatot** (a szöveg csak a szövegrétegből jön), és **nem végez OCR-t**. Szkennelt PDF-nél a script hibával megáll, és a fájl az `input/pdf/`-ben marad. Ezt mondd ki; ne találgasd a tartalmat.
4. Ha a `pdftotext` nincs meg, a script megáll. **Ne telepíts csomagot** a felhasználó kérése nélkül; kérdezd meg, engedélyezi-e (pl. egy Python PDF-könyvtárat).
5. A PDF-ek személyes adatot is tartalmazhatnak (számla, bevallás): a `data/pdf/` és `archive/pdf/` nincs verziókezelve; a tartalom nem kerül `.claude/memory/`-ba és külső szolgáltatásba.
6. Archivált PDF-et törölni csak a felhasználó kérésére szabad.
