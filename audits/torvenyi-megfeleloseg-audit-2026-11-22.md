# Törvényi megfelelőségi audit: felülvizsgálat (2026-11-22)

**Alap:** `audits/torvenyi-megfeleloseg-audit-2026-11-08.md`. **Hatókör:** csak az, ami a 2026-11-08-i audit óta változhatott vagy nyitott volt (a letöltött mellékletek, az Art., az Áfa tv., a szabályfájlok, a tesztek). A 2026-11-08-i audit 1. táblázatának azon sorait (pl. 13–21.), amelyekre ez a felülvizsgálat nem tér ki, **nem olvastam újra**; azok állapota változatlan az eredeti audit szerint.

> Nem adótanácsadás. Döntési és jogértelmezési kérdésben a könyvelő vagy a NAV az illetékes.

## Mi változott a 2026-11-08-i audit óta

- A mellékletek tartalmát (Szja tv. 1., 4., 8., 10.; Áfa tv. 4/A.; Art. 50. §) **elolvastam**, amit az eredeti audit „Frissítés” szakasza még a következő lépésként jelölt. Lásd az 1. fejezetet.
- A szabályfájlok kaptak „Törvényi helyek” szakaszokat (`atalanyado.md`, `hataridok.md`, `afa.md`), és új szabályfájlok készültek (`kedvezmenyek.md`, `kamarai-hozzajarulas.md`, `szamlazas.md`, `bevetel-nyilvantartas.md`).
- Új számítások kerültek a repóba: kedvezmények (`kedvezmenyek.py`), számlamegfelelőség (`szamla_ellenorzes.py`), kamarai hozzájárulás. A lenti tesztek lefutottak.
- A forrásállapot **változatlan**: a törvények letöltése 2026-11-08 (`.forras.json`), azóta nem töltöttem le újat.

## 1. Korábban nyitott pontok: újraértékelés

Minden idézet a `torvenytar/docs/.../*.jogtar.txt` fájlból való, a sorszámot a fájlban ellenőriztem.

| Pont (eredeti audit) | Törvényi hely, amit most elolvastam | Új állapot |
|---|---|---|
| 5. sor: adómentes jövedelemrész = éves minimálbér fele | Szja tv. 1. sz. melléklet **4.48.**: „az átalányadózást alkalmazó egyéni vállalkozó e tevékenységéből származó jövedelmének az éves minimálbér felét meg nem haladó rész” | 🟡 → ✅. Az év közbeni kezdésnél való nem-arányosítás továbbra is csak NAV-állítás (🟡). |
| 8. sor: előleg csak a keret feletti rész után | Szja tv. 47. § (4a) | ✅ (változatlan, a szöveg egyezik) |
| 9., 22. sor: negyedéves előleg és bevallás határideje (12.) | Szja tv. 8. sz. melléklet **9.** („Az átalányadó-előleget a negyedévet követő hó 12. napjáig kell megfizetni”); Art. **50. § (1a)** (a Tbj. 6. § (1) d) szerinti egyéni vállalkozó a tárgynegyedévet követő hónap tizenkettedik napjáig tesz bevallást) | 🟡 → ✅ a 12-e, ha a vállalkozó a Tbj. 6. § (1) d) szerinti egyéni vállalkozó (ezt a repó a profilból veszi, **nem ellenőriztem**). A május 20. és 31., valamint a kamarai határidő forrása a korábbi szerint. |
| 11. sor: bevételek nyilvántartása | Szja tv. 51. § (3) (pénztárkönyv/naplófőkönyv bevételi adatai, ha az áfa-levonási jog nem érvényesül); 10. sz. melléklet I. **1.** (ellenérték vagy **előleg** mint bevétel) | ❓ → ✅ a szabály. A repó nyilvántartást generál (`bevetel_nyilvantartas.py`); ennek helyességét ez az audit nem vizsgálta. |
| 10. sor / 4. fejezet 7. pont: bevétel időpontja | Szja tv. 9. § (2) a): jóváírás napja; ha a kifizető **átutalja** az összeget, az átutalás napja a megszerzés napja (a szöveg tovább feltételez, a mondat végét nem idéztem) | ❓ **marad**: a Billingo `paid_date` eltérhet az átutalás napjától. |
| 4. fejezet 6. pont: 4. melléklet | Szja tv. 4. sz. melléklet **3.**: alanyi adómentes áfa-státusznál a fizetendő áfa a bevételt nem csökkenti, a le nem vonható áfa költségnövelő tényező | ✅. Átalányadózónál a költség nem számít, ezért ebből a repó költséget nem állít (`atalanyado.md` is ezt mondja). |
| Áfa: összesítő nyilatkozat (⛔) | Áfa tv. 4/A. sz. melléklet I. **1. e)** (37. § alá eső szolgáltatás, ahol az igénybevevő az adófizetésre kötelezett) és I. **2.** (havi/negyedéves bevallónak a következő hó **20.** napjáig) | ⛔ → ✅ a szöveg ismert. ❓ marad: a vállalkozóra, alanyi adómentesként, mikor vonatkozik. A repó nem számolja, csak tennivalóként jelzi. |
| 7. sor: **89%-os szabály** | Szja tv. 29. § (utolsó mondat) és 47. § (5): „… ha a jövedelem után a magánszemély kötelezett a szociális hozzájárulási adó megfizetésére … a megállapított jövedelem 89 százalékát kell … figyelembe venni” | ❓ **marad, változatlanul a legnagyobb nyitott kockázat.** A mellékletek nem oldják fel. A repó és a NAV számpéldája nem alkalmazza. Könyvelő / NAV. |
| 16. sor: minimálbér vs. garantált bérminimum | nem volt új forrás | ❓ marad |
| 12. sor, 19. sor, 21. sor, nevező (365) | nem volt új forrás | ❓ marad |

