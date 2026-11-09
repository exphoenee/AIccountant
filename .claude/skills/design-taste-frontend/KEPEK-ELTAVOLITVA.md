# Képek eltávolítva

A repó üzemeltetője kérésére ebből a skillből az **összes rasztergrafikus képfájl** (JPG, PNG, WebP: fényképek, renderek, demóképek, kb. 27 MB, 151 fájl) törölve lett. Az indok: a fényképek külön licencűek (Unsplash License, Wikimedia Commons CC0/CC BY/CC BY-SA), ezért a repó MIT licencével nem terjeszthetők egységesen (lásd a `LICENCE.md` fájlt).

- A vektoros **SVG-ikonok** és a skill kódja, szövege, scriptjei megmaradtak.
- Az `assets/photos/photos.json` (a fényképek leírása és licencadata) megmaradt dokumentációnak; a hivatkozott képfájlok nincsenek meg, ezért a skill fényképekre építő részei (pl. `scripts/photos.mjs`, az `fx-photo` komponens) képek nélkül nem működnek.
- A repó adóreportja (`adoreport`) nem használ ebből a skillből képet.
- Visszaállítás: a törölt fájlok a git előzményben megvannak (`git checkout -- .claude/skills/design-taste-frontend/assets`).
