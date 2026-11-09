# Az összevont adóalapot csökkentő kedvezmények (átalányadózó egyéni vállalkozó)

> Forrás: Szja tv. 29/A.–29/H. § (`torvenytar/docs/szja-tv/2026/1995-evi-cxvii-torveny.jogtar.txt`, hatály 2026.X.1.), 2025. évi XIII. tv. (30 év alatti anyák), 2025. évi XIV. tv. (két gyermeket nevelő anyák), 2025. évi XV. tv. (három gyermeket nevelő anyák) (`torvenytar/docs/2025-xiii-tv`, `2025-xiv-tv`, `2025-xv-tv`). Végrehajtás: `.claude/skills/adoszamitas/scripts/kedvezmenyek.py` (önteszt: `teszt_kedvezmenyek.py`).

## Mit számol a script (a szövegből igazolt képletek)

| Jogcím | Kedvezmény összege | Törvényi hely |
|---|---|---|
| **Családi kedvezmény** | kedvezményezett eltartottanként és jogosultsági hónaponként: 1 eltartott esetén 133 340 Ft, 2 esetén 266 660 Ft, 3 és minden további esetén 440 000 Ft (az eltartottak lélekszáma szerinti sáv, a kedvezményezett eltartottak mindegyikére); tartósan beteg/súlyosan fogyatékos kedvezményezett eltartottanként +133 340 Ft/hó | Szja tv. 29/A. § (2), (2a), (4), (5) |
| Családi kedvezmény megosztása / közös igénybevétele | a házastársak/jogosultak döntése szerint: a script a `sajat_resz` hányadot veszi (a döntést te adod meg, a nyilatkozat az adóbevallásban kell) | Szja tv. 29/B. § (1a)–(1d) |
| Családi járulékkedvezménnyel való összekapcsolás | az együttesen igénybe vett családi járulékkedvezmény az adókulccsal elosztott része csökkenti a családi kedvezményt (a törvény zárójelben 667%-ot ír) | Szja tv. 29/B. § (6) |
| **Első házasok kedvezménye** | 33 335 Ft/hó (a házastársak együtt), legfeljebb 24 hónap, a házasságkötést követő hónaptól | Szja tv. 29/C. § (3)–(5) |
| **Személyi kedvezmény** (súlyosan fogyatékos) | jogosultsági hónaponként a minimálbér egyharmada, 100 Ft-ra kerekítve | Szja tv. 29/E. § (3), (4) |
| **25 év alatti fiatalok kedvezménye** | az átalányban megállapított jövedelem jogosultsági hónapokkal arányos része, legfeljebb jogosultsági hónapok × a tárgyévet megelőző év júliusára közzétett nemzetgazdasági bruttó átlagkereset | Szja tv. 29/F. § (2), (3), (4) |
| **Négy vagy több gyermeket nevelő anyák** | az átalányban megállapított jövedelem jogosultsági hónapokkal arányos része | Szja tv. 29/D. § (2), (5) |
| **Három / két gyermeket nevelő anyák** | ugyanez | 2025. évi XV. tv. 1. § (2), (6); 2025. évi XIV. tv. 1. § (2), (6) |
| **30 év alatti anyák** | ugyanez | 2025. évi XIII. tv. 1. § (3)–(5) |

- **Sorrend és korlát:** Szja tv. 29/H. § (1): 30 év alatti anyák, négy+/három/két gyermekes anyák, (csecsemőgondozási stb. díj kedvezménye: nincs implementálva), 25 év alattiak, személyi, első házasok, családi. Minden kedvezmény csak az éppen megmaradt adóalapig érvényesíthető; a fel nem használt rész a kimenetben külön szerepel (a repó nem viszi tovább).
- **Az anyai jogcímek közül egy választható** (négy+/három/két gyermek): Szja tv. 29/H. § (2). Több megadásánál a script megáll (NEM SZÁMOLHATÓ), a választás a tiéd.
- **Az adóalap:** az átalányos jövedelem az éves minimálbér felét meg nem haladó, adómentes része nélkül (Szja tv. 1. számú melléklet 4.48.). A kedvezmény ebből vonódik le, az eredmény × 15% a kedvezményes éves szja.

## Amit a script NEM csinál (kimondva)

- **Nem ellenőrzi a jogosultságot** (családi pótlék, házasság, életkor, igazolások), csak a megadott hónapokkal számol; az adóbevalláshoz tett nyilatkozat (Szja tv. 29/B. § (2), 29/C. § (6), 29/D. § (6), 2025. évi XIII–XV. tv. nyilatkozati szabályai) a te feladatod.
- **A negyedéves előleg és a tbj/szocho nem változik.** A kedvezmény az éves adóra vonatkozik. Az előleg csökkentésére az Szja tv. 48. §-a a munkáltatónak/kifizetőnek tett adóelőleg-nyilatkozatot ír elő; hogy az átalányadózó saját negyedéves előlegére mi vonatkozik, **nem ellenőrzött**.
- **Családi járulékkedvezmény** (Tbj. 79–80. §): számítása nincs implementálva (csak a 29/B. § (6) szerinti csökkentés, ha megadod az igénybe vett összeget).
- **Csecsemőgondozási díj, gyermekgondozási díj, örökbefogadói díj kedvezménye** (29/H. § (1) c)): nincs implementálva.
- **A 25 év alatti kedvezmény plafonja** a KSH bruttó átlagkeresetét igényli (`brutto_atlagkereset_elozo_julius` a `config/szabalyok_<év>.json`-ban); az értéket **te adod meg** a KSH közleményéből, a repó nem találja ki. Amíg `null`, ez a jogcím NEM SZÁMOLHATÓ.
- **Az adóalap a 89%-os kérdésen áll** (Szja tv. 29. §, 47. § (5)): ha az alkalmazandó, az adóalap és így a kedvezmény hatása más. Nyitott kérdés (`atalanyado.md`).

## Bemenet: `config/vallalkozas.json` → `kedvezmenyek`

Minta: `python -I .claude/skills/adoszamitas/scripts/kedvezmenyek.py --pelda`. Csak a jogosult jogcímeket kell megadni (`nincs: true`, ha egyik sem jár). Jogcímenként a jogosultsági hónapok (1–12), a családi kedvezménynél az eltartottak száma is. Az igen/nem jelzés önmagában nem elég: a script NEM SZÁMOLHATÓ-t ír.