## 2. Technikai ellenőrzések (ma lefuttatva)

| Ellenőrzés | Eredmény |
|---|---|
| `nav-forrasok --ellenoriz` (szabályfájlok törvényhivatkozásai) | 53 hivatkozás megtalálva, 0 hiányzik. **Csak a szakasz meglétét ellenőrzi**, a tartalmi egyezést nem; a fenti 1. fejezet pontjainál ezt kézzel pótoltam. |
| `teszt_nav_peldak.py` | minden teszt megfelelt |
| `teszt_kedvezmenyek.py` | minden teszt megfelelt |
| `teszt_szamla_ellenorzes.py` | minden teszt megfelelt |
| `teszt_keresztvalidalas.py` | **KIHAGYVA**: nincs vállalkozói azonosító vagy feldolgozott Billingo-számla ezen a gépen, ezért ezt nem tudom igazolni |

## 3. Új észrevételek

1. **A források kora:** a törvényszövegek 2026-11-08-iak. Hogy azóta módosult-e valamelyik (az Szja tv. és az Áfa tv. hatálya 2026.XII.31-ig tart, a Tbj. 2027.XII.31-ig), **nem ellenőriztem**; újraletöltés nélkül nem állítható. A `nav-forrasok` skill futtatásával újraellenőrizhető.
2. **Hibás hivatkozás a szabályfájlban:** az `atalanyado.md` „Még mindig nyitott” bekezdése a `config/konyvelo-dontesek.json` fájlra és egy `plans/` terv B fázisára hivatkozik. Ezek a repóban nem léteznek (`config/` tartalma: `iratrend.json`, `szabalyok.example.json`, `szabalyok_2026.json`, `vallalkozas.example.json`; nincs `plans/` mappa, és a terv fájlja törölve lett). A `struktura.md` szerint rule-ban nem lehet nem létező mappára hivatkozni. Javasolt: a hivatkozást a `jogi_kerdesek.py` kérdéslistájára cserélni.
3. **Nem ellenőrzött jogcímek:** a családi, első házasok, személyi, 25 év alatti és anyai kedvezmények képleteit a szöveghelyekkel a `kedvezmenyek.md` adja; ebben az auditban a törvényszöveget **nem olvastam újra**, csak a tesztek lefutását igazoltam.
4. **Értelmezési kérdés a 12-e hatályánál:** az Art. 50. § (1a) a Tbj. 6. § (1) d) szerinti, foglalkoztatónak nem minősülő egyéni vállalkozóra szól. Hogy a vállalkozó ide tartozik-e, a profilból jön, nem törvényből ellenőrzött.

## 4. Összegzés

- **Lezárt vagy javult:** adómentes jövedelemrész törvényi helye, bevétel-nyilvántartás szabálya, előleg- és bevallási határidők (12.), 4. melléklet, összesítő nyilatkozat szövege.
- **Nem változott, könyvelőhöz/NAV-hoz való:** 89%-os szabály, garantált bérminimum vs. minimálbér, időarányosítás nevezője, devizás árfolyam alkalmazhatósága, bevétel időpontja kifizetői átutalásnál, tételes IPA bejelentése, szünetelés hatása a járulékra, összesítő nyilatkozat vonatkozása a vállalkozóra.
- **Teendő a repóban:** az `atalanyado.md` nem létező hivatkozásainak javítása; a törvényszövegek frissességének ellenőrzése.
- **Nem vizsgáltam:** az eredeti audit 13–21. sorát és a report-elemek tartalmi helyességét újra; a `teszt_keresztvalidalas.py` a saját adatok hiányában nem futott.
