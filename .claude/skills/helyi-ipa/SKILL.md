---
name: helyi-ipa
description: A helyi iparűzési adó (IPA) szabályainak beszerzése és az adó kiszámítása az illetékes önkormányzatra (a vállalkozói profilban megadott település): adókulcs a helyi rendeletből, tételes vagy hagyományos adóalap, éves adó, határidők. Használd, ha az iparűzési adóról, annak mértékéről, határidejéről vagy a bevallásról kérdeznek, vagy ha az IPA-hely (ipa_telepules) új.
---

# Helyi iparűzési adó (IPA)

**Kötelező szabályok:** [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md) és [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md). Előbb olvasd el őket.

## Bemenet

Az **illetékességi település** (`ipa_telepules` a `config/vallalkozas.json`-ban) a `vallalkozas-dokumentumok` skill kimenete: az kérdezi meg a felhasználót (`--ipa-javaslat`, `--ipa-beallit`). Ha a település üres, ez a skill nem számol; küldd vissza a vállalkozói profil lépéshez. Több telephely esetén (`ipa_telephelyek`) az adóalapot települések között fel kell osztani; ezt a script nem találgatja, a felosztást a felhasználótól kell kérni.

## Menete

1. `ipa.py --allapot`: mi hiányzik (település, adózás módja, kulcs).
2. **Adózás módja: KÖTELEZŐ KÉRDÉS.** Ha `ipa_adozasi_mod` üres, mindig kérdezd meg a felhasználót (AskUserQuestion), és addig ne számolj. Kérdezd meg: *tételes* (Htv. 39/A. §: 25 millió Ft bevételig, sávos adóalap) vagy *hagyományos* (nettó árbevétel, 39. § szerinti csökkentő tételekkel). Rögzítés: `ipa.py --mod tetelesen|hagyomanyos`. A tételes adózás választását az adóhatóságnak be kell jelenteni (39/A. § (4)); ezt a script nem tudja ellenőrizni.
3. **Az önkormányzati szabály beszerzése:** a település helyi iparűzési adó rendeletét keresd meg (WebSearch/WebFetch; az önkormányzat honlapja vagy a Nemzeti Jogszabálytár / önkormányzati rendeletek), az **adóévre hatályos mértéket** olvasd ki (nem memóriából!), és az eredeti szöveget a `nav-forrasok` skill szerint `torvenytar/docs/<település>-ipa-rendelet/<év>/` alá mentsd módosítás nélkül. Mentességet/kedvezményt (Htv. 39/C.) is keress. Rögzítés: `ipa.py --rogzit <település> --kulcs 0.0X --forras <URL vagy torvenytar útvonal> --ev 2026`. A script 2% fölötti kulcsot elutasít (Htv. 40. § c)), és forrás nélkül nem rögzít.
4. `ipa.py --szamol --ev 2026 [--arbevetel N]`: éves IPA és határidők. Eredmény: `data/ipa/ipa_<év>.json`.

## Ellenőrzött, a törvényből idézett szabályok (`torvenytar/docs/htv/2026/1990-evi-c-torveny.txt`)

- **40. §:** a mérték felső határa 2000-től az adóalap 2%-a; a tényleges mértéket az önkormányzat rendelete adja.
- **39/A. § (1)-(3):** tételes adóalap: bevétel ≤ 12 millió Ft: 2,5 millió Ft; ≤ 18 millió Ft: 6 millió Ft; ≤ 25 millió Ft: 8,5 millió Ft; magánszemélynél a bevétel az szja szerinti bevétel; 12 hónapnál rövidebb adóévnél a határok és az adóalap napi arányosítással időarányos; önkormányzatonként (székhely/telephely) alkalmazandó; a választás a teljes adóévre szól.
- **39/A. § (4):** a választás bejelentése az előző évi bevallási nyomtatványon az adóév 5. hónapjának utolsó napjáig; új tevékenységnél a bejelentkezési nyomtatványon.
- **39/A. § (7), (9):** tételes adózónál az adóév 5. hónapjának utolsó napjáig előleg az előző év adója összegében; az adót az adóévet követő év 5. hónapjának utolsó napjáig kell megfizetni.

## Szabályok ehhez a skillhez

1. A számítás a script dolga; az AI nem számol. A kulcs csak forrással rögzíthető; **a kulcsot nem találgatjuk, nem emlékezetből mondjuk.**
2. A script a megadott adatokból pontosan számol, de a kimenetében felsorolt pontok **nem ellenőrzöttek** (kerekítés, 365 nevező, szünetelés napjainak kezelése, helyi kedvezmény, bejelentés). Ezeket a válaszban is jelezd, és bizonytalan esetben: könyvelő vagy az önkormányzati adóhatóság.
3. Az IPA nem azonos az szja-val, a tbj-vel és a szochóval; a bevallás a NAV-hoz megy, a fizetés az önkormányzat adóbeszedési számlájára.
4. Az `adoellenorzes` az IPA-határidőket az adónaptárból ellenőrzi; ez a skill adja hozzá a számított összeget. Személyes azonosítót ne írj ki.

## Jogi forrás ehhez a skillhez

A hivatkozott törvényhelyek (Htv. 39/A. §, 40. §) a `torvenytar/` letöltött szövegében vannak (a mellékletek a `*.jogtar.txt`-ben); a hivatkozások meglétét a `nav-forrasok` skill `--ellenoriz` parancsa ellenőrzi. Ha a szabályfájl és a törvényszöveg eltér, a törvényszöveg az irányadó, az eltérést jelezni kell. Nyitott jogi kérdés: `adoszamitas/scripts/jogi_kerdesek.py --lista`; döntés nélkül a könyvelő/NAV dönt.
